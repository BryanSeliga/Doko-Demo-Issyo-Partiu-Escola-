"""Dados iniciais do jogo (TITLE.BPM DEFPLAYDATA.BIN): o vocabulario inicial do Toro.

O arquivo e uma arvore de valores de 4 bytes com tag no nibble alto (9 = lista com n valores, B = ponteiro para
lista, 6 = ponteiro para texto, 2 = inteiro), sem alinhamento. Cada palavra e uma lista 0x90000010: o valor 1 e a
palavra, o valor 2 a leitura em kana (tag 6, offsets absolutos) e o valor 3 o tamanho da palavra em caracteres; os
textos ficam logo depois da lista. Os 163 registros sao o nome "Toro" e as 162 palavras do gato, na mesma ordem do
NEKO.DIC do Issyo (tools/dic.py de la), cuja traducao e reaproveitada aqui. O mesmo arquivo traz os nomes padrao
dos 5 Pokepi que aparecem no teclado do nome (NAMES).

O jogo agrupa as palavras no Caderno e encadeia o Shiritori pela leitura. Ela passa a ser a propria palavra em
portugues (Shiritori por letras), e o registro guarda tambem, ja calculados, as flags (valor 0) e o codigo do
primeiro caractere da leitura (valor 0xE). Como os textos mudam de tamanho, o arquivo e remontado e todos os
ponteiros (tags B e 6) sao corrigidos. O fim do arquivo (listas vazias
que nada referencia) so e deslocado. Vale para jogo novo: um save ja criado guarda as palavras de quando foi criado.
"""
import bisect
import struct

import shiritori_code
from gtext import to_bytes

NEKO = [
    "Gato", "Mangaká", "Assalariado", "Espião", "Sushiman", "Apostador", "Musa", "Modelo", "Piloto", "Perdedor",
    "Megera", "Otaku", "Paparazzo", "Bêbado", "Besouro", "Caracol", "Baleia", "Leão", "ET", "Pulga-d'água",
    "Barata", "Cupim", "Lagostim", "Sushi", "Atum", "Ouriço", "Ovas", "Sundae", "Natto", "Pudim",
    "Tataki", "Maionese", "Wasabi", "Cebola", "Casca", "Alho", "Gengibre", "Picles", "Mentaiko", "Mostarda",
    "Pimenta", "Gelatina", "Missô", "Chá gelado", "Suco", "Leite quente", "Refri", "Chá oolong", "Shoyu", "Molho",
    "Trem-bala", "Triciclo", "Roda-gigante", "Carrossel", "Viatura", "Ambulância", "Caminhão", "Limpa-fossa",
    "Carrinho", "Rosto",
    "Olho", "Pinta", "Rabo", "Clavícula", "Costas", "Tanquinho", "Cintura", "Umbigo", "Tornozelo", "Frieira",
    "Cólica", "Rinite", "Ressaca", "Dor de amor", "Olá", "Tchau", "Passeio", "Banho de sol", "Praia", "Soneca",
    "Agito", "Cartomancia", "Bocha", "Skate", "Karaokê", "Videogame", "Mahjong", "Romance", "Diário a dois", "Paixão",
    "Encontro", "Simpatia", "Promessa", "Almofadada", "Luta livre", "Estudo", "Esquecimento", "Beisebol", "Esforço",
    "Trabalho",
    "Noitada", "Briga", "Faxina", "Lavar WC", "Lavar roupa", "Acordar cedo", "Telefonema", "Declaração", "Amor",
    "Presente",
    "Amor secreto", "Massagem", "Cafuné", "Beijo", "Tapinhas", "Spa", "Fofoca", "Traição", "Ciúme", "Mandinga",
    "Peteleco", "Travessura", "Infantilizar", "Vacina", "Mercadinho", "Sushiaria", "Videokê", "Posto policial",
    "Biblioteca", "Bombeiros",
    "Delegacia", "Templo", "Parquinho", "Shinjuku", "Harajuku", "Asakusa", "Escola", "Hotel cápsula", "Torre Tóquio",
    "Festa Nebuta",
    "Havaí", "Anisong", "Enka", "Yodel", "Heavy metal", "Frigideira", "Toalha", "Travesseiro", "Fita adesiva",
    "Máscara",
    "Chinelo", "Vestido", "Vídeo", "Micro-ondas", "Escova", "Touca", "Batom", "Papelão", "Computador", "Despertador",
    "Prendedor", "Ábaco",
]
WORDS = ["Toro"] + NEKO
# Nomes padrao dos Pokepi no teclado do nome (lista apontada pelo valor 1 da raiz, 5 textos tag 6), na ordem do
# arquivo. Os mesmos nomes das falas (traducao dos ids 6746-6750)
NAMES = ["Toro", "Suzuki", "Jun", "Pierre", "Ricky"]
NUL = bytes(1)


