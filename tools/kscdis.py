"""Decodificador linear do bytecode KSC do Let's Gakkou (UCJS10039).

Tamanhos tirados dos tratadores do VM no BOOT (laco em 0x4DAA0; contexto: base em 0(ctx), pc em 4(ctx),
ctx em 0x10 do VM). Enderecos de codigo sao relativos a CODE_BASE (0x1C); offsets de pool sao relativos
ao inicio do pool (0x480 do VM = base + u32 em 0x0C do arquivo).

Leitores de operando que avancam o pc:
  0x5472C  u24 (pc += 3)                        ops 88, a1, 8a
  0x547B0  u32 (pc += 4)                        cabecalhos de case do op 13
  0x4D5DC  u16, u8 f, u16 se f != 0             ops 24, 25 (chamada de funcao do script)
  0x48938  string-modelo ate 00; 14/15/17/1b levam u16; 1d sozinho   ops 48, 49, 4a, 8e
Os outros ajudantes (0x546F0, 0x547F0, 0x54834, 0x5486C, 0x5BFFC, 0x3B89C, 0x5B1E4, 0x3BB3C, 0x4827C,
0x48758, 0x4D3F4 depois do u16, 0x49258 depois dos 2 u8 ...) so mexem na pilha/valores.
Opcodes sem tratador proprio caem no fim do laco (0x53EC4): no-op de 1 byte.
Nomes dos tipos de alvo (goto, call...) sao so rotulos; o que importa para o montador e onde fica o u24.
Pool: [bytes][00][1 byte extra] para strings; o op a1 e a tag 0xE da tabela apontam para blobs binarios
(padroes compilados, com zeros no meio), por isso pool_entries usa os pontos referenciados como ancoras.
"""
import struct

CODE_BASE = 0x1C
NUL = bytes(1)

# ---- tamanho total da instrucao (opcode incluido) para os opcodes de tamanho fixo ----
LEN = {}
for _op in (0x04, 0x22, 0x30, 0x80, 0xA0, 0xA2):
    LEN[_op] = 2                                   # u8
for _op in (0x71, 0x72, 0x73, 0x75, 0x81, 0x90, 0x91, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99):
    LEN[_op] = 3                                   # u16
LEN[0x8B] = 3                                      # u8 funcao nativa, u8 n_args
for _op in (0x10, 0x11, 0x12, 0x14, 0x15, 0x18, 0x1B, 0x21, 0x29, 0x82, 0x88, 0x8A, 0xA1, 0x4B, 0x4C, 0x4D):
    LEN[_op] = 4                                   # u24
LEN[0x2F] = 4                                      # u8 escopo, u16 indice
for _op in (0x20, 0x28):
    LEN[_op] = 5                                   # u8 n_args, u24 alvo
LEN[0x2E] = 5                                      # u8 escopo, u16 indice, u8 n_args
LEN[0x4E] = 5                                      # u16, u16
LEN[0x83] = 5                                      # u32
LEN[0x2D] = 7                                      # u8 escopo, u16 indice, u24 alvo
LEN[0x2C] = 8                                      # u8 escopo, u16 indice, u8 n_args, u24 alvo

# opcodes de 1 byte: 01/02/03 tem caso proprio no despachante que so volta ao laco (no-op); 07 cai no fim do
# laco tambem (0x53EC8). Os demais tem tratador que nao le operandos.
VALID0 = {int(x, 16) for x in """01 02 03 07 05 0b 0c 0d 0e 0f 13 16 17 19 1c 1d 1e 1f 23 31 32 37 38 3a 3b 40 41 43 44 47 4f
    50 51 52 53 54 55 56 57 5a 5b 5c 5d 5e 5f 60 61 62 63 64 65 66 67 68 69 6a 6b 6c 6d 70 78 7e 7f
    84 85 86 87 89 8c 8d 8f 9a b0 b1 b2 b3 b4 b8 b9 ba bb bc bd c0 c1 c2 c3 c4 c5 c8 c9 d0 d1 d2 d4 d5 d6 d7
    e0 e1 e2 e3 f0 f1 f4 f5 f8 f9 fc fd ff""".split()}
STR_OPS = (0x48, 0x49, 0x4A, 0x8E)                 # string-modelo embutida no codigo
TMPL_U16 = (0x14, 0x15, 0x17, 0x1B)                # variaveis da string-modelo seguidas de u16
TMPL_BARE = (0x1D,)                                # variavel sem operando (valor vem da pilha)
VAR_OPS = (0x24, 0x25, 0xF6, 0xF7)                 # tamanho depende de um byte de flag
VALID = VALID0 | set(LEN) | set(STR_OPS) | set(VAR_OPS)

# ---- operandos que apontam para strings do pool: opcode -> (deslocamento do operando, tamanho) ----
# u24 little-endian, relativo ao inicio do pool (o VM soma com 0x480 do contexto = base + u32@0x0C).
#   88 empurra a string (valor marcado tag 5); a1 empurra valor tag 0xE com o mesmo ponteiro;
#   4b copia a string para o buffer de fala (0x78 do VM); 4c/4d passam a string para 0x125B0.
POOL_REF_OPS = {0x88: (1, 3), 0xA1: (1, 3), 0x4B: (1, 3), 0x4C: (1, 3), 0x4D: (1, 3)}

