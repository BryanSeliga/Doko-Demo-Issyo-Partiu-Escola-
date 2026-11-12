"""Video do icone do jogo no menu do PSP (PSP_GAME/ICON1.PMF): 300 quadros de 144x80 em H.264, sem som.

O logotipo japones aparece no primeiro segundo (cartao rosa que se dissolve na cena) e no fim (o cartao volta).
So esses quadros mudam; o resto do video fica como esta, byte a byte.

O arquivo e um cabecalho de 0x800 bytes e 70 pacotes de 2048 bytes. O video vem em 6 grupos de quadros (GOPs),
cada um comecando num pacote novo com: cabecalho de sistema, um pacote de navegacao (0xBF) com a tabela
(marca, tamanho) de cada quadro do grupo, e o primeiro pedaco do video com o tempo do quadro. Alguns pacotes no
meio do grupo tambem trazem tempo: e o do primeiro quadro que comeca dentro deles (90000 + n * 3003).

A troca recodifica so os grupos que tem quadro mudado (o primeiro e os dois ultimos), cada um num tamanho menor
ou igual ao original e completado com enchimento ate o tamanho exato. Assim nenhum pacote muda de lugar: so
mudam os bytes de video desses grupos, os tempos dos pacotes do meio deles e as tabelas de navegacao.

Precisa do ffmpeg com libx264 (pacote imageio-ffmpeg). Sem ele, build() devolve None e o video original fica.
"""
import re
import struct
import subprocess

import numpy as np
from PIL import Image, ImageFilter

import xmb

W, H = 144, 80
HEADER = 0x800
PACK = 2048
FIRST_PTS, TICKS = 90000, 3003   # tempo do primeiro quadro e duracao de um quadro (29,97 por segundo)
START = b"\x00\x00\x01"
AUD = START + b"\x09"            # todo quadro comeca com este marcador (precedido de um zero)


def ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def get_ts(b):
    return ((b[0] >> 1 & 7) << 30) | (b[1] << 22) | ((b[2] >> 1) << 15) | (b[3] << 7) | (b[4] >> 1)


def put_ts(prefix, v):
    return bytes([prefix << 4 | (v >> 30 & 7) << 1 | 1, v >> 22 & 0xFF, (v >> 15 & 0x7F) << 1 | 1,
                  v >> 7 & 0xFF, (v & 0x7F) << 1 | 1])


def parse(data):
    """(video, pedacos, navegacao): o fluxo de video inteiro; pedacos = [(offset do payload no arquivo, tamanho,
    offset do tempo no arquivo ou None)]; navegacao = [offset no arquivo dos dados de cada pacote 0xBF]."""
    video, chunks, nav = bytearray(), [], []
    assert (len(data) - HEADER) % PACK == 0
    for base in range(HEADER, len(data), PACK):
        assert data[base:base + 4] == START + b"\xba", hex(base)
        i = base + 14 + (data[base + 13] & 7)
        while i + 6 <= base + PACK and data[i:i + 3] == START:
            sid, size = data[i + 3], struct.unpack_from(">H", data, i + 4)[0]
            if sid == 0xE0:
                flags, hl = data[i + 7], data[i + 8]
                pay = i + 9 + hl
                assert flags >> 6 in (0, 3), hex(i)  # sem tempo, ou com os dois (exibicao e decodificacao)
                chunks.append((pay, size - 3 - hl, i + 9 if flags >> 6 == 3 else None))
                video += data[pay:pay + size - 3 - hl]
            elif sid == 0xBF:
                nav.append(i + 6)
            i += 6 + size
    return bytes(video), chunks, nav


def frame_starts(video):
    """(offset do quadro contando os zeros antes do marcador, offset do marcador) de cada quadro."""
    out = []
    for m in re.finditer(re.escape(AUD), video):
        s = m.start()
        while s > 0 and video[s - 1] == 0:
            s -= 1
        out.append((s, m.start()))
    return out


def slice_info(unit):
    """(tipo do NAL de imagem, quadro de referencia?) de um quadro."""
    for m in re.finditer(re.escape(START), unit):
        head = unit[m.start() + 3]
        if head & 31 in (1, 5):
            return head & 31, bool(head >> 5 & 3)
    raise ValueError("quadro sem imagem")


def decode(exe, data):
    out = subprocess.run([exe, "-hide_banner", "-loglevel", "error", "-f", "mpeg", "-i", "-", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], input=data, capture_output=True, check=True).stdout
    return np.frombuffer(out, np.uint8).reshape(-1, H, W, 3)


def encode(exe, frames, qp):
    """Um grupo fechado (um quadro-chave e so quadros P), sem SEI: marcador de quadro, SPS e PPS no comeco."""
    n = len(frames)
    cmd = [exe, "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", "30000/1001", "-i", "-", "-c:v", "libx264", "-profile:v", "main", "-level:v", "2.1",
           "-pix_fmt", "yuvj420p", "-color_range", "pc", "-g", str(n), "-keyint_min", str(n), "-sc_threshold", "0",
           "-bf", "0", "-refs", "1", "-qp", str(qp), "-threads", "1", "-x264-params", "aud=1",
           "-bsf:v", "filter_units=remove_types=6", "-f", "h264", "-"]
    return subprocess.run(cmd, input=frames.tobytes(), capture_output=True, check=True).stdout


def filler(n):
    """n bytes de enchimento: um NAL de enchimento (tipo 12) ou, se nao couber, zeros (validos entre dois NALs)."""
    return START + b"\x0c" + b"\xff" * (n - 5) + b"\x80" if n >= 5 else b"\0" * n


