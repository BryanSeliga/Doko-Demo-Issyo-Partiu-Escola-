"""Reconstroi um .KSC com textos trocados, corrigindo todos os enderecos de codigo.

Layout do arquivo:
  0x00 'KSC\\0', versao, u32 entrada, u32 inicio_pool, u32 tam_pool, u16 x2, u16 x2
  0x1C codigo | stub de entrada | pool de strings | tabela de valores marcados

Enderecos de codigo sao relativos a 0x1C. Strings do pool sao relativas ao inicio do pool
e podem ficar em qualquer lugar depois dele, entao as novas vao para o fim do arquivo.
"""
import struct

from kscdis import CODE_BASE, STR_OPS, decode

# (opcode, deslocamento do operando u24 dentro da instrucao)
CODE_REFS = {0x10: 1, 0x11: 1, 0x12: 1, 0x21: 1, 0x20: 2, 0x28: 2, 0x8A: 1, 0x15: 1, 0x18: 1}
STRING_REF_OP = 0x88


def u24(d, i):
    return int.from_bytes(d[i:i + 3], "little")


def layout(d):
    entry, pool, pool_size = struct.unpack_from("<3I", d, 8)
    return {
        "entry": CODE_BASE + entry,
        "pool": CODE_BASE + pool,
        "table": CODE_BASE + pool + pool_size,
    }


def extract_inline(d):
    """Lista (indice_da_instrucao, opcode, bytes_da_string) dos textos embutidos."""
    ins, end = decode(d)
    return [(n, x[1], d[x[0] + 1:x[0] + x[2] - 1]) for n, x in enumerate(ins) if x[1] in STR_OPS]


def extract_pool(d):
    """Mapa offset->bytes das strings do pool realmente referenciadas (op 88 e tag 5)."""
    lay = layout(d)
    ins, _ = decode(d)
    refs = {u24(d, x[0] + 1) for x in ins if x[1] == STRING_REF_OP}
    n = (len(d) - lay["table"]) // 4
    table = struct.unpack_from(f"<{n}I", d, lay["table"])
    refs |= {v & 0xFFFFFFF for v in table if v >> 28 == 5}
    out = {}
    for off in sorted(refs):
        p = lay["pool"] + off
        out[off] = d[p:d.index(b"\0", p)]
    return out


def pool_uses(d):
    """Mapa offset->conjunto de usos de cada string do pool referenciada no codigo.
    "opcao": argumento do menu de opcoes (chamada 8b 21 NN, NN = numero de opcoes);
    "var": guardada numa variavel (op 84), que depois entra no meio de uma fala;
    "destino": campo de um destino do passeio (vai para as falas); "placa": texto de placa do cenario;
    "tabela": outro valor da tabela (itens, diario...); "outro": o resto."""
    ins, _ = decode(d)
    uses = {}
    for n, x in enumerate(ins):
        if x[1] != STRING_REF_OP:
            continue
        k = n + 1
        # as outras opcoes podem vir antes, como string embutida
        while k < len(ins) and ins[k][1] in (STRING_REF_OP, 0x49, 0x4A, 0x8E):
            k += 1
        o, op = ins[k][0], ins[k][1]
        use = "opcao" if op == 0x8B and d[o + 1] == 0x21 else "var" if op == 0x84 else "outro"
        uses.setdefault(u24(d, x[0] + 1), set()).add(use)
    lay = layout(d)
    n = (len(d) - lay["table"]) // 4
    t = struct.unpack_from(f"<{n}I", d, lay["table"])
    # destinos do passeio: lista de 9 valores (2, b, 0 ou b, lugar, ponto, descricao, 1, acao, pergunta)
    dest = set()
    for k in range(n - 10):
        if t[k] == (9 << 28) | 9 and (t[k + 1] >> 28, t[k + 2] >> 28) == (2, 0xB) and (t[k + 3] == 0 or t[k + 3] >> 28 == 0xB):
            dest.update(k + 1 + j for j in range(9))
    # placas, faixas e dirigiveis do cenario: registro que termina em (2:0, 2:6, 2:20, 2:3, 2:5, 2:N),
    # seguido das listas com os textos possiveis, ate o proximo registro (9:N, 2:0)
    sign = set()
    pairs = [(v >> 28, v & 0xFFFFFFF) for v in t]
    k = 0
    while k < n - 6:
        if pairs[k:k + 5] != [(2, 0), (2, 6), (2, 0x20), (2, 3), (2, 5)]:
            k += 1
            continue
        k += 6
        while k < n and not (pairs[k][0] == 9 and k + 1 < n and pairs[k + 1] == (2, 0)):
            sign.add(k)
            k += 1
    for k, v in enumerate(t):
        if v >> 28 == 5:
            use = "destino" if k in dest else "placa" if k in sign else "tabela"
            uses.setdefault(v & 0xFFFFFFF, set()).add(use)
    return uses