# ---- operandos que sao enderecos de codigo: opcode -> (deslocamento, tipo) ; todos u24 relativos a CODE_BASE
CODE_REF_OPS = {
    0x10: (1, "goto"), 0x11: (1, "jump_if_false"), 0x12: (1, "jump_if_true"),
    0x14: (1, "iter_begin"), 0x15: (1, "iter_next"), 0x18: (1, "loop_test"),
    0x1B: (1, "handler"),        # empurrado como int; os ops 1c/1e depois poem esse valor no pc
    0x21: (1, "call"), 0x20: (2, "call"), 0x28: (2, "spawn"), 0x29: (1, "spawn"),
    0x8A: (1, "push_addr"),      # empurra valor tag 7 (endereco de codigo)
    0x2D: (4, "def_func"), 0x2C: (5, "def_func"),   # guardam tag 7 numa variavel (nao aparecem nos scripts)
}
CASE = -1        # cabecalho de case: u32 valor (tag != 0), u24 proximo cabecalho
CASE_END = -2    # fim da lista de cases: u32 com tag 0


def u16(d, i):
    return d[i] | d[i + 1] << 8


def u24(d, i):
    return d[i] | d[i + 1] << 8 | d[i + 2] << 16


def u32(d, i):
    return struct.unpack_from("<I", d, i)[0]


def code_end(d):
    """Inicio do stub de entrada = fim do codigo."""
    return CODE_BASE + u32(d, 8)


def tmpl_end(d, i):
    """Fim (exclusivo) da string-modelo que comeca em i (helper 0x48938)."""
    while True:
        c = d[i]
        i += 1
        if c == 0:
            return i
        if c in TMPL_U16:
            i += 2


def callspec_end(d, i):
    """Chamada de funcao do script (helper 0x4D5DC): u16 indice, u8 escopo, u16 se escopo != 0."""
    return i + 3 if d[i + 2] == 0 else i + 5


def insn_len(d, i):
    """Tamanho da instrucao em i (None = opcode sem tratador). Nao trata cabecalhos de case."""
    op = d[i]
    if op in LEN:
        return LEN[op]
    if op in STR_OPS:
        return tmpl_end(d, i + 1) - i
    if op == 0x25:
        return callspec_end(d, i + 1) - i
    if op == 0x24:
        return callspec_end(d, i + 2) - i
    if op in (0xF6, 0xF7):
        return 2 if d[i + 1] == 0 else 4
    if op in VALID0:
        return 1
    return None


def orphan_chain(d, p, end, switch_end):
    """Cabecalhos de case inalcancaveis: quando o 'default' vem antes dos outros cases, o compilador poe o
    terminador (u32 tag 0) logo depois do op 13 e os cases seguintes ficam encadeados depois do corpo do
    default, sem ninguem apontando para o primeiro. Aceita a cadeia em p so se ela for crescente, terminar
    num u32 com tag 0 e o terminador acabar exatamente em switch_end (alvo do goto do corpo anterior)."""
    chain = []
    while p + 4 <= end:
        v = u32(d, p)
        if v >> 28 == 0:
            chain.append(p)
            return chain if p + 4 == switch_end and len(chain) > 1 else None
        if p + 7 > end or (v >> 28) not in (2, 5):
            return None
        nxt = CODE_BASE + u24(d, p + 4)
        if not p + 7 <= nxt <= end:
            return None
        chain.append(p)
        p = nxt
    return None


def decode_ex(d, start=CODE_BASE, end=None, strict=True):
    """Devolve (lista de (offset, op, tamanho), fim_alcancado, desconhecidos).
    op = CASE / CASE_END para os cabecalhos do switch (op 13). Com strict, opcode desconhecido gera erro;
    sem strict, vira no-op de 1 byte (como no VM) e entra na lista de desconhecidos."""
    if end is None:
        end = code_end(d)
    i = start
    headers = set()
    out, unknown = [], []
    in_switch = False
    while i < end:
        if i in headers:
            if u32(d, i) >> 28 == 0:
                out.append((i, CASE_END, 4))
                i += 4
            else:
                nxt = CODE_BASE + u24(d, i + 4)
                if nxt <= i:
                    raise ValueError(f"case em {i:#x} aponta para tras ({nxt:#x})")
                headers.add(nxt)
                out.append((i, CASE, 7))
                i += 7
            continue
        op = d[i]
        n = insn_len(d, i)
        if n is None:
            if strict:
                raise ValueError(f"opcode desconhecido {op:02x} em {i:#x}")
            unknown.append(i)
            n = 1
        out.append((i, op, n))
        if op == 0x13:
            headers.add(i + 1)
            in_switch = True
        elif op == 0x10 and in_switch and i + n not in headers:
            orphans = orphan_chain(d, i + n, end, CODE_BASE + u24(d, i + 1))
            if orphans:
                headers.update(orphans)
        i += n
    return out, i, unknown


