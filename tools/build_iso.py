"""Monta a ISO traduzida a partir da original, sem alterar a original.

O DATA.BP e o ultimo arquivo do disco: arquivos do topo que mudam de tamanho (scripts KSC, BPM remontados) vao
para o fim dele, e so a entrada da tabela do topo muda. Arquivos de mesmo tamanho sao gravados no lugar.
O EBOOT.BIN criptografado e trocado pelo BOOT.BIN, que e o mesmo executavel sem criptografia.
"""
import shutil
import struct

from iso_common import (BOOT_LBA, BOOT_SIZE, DATA_BP_LBA, DATA_BP_SIZE, EBOOT_LBA, EBOOT_SIZE, SECTOR, TOP_DATA, Iso,
                        inner_files, parse_bp_table, top_files)


def find_dir_record(f, lba_size):
    """Procura no sistema de arquivos o registro com (lba, tamanho) e devolve a posicao dele."""
    lba, size = lba_size
    needle = struct.pack("<I", lba) + struct.pack(">I", lba) + struct.pack("<I", size) + struct.pack(">I", size)
    f.seek(0)
    head = f.read(64 * SECTOR)
    pos = head.find(needle)
    assert pos > 0, (lba, size)
    return pos - 2


def set_record_size(f, rec, size):
    f.seek(rec + 10)
    f.write(struct.pack("<I", size) + struct.pack(">I", size))


def rebuild_bpm(iso, off, files):
    """BPM remontado com os arquivos de files no lugar dos originais (alinhados em 16)."""
    table_size = struct.unpack_from("<I", iso.bp(off, 16), 12)[0]
    blob = bytearray(iso.bp(off, table_size))
    ents, _ = parse_bp_table(bytes(blob))
    for name, old_off, old_size, i, _nxt in sorted(ents, key=lambda e: e[1]):
        data = files.get(name, iso.bp(off + table_size + old_off, old_size))
        blob += b"\0" * ((-len(blob)) % 16)
        struct.pack_into("<2I", blob, 16 + i * 16 + 4, len(blob) - table_size, len(data))
        blob += data
    blob += b"\0" * ((-len(blob)) % 16)
    return bytes(blob)


def build(src, dst, top=None, bpm=None, inplace=None, boot=None, loose=None):
    """top: {nome_no_topo: bytes} arquivos novos do topo do DATA.BP (KSC, BPM inteiro...).
    bpm: {nome_bpm: {arquivo_interno: bytes}} BPMs remontados com arquivos novos.
    inplace: {(nome_bpm, arquivo_interno): bytes} de mesmo tamanho, gravados no lugar.
    boot: BOOT.BIN de mesmo tamanho. loose: {(lba, tamanho): bytes} arquivos soltos do disco."""
    iso = Iso(src)
    shutil.copyfile(src, dst)
    base = DATA_BP_LBA * SECTOR
    entries = {n: (o, s, i) for n, o, s, i in top_files(iso)}
    new_top = dict(top or {})
    inplace = dict(inplace or {})
    for name, files in (bpm or {}).items():
        files = dict(files)
        for key in [k for k in inplace if k[0] == name]:
            files[key[1]] = inplace.pop(key)
        new_top[name] = rebuild_bpm(iso, entries[name][0], files)
    with open(dst, "r+b") as f:
        end = DATA_BP_SIZE
        for name, data in new_top.items():
            off, size, i = entries[name]
            if len(data) <= size:
                f.seek(base + off)
                f.write(data + b"\0" * (size - len(data)))
                where = off
            else:
                end += (-end) % SECTOR
                f.seek(base + end)
                f.write(data)
                where = end
                end += len(data)
            f.seek(base + 16 + i * 16 + 4)
            f.write(struct.pack("<2I", where - TOP_DATA, len(data)))
        cache = {}
        for (pack, name), data in inplace.items():
            if pack not in cache:
                cache[pack] = {n: (o, s) for n, o, s in inner_files(iso, entries[pack][0])}
            o, s = cache[pack][name]
            assert len(data) == s, (pack, name)
            f.seek(base + o)
            f.write(data)
        for (lba, size), data in (loose or {}).items():
            span = (size + SECTOR - 1) // SECTOR * SECTOR
            assert len(data) <= span, (lba, len(data), span)
            rec = find_dir_record(f, (lba, size))
            f.seek(lba * SECTOR)
            f.write(data + b"\0" * (span - len(data)))
            set_record_size(f, rec, len(data))
        boot_bytes = boot if boot is not None else iso.read(BOOT_LBA, BOOT_SIZE)
        assert len(boot_bytes) == BOOT_SIZE and BOOT_SIZE <= EBOOT_SIZE
        f.seek(BOOT_LBA * SECTOR)
        f.write(boot_bytes)
        rec = find_dir_record(f, (EBOOT_LBA, EBOOT_SIZE))
        f.seek(EBOOT_LBA * SECTOR)
        f.write(boot_bytes + b"\0" * (EBOOT_SIZE - BOOT_SIZE))
        set_record_size(f, rec, BOOT_SIZE)
        if end != DATA_BP_SIZE:
            rec = find_dir_record(f, (DATA_BP_LBA, DATA_BP_SIZE))
            set_record_size(f, rec, end)
        total = base + end
        total += (-total) % SECTOR
        f.seek(0, 2)
        if total > f.tell():
            f.truncate(total)
            sectors = total // SECTOR
            f.seek(16 * SECTOR + 80)
            f.write(struct.pack("<I", sectors) + struct.pack(">I", sectors))
    return end
