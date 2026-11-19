#!/usr/bin/env python3
"""Arma el PDF de la presentación: una página por pantalla.

Cada página = la captura de la pantalla (JPEG a toda página) + una capa de texto invisible (para buscar y copiar)
+ marcadores (índice lateral) agrupados por tramo. Sin dependencias: escribe el PDF a mano.

Uso: python3 -I build_pdf.py <carpeta-capturas> <salida.pdf> <informe-scroll.html>
Variables: IMG_W (ancho del JPEG, 4320 = tal cual la captura al doble), Q (calidad JPEG), TEXT=0 (sin capa de texto),
           ONLY=1,2,3 (solo esas pantallas, para probar), JPG_DIR (dónde guardar los JPEG)
"""
import sys, os, re, json, zlib, subprocess, datetime, html as htmllib, unicodedata, secrets
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin

SHOTS, OUT_PDF, SRC_HTML = sys.argv[1], sys.argv[2], sys.argv[3]
PUBLIC_BASE = os.environ.get('PUBLIC_BASE', 'https://rendicionnqn2026.vercel.app/')   # donde viven los videos de los enlaces
IMG_W = int(os.environ.get('IMG_W', 4320))
Q = int(os.environ.get('Q', 82))
WITH_TEXT = os.environ.get('TEXT', '1') != '0'
ONLY = [int(x) for x in os.environ['ONLY'].split(',') if x.strip()] if os.environ.get('ONLY') else None
JPG_DIR = os.environ.get('JPG_DIR') or os.path.join(SHOTS, f'jpg-{IMG_W}-q{Q}')
CSS_W, CSS_H = 2160, 1080          # la ventana de proyección
PAGE_W, PAGE_H = 1440.0, 720.0     # página en puntos (2:1, 20 × 10 pulgadas)
S = PAGE_W / CSS_W                 # puntos por píxel CSS
os.makedirs(JPG_DIR, exist_ok=True)

meta = json.load(open(os.path.join(SHOTS, 'meta.json'), encoding='utf-8'))
meta = {m['n']: m for m in meta}
nums = sorted(n for n in meta if (ONLY is None or n in ONLY))


# ---------- JPEG ----------
def make_jpeg(n):
    png = os.path.join(SHOTS, f's{n:02d}.png')
    jpg = os.path.join(JPG_DIR, f'p{n:02d}.jpg')
    if os.path.exists(jpg) and os.path.getmtime(jpg) >= os.path.getmtime(png):
        return jpg
    vf = [] if IMG_W == 4320 else ['-vf', f'scale={IMG_W}:{IMG_W // 2}:flags=lanczos']
    ff = subprocess.Popen(['ffmpeg', '-loglevel', 'error', '-y', '-i', png, *vf, '-f', 'image2pipe', '-vcodec', 'ppm', '-'],
                          stdout=subprocess.PIPE)
    with open(jpg, 'wb') as fo:
        cj = subprocess.run(['cjpeg', '-quality', str(Q), '-optimize', '-sample', '2x2'], stdin=ff.stdout, stdout=fo)
    ff.stdout.close(); ff.wait()
    if ff.returncode or cj.returncode:
        raise RuntimeError(f'falló el JPEG de la pantalla {n}')
    return jpg


def jpeg_info(data):
    i = 2
    while i < len(data):
        if data[i] != 0xFF:
            i += 1; continue
        m = data[i + 1]
        if m in (0xC0, 0xC1, 0xC2):
            h = int.from_bytes(data[i + 5:i + 7], 'big'); w = int.from_bytes(data[i + 7:i + 9], 'big'); c = data[i + 9]
            return w, h, c
        if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7:
            i += 2; continue
        i += 2 + int.from_bytes(data[i + 2:i + 4], 'big')
    raise ValueError('JPEG sin SOF')


# ---------- títulos (marcadores) ----------
def slugify(s):
    t = unicodedata.normalize('NFD', s)
    t = ''.join(ch for ch in t if not unicodedata.combining(ch))
    return '-'.join(re.sub(r'[^a-z0-9]+', ' ', t.lower()).split()[:6])