def decode(d, end=None):
    """Lista (offset, op, tamanho) cobrindo [CODE_BASE, inicio do stub) sem buracos."""
    ins, stop, _ = decode_ex(d, end=end)
    if stop != (end if end is not None else code_end(d)):
        raise ValueError(f"decodificacao passou do fim: {stop:#x}")
    return ins


def pool_refs_ex(d, ins=None):
    """{offset_do_operando: (offset_no_pool, opcode, tamanho_do_operando)}."""
    out = {}
    for off, op, n in ins if ins is not None else decode(d):
        if op in POOL_REF_OPS:
            at, size = POOL_REF_OPS[op]
            out[off + at] = (u24(d, off + at), op, size)
    return out


def pool_refs(d, ins=None):
    """{offset_do_operando_no_arquivo: offset_no_pool}. Operando u24 LE, relativo ao inicio do pool."""
    return {k: v[0] for k, v in pool_refs_ex(d, ins).items()}


def code_refs(d, ins=None, stub=True):
    """{offset_do_operando_no_arquivo: (alvo_absoluto_no_arquivo, tipo)}; todos u24 LE relativos a CODE_BASE.
    Inclui os 'proximo' dos cabecalhos de case e, com stub, os do stub de entrada."""
    ins = list(ins if ins is not None else decode(d))
    if stub:
        ins += decode_stub(d)
    out = {}
    for off, op, n in ins:
        if op in CODE_REF_OPS:
            at, kind = CODE_REF_OPS[op]
            out[off + at] = (CODE_BASE + u24(d, off + at), kind)
        elif op == CASE:
            out[off + 4] = (CODE_BASE + u24(d, off + 4), "case_next")
    return out


def decode_stub(d):
    """Instrucoes do stub de entrada (do fim do codigo ate o pool), sem os zeros de alinhamento do fim.
    O stub pode ter switch (MAIN.KSC). Bytes desconhecidos so sao aceitos se forem o enchimento final."""
    pool = CODE_BASE + u32(d, 12)
    ins, stop, unk = decode_ex(d, start=code_end(d), end=pool, strict=False)
    while ins and ins[-1][0] in unk and d[ins[-1][0]] == 0:
        unk.remove(ins.pop()[0])
    if unk or stop != pool:
        raise ValueError(f"stub de entrada invalido: desconhecidos {[hex(u) for u in unk]}, fim {stop:#x}")
    return ins


def layout(d):
    entry, pool, pool_size = struct.unpack_from("<3I", d, 8)
    return {"entry": CODE_BASE + entry, "pool": CODE_BASE + pool, "table": CODE_BASE + pool + pool_size}


def pool_anchors(d, ins=None):
    """(starts de string, starts de blob) referenciados pelo codigo e pela tabela.
    Strings: ops 88/4b/4c/4d e tag 5 da tabela. Blobs (padrao compilado, tag 0xE): op a1 e tag 0xE da tabela."""
    sref, bref = set(), set()
    for po, op, _ in pool_refs_ex(d, ins).values():
        (bref if op == 0xA1 else sref).add(po)
    for v in table_values(d):
        if v >> 28 == 5:
            sref.add(v & 0xFFFFFFF)
        elif v >> 28 == 0xE:
            bref.add(v & 0xFFFFFFF)
    return sref, bref


def pool_entries(d, ins=None):
    """Segmenta o pool em [(offset, tipo, fim)], offsets relativos ao pool, tipo 'str' ou 'blob'.
    String: [bytes][00][1 byte extra]. Blob (tag 0xE, tem zeros no meio): vai do ponto referenciado ate o
    proximo ponto referenciado (strings nao referenciadas logo depois de um blob ficam dentro dele).
    Gera ValueError se algum ponto referenciado cair no meio de uma string."""
    lay = layout(d)
    p, size = lay["pool"], lay["table"] - lay["pool"]
    sref, bref = pool_anchors(d, ins)
    anchors = sorted(sref | bref | {size})
    out = []
    i = 0
    k = 0
    while i < size:
        while anchors[k] <= i:
            k += 1
        nxt = anchors[k]
        if i in bref:
            out.append((i, "blob", nxt))
            i = nxt
            continue
        z = d.find(NUL, p + i, p + size)
        e = size if z < 0 else min(z - p + 2, size)
        if e > nxt:
            raise ValueError(f"referencia {nxt:#x} no meio da string {i:#x}..{e:#x}")
        out.append((i, "str", e))
        i = e
    return out


def pool_strings(d, ins=None):
    """Offsets (relativos ao pool) do inicio de cada string do pool (blobs fora)."""
    return [o for o, kind, _ in pool_entries(d, ins) if kind == "str"]


def table_values(d):
    lay = layout(d)
    n = (len(d) - lay["table"]) // 4
    return list(struct.unpack_from(f"<{n}I", d, lay["table"]))
