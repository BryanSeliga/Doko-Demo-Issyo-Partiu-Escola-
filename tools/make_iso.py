"""Monta a ISO traduzida do Let's Gakkou. Uso: make_iso.py <iso_original> <iso_saida>

As traducoes ficam em traducao/*.jsonl, uma linha por texto: {"id": n, "pt": "..."}. O id e a posicao do texto
na lista de extract_all.collect (a mesma ISO sempre gera a mesma lista). O texto japones nunca fica no repositorio.
Cada texto traduzido e trocado em todos os scripts onde aparece, nas falas do codigo e no pool.
"""
import glob
import json
import os
import re
import sys

from build_iso import build
from extract_all import collect
from gtext import TOKEN, to_bytes, to_text
from iso_common import BOOT_LBA, BOOT_SIZE, Iso, bpm_files, inner_files, ksc_files
from ksc import extract, reading_pairs, reading_slots, rebuild
from kscdis import table_values
import boot_text
import defplay
import gui_render
import shiritori_code
import textures
import title_logo

HERE = os.path.dirname(os.path.abspath(__file__))
# O op 4b copia a string do pool com strcpy para o buffer de fala do VM (+0x78, ate +0x477): mais que isso
# sobrescreve a base do pool (+0x480) e o jogo trava. O maior texto original tem 265 bytes.
MAX_BYTES = 600
PT_DIR = os.environ.get("PT_DIR", os.path.join(HERE, "..", "traducao"))  # PT_DIR troca a pasta nos testes


def load_translations(items):
    """{texto_jp: texto_pt}; confere se as variaveis do original ficaram na traducao."""
    by_id = {it["id"]: it["jp"] for it in items}
    out, bad = {}, []
    for path in sorted(glob.glob(os.path.join(PT_DIR, "*.jsonl"))):
        for line in open(path, encoding="utf-8"):
            if not line.strip():
                continue
            row = json.loads(line)
            jp = by_id[row["id"]]
            if sorted(TOKEN.findall(jp)) != sorted(TOKEN.findall(row["pt"])):
                bad.append(row["id"])
                continue
            if len(to_bytes(row["pt"])) > MAX_BYTES:
                sys.exit(f"texto {row['id']} passa de {MAX_BYTES} bytes e travaria o jogo")
            out[jp] = row["pt"]
    if bad:
        print("variaveis diferentes do original (ignorados):", bad[:20], "..." if len(bad) > 20 else "")
    return out


# Rotina comum de todos os scripts que abre o teclado de nome: empilha a funcao 0x24, o tipo 3 (kana + ABC) e o
# limite 4, e chama o sistema (8b f1 03). O limite passa a 7, como no Issyo: "Sophia" tem 6 letras.
NAME_CALL = bytes.fromhex("8024 8003 8004 8bf103")
NAME_CALL_NEW = bytes.fromhex("8024 8003 8007 8bf103")


def apply(d, pt):
    d = shiritori_code.patch_script(d)  # ensinar palavra: a leitura de uma palavra em letras e ela mesma
    inline, pool = extract(d)

    def tr(group):
        new = {}
        for k, raw in group.items():
            try:
                text = to_text(raw, extra=True)
            except (UnicodeDecodeError, KeyError):
                continue
            if text in pt:
                new[k] = to_bytes(pt[text])
        return new

    new_inline, new_pool = tr(inline), tr(pool)
    if not new_inline and not new_pool:
        return d.replace(NAME_CALL, NAME_CALL_NEW), 0
    # Leituras dos dicionarios (Shiritori, provincias): o jogo encadeia e agrupa as palavras por elas. Palavra
    # traduzida: a leitura passa a ser a propria palavra (Shiritori por letras, ver shiritori_code), com as flags
    # e o codigo do primeiro caractere do registro refeitos. Palavra sem traducao: a leitura fica em kana; se o
    # texto dela foi traduzido em outro lugar, passa a apontar para uma copia do original
    extra, table_new, copy_of, table_copy, table_val = [], {}, {}, {}, {}
    tv, pairs = table_values(d), reading_pairs(d)
    for k, o in reading_slots(d).items():
        word, head = pairs[k]
        raw = new_pool.get(tv[word] & 0xFFFFFFF)
        vals = shiritori_code.record_values(tv[head + 1] if head is not None else 0, raw) if raw else None
        if vals:
            table_copy[k] = word
            if head is not None:
                table_val[head + 1], table_val[head + 15] = vals
        elif o in new_pool:
            if o not in copy_of:
                copy_of[o] = len(extra)
                extra.append(pool[o])
            table_new[k] = copy_of[o]
    out = rebuild(d, new_inline, new_pool, extra, table_new, table_copy, table_val)
    return out.replace(NAME_CALL, NAME_CALL_NEW), len(new_inline) + len(new_pool)


def main(src, dst):
    iso = Iso(src)
    items = collect(iso)
    pt = load_translations(items)
    top, total = {}, 0
    for name, off, size in ksc_files(iso):
        new, n = apply(iso.bp(off, size), pt)
        if new is not None:
            top[name] = new
            total += n
    print(f"{len(pt)} traducoes; {total} trocas em {len(top)} scripts")
    # tela-titulo com o logotipo "Partiu Escola!" (as texturas crescem: o TITLE.BPM e remontado no fim)
    bpms = {n: (o, s) for n, o, s in bpm_files(iso)}
    tfiles = {n: (o, s) for n, o, s in inner_files(iso, bpms["TITLE.BPM"][0])}
    title = title_logo.build(iso.bp(*tfiles[title_logo.LOGO[1]]), iso.bp(*tfiles[title_logo.BG[1]]))
    # rotulos de interface que sao imagens (botoes, rodapes, titulos das salas), no mesmo tamanho
    # vocabulario inicial do Toro (palavras em portugues, leituras em kana)
    title["DEFPLAYDATA.BIN"] = defplay.rebuild(iso.bp(*tfiles["DEFPLAYDATA.BIN"]))
    bpm = {"TITLE.BPM": title}
    # e texto desenhado no cenario (lanternas, placas, etiquetas, o bilhete do album)
    for (pack, name), data in {**gui_render.build_all(iso, bpms), **textures.build_all(iso, bpms)}.items():
        bpm.setdefault(pack, {})[name] = data
    print(f"{sum(len(v) for v in bpm.values())} imagens em {len(bpm)} pacotes")
    boot = boot_text.patch_boot(iso.read(BOOT_LBA, BOOT_SIZE))  # menus, botoes e janelas do sistema
    print("DATA.BP ->", build(src, dst, top=top, bpm=bpm, boot=boot))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
