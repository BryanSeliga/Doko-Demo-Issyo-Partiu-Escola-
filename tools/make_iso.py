"""Monta a ISO traduzida do Let's Gakkou. Uso: make_iso.py <iso_original> <iso_saida>

As traducoes ficam em traducao/*.jsonl, uma linha por texto: {"id": n, "pt": "..."}. O id e a posicao do texto
na lista de extract_all.collect (a mesma ISO sempre gera a mesma lista). O texto japones nunca fica no repositorio.
Cada texto traduzido e trocado em todos os scripts onde aparece, nas falas do codigo e no pool. Uma linha com
"so_em": ["NOME.KSC", ...] vale so nesses scripts, por cima da traducao geral (traducao/ajustes_por_script.jsonl).
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
import selos
import shiritori_code
import textures
import title_logo
import xmb

HERE = os.path.dirname(os.path.abspath(__file__))
# O op 4b copia a string do pool com strcpy para o buffer de fala do VM (+0x78, ate +0x477): mais que isso
# sobrescreve a base do pool (+0x480) e o jogo trava. O maior texto original tem 265 bytes.
MAX_BYTES = 600
PT_DIR = os.environ.get("PT_DIR", os.path.join(HERE, "..", "traducao"))  # PT_DIR troca a pasta nos testes
# Textos cuja traducao pode ter MENOS variaveis que o original (nunca outras). 2629: fala do Shiritori "palavra!
# (leitura)"; a leitura agora e a propria palavra e so repetia o texto, entao a traducao mostra so a palavra.
FEWER_VARS = {2629}


def same_vars(row, jp):
    """As variaveis da traducao sao as do original (nos textos de FEWER_VARS, parte delas, na mesma ordem)."""
    a, b = TOKEN.findall(jp), TOKEN.findall(row["pt"])
    if row["id"] in FEWER_VARS:
        return 0 < len(b) <= len(a) and b == a[:len(b)]
    return sorted(a) == sorted(b)


def load_translations(items):
    """({texto_jp: texto_pt}, {script: {texto_jp: texto_pt}}); confere se as variaveis do original ficaram na
    traducao. A segunda parte sao as linhas com "so_em": [scripts]: valem so nesses scripts, por cima da traducao
    geral (o mesmo texto e leitura numa aula e palavra de vocabulario em outra)."""
    by_id = {it["id"]: it["jp"] for it in items}
    out, only, bad = {}, {}, []
    for path in sorted(glob.glob(os.path.join(PT_DIR, "*.jsonl"))):
        for line in open(path, encoding="utf-8"):
            if not line.strip():
                continue
            row = json.loads(line)
            jp = by_id[row["id"]]
            if not same_vars(row, jp):
                bad.append(row["id"])
                continue
            if len(to_bytes(row["pt"])) > MAX_BYTES:
                sys.exit(f"texto {row['id']} passa de {MAX_BYTES} bytes e travaria o jogo")
            if "so_em" in row:
                for name in row["so_em"]:
                    only.setdefault(name, {})[jp] = row["pt"]
            else:
                out[jp] = row["pt"]
    if bad:
        print("variaveis diferentes do original (ignorados):", bad[:20], "..." if len(bad) > 20 else "")
    return out, only


# Rotina comum de todos os scripts que abre o teclado de nome: empilha a funcao 0x24, o tipo 3 (kana + ABC) e o
# limite 4, e chama o sistema (8b f1 03). O limite passa a 7, como no Issyo: "Sophia" tem 6 letras.
NAME_CALL = bytes.fromhex("8024 8003 8004 8bf103")
NAME_CALL_NEW = bytes.fromhex("8024 8003 8007 8bf103")
# O mesmo para o teclado das palavras ensinadas (tipo 1): o limite era 8 caracteres, que em kana sao 16 bytes.
# Letras latinas ocupam 1 byte: os campos fixos do BOOT para a palavra tem 17 bytes e as copias para eles sao
# limitadas e sempre terminam o texto (rotina 0xF5B8), e o teclado ja trabalha com limite 16 nos campos de
# leitura (tipos 2 e 7). Com 16 letras o jogo funciona e o save abre, mas no Caderno a coluna da palavra so
# comporta umas 11 letras largas e o texto passa por cima da leitura; por isso o limite fica em 12.
WORD_CALL = bytes.fromhex("8024 85 8008 8bf103")
WORD_CALL_NEW = bytes.fromhex("8024 85 800c 8bf103")
# A chamada tem uma segunda forma, com um argumento a mais (8b f1 04), usada logo antes de abrir o teclado ao
# ensinar uma palavra (cerca de uma por script); a de 3 argumentos devolve o limite ao padrao depois de trocas
WORD_CALL4 = bytes.fromhex("8024 85 8008 8001 8bf104")
WORD_CALL4_NEW = bytes.fromhex("8024 85 800c 8001 8bf104")


def keyboard_limits(d):
    d = d.replace(NAME_CALL, NAME_CALL_NEW)
    return d.replace(WORD_CALL, WORD_CALL_NEW).replace(WORD_CALL4, WORD_CALL4_NEW)

# Nome da escola. O jogo nao pede esse nome: no roteiro do diretor ele junta o nome de quem joga com um sufixo
# ("K" + sufixo), e em portugues saia "KEscola". A ordem natural e a contraria ("Escola K", como "Escola Movel" e
# "Escola Kuro"): os dois operandos da juncao trocam de lugar, o que nao muda o tamanho do codigo, e so neste
# script o sufixo ganha um espaco no fim (o mesmo texto e palavra de vocabulario em outras aulas).
#   95 00 00 80 1d f5   destino: campo 0x1d (nome da escola)
#   95 00 00 85 f4      nome de quem joga         -> passa para depois do sufixo
#   88 <pool>           sufixo
#   e0 51               junta e guarda
SCHOOL_KSC = "KOUCHOU1.KSC"
SCHOOL_JOIN = re.compile(rb"(\x95\x00\x00\x80\x1d\xf5)(\x95\x00\x00\x85\xf4)(\x88...)(\xe0\x51)", re.S)
SCHOOL_JP, SCHOOL_PT = "\u5b66\u6821", "Escola"


def school_name(d, pt):
    """(script com a juncao invertida, traducoes deste script com o sufixo seguido de espaco)."""
    hits = list(SCHOOL_JOIN.finditer(d))
    assert len(hits) == 1, len(hits)
    m = hits[0]
    assert pt.get(SCHOOL_JP) == SCHOOL_PT, pt.get(SCHOOL_JP)
    return d[:m.start(2)] + m.group(3) + m.group(2) + d[m.end(3):], {**pt, SCHOOL_JP: SCHOOL_PT + " "}


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
        return keyboard_limits(d), 0
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
    return keyboard_limits(out), len(new_inline) + len(new_pool)


def main(src, dst):
    iso = Iso(src)
    items = collect(iso)
    pt, only = load_translations(items)
    names = {name for name, _, _ in ksc_files(iso)}
    assert set(only) <= names, sorted(set(only) - names)
    top, total = {}, 0
    for name, off, size in ksc_files(iso):
        d, ptk = iso.bp(off, size), ({**pt, **only[name]} if name in only else pt)
        if name == SCHOOL_KSC:
            d, ptk = school_name(d, ptk)  # "Escola K" em vez de "KEscola"
        new, n = apply(d, ptk)
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
    # e texto desenhado no cenario (lanternas, placas, etiquetas, o bilhete do album) e nos selos de avaliacao
    images = {**gui_render.build_all(iso, bpms), **textures.build_all(iso, bpms), **selos.build_all(iso, bpms)}
    for (pack, name), data in images.items():
        bpm.setdefault(pack, {})[name] = data
    print(f"{sum(len(v) for v in bpm.values())} imagens em {len(bpm)} pacotes")
    boot = boot_text.patch_boot(iso.read(BOOT_LBA, BOOT_SIZE))  # menus, botoes e janelas do sistema
    loose = xmb.build(iso)  # titulo, icone e painel do jogo no menu do PSP
    print("DATA.BP ->", build(src, dst, top=top, bpm=bpm, boot=boot, loose=loose))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
