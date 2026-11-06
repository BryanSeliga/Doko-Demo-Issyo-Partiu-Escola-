"""Mapa opcode -> tratador do VM de scripts (KSC) no BOOT do Let's Gakkou.

O despachante (0x4DAA0) le o opcode em s0 e decide por comparacoes encadeadas. Aqui cada valor 0..255 e
simulado nesse trecho ate cair num endereco fora dele (o tratador).
Uso: vm_ops.py <boot.asm> [saida.json]
"""
import json
import re
import sys

START, CHAIN_END = 0x4DAA4, 0x4E260
SIGNED = lambda v: v - (1 << 32) if v & 0x80000000 else v


def load(path):
    asm = {}
    for line in open(path, encoding="ascii"):
        asm[int(line[:6], 16)] = line[8:].split("  ;")[0].rstrip()
    return asm


def imm(s):
    return int(s, 0)


def run(asm, op):
    regs = {"$zero": 0, "$v1": 0xFF, "$s0": op}
    pc = START
    for _ in range(4000):
        if not (START <= pc < CHAIN_END):
            return pc
        t = asm[pc]
        name, _, args = t.partition(" ")
        a = [x.strip() for x in args.split(",")] if args else []
        nxt = pc + 4
        taken = None
        if name == "addiu":
            regs[a[0]] = (regs.get(a[1], 0) + imm(a[2])) & 0xFFFFFFFF
        elif name in ("slti", "sltiu"):
            x = regs.get(a[1], 0)
            regs[a[0]] = int((SIGNED(x) if name == "slti" else x) < (imm(a[2]) & (0xFFFFFFFF if name == "sltiu" else -1)))
        elif name in ("slt", "sltu"):
            x, y = regs.get(a[1], 0), regs.get(a[2], 0)
            regs[a[0]] = int(SIGNED(x) < SIGNED(y)) if name == "slt" else int(x < y)
        elif name in ("beq", "beql", "bne", "bnel"):
            eq = regs.get(a[0], 0) == regs.get(a[1], 0)
            taken = eq if name.startswith("beq") else not eq
            target = imm(a[2])
        elif name in ("beqz", "beqzl", "bnez", "bnezl"):
            z = regs.get(a[0], 0) == 0
            taken = z if name.startswith("beqz") else not z
            target = imm(a[1])
        elif name in ("b", "j"):
            taken, target = True, imm(a[0])
        elif name in ("nop", "lh", "lw", "sw", "sh", "lbu", "andi", "move", "addu", "subu", "sll"):
            if name == "andi" and a[1] in regs:
                regs[a[0]] = regs[a[1]] & imm(a[2])
            elif name == "move" and a[1] in regs:
                regs[a[0]] = regs[a[1]]
            elif a and a[0] in regs and a[0] != "$s0" and name not in ("sw", "sh"):
                regs.pop(a[0], None)
        else:
            raise ValueError(f"instrucao nao tratada em {pc:x}: {t}")
        if taken is None:
            pc = nxt
            continue
        likely = name.endswith("l") and name not in ("bnel", "beql") or name in ("beql", "bnel", "beqzl", "bnezl")
        if taken or not likely:
            slot = asm[nxt]
            m = re.match(r"addiu (\$\w+), (\$\w+), (-?0x[0-9a-f]+|-?\d+)$", slot)
            if m:
                regs[m.group(1)] = (regs.get(m.group(2), 0) + imm(m.group(3))) & 0xFFFFFFFF
        pc = target if taken else nxt + 4
    raise RuntimeError(f"laco sem fim no op {op:02x}")


def main(path, out=None):
    asm = load(path)
    ops = {op: run(asm, op) for op in range(256)}
    common = max(set(ops.values()), key=list(ops.values()).count)
    valid = {op: h for op, h in ops.items() if h != common}
    print(f"tratador padrao (op invalido?) {common:x}; {len(valid)} opcodes com tratador proprio")
    print(" ".join(f"{op:02x}" for op in sorted(valid)))
    if out:
        json.dump({f"{op:02x}": h for op, h in ops.items()}, open(out, "w"), indent=0)


if __name__ == "__main__":
    main(*sys.argv[1:])
