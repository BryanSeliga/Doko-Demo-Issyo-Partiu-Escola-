"""Extrai as falas unicas de um KSC para traducao, na ordem em que aparecem no script.

Uso: extract_text.py <arquivo.KSC> <saida.jsonl>
Cada linha: {"id": n, "tipo": "fala|pergunta|pool", "jp": "...", "usos": n}
A saida contem texto do jogo: fica em work/ e nunca vai para o repositorio.
"""
import json
import re
import sys

from kscbuild import extract_inline, extract_pool
from textfmt import HEART, to_text

JP = re.compile(r"[぀-ヿ一-鿿＀-￯]")


def collect(d):
    """Os textos com coracao (HEART) vao para o fim da lista, para nao mudar os ids dos demais."""
    seen = {}
    order = []

    def add(raw, tipo, hearts):
        try:
            text = to_text(raw)
        except UnicodeDecodeError:
            return
        if not JP.search(text) or (HEART in text) != hearts:
            return
        key = text
        if key in seen:
            seen[key]["usos"] += 1
            return
        item = {"id": len(order), "tipo": tipo, "jp": text, "usos": 1}
        seen[key] = item
        order.append(item)

    for hearts in (False, True):
        for n, op, raw in extract_inline(d):
            add(raw, "fala" if op == 0x48 else "pergunta", hearts)
        for off, raw in extract_pool(d).items():
            add(raw, "pool", hearts)
    return order


def main(src, dst):
    d = open(src, "rb").read()
    items = collect(d)
    with open(dst, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    print(len(items), "textos unicos,", sum(len(i["jp"]) for i in items), "caracteres")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