def u32(d, p):
    return struct.unpack_from("<I", d, p)[0]


def parse(d):
    """(listas {offset: n}, ponteiros [offset do valor]) a partir da lista raiz em 0."""
    lists, slots, todo = {}, [], [0]
    while todo:
        p = todo.pop()
        if p in lists:
            continue
        h = u32(d, p)
        assert h >> 28 == 9, (hex(p), hex(h))
        lists[p] = h & 0xFFFFFFF
        for k in range(lists[p]):
            q = p + 4 + 4 * k
            v = u32(d, q)
            if v >> 28 == 0xB:
                slots.append(q)
                todo.append(v & 0xFFFFFFF)
            elif v >> 28 == 6:
                slots.append(q)
    return lists, slots


def word_records(d, lists):
    """Offsets das listas de palavra (0x90000010 com palavra e leitura), na ordem do arquivo."""
    return [p for p, n in sorted(lists.items())
            if n == 0x10 and u32(d, p + 8) >> 28 == 6 and u32(d, p + 12) >> 28 == 6]


def name_list(d, lists):
    """Offset da lista dos nomes padrao dos Pokepi: valor 1 da raiz, uma lista so de textos (tag 6)."""
    v = u32(d, 8)
    assert v >> 28 == 0xB, hex(v)
    p = v & 0xFFFFFFF
    assert lists[p] == len(NAMES) and all(u32(d, p + 4 + 4 * k) >> 28 == 6 for k in range(lists[p])), hex(p)
    return p


def rebuild(d, words=None, names=None):
    words, names = words or WORDS, names or NAMES
    lists, slots = parse(d)
    recs = word_records(d, lists)
    assert len(recs) == len(words), (len(recs), len(words))
    nl = name_list(d, lists)
    # textos em ordem de posicao: (inicio do texto, valor com o tamanho em caracteres ou None, texto novo)
    plan = [(u32(d, p + 8) & 0xFFFFFFF, p + 16, w) for p, w in zip(recs, words)]
    # a leitura passa a ser a propria palavra (Shiritori por letras, ver shiritori_code)
    plan += [(u32(d, p + 12) & 0xFFFFFFF, None, w) for p, w in zip(recs, words)]
    plan += [(u32(d, nl + 4 + 4 * k) & 0xFFFFFFF, None, w) for k, w in enumerate(names)]
    plan.sort()
    assert len({at for at, q, w in plan}) == len(plan)
    out, i, ends, shifts = bytearray(), 0, [], []
    for at, q, w in plan:
        end = d.index(NUL, at) + 1
        out += d[i:at] + to_bytes(w) + NUL
        i = end
        ends.append(end)
        shifts.append(len(out) - end)
    out += d[i:]

    def moved(old):
        k = bisect.bisect_right(ends, old)
        return old + (shifts[k - 1] if k else 0)

    for q in slots:
        v = u32(d, q)
        struct.pack_into("<I", out, moved(q), (v & 0xF0000000) | moved(v & 0xFFFFFFF))
    for at, q, w in plan:
        if q is not None:  # valor 3 do registro de palavra: tamanho em caracteres
            struct.pack_into("<I", out, moved(q), (u32(d, q) & 0xF0000000) | len(w))
    for p, w in zip(recs, words):  # valor 0 = flags, valor 0xE = codigo do primeiro caractere da leitura
        flags, first = shiritori_code.record_values(u32(d, p + 4), to_bytes(w))
        struct.pack_into("<I", out, moved(p + 4), flags)
        struct.pack_into("<I", out, moved(p + 4 + 4 * 0xE), first)
    return bytes(out)