def strip_tags(s):
    s = re.sub(r'<br\s*/?>', ' ', s)
    s = re.sub(r'<[^>]+>', '', s)
    return re.sub(r'\s+', ' ', htmllib.unescape(s)).strip()


src = open(SRC_HTML, encoding='utf-8').read()
cands = {}
def add_cand(t):
    t = t.strip()
    if t and slugify(t) not in cands:
        cands[slugify(t)] = t
for m in re.finditer(r'data-name="([^"]+)"', src):
    add_cand(htmllib.unescape(m.group(1)))
for m in re.finditer(r'<(\w+)\b[^>]*\bclass="[^"]*\b(?:tag|sr|trans-title)\b[^"]*"[^>]*>(.*?)</\1>', src, re.S):
    add_cand(strip_tags(m.group(2)))
for m in re.finditer(r'<figcaption[^>]*>(.*?)</figcaption>', src, re.S):
    add_cand('Video · ' + strip_tags(re.sub(r'<small>.*?</small>', '', m.group(1), flags=re.S)))

PARTS = {'enc': 'Lo que encontramos', 'giro': 'El giro', 'hic': 'Lo que hicimos'}


def heuristic_title(words):
    c = [w for w in words if re.search(r'[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{3,}', w[0]) and not re.search(r'\d', w[0])]
    if not c:
        return ''
    mx = max(w[5] for w in c)
    top = [w for w in c if w[5] >= mx * 0.9]
    top.sort(key=lambda w: (round(w[2] / (mx * 0.8)), w[1]))
    return ' '.join(w[0] for w in top)[:80]


OVERRIDES = {1: 'Portada'}
TITLE_ONLY = {45: 'Centro de Artes Escénicas “La Usina”', 46: 'Neuquén Habita'}  # v124: #45 es La Usina y #46 Habita (v117: #46 y #47; el v124 sacó «Transición planificada»); v117 aclaraba (su hash sale del epígrafe del video; en v101 Habita era #46)


def page_info(n):
    h = meta[n].get('hash', '').lstrip('#')
    if n in OVERRIDES:
        m0 = re.match(r'^\d{2}-(?:(enc|giro|hic)-)?', h)
        return ((m0.group(1) or '') if m0 else ''), OVERRIDES[n]
    m = re.match(r'^(\d{2})-(?:(enc|giro|hic)-)?(.*)$', h)
    part = (m.group(2) or '') if m else ''
    sl = m.group(3) if m else h
    title = cands.get(sl)
    if not title:
        ht = heuristic_title(meta[n].get('words', []))
        if sl.startswith('titulo-'):
            title = 'Título · ' + (ht or sl[7:].replace('-', ' '))
        else:
            title = ht or sl.replace('-', ' ').capitalize()
    title = TITLE_ONLY.get(n, title)
    return part, title


# ---------- PDF a mano ----------
WIN = {'−': '-', '‑': '-', '→': '->', '↓': 'v', '←': '<-', '↑': '^', '≈': '~', ' ': ' ',
       ' ': ' ', '≤': '<=', '≥': '>='}


def pdf_str(s):
    for k, v in WIN.items():
        s = s.replace(k, v)
    b = s.encode('cp1252', errors='replace')
    return b.replace(b'\\', b'\\\\').replace(b'(', b'\\(').replace(b')', b'\\)')


def utf16hex(s):
    return '<FEFF' + s.encode('utf-16-be').hex().upper() + '>'


class PDF:
    def __init__(self):
        self.objs = []
    def reserve(self):
        self.objs.append(None); return len(self.objs)
    def set(self, num, body):
        self.objs[num - 1] = body
    def add(self, body):
        self.objs.append(body); return len(self.objs)
    def stream(self, d, data):
        return b'<< ' + d.encode() + b' /Length ' + str(len(data)).encode() + b' >>\nstream\n' + data + b'\nendstream'
    def write(self, path, root, info):
        out = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
        offs = []
        for i, body in enumerate(self.objs, 1):
            offs.append(len(out))
            out += f'{i} 0 obj\n'.encode() + body + b'\nendobj\n'
        xpos = len(out)
        out += f'xref\n0 {len(self.objs) + 1}\n'.encode() + b'0000000000 65535 f \n'
        for o in offs:
            out += f'{o:010d} 00000 n \n'.encode()
        ident = secrets.token_hex(16)
        out += (f'trailer\n<< /Size {len(self.objs) + 1} /Root {root} 0 R /Info {info} 0 R /ID [<{ident}> <{ident}>] >>\n'
                f'startxref\n{xpos}\n%%EOF\n').encode()
        open(path, 'wb').write(out)


