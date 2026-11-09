"""Gera o patch .xdelta a partir da ISO original e da ISO traduzida, e confere aplicando de volta.

Uso: make_patch.py <iso_original> <iso_traduzida> <saida.xdelta>
"""
import hashlib
import os
import sys

from iso_common import BOOT_LBA, BOOT_SIZE, DATA_BP_LBA, SECTOR, Iso, top_files
from vcdiff import apply, create


def sha1(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(src, dst, out):
    # arquivos do topo do DATA.BP que mudaram de lugar (scripts e pacotes que cresceram vao para o fim): o
    # codificador procura trechos deles na posicao antiga, no original
    old = {e[0]: (e[1], e[2]) for e in top_files(Iso(src))}
    new = {e[0]: (e[1], e[2]) for e in top_files(Iso(dst))}
    regions = [(BOOT_LBA * SECTOR, BOOT_LBA * SECTOR + BOOT_SIZE)]
    for name, (off, size) in old.items():
        if new.get(name, (off, size))[0] != off:
            start = DATA_BP_LBA * SECTOR + off
            regions.append((start, start + size))
    print(len(regions) - 1, "arquivos mudaram de lugar")
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
