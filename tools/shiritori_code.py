"""Shiritori por letras: reescreve as tres funcoes do BOOT que os scripts chamam pelo op 8b.

  0x70  0x5A66C  a leitura vale? (so caracteres de encadear e ignoraveis, pelo menos um de encadear, ate 32 bytes)
  0x71  0x5A764  primeiro caractere de encadear, normalizado (ponteiro para 2 bytes, ou 0)
  0x72  0x5A804  ultimo caractere de encadear, normalizado (ponteiro para 2 bytes, ou 0)

No original so hiragana encadeia (o traco de vogal longa e pulado e qualquer outro caractere invalida a
leitura). Agora as letras latinas tambem: A-Z e a-z viram a maiuscula, as acentuadas do gtext (0x85xx) viram a
letra sem acento, e os outros caracteres de 1 byte (espaco, hifen, apostrofo, numeros) sao pulados. O kana
continua valendo como antes, para as palavras de saves antigos e para quem digitar em kana.

As funcoes devolvem um ponteiro para 2 bytes, que o VM entrega ao script como inteiro (b1 << 8 | b0): para uma
letra, a maiuscula ASCII seguida de 00 (0x0041 = A). O script so compara esses inteiros entre si.

Relocacoes: o BOOT e um PRX, e o carregador soma a base aos pares lui/addiu que estao na tabela de relocacao.
Os 6 pares desta regiao ficam em posicoes fixas (SITES); o codigo novo poe neles uma carga de endereco de
verdade (tabelas) ou uma carga sem efeito no registrador at. Nao ha jal: a rotina comum e chamada com bal.

Dados: a area dos textos de kana (VA 0xD51F8-0xD5340, 4 bytes por entrada, com repeticoes) e reempacotada em
2 bytes por kana diferente; os 83 ponteiros (VA 0xD5340, cada um com relocacao propria) passam a apontar para
la, e sobra lugar para a tabela de letras (26 x 2 bytes) e a dos acentos (segundo byte 0x56-0x91 -> letra).
"""
import re
import struct
import unicodedata

from gtext import ACCENTS

FILE_OFF = 0x60                      # arquivo = endereco virtual + 0x60
CODE_VA, CODE_END = 0x5A66C, 0x5A8AC
ENTRY = {"valid": 0x5A66C, "first": 0x5A764, "last": 0x5A804}
SITES = [(0x5A684, 0x5A690), (0x5A6F8, 0x5A6FC), (0x5A730, 0x5A734), (0x5A748, 0x5A74C),
         (0x5A778, 0x5A784), (0x5A818, 0x5A824)]          # (lui, parte baixa) de cada par relocado
KANA_VA, KANA_END = 0xD51F8, 0xD5340                      # textos de kana (sem relocacoes)
PTR_VA, KANA_N = 0xD5340, 83                              # ponteiros, indice = segundo byte - 0x9F
ACC_LO, ACC_N = 0x56, 0x91 - 0x56 + 1
MAX_BYTES = 32

# Caderno: a funcao 0xB2EC8 escolhe a aba pelo primeiro caractere do texto em +0x19 do registro. No original sao
# 10 abas por coluna do silabario (fronteiras u16 em VA 0xD93A8), uma 11a para letras latinas e uma 12a para o
# resto. Agora as 10 primeiras sao grupos de iniciais (maiuscula, sem acento), a 11a recebe as palavras em kana
# e a 12a o resto. O trecho trocado vai de MEMO_VA ate MEMO_END (onde a funcao insere o registro na aba s0) e
# tem um par relocado (MEMO_SITE), usado para o endereco da tabela de acentos; as fronteiras ficam logo depois.
MEMO_VA, MEMO_END, MEMO_SITE = 0xB2EDC, 0xB2FDC, (0xB2EFC, 0xB2F08)
MEMO_GROUPS = ["AB", "C", "DE", "FG", "HIJK", "LM", "NO", "PQ", "RS", "TUVWXYZ"]

R = {n: i for i, n in enumerate("zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 "
                                "k0 k1 gp sp fp ra".split())}