def rebuild(d, inline=None, pool=None):
    """inline: {indice_instrucao: bytes}; pool: {offset: bytes}. Sem trocas devolve o arquivo identico."""
    inline = inline or {}
    pool = pool or {}
    lay = layout(d)
    ins, end = decode(d)
    # 1) novo layout do codigo: mapa endereco antigo -> novo (relativo a CODE_BASE)
    newoff = {}
    pos = CODE_BASE
    for n, (off, op, length) in enumerate(ins):
        newoff[off] = pos
        pos += len(inline[n]) + 2 if n in inline else length
    delta_end = pos - end
    newoff[end] = pos

    def reloc(old):
        return newoff[old + CODE_BASE] - CODE_BASE

    # 2) emite o codigo
    code = bytearray()
    for n, (off, op, length) in enumerate(ins):
        if n in inline:
            code += bytes([op]) + inline[n] + b"\0"
            continue
        raw = bytearray(d[off:off + length])
        if op in CODE_REFS:
            at = CODE_REFS[op]
            raw[at:at + 3] = reloc(u24(d, off + at)).to_bytes(3, "little")
        elif op == -1:  # cabecalho de case: u32 valor, u24 proximo cabecalho
            raw[4:7] = reloc(u24(d, off + 4)).to_bytes(3, "little")
        code += raw
    # 3) stub de entrada: 30 02 90 00 00 20 01 <call> 21 <goto> 38 00...
    stub = bytearray(d[lay["entry"]:lay["pool"]])
    assert stub[5] == 0x20 and stub[10] == 0x21, stub.hex()
    stub[7:10] = reloc(u24(stub, 7)).to_bytes(3, "little")
    stub[11:14] = reloc(u24(stub, 11)).to_bytes(3, "little")
    # O pool e a tabela sao lidos em palavras de 4 bytes: no PSP real, endereco desalinhado trava o jogo
    # (o PPSSPP nao reclama). O original completa o stub com zeros ate alinhar; aqui tambem.
    assert stub[14] == 0x38 and not any(stub[15:]), stub.hex()
    stub = stub[:16]
    stub += b"\0" * ((-(CODE_BASE + len(code) + len(stub))) % 4)
    # 4) tabela de valores: enderecos de codigo (tag 7) e strings trocadas (tag 5)
    n = (len(d) - lay["table"]) // 4
    table = list(struct.unpack_from(f"<{n}I", d, lay["table"]))
    tail = d[lay["table"] + n * 4:]
    extra = bytearray()
    pool_bytes = d[lay["pool"]:lay["table"]]
    new_pool_ref = {}
    # strings novas ficam depois da tabela; o offset e relativo ao inicio do pool
    base_extra = len(pool_bytes) + n * 4 + len(tail)
    for off, s in pool.items():
        if s == extract_cstr(d, lay["pool"] + off):
            continue
        new_pool_ref[off] = base_extra + len(extra)
        extra += s + b"\0"
    for i, v in enumerate(table):
        tag = v >> 28
        if tag == 7:
            table[i] = (7 << 28) | reloc(v & 0xFFFFFFF)
        elif tag == 5 and (v & 0xFFFFFFF) in new_pool_ref:
            table[i] = (5 << 28) | new_pool_ref[v & 0xFFFFFFF]
    # 5) referencias de pool no codigo (op 88): offsets mudam so se a string foi trocada
    if new_pool_ref:
        for n2, (off, op, length) in enumerate(ins):
            if op == STRING_REF_OP:
                old = u24(d, off + 1)
                if old in new_pool_ref:
                    code[newoff[off] - CODE_BASE + 1:newoff[off] - CODE_BASE + 4] = new_pool_ref[old].to_bytes(3, "little")
    # 6) cabecalho
    head = bytearray(d[:CODE_BASE])
    entry_rel = len(code)
    pool_rel = entry_rel + len(stub)
    struct.pack_into("<2I", head, 8, entry_rel, pool_rel)
    out = bytes(head) + bytes(code) + bytes(stub) + pool_bytes + struct.pack(f"<{n}I", *table) + tail + bytes(extra)
    pad = (-len(out)) % 4
    return out + b"\0" * pad


def extract_cstr(d, p):
    return d[p:d.index(b"\0", p)]