def fit(exe, frames, size):
    """Grupo recodificado com exatamente size bytes: a melhor qualidade que cabe, e o que sobra vira enchimento
    repartido entre os quadros (assim os quadros ficam espalhados pelo grupo todo, como no original, e todo
    pacote com tempo tem um quadro comecando nele)."""
    for qp in range(12, 52):
        out = encode(exe, frames, qp)
        if len(out) <= size:
            break
    else:
        raise ValueError(f"grupo de {len(frames)} quadros nao cabe em {size} bytes")
    starts = frame_starts(out)
    n = len(starts)
    assert n == len(frames) and starts[0][0] == 0, (n, len(frames))
    ends = [s for s, _ in starts[1:]] + [len(out)]
    gap = size - len(out)
    parts = [out[starts[k][0]:ends[k]] + filler(gap // n + (k < gap % n)) for k in range(n)]
    return b"".join(parts), qp


def background(card):
    """Degrade do cartao sem o logotipo: a cor de cada linha vem da borda esquerda."""
    rows = np.median(card[:, :3].astype(float), axis=1)
    rows = np.array([np.median(rows[max(0, y - 6):y + 7], axis=0) for y in range(H)])
    return np.repeat(rows[:, None, :], W, axis=1)


def high_pass(img):
    gray = img.mean(axis=2)
    soft = Image.fromarray(np.clip(gray + 128, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3))
    return gray - (np.asarray(soft).astype(float) - 128)


def new_frames(frames):
    """(quadros novos, indices mudados). Em cada ponta do video o cartao de referencia e o quadro em que o
    logotipo esta inteiro (o primeiro e o ultimo); a forca do logotipo em cada quadro e medida pelo quanto dos
    contornos dele aparece, e o quadro novo e o original mais essa forca vezes (cartao novo - cartao velho)."""
    out, changed = frames.copy(), []
    n = len(frames)
    # de cada ponta para dentro, ate o primeiro quadro sem logotipo (no meio do video os contornos da cena as
    # vezes coincidem com os do logotipo e dariam falso positivo)
    for ref, span in ((0, range(0, n // 2)), (n - 1, range(n - 1, n // 2, -1))):
        old = frames[ref].astype(float)
        bg = background(old)
        card = Image.fromarray(bg.astype(np.uint8), "RGB").convert("RGBA")
        xmb.paste_logo(card, xmb.ICON_LOGO)
        new = np.asarray(card.convert("RGB")).astype(float)
        edges = high_pass(old - bg)
        full = (edges * edges).sum()
        for k in span:
            f = frames[k].astype(float)
            force = float((high_pass(f - bg) * edges).sum() / full)
            if force < 0.03:
                break
            force = min(force, 1.0)
            pic = new if force > 0.97 else f + force * (new - old)
            out[k] = np.clip(pic + 0.5, 0, 255).astype(np.uint8)
            changed.append(k)
    return out, changed


def build(data):
    """ICON1.PMF com o logotipo em portugues, do mesmo tamanho; None se nao houver ffmpeg."""
    exe = ffmpeg()
    if exe is None:
        print("icon_video: sem ffmpeg (pip install imageio-ffmpeg); o video do icone fica como esta")
        return None
    video, chunks, nav = parse(data)
    starts = frame_starts(video)
    ends = [s for s, _ in starts[1:]] + [len(video)]
    keys = [k for k, (s, _) in enumerate(starts) if slice_info(video[s:ends[k]])[0] == 5]
    assert len(keys) == len(nav) and keys[0] == 0, (keys, len(nav))
    frames = decode(exe, data)
    assert len(frames) == len(starts), (len(frames), len(starts))
    fresh, changed = new_frames(frames)
    new_video = bytearray(video)
    groups = []  # (primeiro quadro, fim, offset no video, tamanho)
    for g, a in enumerate(keys):
        b = keys[g + 1] if g + 1 < len(keys) else len(starts)
        if any(a <= k < b for k in changed):
            off, size = starts[a][0], ends[b - 1] - starts[a][0]
            part, qp = fit(exe, fresh[a:b], size)
            new_video[off:off + size] = part
            groups.append((g, a, b, off, size, qp))
    new_video = bytes(new_video)
    assert len(new_video) == len(video)
    new_starts = frame_starts(new_video)
    assert len(new_starts) == len(starts)
    new_ends = [s for s, _ in new_starts[1:]] + [len(new_video)]
    out = bytearray(data)
    pos = 0
    for pay, size, ts_at in chunks:
        out[pay:pay + size] = new_video[pos:pos + size]
        if ts_at is not None and any(off <= pos < off + sz for _, _, _, off, sz, _ in groups):
            k = next(k for k, (_, sc) in enumerate(new_starts) if pos <= sc < pos + size)
            pts = FIRST_PTS + k * TICKS
            out[ts_at:ts_at + 10] = put_ts(3, pts) + put_ts(1, pts - TICKS)
        pos += size
    for g, a, b, off, size, qp in groups:
        table = nav[g] + 14
        length, count = struct.unpack_from(">HH", data, table)
        assert count == b - a and length == 2 + 4 * count, (g, count, b - a)
        for j, k in enumerate(range(a, b)):
            ref = slice_info(new_video[new_starts[k][0]:new_ends[k]])[1]
            struct.pack_into(">HH", out, table + 4 + 4 * j, 0x80 if ref else 0, new_ends[k] - new_starts[k][0])
    out = bytes(out)
    assert len(out) == len(data) and len(decode(exe, out)) == len(frames)
    print("icon_video:", len(changed), "quadros mudados;", ", ".join(f"grupo {g} (quadros {a}-{b - 1}) qp {qp}"
                                                                    for g, a, b, _, _, qp in groups))
    return out
