#!/usr/bin/env python3
"""Arma la cadena de tomas de un bloque de «Neuquén vive» en UN solo mp4 que cierra en loop sin salto.

uso: build_playlist.py BLOQUE ANCHO ALTO CRF PRESET SALIDA.mp4 [maxrate_k] [nivel]
Cada toma se funde con la siguiente (xfade, 12 cuadros = 0,5 s a 24 fps) y la última se funde con el
principio de la primera: el archivo es el tramo [f, R_N) de la cadena [T1, …, TN, T1'], así el último cuadro
(T1 en el cuadro f−1, casi puro) empalma con el primero (T1 en el cuadro f) sin saltar.
Sin audio, H.264 High 8 bits, etiquetado BT.709, moov al principio.
"""
import os, subprocess, sys, time

ROOT = os.environ.get('NVROOT', '/Users/fran/Downloads/Videos Neuquen Vive')  # v154: las fuentes hoy están en Insumos/Videos Neuquen Vive (env NVROOT)
FPS = 24
F = 12  # cuadros del fundido

FOTO_S = 3.5  # segundos que dura cada foto
# v125: la foto se agranda 8× antes del zoompan (con 2× el recorte saltaba de a 0,5 px de salida y la imagen «vibraba»)
FOTOS = os.environ.get('FOTOS', '/private/tmp/fotos-cdc')
BLOCKS = {
    'natatorios': ['videos Olimpico/natatorio %d.mp4' % i for i in (1, 2, 3, 4)] + ['video semi/natatorio semi %d.mp4' % i for i in (1, 2, 3, 4, 5, 6)],
    # v92: el render del natatorio (New project 3 13-26: HDR 2560 × 1440 → SDR 1280 × 720 a 24 fps, sin audio; env NATNUEVO) entra después de las cuatro tomas del olímpico
    'natatorios3': ['videos Olimpico/natatorio %d.mp4' % i for i in (1, 2, 3, 4)] + [os.environ.get('NATNUEVO', '/private/tmp/natatorio-nuevo.mp4')] + ['video semi/natatorio semi %d.mp4' % i for i in (1, 2, 3, 4, 5, 6)],
    # Alumine 4 es idéntico byte por byte a Alumine 1: se usa una sola vez
    'paseos': ['PASEOS COSTEROS/IA ALUMINE/Alumine %d.mp4' % i for i in (1, 2, 3, 5, 6, 7, 8, 9)] + ['PASEOS COSTEROS/IA TRAFULL/Trafull %d.mp4' % i for i in range(1, 9)],
    'cdc': ['CDC/cdc %d.mp4' % i for i in (1, 2, 4, 5)],
    'convenciones': ['CENTROS DE CONVENCIONES/CHOS MALAL/Chos Malal %d.mp4' % i for i in range(1, 8)] + ['CENTROS DE CONVENCIONES/ccvp 14/ccvp %d.mp4' % i for i in range(1, 7)],
    # v84: tomas y fotos de obra intercaladas (las fotos: recortes 16:9 en nv72/fotos-cdc; cada una dura FOTO_S s con un zoom lento)
    'cdcmix': ['CDC/cdc 1.mp4', FOTOS + '/f32.jpg', 'CDC/cdc 4.mp4', FOTOS + '/f33.jpg', 'CDC/cdc 2.mp4', FOTOS + '/f31.jpg', 'CDC/cdc 5.mp4', FOTOS + '/f35.jpg', FOTOS + '/f34.jpg'],
    # v94: Neuquén Habita (pantalla única): las dos tomas de las viviendas y las dos imágenes (recortadas a 16:9 en VIVDIR), intercaladas
    'vivienda': ['/Users/fran/Downloads/vivienda/1 viviendas.mp4', os.environ.get('VIVDIR', '/tmp') + '/interior.jpg', '/Users/fran/Downloads/vivienda/2 viviendas.mp4', os.environ.get('VIVDIR', '/tmp') + '/frente.jpg'],
    # v97: cdcmix + tres renders del CDC en negro (Downloads/1, 3 y 4 NEGRO) intercalados entre las tomas y las fotos
    'cdcmix2': ['CDC/cdc 1.mp4', '/Users/fran/Downloads/1 NEGRO.mp4', FOTOS + '/f32.jpg', 'CDC/cdc 4.mp4', FOTOS + '/f33.jpg', '/Users/fran/Downloads/3 NEGRO.mp4', 'CDC/cdc 2.mp4', FOTOS + '/f31.jpg', '/Users/fran/Downloads/4 NEGRO.mp4', 'CDC/cdc 5.mp4', FOTOS + '/f35.jpg', FOTOS + '/f34.jpg'],
    # v98: «Más conectividad para toda la región» (Trenque Lauquen y Río Colorado): los 7 videos de Downloads/VIDEOS TL en su orden (el 1.º, de 2432 × 1440, recortado a 16:9 en TLDIR/t1.mp4)
    'tl': [os.environ.get('TLDIR', '/tmp') + '/t1.mp4'] + ['/Users/fran/Downloads/VIDEOS TL/' + n for n in ('2- TRENQUE LAUQEN ACTUAL.mp4', '3- TRENQUE LAUQUEN OBRA.mp4', '4- TRENQUE LAUQUEN RENDER.mp4', '5- TRENQUE LAUQUEN TRANSFORMACION 2.mp4', '6-RIO COLORADO ACTUAL.mp4', '7- RIO COLARADO RENDER.mp4')],
    # v111: «Más conectividad…» arranca con el mapa de Las Perlas–Autovía Norte (PDF de Downloads: vertical, entero, sobre su fondo desenfocado; MAPADIR/mapa.mp4, 5 s fijos) y sigue con los 7 videos
    'tl2': [os.environ.get('MAPADIR', '/tmp') + '/mapa.mp4'] + [os.environ.get('TLDIR', '/tmp') + '/t1.mp4'] + ['/Users/fran/Downloads/VIDEOS TL/' + n for n in ('2- TRENQUE LAUQEN ACTUAL.mp4', '3- TRENQUE LAUQUEN OBRA.mp4', '4- TRENQUE LAUQUEN RENDER.mp4', '5- TRENQUE LAUQUEN TRANSFORMACION 2.mp4', '6-RIO COLORADO ACTUAL.mp4', '7- RIO COLARADO RENDER.mp4')],
    # v101: Renovarse (Termas de Copahue): una sola toma aérea de dron (DJI, 3840 × 2160, 16 s) que cierra en loop fundiendo el final con el principio
    'copahue': ['/Users/fran/Downloads/1 DJI_20260226124211_0052_D COPAHUE (1).MP4'],
    # v101: cdcmix2 empezando con la foto del CDC en obra (WhatsApp Image 2026-11-16 at 2.32.42 PM, 1600 × 900): es el cartel y el empalme del loop
    'cdcmix3': ['/Users/fran/Downloads/WhatsApp Image 2026-11-16 at 2.32.42 PM.jpeg', 'CDC/cdc 1.mp4', '/Users/fran/Downloads/1 NEGRO.mp4', FOTOS + '/f32.jpg', 'CDC/cdc 4.mp4', FOTOS + '/f33.jpg', '/Users/fran/Downloads/3 NEGRO.mp4', 'CDC/cdc 2.mp4', FOTOS + '/f31.jpg', '/Users/fran/Downloads/4 NEGRO.mp4', 'CDC/cdc 5.mp4', FOTOS + '/f35.jpg', FOTOS + '/f34.jpg'],
    # v115: cdcmix3 SIN las cuatro tomas de render con techo blanco (cdc 1, 2, 4 y 5): quedan la foto de la obra, los tres renders en negro y las fotos de obra
    'cdcmix4': ['/Users/fran/Downloads/WhatsApp Image 2026-11-16 at 2.32.42 PM.jpeg', '/Users/fran/Downloads/1 NEGRO.mp4', FOTOS + '/f32.jpg', FOTOS + '/f33.jpg', '/Users/fran/Downloads/3 NEGRO.mp4', FOTOS + '/f31.jpg', '/Users/fran/Downloads/4 NEGRO.mp4', FOTOS + '/f35.jpg', FOTOS + '/f34.jpg'],
    # v115: Neuquén Habita con las otras dos tomas (3 y 4 viviendas, 2560 × 1440, 5,2 s) al final; 1 y 2 son las mismas de siempre
    'vivienda2': ['/Users/fran/Downloads/1 viviendas.mp4', os.environ.get('VIVDIR', '/tmp') + '/interior.jpg', '/Users/fran/Downloads/2 viviendas.mp4', os.environ.get('VIVDIR', '/tmp') + '/frente.jpg', '/Users/fran/Downloads/3 viviendas.mp4', '/Users/fran/Downloads/4 viviendas.mp4'],
    # v116: CDC solo con lo de Downloads/CDC: la foto de la obra primero (WhatsApp Image 2.32.40 PM, 2560 × 1441) y los cuatro renders en negro
    'cdcmix5': ['/Users/fran/Downloads/CDC/WhatsApp Image 2026-11-16 at 2.32.40 PM.jpeg', '/Users/fran/Downloads/CDC/1 NEGRO.mp4', '/Users/fran/Downloads/CDC/2 NEGRO -OK.mp4', '/Users/fran/Downloads/CDC/3 NEGRO.mp4', '/Users/fran/Downloads/CDC/4 NEGRO.mp4'],
    # v104/v105: «La Usina» (Centro de Artes Escénicas), todo VERTICAL 9:16: el dron (HEVC 3840 × 2160 con giro de 90°) y las cuatro tomas de iPhone de la obra
    'usina': ['/Users/fran/Downloads/La Usina/dji_fly_20261012_124926_0230_1791839388276_video.mp4'] + ['/Users/fran/Downloads/La Usina/IMG_%s.MOV' % n for n in ('9878', '9893', '9895', '9900')],
    # v123: Hospital Norpatagónico: las 4 tomas aéreas del video (cortadas en sus cambios de plano, HDR → SDR) con las 5 imágenes (16:9 con la imagen entera sobre su fondo desenfocado) intercaladas; HOSPDIR = carpeta con t1-t4.mp4 y f1-f5.jpg
    'hospital': [os.environ.get('HOSPDIR', '/tmp') + '/' + n for n in ('t1.mp4', 'f1.jpg', 't2.mp4', 'f2.jpg', 't3.mp4', 'f3.jpg', 't4.mp4', 'f4.jpg', 'f5.jpg')],
    # v154: Neuquén Habita arranca con 1 viviendas + FRENTE + INTERIOR 3 + INTERIOR 2 (16:9 en PREPDIR) y sigue con 2, 3 y 4 viviendas
    'vivienda3': ['/Users/fran/Downloads/Informe Gestión B/Insumos/1 viviendas.mp4'] + [os.environ.get('PREPDIR', '/tmp') + '/' + n for n in ('frente.jpg', 'interior3.jpg', 'interior2.jpg')] + ['/Users/fran/Downloads/Informe Gestión B/Insumos/%d viviendas.mp4' % i for i in (2, 3, 4)],
    # v154: Superarse (natatorios) SIN las seis tomas semiolímpicas (techo de estructura metálica): olímpico 1–4, el render nuevo y dos renders fijos (16:9 en PREPDIR)
    'natatorios4': ['videos Olimpico/natatorio %d.mp4' % i for i in (1, 2, 3, 4)] + [os.environ.get('NATNUEVO', '/Users/fran/Downloads/Informe Gestión B/Insumos/Natatorio.mp4')] + [os.environ.get('PREPDIR', '/tmp') + '/' + n for n in ('nat-a.jpg', 'nat-b.jpg')],
    'museo': ['MUSEO CHOCON horizontal/museo horizontal %d.mp4' % i for i in (1, 2, 3, 4, 6, 7)],
}