def _i(op, rs, rt, imm):
    return op << 26 | R[rs] << 21 | R[rt] << 16 | (imm & 0xFFFF)


def _r(fn, rd, rs, rt, sa=0):
    return R[rs] << 21 | R[rt] << 16 | R[rd] << 11 | sa << 6 | fn


def assemble(kana_ptrs, let, acc):
    """Devolve a lista de palavras de CODE_VA ate CODE_END. Os tres argumentos sao enderecos virtuais."""
    prog, labels = [], {}

    def at(name):
        labels[name] = len(prog)

    def emit(kind, *a):
        prog.append((kind,) + a)

    def hi(addr):
        return (addr + 0x8000) >> 16

    I = lambda op, rt, rs, imm: emit("w", _i(op, rs, rt, imm))
    addiu = lambda rt, rs, imm: I(0x09, rt, rs, imm)
    andi = lambda rt, rs, imm: I(0x0C, rt, rs, imm)
    xori = lambda rt, rs, imm: I(0x0E, rt, rs, imm)
    slti = lambda rt, rs, imm: I(0x0A, rt, rs, imm)
    sltiu = lambda rt, rs, imm: I(0x0B, rt, rs, imm)
    lui = lambda rt, imm: I(0x0F, rt, "zero", imm)
    lbu = lambda rt, off, rs: I(0x24, rt, rs, off)
    lw = lambda rt, off, rs: I(0x23, rt, rs, off)
    addu = lambda rd, rs, rt: emit("w", _r(0x21, rd, rs, rt))
    subu = lambda rd, rs, rt: emit("w", _r(0x23, rd, rs, rt))
    or_ = lambda rd, rs, rt: emit("w", _r(0x25, rd, rs, rt))
    sltu = lambda rd, rs, rt: emit("w", _r(0x2B, rd, rs, rt))
    sll = lambda rd, rt, sa: emit("w", _r(0x00, rd, "zero", rt, sa))
    jr = lambda rs: emit("w", R[rs] << 21 | 0x08)
    nop = lambda: emit("w", 0)
    beq = lambda rs, rt, lab: emit("b", _i(0x04, rs, rt, 0), lab)
    bne = lambda rs, rt, lab: emit("b", _i(0x05, rs, rt, 0), lab)
    blez = lambda rs, lab: emit("b", _i(0x06, rs, "zero", 0), lab)
    bal = lambda lab: emit("b", 0x04110000, lab)          # bgezal zero: ra = endereco depois do delay slot
    junk_hi = lambda: lui("at", 0)                        # par relocado sem uso: at = base do modulo
    junk_lo = lambda: addiu("at", "at", 0)

    def pad_to(va):
        while CODE_VA + 4 * len(prog) < va:
            nop()
        assert CODE_VA + 4 * len(prog) == va, hex(CODE_VA + 4 * len(prog))

    # ---- 0x70: a leitura vale? ----
    at("valid")
    addu("t6", "ra", "zero")
    addu("t5", "zero", "zero")            # quantos caracteres de encadear
    addiu("t4", "a0", MAX_BYTES)          # o 00 final tem que estar ate aqui
    at("va_loop")
    bal("next")
    nop()
    beq("v1", "zero", "va_end")
    junk_hi()
    addiu("t0", "v1", -3)
    beq("t0", "zero", "ret0")             # caractere que invalida
    junk_lo()
    addiu("t0", "v1", -1)
    bne("t0", "zero", "va_loop")          # ignoravel
    nop()
    beq("zero", "zero", "va_loop")
    addiu("t5", "t5", 1)
    at("va_end")
    blez("t5", "ret0")
    sltu("t0", "t4", "a0")
    bne("t0", "zero", "ret0")
    nop()
    jr("t6")
    addiu("v0", "zero", 1)
    at("ret0")
    jr("t6")
    addu("v0", "zero", "zero")

    # ---- rotina comum: le um caractere em a0 e avanca. v1 = 0 fim, 1 encadeia (v0 = ponteiro para os
    #      2 bytes), 2 ignoravel, 3 invalida. Usa t0-t3, t7-t9 ----
    at("next")
    lbu("t0", 0, "a0")
    beq("t0", "zero", "n_ret")
    addu("v1", "zero", "zero")
    addiu("a0", "a0", 1)
    andi("t1", "t0", 0xDF)                # maiuscula, se for letra
    addiu("t2", "t1", -0x41)
    sltiu("t2", "t2", 26)
    bne("t2", "zero", "n_letter")
    slti("t2", "t0", 0x80)
    bne("t2", "zero", "n_ret")            # outro caractere de 1 byte: ignoravel
    addiu("v1", "zero", 2)
    lbu("t1", 0, "a0")                    # segundo byte
    lui("t7", hi(kana_ptrs))
    addiu("t7", "t7", kana_ptrs)
    beq("t1", "zero", "n_ret")            # texto cortado no meio do caractere
    addiu("v1", "zero", 3)
    addiu("a0", "a0", 1)
    addiu("t2", "zero", 0x82)
    beq("t0", "t2", "n_kana")
    addiu("t3", "t1", -0x9F)
    addiu("t2", "zero", 0x85)
    bne("t0", "t2", "n_other")
    addiu("t3", "t1", -ACC_LO)
    sltiu("t2", "t3", ACC_N)
    beq("t2", "zero", "n_ret")            # 0x85xx fora da tabela (simbolos): ignoravel
    addiu("v1", "zero", 2)
    lui("t8", hi(acc))
    addiu("t8", "t8", acc)
    addu("t3", "t8", "t3")
    lbu("t1", 0, "t3")
    beq("t1", "zero", "n_ret")            # 0x85xx que nao e letra: ignoravel
    nop()
    at("n_letter")                        # t1 = letra maiuscula ASCII
    lui("t9", hi(let))
    addiu("t9", "t9", let)
    addiu("t1", "t1", -0x41)
    sll("t1", "t1", 1)
    addu("v0", "t9", "t1")
    jr("ra")
    addiu("v1", "zero", 1)

    # ---- 0x71: primeiro caractere de encadear ----
    pad_to(ENTRY["first"])
    at("first")
    addu("t6", "ra", "zero")
    at("f_loop")
    bal("next")
    nop()
    addiu("t0", "v1", -1)
    beq("t0", "zero", "f_ret")
    junk_hi()
    addiu("t0", "v1", -2)
    beq("t0", "zero", "f_loop")
    junk_lo()
    addu("v0", "zero", "zero")            # fim ou caractere que invalida
    at("f_ret")
    jr("t6")
    nop()

    at("n_kana")                          # 0x82xx: t3 = segundo byte - 0x9F, v1 = 3
    sltiu("t2", "t3", KANA_N)
    beq("t2", "zero", "n_ret")            # 0x82xx que nao e hiragana: invalida
    sll("t3", "t3", 2)
    addu("t3", "t7", "t3")
    lw("v0", 0, "t3")
    sltu("t2", "zero", "v0")
    addiu("v1", "zero", 2)
    jr("ra")
    subu("v1", "v1", "t2")                # 1 se a tabela tem o kana, 2 se nao
    at("n_other")                         # outro caractere de 2 bytes: so o traco 0x815B e ignoravel
    sll("t2", "t0", 8)
    or_("t2", "t2", "t1")
    xori("t2", "t2", 0x815B)
    sltiu("t2", "t2", 1)
    jr("ra")
    subu("v1", "v1", "t2")                # v1 era 3
    at("n_ret")
    jr("ra")
    nop()

    # ---- 0x72: ultimo caractere de encadear ----
    pad_to(ENTRY["last"])
    at("last")
    addu("t6", "ra", "zero")
    addu("t5", "zero", "zero")
    at("l_loop")
    bal("next")
    nop()
    beq("v1", "zero", "l_end")
    junk_hi()
    addiu("t0", "v1", -3)
    beq("t0", "zero", "l_bad")
    junk_lo()
    addiu("t0", "v1", -1)
    bne("t0", "zero", "l_loop")
    nop()
    beq("zero", "zero", "l_loop")
    addu("t5", "v0", "zero")
    at("l_bad")
    addu("t5", "zero", "zero")
    at("l_end")
    jr("t6")
    addu("v0", "t5", "zero")
    pad_to(CODE_END)

    words = []
    for k, item in enumerate(prog):
        if item[0] == "b":
            off = labels[item[2]] - (k + 1)
            assert -0x8000 <= off < 0x8000
            words.append(item[1] | (off & 0xFFFF))
        else:
            words.append(item[1])
    for name, va in ENTRY.items():
        assert CODE_VA + 4 * labels[name] == va, name
    for h, l in SITES:                    # cada par relocado tem que ser lui + instrucao com imediato de 16 bits
        wh, wl = words[(h - CODE_VA) // 4], words[(l - CODE_VA) // 4]
        assert wh >> 26 == 0x0F and wl >> 26 == 0x09 and (wh >> 16) & 31 == (wl >> 16) & 31 == (wl >> 21) & 31, hex(h)
    sites = {a for pair in SITES for a in pair}
    for k, w in enumerate(words):         # e nenhuma outra carga de endereco fora deles
        assert w >> 26 != 0x0F or CODE_VA + 4 * k in sites, hex(CODE_VA + 4 * k)
    return words


def memo_bounds():
    """11 fronteiras u16: a aba i recebe as letras de bounds[i] ate bounds[i + 1] - 1."""
    assert "".join(MEMO_GROUPS) == "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return [ord(g[0]) for g in MEMO_GROUPS] + [ord("Z") + 1]


def assemble_memo(acc):
    """Palavras de MEMO_VA ate MEMO_END. Entra com a0 = caderno e a1 = registro; sai com s1 = registro,
    s2 = caderno e s0 = aba (caderno + 0x30 + 24 * indice)."""
    prog, labels = [], {}
    w = lambda x: prog.append((x, None))
    br = lambda x, lab: prog.append((x, lab))
    lab = lambda name: labels.__setitem__(name, len(prog))
    I = lambda op, rt, rs, imm: w(_i(op, rs, rt, imm))
    addiu = lambda rt, rs, imm: I(0x09, rt, rs, imm)
    move = lambda rd, rs: w(_r(0x21, rd, rs, "zero"))
    beq = lambda rs, rt, name: br(_i(0x04, rs, rt, 0), name)
    bne = lambda rs, rt, name: br(_i(0x05, rs, rt, 0), name)
    nop = lambda: w(0)

    move("s1", "a1")
    move("s2", "a0")
    I(0x24, "a1", "s1", 0x19)             # lbu: primeiro byte do texto
    I(0x24, "v1", "s1", 0x1A)             # lbu: segundo byte
    move("s0", "zero")
    I(0x0C, "t1", "a1", 0xDF)             # andi: maiuscula, se for letra
    addiu("t2", "t1", -0x41)
    I(0x0B, "t2", "t2", 26)               # sltiu
    I(0x0F, "t8", "zero", (acc + 0x8000) >> 16)   # lui: tabela de acentos (par relocado)
    addiu("t3", "zero", 0x85)
    addiu("t4", "v1", -ACC_LO)
    addiu("t8", "t8", acc)
    bne("t2", "zero", "letter")
    I(0x0B, "t5", "t4", ACC_N)            # sltiu
    bne("a1", "t3", "not_letter")
    nop()
    beq("t5", "zero", "not_letter")
    w(_r(0x21, "t4", "t8", "t4"))         # addu
    I(0x24, "t1", "t4", 0)                # lbu: letra sem acento, ou 0
    beq("t1", "zero", "not_letter")
    nop()
    lab("letter")                         # t1 = letra maiuscula
    addiu("t9", "t8", ACC_N)              # fronteiras, logo depois dos acentos
    move("a0", "zero")
    lab("loop")
    I(0x25, "v0", "t9", 2)                # lhu: fim da aba a0
    w(_r(0x2B, "at", "t1", "v0"))         # sltu
    bne("at", "zero", "found")
    addiu("t9", "t9", 2)
    addiu("a0", "a0", 1)
    I(0x0A, "at", "a0", len(MEMO_GROUPS))  # slti
    bne("at", "zero", "loop")
    nop()
    addiu("a0", "zero", len(MEMO_GROUPS) - 1)
    lab("found")
    w(_r(0x00, "v0", "zero", "a0", 1))    # sll: 24 * a0
    w(_r(0x21, "v0", "v0", "a0"))
    w(_r(0x00, "v0", "zero", "v0", 3))
    w(_r(0x21, "v0", "s2", "v0"))
    beq("zero", "zero", "done")
    addiu("s0", "v0", 0x30)
    lab("not_letter")
    addiu("t3", "zero", 0x82)
    bne("a1", "t3", "other")
    addiu("t4", "v1", -0x9F)
    I(0x0B, "t5", "t4", KANA_N)           # sltiu: hiragana?
    beq("t5", "zero", "other")
    nop()
    beq("zero", "zero", "done")
    addiu("s0", "s2", 0x120)              # 11a aba: palavras em kana
    lab("other")
    beq("zero", "zero", "done")
    addiu("s0", "s2", 0x138)              # 12a aba: o resto
    total = (MEMO_END - MEMO_VA) // 4
    assert len(prog) <= total, len(prog)
    while len(prog) < total:
        nop()
    labels["done"] = total
    words = [x if name is None else x | ((labels[name] - (k + 1)) & 0xFFFF) for k, (x, name) in enumerate(prog)]
    h, l = ((a - MEMO_VA) // 4 for a in MEMO_SITE)
    assert words[h] >> 26 == 0x0F and words[l] >> 26 == 0x09 and (words[l] >> 16) & 31 == (words[h] >> 16) & 31
    assert all(x >> 26 != 0x0F or k == h for k, x in enumerate(words))
    return words


def accent_table():
    out = bytearray(ACC_N)
    for ch, code in ACCENTS.items():
        assert code >> 8 == 0x85 and ACC_LO <= code & 0xFF < ACC_LO + ACC_N, ch
        out[(code & 0xFF) - ACC_LO] = ord(unicodedata.normalize("NFD", ch)[0].upper())
    return bytes(out)


def patch(boot):
    """Aplica a troca num bytearray do BOOT.BIN (ja com os outros patches)."""
    f = lambda va: va + FILE_OFF
    # confere que e o codigo e a tabela originais
    assert struct.unpack_from("<I", boot, f(ENTRY["first"]))[0] == 0x00801021, "BOOT diferente"
    old_ptrs = struct.unpack_from(f"<{KANA_N}I", boot, f(PTR_VA))
    # uma entrada e nula (o tsu pequeno, que nao encadeia): ela nao tem relocacao e continua nula
    assert all(p == 0 or KANA_VA <= p < KANA_END for p in old_ptrs), "tabela de kana diferente"
    kana = [bytes(boot[f(p):f(p) + 2]) if p else None for p in old_ptrs]
    uniq = list(dict.fromkeys(k for k in kana if k))
    data = bytearray(b"".join(uniq))
    let = KANA_VA + len(data)
    data += b"".join(bytes([0x41 + i, 0]) for i in range(26))
    acc = KANA_VA + len(data)
    data += accent_table()
    assert (KANA_VA + len(data)) % 2 == 0
    data += struct.pack("<11H", *memo_bounds())           # fronteiras das abas do Caderno, logo depois dos acentos
    assert len(data) <= KANA_END - KANA_VA, len(data)
    data += bytes(KANA_END - KANA_VA - len(data))
    boot[f(KANA_VA):f(KANA_END)] = data
    struct.pack_into(f"<{KANA_N}I", boot, f(PTR_VA), *(KANA_VA + 2 * uniq.index(k) if k else 0 for k in kana))
    words = assemble(PTR_VA, let, acc)
    struct.pack_into(f"<{len(words)}I", boot, f(CODE_VA), *words)
    assert struct.unpack_from("<I", boot, f(MEMO_VA))[0] == 0x00A08821, "BOOT diferente"   # move s1, a1
    words = assemble_memo(acc)
    struct.pack_into(f"<{len(words)}I", boot, f(MEMO_VA), *words)
    return boot


# ---- referencia em Python e conferencia do codigo de maquina (roda as instrucoes sobre a imagem) ----
def classify(raw):
    """Lista de (classe, codigo) por caractere: 1 encadeia (codigo = b1 << 8 | b0), 2 ignoravel, 3 invalida."""
    out, i = [], 0
    acc = accent_table()
    while i < len(raw):
        c = raw[i]
        i += 1
        if 0x41 <= c & 0xDF <= 0x5A:
            out.append((1, c & 0xDF))
        elif c < 0x80:
            out.append((2, 0))
        elif i >= len(raw):
            out.append((3, 0))
        else:
            s = raw[i]
            i += 1
            if c == 0x82:
                out.append((1, None) if 0x9F <= s <= 0xF1 else (3, 0))       # o codigo do kana vem da tabela
            elif c == 0x85:
                letter = acc[s - ACC_LO] if ACC_LO <= s < ACC_LO + ACC_N else 0
                out.append((1, letter) if letter else (2, 0))
            else:
                out.append((2, 0) if (c, s) == (0x81, 0x5B) else (3, 0))
    return out


def reading_info(raw):
    """(vale, codigo do primeiro caractere) de uma leitura em letras, como as funcoes novas calculam; None se o
    texto tem kana (o codigo do kana vem da tabela do BOOT e esses registros ficam como estao)."""
    cls = classify(raw)
    if any(k == 1 and c is None for k, c in cls):
        return None
    chain = [c for k, c in cls if k == 1]
    bad = any(k == 3 for k, c in cls)
    head = next(((k, c) for k, c in cls if k != 2), (0, 0))
    return (not bad and bool(chain) and len(raw) <= MAX_BYTES), (head[1] if head[0] == 1 else 0)


def record_values(flags, raw):
    """(flags novas, valor do campo 0xE) de um registro de palavra cuja leitura passa a ser raw; None se nao
    muda. As flags seguem a rotina comum dos scripts: valida -> liga 0x1000 e 0x4000 (nao termina em N);
    invalida -> desliga 0x1000. Registros que ja nao valiam para o Shiritori ficam com as flags que tinham."""
    info = reading_info(raw)
    if info is None:
        return None
    ok, first = info
    if flags & 0x1000:
        flags = flags | 0x4000 if ok else flags & ~0x1000
    return flags, (0x20000000 | first if first else 0)


# Rotina comum dos scripts que roda ao ensinar uma palavra. No original: se a palavra casa com o padrao "so
# letras" (blob do pool), o Pokepi pergunta se e ingles e abre o teclado da leitura. Agora: se a palavra vale
# como leitura (funcao 0x70: letras ou kana), a leitura passa a ser a propria palavra e o teclado e pulado.
#   90 04 00  a1 <pool>  c0        palavra casa com o padrao?      ->  90 04 00  8b 70 01  89  01
#   11 <senao>
#   21 <f>  98 <g>  11 <x>  90 01 00  90 04 00  20 02 <fala>  10 <y>  90 01 00  90 04 00  20 02 <fala2>
#                                                               ->  91 03 00  90 04 00  51  10 <fim + 0x13>  01...
#   10 <fim>      fim: 91 03 00  90 04 00  90 02 00  90 03 00  20 03 <teclado>  89  51   (leitura = teclado)
TEACH = re.compile(rb"\x90\x04\x00(\xa1...\xc0)\x11...(\x21...\x98..\x11...\x90\x01\x00\x90\x04\x00\x20\x02..."
                   rb"\x10...\x90\x01\x00\x90\x04\x00\x20\x02...)\x10(...)", re.S)
TEACH_END = bytes.fromhex("910300 900400 900200 900300 2003")
SCRIPT_BASE = 0x1C                   # os enderecos de codigo do script sao relativos a este offset


def patch_script(d):
    """Devolve o KSC com a troca acima (todos os scripts tem a rotina, uma vez)."""
    hits = list(TEACH.finditer(d))
    assert len(hits) == 1, len(hits)
    m = hits[0]
    end = int.from_bytes(m.group(3), "little") + SCRIPT_BASE
    assert d[end:end + len(TEACH_END)] == TEACH_END and d[end + 17:end + 19] == b"\x89\x51", hex(end)
    test = bytes.fromhex("8b7001 89 01")
    body = bytes.fromhex("910300 900400 51 10") + (end + 0x13 - SCRIPT_BASE).to_bytes(3, "little")
    body += b"\x01" * (len(m.group(2)) - len(body))
    out = bytearray(d)
    out[m.start(1):m.end(1)] = test
    out[m.start(2):m.end(2)] = body
    assert len(out) == len(d)
    return bytes(out)


def run(boot, entry, raw, base=0x08804000, poke=None, stop=None, regs=None, span=(CODE_VA, CODE_END)):
    """Executa a funcao em entry com a0 = texto, sobre a imagem relocada para base. Devolve v0.
    poke: {endereco virtual: palavra} para valores que so existem com o jogo rodando."""
    import prx_relocs
    img = bytearray(prx_relocs.relocated(boot, base))
    for va, w in (poke or {}).items():
        struct.pack_into("<I", img, va + FILE_OFF, w)
    str_at = 0x09F00000
    mem = lambda a: (img, a - base + FILE_OFF) if a < str_at else (raw + bytes(4), a - str_at)
    reg = [0] * 32
    reg[R["a0"]], reg[R["ra"]], reg[R["sp"]] = str_at, 0xDEAD0000, 0x09FF0000
    for name, v in (regs or {}).items():
        reg[R[name]] = v
    pc, npc = base + entry, base + entry + 4
    for _ in range(100000):
        if pc == 0xDEAD0000:
            return reg[R["v0"]]
        if stop is not None and pc == base + stop:      # trecho no meio de uma funcao: devolve os registradores
            return reg
        assert base + span[0] <= pc < base + span[1], hex(pc)
        w = struct.unpack_from("<I", img, pc - base + FILE_OFF)[0]
        op, rs, rt, rd, sa, fn = w >> 26, (w >> 21) & 31, (w >> 16) & 31, (w >> 11) & 31, (w >> 6) & 31, w & 63
        imm = w & 0xFFFF
        simm = imm - 0x10000 if imm & 0x8000 else imm
        nxt = npc + 4
        tgt = npc + 4 * simm
        S, T = reg[rs], reg[rt]
        sg = lambda v: v - (1 << 32) if v & 0x80000000 else v
        if op == 0:
            if fn == 0x21: reg[rd] = (S + T) & 0xFFFFFFFF
            elif fn == 0x23: reg[rd] = (S - T) & 0xFFFFFFFF
            elif fn == 0x25: reg[rd] = S | T
            elif fn == 0x2B: reg[rd] = int(S < T)
            elif fn == 0x00: reg[rd] = (T << sa) & 0xFFFFFFFF
            elif fn == 0x03: reg[rd] = (sg(T) >> sa) & 0xFFFFFFFF
            elif fn == 0x08: nxt = S
            else: raise AssertionError(hex(w))
        elif op == 0x09: reg[rt] = (S + simm) & 0xFFFFFFFF
        elif op == 0x0C: reg[rt] = S & imm
        elif op == 0x0E: reg[rt] = S ^ imm
        elif op == 0x0A: reg[rt] = int(sg(S) < simm)
        elif op == 0x0B: reg[rt] = int(S < (simm & 0xFFFFFFFF))
        elif op == 0x0F: reg[rt] = imm << 16
        elif op == 0x24:
            b, o = mem((S + simm) & 0xFFFFFFFF)
            reg[rt] = b[o]
        elif op == 0x23:
            b, o = mem((S + simm) & 0xFFFFFFFF)
            reg[rt] = struct.unpack_from("<I", b, o)[0]
        elif op == 0x25:
            b, o = mem((S + simm) & 0xFFFFFFFF)
            reg[rt] = struct.unpack_from("<H", b, o)[0]
        elif op == 0x04: nxt = tgt if S == T else nxt
        elif op == 0x05: nxt = tgt if S != T else nxt
        elif op == 0x06: nxt = tgt if sg(S) <= 0 else nxt
        elif op in (0x14, 0x15):          # beql/bnel do codigo original: sem desvio, o delay slot e pulado
            if (S == T) == (op == 0x14):
                nxt = tgt
            else:
                reg[0] = 0
                pc, npc = npc + 4, npc + 8
                continue
        elif op == 0x01 and rt == 0x11:
            reg[31] = npc + 4
            nxt = tgt if sg(S) >= 0 else nxt
        else:
            raise AssertionError(hex(w))
        reg[0] = 0
        pc, npc = npc, nxt
    raise AssertionError("nao terminou")


def selftest(boot_path):
    import prx_relocs
    from gtext import to_bytes
    orig = open(boot_path, "rb").read()
    new = bytes(patch(bytearray(orig)))
    base = 0x08804000
    img_new, img_old = prx_relocs.relocated(new, base), prx_relocs.relocated(orig, base)

    def code(img, ptr):
        return 0 if ptr == 0 else int.from_bytes(img[ptr - base + FILE_OFF:ptr - base + FILE_OFF + 2], "little")

    kana = lambda s: s.encode("cp932")
    old_ok = ["\u3042", "\u304c\u3063\u3053\u3046", "\u3089\u30fc\u3081\u3093", "\u3057\u3083", "\u3071\u30fc",
              "\u3092", "\u3093", "\u3083"]
    cases = [kana(s) for s in old_ok] + [b"", b"\x81\x5b", kana("\u30a2"), kana("\u3042") * 16, kana("\u3042") * 17]
    for raw in cases:                     # o que o original aceitava ou recusava continua igual
        for name in ("valid", "first", "last"):
            # o original devolve as constantes verdadeiro/falso do VM (0xEC8D0 e 0xEC8E0), postas em tempo de execucao
            a = run(orig, ENTRY[name], raw, base, {0xEC8D0: 0x10000001, 0xEC8E0: 0x10000000})
            b = run(new, ENTRY[name], raw, base)
            a, b = (a, b) if name == "valid" else (code(img_old, a), code(img_new, b))
            assert a == b, (name, raw, a, b)
    words = ["Gato", "Mangaká", "Ábaco", "Chá gelado", "Pulga-d'água", "Micro-ondas", "ET", "a",
             "ç", "3D", "123", " ", "Lavar WC", "x" * 32, "x" * 33, "Óculos", "pão", "Torre Tóquio"]
    for w in words:
        raw = to_bytes(w)
        cls = classify(raw)
        chain = [c for k, c in cls if k == 1]
        bad = any(k == 3 for k, c in cls)
        want_valid = int(not bad and bool(chain) and len(raw) <= MAX_BYTES)
        assert run(new, ENTRY["valid"], raw, base) == want_valid, w
        # primeiro: para no primeiro caractere que nao e ignoravel; se ele invalida, devolve 0
        k0 = next(((k, c) for k, c in cls if k != 2), (0, 0))
        assert code(img_new, run(new, ENTRY["first"], raw, base)) == (k0[1] if k0[0] == 1 else 0), w
        assert code(img_new, run(new, ENTRY["last"], raw, base)) == (0 if bad or not chain else chain[-1]), w
    book = 0x09E00000
    tabs = {"Gato": "FG", "\u00c1baco": "AB", "\u00e7a": "C", "zebra": "TUVWXYZ", "Karaok\u00ea": "HIJK", "Sushi": "RS",
            "\u00d3culos": "NO", "\u3042\u3081": 10, "3D": 11, "\u30a2": 11, "\u2665": 11}
    for w, want in tabs.items():
        raw = w.encode("cp932") if "\u3000" < w[0] < "\u3100" else to_bytes(w)
        reg = run(new, MEMO_VA, raw, base, stop=MEMO_END, span=(MEMO_VA, MEMO_END),
                  regs={"a0": book, "a1": 0x09F00000 - 0x19})
        got = (reg[R["s0"]] - book - 0x30) // 24
        assert got == (MEMO_GROUPS.index(want) if isinstance(want, str) else want), (w, got)
        assert reg[R["s1"]] == 0x09F00000 - 0x19 and reg[R["s2"]] == book
    print("shiritori_code: ok,", len(cases) + len(words), "textos,", len(tabs), "abas do Caderno")


if __name__ == "__main__":
    import sys
    selftest(sys.argv[1])
