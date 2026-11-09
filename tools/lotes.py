"""Lotes de traducao.

  lotes.py gerar <iso> <fase>    separa os textos ainda sem traducao dos scripts da fase, na ordem em que
                                 aparecem, em work/lotes/<fase>_NN.jsonl (com o japones: so em work/)
  lotes.py conferir <iso> <arquivo.jsonl>...   confere traducoes em traducao/ (ou em work/) contra o original

Traducao: uma linha por texto, {"id": n, "pt": "..."}; o id e o de extract_all.collect.
"""
import glob
import json
import os
import re
import sys

from extract_all import JP, collect
from gtext import TOKEN, to_bytes, to_text
from iso_common import Iso, ksc_files
from ksc import extract, reading_slots
from kscdis import pool_refs_ex, table_values
from widths import width

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
FASES = {
    "inicio": ["NYUUGAKU.KSC", "NYUUGAKU_ARRIVE.KSC", "NYUUGAKU_D.KSC", "KOUCHOU1.KSC", "MAEFURI.KSC", "MAIN.KSC",
               "SHARE.KSC"],
    # aulas: scripts em ordem numerica dentro de cada grupo (ver grupo())
    "take": ["TAKE"],
    "masa": ["MASA", "MASATK", "MASAPD", "MASAST", "MASASP", "MASAIP", "MASAIQ"],
    "miya": ["MIYA", "MIYASP"],
    # eventos e clubes: nome com .KSC e o script exato, sem .KSC e prefixo de grupo numerado
    "eventos": ["MASABUS.KSC", "SOTSUGYO_ARRIVE.KSC", "SOTSUGYO.KSC", "NISHISP", "ASCHOOL", "OSCHOOL", "SKETCH.KSC",
                "SYUGYO", "SARU_INTRO.KSC", "SARU", "_CLUB_JAPAN.KSC", "_CLUB_MASAMI_IQ", "_CLUB_NANKAIKANJI.KSC",
                "_CLUB_SHIRITORI.KSC", "ADHOC.KSC", "INPSP.KSC"],
    # dicionario do Shiritori em equipes: so as palavras; as leituras em kana ficam no original (ksc.reading_slots)
    "shiritori": ["_SHIRITORI_TEAM"],
    # aulas em que quem joga digita palavras (os pares palavra|leitura vao para o vocabulario)
    "inp": ["INP"],
}


def grupo(iso, prefixos):
    """Scripts KSC de cada prefixo (TAKE1, TAKE2, ...), em ordem numerica."""
    nomes = [n for n, _, _ in ksc_files(iso)]
    out = []
    for pre in prefixos:
        achados = [n for n in nomes if re.fullmatch(re.escape(pre) + r"\d+\.KSC", n)]
        out += sorted(achados, key=lambda n: int(re.search(r"(\d+)\.KSC$", n).group(1)))
    return out
LOTE_CHARS = 4000
MAX_BYTES = 600
SHORT_POOL = 8      # pool japones com ate 8 caracteres: opcao, nome ou titulo em caixa que nao quebra
SHORT_WIDTH = 190   # largura maxima de uma linha nessas caixas (unidades de widths.py)


KANA = re.compile(r"^[ぁ-ゖァ-ヺー・]+$")
WORDISH = re.compile(r"^[^\s、。！？!?{}…～/]{1,14}$")
HAS_KANJI_KATA = re.compile(r"[一-鿿ァ-ヺ]")


def hira(s):
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)


def is_reading(word, reading):
    """reading pode ser a leitura de word: kana de word aparecem iguais, cada kanji vale de 1 a 3 kana."""
    pat, k = "", 0
    word = hira(word)
    while k < len(word):
        if "一" <= word[k] <= "鿿" or word[k] in "々〆":
            n = 1
            while k + n < len(word) and ("一" <= word[k + n] <= "鿿" or word[k + n] in "々〆"):
                n += 1
            pat += ".{%d,%d}" % (n, 3 * n)
            k += n
        else:
            pat += re.escape(word[k])
            k += 1
    return re.fullmatch(pat, hira(reading)) is not None


def vocab_pairs(texts):
    """Indices de pares palavra|leitura numa sequencia do pool: texto so de kana logo depois de uma palavra curta
    com kanji ou katakana. As leituras servem ao shiritori e aos exercicios de leitura: ficam para a fase de
    vocabulario."""
    cand = set()
    for k in range(1, len(texts)):
        a, b = texts[k - 1], texts[k]
        if (a and b and KANA.match(b) and WORDISH.match(a) and HAS_KANJI_KATA.search(a) and a != b
                and is_reading(a, b)):
            cand.add(k - 1)
    # pares de verdade vem em sequencia (palavra, leitura, palavra, leitura...); par isolado e lista de atributos
    out = set()
    for i in cand:
        if cand & {i - 2, i - 3, i + 2, i + 3}:
            out.update((i, i + 1))
    return out


def reading_only(d):
    """Offsets do pool usados so como leitura do dicionario do Shiritori (nao aparecem como texto)."""
    slots = reading_slots(d)
    other = {po for po, _, _ in pool_refs_ex(d).values()}
    other |= {v & 0xFFFFFFF for k, v in enumerate(table_values(d)) if v >> 28 == 5 and k not in slots}
    return set(slots.values()) - other


