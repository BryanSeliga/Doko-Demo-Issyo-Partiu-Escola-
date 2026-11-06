"""Leitura somente-leitura da ISO original do Let's Gakkou (UCJS10039) e do indice do DATA.BP.

O DATA.BP e o ultimo arquivo do disco. No topo dele ficam os scripts (KSC), as musicas (SGD) e os pacotes (BPM).
"""
import struct

SECTOR = 2048
DATA_BP_LBA = 34752
DATA_BP_SIZE = 224436224
BOOT_LBA = 21104
BOOT_SIZE = 1151574
EBOOT_LBA = 32
EBOOT_SIZE = 1151920
PARAM_SFO = (21776, 472)
ICON0_PNG = (21680, 18409)
ICON1_PMF = (21696, 145408)
PIC0_PNG = (21792, 88646)
PIC1_PNG = (21840, 55104)
TOP_DATA = 0x9800  # tamanho da tabela do topo do DATA.BP


class Iso:
    def __init__(self, path):
        self.f = open(path, "rb")

    def read(self, lba, size):
        self.f.seek(lba * SECTOR)
        return self.f.read(size)

    def bp(self, offset, size):
        self.f.seek(DATA_BP_LBA * SECTOR + offset)
        return self.f.read(size)


def parse_bp_table(data):
    """Tabela hash do BP: cabecalho (buckets, total, tam_nomes, tam_tabela), entradas
    (nome, offset, tamanho, proximo) e tabela de nomes."""
    buckets, total, names_size, table_size = struct.unpack_from("<4I", data, 0)
    names_at = 16 + total * 16
    out = []
    for i in range(total):
        name_off, off, size, nxt = struct.unpack_from("<4I", data, 16 + i * 16)
        if name_off == 0xFFFFFFFF:
            continue
        end = data.index(b"\0", names_at + name_off)
        out.append((data[names_at + name_off:end].decode("ascii"), off, size, i, nxt))
    return out, (buckets, total, names_size, table_size)


def top_files(iso):
    """Lista (nome, offset_absoluto_no_BP, tamanho, indice_na_tabela) de tudo que esta no topo do DATA.BP."""
    ents, _ = parse_bp_table(iso.bp(0, TOP_DATA))
    return sorted(((e[0], TOP_DATA + e[1], e[2], e[3]) for e in ents), key=lambda e: e[1])


def bpm_files(iso):
    """Lista (nome_bpm, offset_absoluto_no_BP, tamanho)."""
    return [(n, o, s) for n, o, s, _ in top_files(iso) if n.endswith(".BPM")]


def ksc_files(iso):
    """Lista (nome_ksc, offset_absoluto_no_BP, tamanho)."""
    return [(n, o, s) for n, o, s, _ in top_files(iso) if n.endswith(".KSC")]


def inner_files(iso, bpm_off):
    """Lista (nome, offset_absoluto_no_BP, tamanho) de um BPM."""
    head = iso.bp(bpm_off, 16)
    table_size = struct.unpack_from("<I", head, 12)[0]
    ents, _ = parse_bp_table(iso.bp(bpm_off, table_size))
    return sorted(((e[0], bpm_off + table_size + e[1], e[2]) for e in ents), key=lambda e: e[1])
