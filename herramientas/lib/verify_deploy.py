import concurrent.futures as cf
import os
import sys
import urllib.error
import urllib.request

base = sys.argv[1].rstrip('/')
root = os.path.abspath(sys.argv[2])
UA = {'User-Agent': 'Mozilla/5.0 (verificacion de deploy)'}

files = []
for d, dirs, fs in os.walk(root):
    dirs[:] = [x for x in dirs if x != '.vercel']
    for f in fs:
        files.append(os.path.relpath(os.path.join(d, f), root))
files.sort()


def fetch(path, method='HEAD', extra=None):
    url = base + '/' + ('' if path == 'index.html' else path)
    h = dict(UA)
    if extra:
        h.update(extra)
    rq = urllib.request.Request(url, method=method, headers=h)
    try:
        with urllib.request.urlopen(rq, timeout=60) as r:
            return r.status, {k.lower(): v for k, v in r.headers.items()}
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in e.headers.items()}
    except Exception as e:  # red, DNS, etc.
        return 0, {'error': repr(e)}


def check(path):
    st, h = fetch(path)
    local = os.path.getsize(os.path.join(root, path))
    note = ''
    ok = st == 200
    ctype = h.get('content-type', '')
    if ok and not path.endswith(('.html', '.json')):
        cl = h.get('content-length')
        if cl is not None and int(cl) != local:
            ok = False
            note = 'tamaño %s != local %s' % (cl, local)
    if ok and path.endswith('.mp4'):
        st2, h2 = fetch(path, 'GET', {'Range': 'bytes=0-1023'})
        if st2 != 206 or 'content-range' not in h2:
            ok = False
            note = 'sin Range (status %s)' % st2
    return path, st, ctype, ok, note, h


res = []
with cf.ThreadPoolExecutor(8) as ex:
    for r in ex.map(check, files):
        res.append(r)

bad = [r for r in res if not r[3]]
print('archivos revisados: %d, con problema: %d' % (len(res), len(bad)))
for p, st, ct, ok, note, h in bad:
    print('  MAL', st, p, ct, note, h.get('error', ''))

by = {r[0]: r for r in res}
for p in ('index.html', 'img/fondos/hero-mil-razones.jpg', 'video/fondos/hero-mil-razones.mp4'):
    if p in by:
        _, st, ct, ok, note, h = by[p]
        print('\n%s -> %s %s' % (p, st, ct))
        for k in ('cache-control', 'x-content-type-options', 'referrer-policy', 'accept-ranges', 'content-length', 'content-encoding', 'x-vercel-cache'):
            if k in h:
                print('   %s: %s' % (k, h[k]))

# la raíz tiene que traer la presentación entera
st, h = fetch('index.html', 'GET')
print('\nGET / ->', st, h.get('content-type'))