def text_ops(words):
    seen, items = set(), []
    for w in words:
        key = (w[0], round(w[1] / 2), round(w[2] / 2))
        if key in seen:
            continue
        seen.add(key); items.append(w)
    ops = [b'BT', b'0 Tr 1 0 0 rg'] if os.environ.get('DEBUG_TEXT') else [b'BT', b'3 Tr']   # DEBUG_TEXT=1: texto visible en rojo para revisar la alineación
    last_fs = None
    for i, (w, x, y, wd, ht, fs, tz) in enumerate(items):
        nxt = items[i + 1] if i + 1 < len(items) else None
        same = nxt is not None and abs(nxt[2] - y) < max(2.0, ht * 0.35) and nxt[1] >= x
        s = w + (' ' if same else '')
        size = max(fs * S, 1.0)
        base = y + 0.78 * ht                      # línea de base en px CSS (y hacia abajo): Manrope, ascenso 1,066 de 1,366 em
        px, py = x * S, PAGE_H - base * S
        tz = min(max(tz, 10.0), 500.0)
        ops.append(f'/F1 {size:.2f} Tf {tz:.1f} Tz 1 0 0 1 {px:.2f} {py:.2f} Tm'.encode() + b' (' + pdf_str(s) + b') Tj')
    ops.append(b'ET')
    return b'\n'.join(ops)


