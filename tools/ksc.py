"""Extrai e remonta os textos de um KSC do Let's Gakkou.

Textos ficam em dois lugares:
- no codigo, como string-modelo dos ops 48/49/4a/8e (falas em balao): trocar muda o tamanho do codigo, entao
  todo endereco de codigo (saltos, chamadas, cases, stub de entrada) e recalculado;
- no pool, citados pelos ops 88/4b/a1 do codigo e pelos valores tag 5/0xE da tabela: o pool e remontado
  entrada por entrada e todas as referencias sao corrigidas.
Remontar sem trocas devolve o arquivo identico (ver selftest).
"""
import struct

from kscdis import (CODE_BASE, STR_OPS, code_end, code_refs, decode, decode_stub, layout, pool_anchors,
                    pool_entries, pool_refs_ex, table_values)


def u24(d, i):
    return int.from_bytes(d[i:i + 3], "little")


def extract(d):
    """(inline, pool): inline = {offset_da_instrucao: bytes da string-modelo sem o op e sem o 00};
    pool = {offset_no_pool: bytes da string} so das strings referenciadas."""
    ins = decode(d)
    inline = {off: d[off + 1:off + n - 1] for off, op, n in ins if op in STR_OPS}
    lay = layout(d)
    sref, _ = pool_anchors(d, ins)
    pool = {}
    for o, kind, e in pool_entries(d, ins):
        if kind == "str" and o in sref:
            raw = d[lay["pool"] + o:lay["pool"] + e]
            pool[o] = raw[:raw.index(b"\0")] if b"\0" in raw else raw
    return inline, pool


def reading_slots(d):
    """{indice_na_tabela: offset_no_pool} dos campos de leitura do dicionario do Shiritori.
    Registro na tabela: 0x90000010, 0x2000f024 ou 0x2000b024, palavra (tag 5), leitura em kana (tag 5), ...
    O jogo encadeia as palavras pela leitura: ela fica sempre em japones."""
    tv = table_values(d)
    out = {}
    for i in range(2, len(tv) - 1):
        if (tv[i - 2] == 0x90000010 and tv[i - 1] in (0x2000F024, 0x2000B024)
                and tv[i] >> 28 == 5 and tv[i + 1] >> 28 == 5):
            out[i + 1] = tv[i + 1] & 0xFFFFFFF
    return out


def rebuild(d, inline=None, pool=None, extra=None, table_new=None):
    """inline: {offset_da_instrucao: bytes novos}; pool: {offset_no_pool: bytes novos}.
    extra: strings novas acrescentadas no fim do pool; table_new: {indice_na_tabela: indice em extra} faz
    aquela entrada (tag 5) da tabela apontar para a string nova."""
    inline, pool = inline or {}, pool or {}
    extra, table_new = extra or [], table_new or {}
    ins = decode(d)
    stub = decode_stub(d)
    lay = layout(d)
    old_end = code_end(d)
    crefs = code_refs(d, ins)
    prefs = pool_refs_ex(d, ins)

    # 1) codigo: novas posicoes de cada instrucao
    code = bytearray(d[:CODE_BASE])
    newpos = {}
    for off, op, n in ins:
        newpos[off] = len(code)
        if off in inline:
            code += bytes([op]) + inline[off] + b"\0"
        else:
            code += d[off:off + n]
    shift = len(code) - old_end
    newpos[old_end] = len(code)
    stub_end = stub[-1][0] + stub[-1][2] if stub else old_end
    for off, op, n in stub:
        newpos[off] = off + shift
    code += d[old_end:stub_end]
    starts = sorted(newpos)

    def moved(pos):
        """Nova posicao de um byte qualquer do codigo antigo (dentro de uma instrucao que nao mudou)."""
        lo, hi = 0, len(starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if starts[mid] <= pos:
                lo = mid
            else:
                hi = mid - 1
        base = starts[lo]
        return newpos[base] + (pos - base)

    # 2) enderecos de codigo
    for at, (target, _kind) in crefs.items():
        p = moved(at)
        code[p:p + 3] = (newpos[target] - CODE_BASE).to_bytes(3, "little")
    # o pool comeca alinhado em 4, com zeros depois do stub (como em todos os originais)
    code += b"\0" * ((-len(code)) % 4)
    new_pool_start = len(code)

    # 3) pool
    newpool = bytearray()
    pmap = {}
    for o, kind, e in pool_entries(d, ins):
        pmap[o] = len(newpool)
        if kind == "str" and o in pool:
            newpool += pool[o] + b"\0\0"
        else:
            newpool += d[lay["pool"] + o:lay["pool"] + e]
    extra_at = []
    if extra:
        # o leitor do pool anda de string em string ([texto][00][1 byte]); os zeros do fim viram strings vazias de
        # 2 bytes. A primeira string nova tem que comecar onde esse passo termina, senao fica 1 byte fora
        i = max(pmap[o] for o, kind, e in pool_entries(d, ins) if kind == "str")
        while i < len(newpool):
            z = newpool.find(b"\0", i)
            i = len(newpool) if z < 0 else z + 2
        newpool += b"\0" * (i - len(newpool))
    for s in extra:
        extra_at.append(len(newpool))
        newpool += s + b"\0\0"
    newpool += b"\0" * ((-len(newpool)) % 4)  # a tabela (u32) comeca alinhada em 4
    for at, (po, op, size) in prefs.items():
        p = moved(at)
        code[p:p + 3] = pmap[po].to_bytes(3, "little")

    # 4) tabela
    table = bytearray(d[lay["table"]:])
    for k, v in enumerate(table_values(d)):
        if k in table_new:
            struct.pack_into("<I", table, 4 * k, 0x50000000 | extra_at[table_new[k]])
        elif v >> 28 in (5, 0xE):
            struct.pack_into("<I", table, 4 * k, (v & 0xF0000000) | pmap[v & 0xFFFFFFF])

    out = bytearray(code) + newpool + table
    struct.pack_into("<3I", out, 8, newpos[old_end] - CODE_BASE, new_pool_start - CODE_BASE, len(newpool))
    return bytes(out)


def selftest(iso_path):
    """Sem trocas o arquivo sai identico. Com todas as strings regravadas (e crescidas com um sufixo), o
    arquivo novo tem que decodificar inteiro e devolver os mesmos textos na mesma ordem."""
    import sys
    from iso_common import Iso, ksc_files
    iso = Iso(iso_path)
    bad = 0
    for name, off, size in ksc_files(iso):
        d = iso.bp(off, size)
        inline, pool = extract(d)
        a = rebuild(d)
        grow = {k: v + b"XYZ" for k, v in inline.items()}
        growp = {k: v + b"XYZ" for k, v in pool.items()}
        b = rebuild(d, grow, growp)
        i2, p2 = extract(b)
        same = (list(i2.values()) == list(grow.values()) and list(p2.values()) == list(growp.values()))
        if a != d or not same:
            bad += 1
            print("diferente:", name, a == d, same, file=sys.stderr)
    print("selftest:", bad, "arquivos diferentes")
    return bad == 0


if __name__ == "__main__":
    import sys
    selftest(sys.argv[1])
