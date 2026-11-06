"""Gera o patch .xdelta a partir da ISO original e da ISO traduzida, e confere aplicando de volta.

Uso: make_patch.py <iso_original> <iso_traduzida> <saida.xdelta>
"""
import hashlib
import os
import sys

from iso_common import BOOT_LBA, BOOT_SIZE, DATA_BP_LBA, SECTOR, Iso, bpm_files
from vcdiff import apply, create

# Pacotes reescritos no fim do DATA.BP: o codificador procura trechos deles no original.
MOVED = ("KSNEKO.BPM", "KSINU.BPM", "KSROBO.BPM", "KSKAERU.BPM", "KSUSAGI.BPM", "TITLE.BPM", "QUICK.BPM")


def sha1(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(src, dst, out):
    iso = Iso(src)
    regions = [(BOOT_LBA * SECTOR, BOOT_LBA * SECTOR + BOOT_SIZE)]
    for name, off, size in bpm_files(iso):
        if name in MOVED:
            start = DATA_BP_LBA * SECTOR + off
            regions.append((start, start + size))
    create(src, dst, out, regions)
    check = out + ".teste.iso"
    apply(src, out, check)
    ok = sha1(check) == sha1(dst)
    os.remove(check)
    print(f"{out}: {os.path.getsize(out)} bytes; original {sha1(src)}; traduzida {sha1(dst)}; aplicacao {'OK' if ok else 'FALHOU'}")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main(*sys.argv[1:4])