def main():
    if os.environ.get('TITLES_ONLY'):
        for n in nums:
            part, title = page_info(n)
            print(f'  #{n:02d} [{part or "-":4}] {title}')
        return
    with ThreadPoolExecutor(4) as ex:
        jpgs = dict(zip(nums, ex.map(make_jpeg, nums)))
    pdf = PDF()
    cat, pages_root, font = pdf.reserve(), pdf.reserve(), pdf.reserve()
    pdf.set(font, b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>')
    page_ids, infos = [], []
    for n in nums:
        data = open(jpgs[n], 'rb').read()
        w, h, comps = jpeg_info(data)
        assert comps == 3 and w * 1 == IMG_W and h * 2 == IMG_W, (n, w, h, comps)
        im = pdf.add(pdf.stream(f'/Type /XObject /Subtype /Image /Width {w} /Height {h} /ColorSpace /DeviceRGB '
                                f'/BitsPerComponent 8 /Filter /DCTDecode', data))
        ops = f'q {PAGE_W:.0f} 0 0 {PAGE_H:.0f} 0 0 cm /Im0 Do Q\n'.encode()
        if WITH_TEXT:
            ops += text_ops(meta[n].get('words', []))
        ct = pdf.add(pdf.stream('/Filter /FlateDecode', zlib.compress(ops, 9)))
        # enlaces: cada video con reproductor (cartel con ▶) abre el archivo de video en el sitio publicado
        annots = []
        for lk in meta[n].get('links', []):
            url = urljoin(PUBLIC_BASE, lk['src'])
            assert url.isascii() and not re.search(r'[\\()\s]', url), url
            x1, y1, x2, y2 = lk['rect']
            rect = f'{x1 * S:.2f} {PAGE_H - y2 * S:.2f} {x2 * S:.2f} {PAGE_H - y1 * S:.2f}'
            annots.append(pdf.add(f'<< /Type /Annot /Subtype /Link /Rect [{rect}] /Border [0 0 0] /F 4 '
                                  f'/Contents {utf16hex("Ver el video: " + (lk.get("title") or "video"))} '
                                  f'/A << /S /URI /URI ({url}) >> >>'.encode()))
        an = (' /Annots [' + ' '.join(f'{a} 0 R' for a in annots) + ']') if annots else ''
        pg = pdf.add(f'<< /Type /Page /Parent {pages_root} 0 R /MediaBox [0 0 {PAGE_W:.0f} {PAGE_H:.0f}] '
                     f'/Resources << /XObject << /Im0 {im} 0 R >> /Font << /F1 {font} 0 R >> >> /Contents {ct} 0 R{an} >>'.encode())
        page_ids.append(pg); infos.append(page_info(n))
    pdf.set(pages_root, ('<< /Type /Pages /Kids [' + ' '.join(f'{p} 0 R' for p in page_ids) + f'] /Count {len(page_ids)} >>').encode())

    # marcadores: portada y cierre sueltos; el resto agrupado por tramo
    groups = []   # (titulo_grupo|None, [(idx, titulo)])
    for idx, (n, (part, title)) in enumerate(zip(nums, infos)):
        label = f'#{n:02d} {title}'
        gname = PARTS.get(part)
        if gname is None:
            groups.append((None, [(idx, label)]))
        elif groups and groups[-1][0] == gname:
            groups[-1][1].append((idx, label))
        else:
            groups.append((gname, [(idx, label)]))
    root = pdf.reserve()
    top = []   # (obj id, hijos)
    for gname, items in groups:
        if gname is None:
            top.append((pdf.reserve(), None, items[0]))
        else:
            top.append((pdf.reserve(), [(pdf.reserve(), it) for it in items], (None, gname, items[0][0])))
    def dest(i):
        return f'/Dest [{page_ids[i]} 0 R /Fit]'
    count_all = 0
    for k, (oid, kids, head) in enumerate(top):
        prev = f' /Prev {top[k - 1][0]} 0 R' if k else ''
        nxt = f' /Next {top[k + 1][0]} 0 R' if k + 1 < len(top) else ''
        if kids is None:
            idx, label = head
            pdf.set(oid, f'<< /Title {utf16hex(label)} /Parent {root} 0 R{prev}{nxt} {dest(idx)} >>'.encode())
            count_all += 1
        else:
            _, gtitle, first_idx = head
            pdf.set(oid, (f'<< /Title {utf16hex(gtitle)} /Parent {root} 0 R{prev}{nxt} /First {kids[0][0]} 0 R /Last {kids[-1][0]} 0 R '
                          f'/Count {len(kids)} {dest(first_idx)} >>').encode())
            count_all += 1 + len(kids)
            for j, (kid, (idx, label)) in enumerate(kids):
                kp = f' /Prev {kids[j - 1][0]} 0 R' if j else ''
                kn = f' /Next {kids[j + 1][0]} 0 R' if j + 1 < len(kids) else ''
                pdf.set(kid, f'<< /Title {utf16hex(label)} /Parent {oid} 0 R{kp}{kn} {dest(idx)} >>'.encode())
    pdf.set(root, f'<< /Type /Outlines /First {top[0][0]} 0 R /Last {top[-1][0]} 0 R /Count {count_all} >>'.encode())
    pdf.set(cat, f'<< /Type /Catalog /Pages {pages_root} 0 R /Outlines {root} 0 R /Lang (es-AR) '
                 f'/ViewerPreferences << /DisplayDocTitle true >> >>'.encode())
    now = datetime.datetime.now().astimezone()
    off = now.strftime('%z'); off = f"{off[:3]}'{off[3:]}'"
    info = pdf.add((f'<< /Title {utf16hex("Rendición de cuentas del gobierno de la provincia del Neuquén")} '
                    f'/Subject {utf16hex(f"Presentación · {len(nums)} pantallas")} '
                    f'/Creator {utf16hex("rendicionnqn2026.vercel.app")} /Producer (build_pdf) '
                    f"/CreationDate (D:{now.strftime('%Y%m%d%H%M%S')}{off}) >>").encode())
    pdf.write(OUT_PDF, cat, info)
    sz = os.path.getsize(OUT_PDF)
    print(f'{OUT_PDF}: {len(nums)} páginas, {sz / 1e6:.1f} MB')
    for n, (part, title) in zip(nums, infos):
        print(f'  {n:02d} [{part or "-":4}] {title}')


main()
