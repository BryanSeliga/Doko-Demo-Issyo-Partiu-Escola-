"""Leitor e gravador de GIM do PSP nos formatos usados pelo jogo (RGBA e indexado, sem swizzle ou com)."""
import struct


def parse(data):
    """Lista os blocos do GIM: (tipo, inicio, fim). Blocos: 2 imagem, 3 quadro, 4 pixels, 5 paleta."""
    assert data[:4] in (b"MIG.", b".GIM"), data[:4]
    blocks = []

    def walk(off, end):
        while off + 16 <= end:
            t, size, nxt, dat = struct.unpack_from("<HxxIII", data, off)
            blocks.append((t, off, off + size, off + dat))
            if t in (2, 3):
                walk(off + dat, off + size)
            off += nxt if nxt else size
            if not nxt and not size:
                break

    walk(16, len(data))
    return blocks


def image_info(data, block_off):
    """Campos do cabecalho de imagem em block_off (bloco 4 ou 5)."""
    d = block_off + 16
    fmt, order, w, h, bpp, pw, ph = struct.unpack_from("<HHHHHHH", data, d + 4)
    pix_off = struct.unpack_from("<I", data, d + 0x1C)[0]
    return {"fmt": fmt, "order": order, "w": w, "h": h, "bpp": bpp, "pix": d + pix_off, "pw": pw, "ph": ph}


def unswizzle(buf, stride, h):
    out = bytearray(len(buf))
    bw, bh = 16, 8
    rows = (h + bh - 1) // bh
    i = 0
    for r in range(rows):
        for bx in range(0, stride, bw):
            for y in range(bh):
                o = (r * bh + y) * stride + bx
                if o + bw <= len(out) and i + bw <= len(buf):
                    out[o:o + bw] = buf[i:i + bw]
                i += bw
    return bytes(out)


def swizzle(buf, stride, h):
    out = bytearray(len(buf))
    bw, bh = 16, 8
    rows = (h + bh - 1) // bh
    i = 0
    for r in range(rows):
        for bx in range(0, stride, bw):
            for y in range(bh):
                o = (r * bh + y) * stride + bx
                if o + bw <= len(buf) and i + bw <= len(out):
                    out[i:i + bw] = buf[o:o + bw]
                i += bw
    return bytes(out)


def to_rgba(data):
    """Decodifica a primeira imagem do GIM. Devolve (w, h, bytes RGBA, info)."""
    blocks = parse(data)
    img = next(b for b in blocks if b[0] == 4)
    pal = next((b for b in blocks if b[0] == 5), None)
    inf = image_info(data, img[1])
    w, h, bpp, fmt = inf["w"], inf["h"], inf["bpp"], inf["fmt"]
    pw = inf["pw"] if inf["pw"] else 8
    stride = ((w * bpp + 7) // 8)
    stride += (-stride) % 16
    size = stride * h
    if h % 8:
        size = stride * (h + 8 - h % 8)
    px = data[inf["pix"]:inf["pix"] + size]
    if inf["order"] == 1:
        px = unswizzle(px, stride, h)
    colors = None
    if pal:
        pi = image_info(data, pal[1])
        raw = data[pi["pix"]:pi["pix"] + pi["w"] * pi["bpp"] // 8]
        colors = _colors(raw, pi["fmt"], pi["w"])
    out = bytearray(w * h * 4)
    for y in range(h):
        for x in range(w):
            o = y * stride
            if fmt == 4:
                b = px[o + x // 2]
                c = colors[(b >> 4) if x & 1 else b & 15]
            elif fmt == 5:
                c = colors[px[o + x]]
            elif fmt == 3:
                c = tuple(px[o + x * 4:o + x * 4 + 4])
            else:
                c = _colors(px[o + x * bpp // 8:o + (x + 1) * bpp // 8], fmt, 1)[0]
            out[(y * w + x) * 4:(y * w + x) * 4 + 4] = bytes(c)
    return w, h, bytes(out), inf


def _colors(raw, fmt, n):
    out = []
    for i in range(n):
        if fmt == 3:
            out.append(tuple(raw[i * 4:i * 4 + 4]))
        else:
            v = struct.unpack_from("<H", raw, i * 2)[0]
            if fmt == 0:
                out.append(((v & 31) * 255 // 31, (v >> 5 & 63) * 255 // 63, (v >> 11 & 31) * 255 // 31, 255))
            elif fmt == 1:
                out.append(((v & 31) * 255 // 31, (v >> 5 & 31) * 255 // 31, (v >> 10 & 31) * 255 // 31, 255 if v >> 15 else 0))
            else:
                out.append(((v & 15) * 17, (v >> 4 & 15) * 17, (v >> 8 & 15) * 17, (v >> 12) * 17))
    return out


def to_gim8(template, im):
    """GIM indexado de 256 cores (CLUT8, sem swizzle) com a imagem RGBA im, copiando os cabecalhos de template.

    Serve para trocar uma textura de 16 cores por uma de 256: o arquivo cresce, entao vai para um BPM realocado.
    """
    w, h = im.size
    q = im.quantize(256, method=2)  # FASTOCTREE: unico metodo do Pillow que aceita RGBA
    pal = q.getpalette("RGBA") or []
    pal = bytes(pal[:1024]) + b"\0" * (1024 - len(pal[:1024]))
    stride = w + (-w) % 16
    px = bytearray(stride * h)
    src = q.tobytes()
    for y in range(h):
        px[y * stride:y * stride + w] = src[y * w:(y + 1) * w]
    blocks = parse(template)
    img = next(b for b in blocks if b[0] == 4)
    pb = next(b for b in blocks if b[0] == 5)
    img_info = bytearray(template[img[3]:img[3] + 0x40])
    pal_info = bytearray(template[pb[3]:pb[3] + 0x40])
    struct.pack_into("<HHHHH", img_info, 4, 5, 0, w, h, 8)
    struct.pack_into("<I", img_info, 0x20, 0x40 + len(px))
    struct.pack_into("<HHHH", pal_info, 4, 3, 0, 256, 1)
    struct.pack_into("<I", pal_info, 0x20, 0x40 + len(pal))
    b4 = bytes(img_info) + bytes(px)
    b5 = bytes(pal_info) + pal
    block4 = struct.pack("<HHIII", 4, 16, 16 + len(b4), 16 + len(b4), 16) + b4
    block5 = struct.pack("<HHIII", 5, 16, 16 + len(b5), 16 + len(b5), 16) + b5
    block3 = struct.pack("<HHIII", 3, 16, 16 + len(block4) + len(block5), 16, 16) + block4 + block5
    block2 = struct.pack("<HHIII", 2, 16, 16 + len(block3), 16, 16) + block3
    return template[:16] + block2
