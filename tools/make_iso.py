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
from iso_common import Iso, ksc_files
from ksc import extract, rebuild

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


def apply(d, pt):
    inline, pool = extract(d)

    def tr(group):
        new = {}
        for k, raw in group.items():
            try:
                text = to_text(raw)
            except (UnicodeDecodeError, KeyError):
                continue
            if text in pt:
                new[k] = to_bytes(pt[text])
        return new

    new_inline, new_pool = tr(inline), tr(pool)
    if not new_inline and not new_pool:
        return None, 0
    return rebuild(d, new_inline, new_pool), len(new_inline) + len(new_pool)


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
    print("DATA.BP ->", build(src, dst, top=top))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