def done_ids():
    out = set()
    for path in glob.glob(os.path.join(ROOT, "traducao", "*.jsonl")):
        for line in open(path, encoding="utf-8"):
            if line.strip():
                out.add(json.loads(line)["id"])
    return out


def gerar(iso_path, fase):
    iso = Iso(iso_path)
    items = collect(iso)
    by_text = {it["jp"]: it for it in items}
    files = {n: (o, s) for n, o, s in ksc_files(iso)}
    done = done_ids()
    order, seen, vocab = [], set(), []

    def texts_of(group):
        out = []
        for raw in group.values():
            try:
                out.append(to_text(raw, extra=True))
            except (UnicodeDecodeError, KeyError):
                out.append("")
        return out

    nomes = [n for e in FASES[fase] for n in ([e] if e.endswith(".KSC") else grupo(iso, [e]))]
    for name in nomes:
        d = iso.bp(*files[name])
        inline, pool = extract(d)
        tin, tpool = texts_of(inline), texts_of(pool)
        so_leitura = reading_only(d)
        # no Shiritori os pares palavra|leitura sao o proprio conteudo: a palavra e traduzida, a leitura nao
        pairs = set() if fase == "shiritori" else vocab_pairs(tpool)
        offs = [None] * len(tin) + list(pool)
        for k, text in enumerate(tin + tpool):
            it = by_text.get(text)
            if not it or it["id"] in seen or it["id"] in done or offs[k] in so_leitura:
                continue
            seen.add(it["id"])
            row = {"id": it["id"], "tipo": it["tipo"], "jp": it["jp"], "arquivo": name}
            (vocab if k >= len(tin) and k - len(tin) in pairs else order).append(row)
    with open(os.path.join(ROOT, "work", "lotes", f"{fase}_vocabulario.jsonl"), "w", encoding="utf-8") as f:
        for r in vocab:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(len(vocab), "textos de pares palavra|leitura separados para a fase de vocabulario")
    out_dir = os.path.join(ROOT, "work", "lotes")
    os.makedirs(out_dir, exist_ok=True)
    lote, chars, n = [], 0, 0
    for row in order + [None]:
        if row is None or (chars >= LOTE_CHARS and lote):
            n += 1
            path = os.path.join(out_dir, f"{fase}_{n:02d}.jsonl")
            with open(path, "w", encoding="utf-8") as f:
                for r in lote:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(path, len(lote), "textos", chars, "caracteres")
            lote, chars = [], 0
            if row is None:
                break
        lote.append(row)
        chars += len(row["jp"])


def conferir(iso_path, paths):
    items = {it["id"]: it for it in collect(Iso(iso_path))}
    erros = 0
    for path in paths:
        lote_path = os.path.join(ROOT, "work", "lotes", os.path.basename(path))
        esperado = [json.loads(l)["id"] for l in open(lote_path, encoding="utf-8")] if os.path.exists(lote_path) else None
        rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
        ids = [r["id"] for r in rows]
        problemas = []
        if esperado is not None and sorted(ids) != sorted(esperado):
            faltam = sorted(set(esperado) - set(ids))
            sobram = sorted(set(ids) - set(esperado))
            problemas.append(f"ids: faltam {faltam[:10]} sobram {sobram[:10]}")
        if len(ids) != len(set(ids)):
            problemas.append("ids repetidos")
        for r in rows:
            it = items.get(r["id"])
            if it is None:
                problemas.append(f"{r['id']}: id inexistente")
                continue
            pt = r["pt"]
            if sorted(TOKEN.findall(it["jp"])) != sorted(TOKEN.findall(pt)):
                problemas.append(f"{r['id']}: variaveis diferentes do original")
            if re.findall(r"\$[A-Za-z]+", it["jp"]) != re.findall(r"\$[A-Za-z]+", pt):  # \w pegaria o japones colado
                problemas.append(f"{r['id']}: marcadores $ diferentes")
            if chr(92) in pt:
                problemas.append(f"{r['id']}: barra invertida (use a quebra de linha de verdade, nao barra-n)")
            if JP.search(TOKEN.sub("", pt)):
                problemas.append(f"{r['id']}: sobrou japones")
            try:
                n = len(to_bytes(pt))
            except UnicodeEncodeError as e:
                problemas.append(f"{r['id']}: caractere sem codigo no jogo ({e.object[e.start]!r})")
                continue
            if n > MAX_BYTES:
                problemas.append(f"{r['id']}: {n} bytes (maximo {MAX_BYTES})")
            jp_plain = TOKEN.sub("", it["jp"])
            if it["tipo"] == "pool" and len(jp_plain) <= SHORT_POOL and "\n" not in it["jp"]:
                w = max(width(TOKEN.sub("Nnnnnn", line)) for line in pt.split("\n"))
                if w > SHORT_WIDTH:
                    problemas.append(f"{r['id']}: texto curto largo demais para caixa ({w:.0f} > {SHORT_WIDTH})")
        erros += len(problemas)
        print(f"{os.path.basename(path)}: {len(rows)} textos, {len(problemas)} problemas")
        for p in problemas[:40]:
            print("   ", p)
    return erros


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "gerar":
        gerar(sys.argv[2], sys.argv[3])
    elif cmd == "conferir":
        sys.exit(1 if conferir(sys.argv[2], sys.argv[3:]) else 0)
