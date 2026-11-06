"""Desmonta o .text do BOOT.BIN do Let's Gakkou (PRX carregado em 0; arquivo = vaddr + 0x60) e resolve lui/addiu."""
import struct
import sys

from capstone import CS_ARCH_MIPS, CS_MODE_32, CS_MODE_LITTLE_ENDIAN, Cs

b = open(sys.argv[1], "rb").read()
md = Cs(CS_ARCH_MIPS, CS_MODE_32 | CS_MODE_LITTLE_ENDIAN)
TEXT_V, TEXT_SIZE = 0x0, 0xCC158
FILE_OFF = 0x60
out = open(sys.argv[2], "w", encoding="ascii")
hi = {}
for va in range(TEXT_V, TEXT_V + TEXT_SIZE, 4):
    w = b[va + FILE_OFF:va + FILE_OFF + 4]
    ins = next(md.disasm(w, va, 1), None)
    if ins is None:
        out.write(f"{va:06x}: .word {struct.unpack('<I', w)[0]:08x}\n")
        continue
    note = ""
    word = struct.unpack("<I", w)[0]
    op = word >> 26
    rt = (word >> 16) & 31
    rs = (word >> 21) & 31
    imm = word & 0xFFFF
    simm = imm - 0x10000 if imm & 0x8000 else imm
    if op == 0x0F:
        hi[rt] = imm << 16
    elif op in (0x09, 0x0D, 0x23, 0x21, 0x25, 0x24, 0x20, 0x2B, 0x28, 0x29, 0x31, 0x39) and rs in hi:
        tgt = (hi[rs] | imm) if op == 0x0D else (hi[rs] + simm) & 0xFFFFFFFF
        note = f"  ; ={tgt:#x}"
    out.write(f"{va:06x}: {ins.mnemonic} {ins.op_str}{note}\n")
