"""Gera e aplica patches VCDIFF (RFC 3284), o formato dos arquivos .xdelta.

O codificador so escreve bytes novos quando nao encontra o mesmo trecho no original. Assim o patch
fica pequeno e nao carrega conteudo do jogo. O aplicador nao depende de nada alem do Python.

Uso:
  vcdiff.py criar <original> <novo> <patch>
  vcdiff.py aplicar <original> <patch> <saida>
"""
import hashlib
import sys
import zlib

WINDOW = 1 << 23
MIN_MATCH = 12
HEADER = b"\xd6\xc3\xc4\x00\x00"
VCD_SOURCE = 1
VCD_ADLER32 = 4  # extensao do xdelta3: Adler-32 de cada janela, para recusar patch corrompido ou ISO errada
INST_ADD = 1  # ADD com tamanho explicito na tabela padrao
INST_COPY_SELF = 19  # COPY modo 0 (VCD_SELF) com tamanho explicito
INST_RUN = 0


def varint(n):
    out = [n & 0x7F]
    n >>= 7
    while n:
        out.append((n & 0x7F) | 0x80)
        n >>= 7
    return bytes(reversed(out))


def read_varint(buf, i):
    n = 0
    while True:
        b = buf[i]
        i += 1
        n = (n << 7) | (b & 0x7F)
        if not b & 0x80:
            return n, i


def build_index(src, regions):
    """Indice de blocos de MIN_MATCH bytes das regioes do original onde vale procurar trechos movidos."""
    index = {}
    for start, end in regions:
        for i in range(start, end - MIN_MATCH):
            key = src[i:i + MIN_MATCH]
            if key not in index:
                index[key] = i
    return index


def match_len(a, ai, b, bi, limit):
    """Quantos bytes iguais a partir de a[ai] e b[bi], comparando em blocos para ser rapido."""
    n = 0
    step = 1 << 16
    while n + step <= limit and a[ai + n:ai + n + step] == b[bi + n:bi + n + step]:
        n += step
    while n < limit and a[ai + n] == b[bi + n]:
        n += 1
    return n


def encode_window(src, tgt, tgt_start, index):
    """Devolve a lista de operacoes (('c', pos_origem, n) ou ('a', inicio, fim)) de um trecho do novo."""
    ops = []
    i = tgt_start[0]
    end = tgt_start[1]
    lit = i
    src_len = len(src)
    while i < end:
        best_pos, best_n = -1, 0
        # mesmo offset do original: o caso mais comum, pois quase tudo fica no lugar
        if i < src_len and src[i] == tgt[i]:
            best_pos, best_n = i, match_len(src, i, tgt, i, min(end - i, src_len - i))
        if best_n < MIN_MATCH:
            pos = index.get(bytes(tgt[i:i + MIN_MATCH]))
            if pos is not None:
                n = match_len(src, pos, tgt, i, min(end - i, src_len - pos))
                if n > best_n:
                    best_pos, best_n = pos, n
        if best_n >= MIN_MATCH:
            if lit < i:
                ops.append(("a", lit, i))
            ops.append(("c", best_pos, best_n))
            i += best_n
            lit = i
        else:
            i += 1
    if lit < end:
        ops.append(("a", lit, end))
    return ops


def write_window(out, ops, tgt, start, length, src_len):
    data = bytearray()
    inst = bytearray()
    addr = bytearray()
    for op in ops:
        if op[0] == "a":
            chunk = bytes(tgt[op[1]:op[2]])
            inst += bytes([INST_ADD]) + varint(len(chunk))
            data += chunk
        else:
            inst += bytes([INST_COPY_SELF]) + varint(op[2])
            addr += varint(op[1])
    check = zlib.adler32(bytes(tgt[start:start + length])).to_bytes(4, "big")
    delta = (varint(length) + b"\0" + varint(len(data)) + varint(len(inst)) + varint(len(addr)) + check
             + bytes(data) + bytes(inst) + bytes(addr))
    out.write(bytes([VCD_SOURCE | VCD_ADLER32]) + varint(src_len) + varint(0) + varint(len(delta)) + delta)


def create(src_path, tgt_path, patch_path, regions=()):
    src = open(src_path, "rb").read()
    tgt = open(tgt_path, "rb").read()
    index = build_index(src, regions)
    with open(patch_path, "wb") as out:
        out.write(HEADER)
        for start in range(0, len(tgt), WINDOW):
            end = min(start + WINDOW, len(tgt))
            write_window(out, encode_window(src, tgt, (start, end), index), tgt, start, end - start, len(src))
    return hashlib.sha1(tgt).hexdigest()


def apply(src_path, patch_path, out_path):
    src = open(src_path, "rb").read()
    p = open(patch_path, "rb").read()
    assert p[:3] == b"\xd6\xc3\xc4", "nao e um arquivo VCDIFF"
    assert p[4] == 0, "cabecalho VCDIFF nao suportado"
    i = 5
    with open(out_path, "wb") as out:
        while i < len(p):
            ind = p[i]
            i += 1
            assert ind & VCD_SOURCE, "janela sem origem nao suportada"
            seg_len, i = read_varint(p, i)
            seg_pos, i = read_varint(p, i)
            _, i = read_varint(p, i)
            win_len, i = read_varint(p, i)
            assert p[i] == 0, "compressao secundaria nao suportada"
            i += 1
            data_len, i = read_varint(p, i)
            inst_len, i = read_varint(p, i)
            addr_len, i = read_varint(p, i)
            check = None
            if ind & VCD_ADLER32:
                check = int.from_bytes(p[i:i + 4], "big")
                i += 4
            data = p[i:i + data_len]
            inst = p[i + data_len:i + data_len + inst_len]
            addr = p[i + data_len + inst_len:i + data_len + inst_len + addr_len]
            i += data_len + inst_len + addr_len
            win = bytearray()
            di = ii = ai = 0
            while ii < len(inst):
                code = inst[ii]
                ii += 1
                n, ii = read_varint(inst, ii)
                if code == INST_ADD:
                    win += data[di:di + n]
                    di += n
                else:
                    assert code == INST_COPY_SELF, code
                    a, ai = read_varint(addr, ai)
                    win += src[seg_pos + a:seg_pos + a + n]
            assert len(win) == win_len
            if check is not None and zlib.adler32(bytes(win)) != check:
                sys.exit("checksum errado: o patch esta corrompido ou a ISO original nao e a certa")
            out.write(win)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "criar":
        print(create(sys.argv[2], sys.argv[3], sys.argv[4]))
    elif cmd == "aplicar":
        apply(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        sys.exit(__doc__)
