"""Junta os textos japoneses usados em todos os KSC: um item por texto unico, com os arquivos onde aparece.

Uso: extract_all.py <iso> <saida.jsonl>
Cada linha: {"id": n, "tipo": "fala" (string-modelo no codigo) | "pool", "jp": "...", "usos": n, "arquivos": [...]}
A saida tem texto do jogo: fica em work/ e nunca vai para o repositorio.
"""
import json
import re
import sys

from gtext import to_text
from iso_common import Iso, ksc_files
from ksc import extract

JP = re.compile(r"[぀-ヿ一-鿿＀-￯]")


def collect(iso):
    """Textos unicos na ordem em que aparecem (o id e a posicao). Os textos com simbolos de gtext.EXTRA (coracao)
    entram numa segunda passada, no fim, para nao mudar os ids da primeira versao da lista."""
    items, order = {}, []
    late = []
    for name, off, size in ksc_files(iso):
        inline, pool = extract(iso.bp(off, size))
        for tipo, group in (("fala", inline), ("pool", pool)):
            for raw in group.values():
                try:
                    text = to_text(raw)
                except (UnicodeDecodeError, KeyError):
                    late.append((name, tipo, raw))
                    continue
                add(items, order, name, tipo, text)
    for name, tipo, raw in late:
        try:
            text = to_text(raw, extra=True)
        except (UnicodeDecodeError, KeyError):
            continue
        add(items, order, name, tipo, text)
    return order


def add(items, order, name, tipo, text):
    if not JP.search(text):
        return
    it = items.get(text)
    if it is None:
        it = items[text] = {"id": len(order), "tipo": tipo, "jp": text, "usos": 0, "arquivos": []}
        order.append(it)
    it["usos"] += 1
    if name not in it["arquivos"]:
        it["arquivos"].append(name)


def main(iso_path, out):
    order = collect(Iso(iso_path))
    with open(out, "w", encoding="utf-8") as f:
        for it in order:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    falas = [i for i in order if i["tipo"] == "fala"]
    print(len(order), "textos unicos,", sum(len(i["jp"]) for i in order), "caracteres;",
          len(falas), "falas no codigo,", sum(len(i["jp"]) for i in falas), "caracteres")


if __name__ == "__main__":
    main(*sys.argv[1:])
