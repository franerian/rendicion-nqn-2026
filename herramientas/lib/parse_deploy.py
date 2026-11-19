#!/usr/bin/env python3
"""Lee el registro de `vercel deploy --prod` y resume el resultado. Uso: parse_deploy.py <registro>
Sale con código 1 si el deploy no terminó bien."""
import json
import re
import sys

raw = open(sys.argv[1], encoding='utf-8', errors='replace').read().replace('\r', '\n')
info = {}
m = re.search(r'^\{\s*\n\s*"status".*?^\}', raw, re.S | re.M)
if m:
    try:
        info = json.loads(m.group(0))
    except Exception:
        info = {}
dep = info.get('deployment') or {}
subidos = re.findall(r'Uploading \[[=\-]+\] \(([^/)]+)/([^)]+)\)', raw)
archivos = re.findall(r'Downloading (\d+) deployment files', raw)
alias = re.findall(r'Aliased\s+(https://\S+)', raw)
ok = info.get('status') == 'ok' and dep.get('readyState') == 'READY'
print('estado: %s | id: %s | %s' % ('OK' if ok else 'FALLÓ', dep.get('id', '?'), dep.get('readyState', '?')))
print('url: %s' % dep.get('url', '?'))
print('subido: %s | archivos: %s | alias: %s' % (
    subidos[-1][1] if subidos else '(nada: no cambió ningún archivo)',
    archivos[-1] if archivos else '?',
    alias[-1] if alias else '(sin alias)'))
sys.exit(0 if ok else 1)
