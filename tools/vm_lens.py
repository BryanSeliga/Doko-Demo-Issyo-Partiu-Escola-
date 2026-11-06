"""Quanto cada tratador do VM avanca o contador do script (pc em 4(contexto)), a partir do mapa de vm_ops.

Procura "addiu R, R, N" seguido de "sw R, 4(X)" no corpo do tratador ate voltar ao laco (0x53EC4).
Uso: vm_lens.py <boot.asm> <ops.json>
"""
import json
import re
import sys

LOOP = 0x53EC4


def main(asm_path, ops_path):
    asm = {}
    for line in open(asm_path, encoding="ascii"):
        asm[int(line[:6], 16)] = line[8:].split("  ;")[0].rstrip()
    ops = {int(k, 16): v for k, v in json.load(open(ops_path)).items()}
    out = {}
    for op in sorted(ops):
        va = ops[op]
        if va == LOOP:
            continue
        incs, calls, n, lbus = [], [], 0, 0
        while n < 400:
            t = asm.get(va, "?")
            m = re.match(r"sw (\$\w+), 4\((\$\w+)\)", t)
            if m:
                r = m.group(1)
                for k in range(-10, 2):
                    p = asm.get(va + 4 * k, "")
                    mm = re.match(r"addiu %s, (\$\w+), (-?0x[0-9a-f]+|-?\d+)$" % re.escape(r), p)
                    if mm:
                        incs.append(int(mm.group(2), 0))
                        break
            if t.startswith("lbu"):
                lbus += 1
            if t.startswith("jal "):
                calls.append(t[4:])
            if t in (f"b 0x{LOOP:x}", f"j 0x{LOOP:x}") or t.startswith("jr $ra"):
                break
            va += 4
            n += 1
        out[op] = (incs, calls[:4], lbus)
        print(f"{op:02x} @{ops[op]:06x} avancos={incs} lbu={lbus} chamadas={calls[:3]}")
    return out


if __name__ == "__main__":
    main(*sys.argv[1:])