def es_foto(path):
    return path.lower().endswith(('.jpg', '.jpeg', '.png'))


def nframes(path):
    """cuadros que quedan tras llevar la toma a 24 fps"""
    if es_foto(path):
        return int(round(FOTO_S * FPS))
    o = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=avg_frame_rate,nb_frames,duration', '-of', 'default=nw=1', path], capture_output=True, text=True).stdout
    kv = dict(l.split('=') for l in o.split())
    num, den = kv['avg_frame_rate'].split('/')
    fr = int(num) / int(den)
    if abs(fr - FPS) < 0.01:
        return int(kv['nb_frames'])
    # otra frecuencia (cdc 5, 30 fps): se cuenta lo que entrega el filtro fps=24
    o = subprocess.run(['ffmpeg', '-hide_banner', '-i', path, '-an', '-vf', 'fps=%d' % FPS, '-f', 'null', '-'], capture_output=True, text=True).stderr
    last = [l for l in o.splitlines() if 'frame=' in l][-1]
    return int(last.split('frame=')[1].split()[0])


def main():
    block, w, h, crf, preset, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5], sys.argv[6]
    maxrate = sys.argv[7] if len(sys.argv) > 7 else '4500'
    level = sys.argv[8] if len(sys.argv) > 8 else '4.1'
    files = [os.path.join(ROOT, f) for f in BLOCKS[block]]
    # v83: ORDER=0,3,1,… reordena las tomas (la primera queda primera: es el cartel y el empalme del loop)
    if os.environ.get('ORDER'):
        files = [files[int(i)] for i in os.environ['ORDER'].split(',')]
    for f in files:
        assert os.path.isfile(f), f
    n = [nframes(f) for f in files]
    N = len(files)
    # entradas: las N tomas + la primera otra vez (solo hace falta su comienzo)
    args = []
    for f in files:
        args += ['-i', f]
    args += ['-t', '%.3f' % ((F + 12) / FPS), '-i', files[0]]
    chain = []
    for i in range(N + 1):
        f = files[i] if i < N else files[0]
        if es_foto(f):
            d = nframes(f)
            chain.append("[%d:v]scale=%d:%d:flags=lanczos,format=yuv420p,zoompan=z='1+0.07*on/%d':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=%d:s=%dx%d:fps=%d,setsar=1,settb=1/%d,setpts=N/(%d*TB)[v%d]" % (i, 8 * w, 8 * h, d, d, w, h, FPS, FPS, FPS, i))
        else:
            # v112: COVER=1 llena el marco recortando lo que sobra (marco más alto que 16:9) en vez de deformar
            sc = ('scale=%d:%d:flags=lanczos:force_original_aspect_ratio=increase,crop=%d:%d' % (w, h, w, h)) if os.environ.get('COVER') else ('scale=%d:%d:flags=lanczos' % (w, h))
            chain.append('[%d:v]fps=%d,%s,format=yuv420p,setsar=1,settb=1/%d,setpts=N/(%d*TB)[v%d]' % (i, FPS, sc, FPS, FPS, i))
    run = n[0]  # cuadros de la cadena hasta ahora
    prev = 'v0'
    for k in range(1, N + 1):
        nk = n[k] if k < N else n[0]
        off = (run - F) / FPS
        chain.append('[%s][v%d]xfade=transition=fade:duration=%.4f:offset=%.4f[x%d]' % (prev, k, F / FPS, off, k))
        prev = 'x%d' % k
        run = run + nk - F
        if k == N:
            pass
    # run = largo de la cadena completa; el tramo del archivo va de F hasta R_N = (largo de N tomas fundidas)
    RN = sum(n) - (N - 1) * F
    chain.append('[%s]trim=start_frame=%d:end_frame=%d,setpts=PTS-STARTPTS[out]' % (prev, F, RN))
    fc = ';'.join(chain)
    xp = 'keyint=96:min-keyint=24:aq-mode=3:aq-strength=0.9:bframes=6:ref=6:colorprim=bt709:transfer=bt709:colormatrix=bt709'
    cmd = ['ffmpeg', '-hide_banner', '-v', 'error', '-y'] + args + ['-filter_complex', fc, '-map', '[out]', '-an', '-r', str(FPS),
           '-c:v', 'libx264', '-preset', preset, '-profile:v', 'high', '-level', level, '-crf', crf, '-maxrate', maxrate + 'k', '-bufsize', str(2 * int(maxrate)) + 'k',
           '-pix_fmt', 'yuv420p', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv',
           '-x264-params', xp, '-movflags', '+faststart', out]
    t0 = time.time()
    print('%s: %d tomas, %d cuadros de entrada, salen %d cuadros (%.2f s)' % (block, N, sum(n), RN - F, (RN - F) / FPS), flush=True)
    subprocess.run(cmd, check=True)
    sz = os.path.getsize(out)
    print('%s %dx%d crf %s %s -> %s  %d bytes  %.0f kbit/s  (%.0f s)' % (block, w, h, crf, preset, out, sz, sz * 8 / ((RN - F) / FPS) / 1000, time.time() - t0), flush=True)


main()
