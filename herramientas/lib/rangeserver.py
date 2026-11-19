#!/usr/bin/env python3
"""Servidor estático local con soporte de Range (el de la biblioteca estándar no lo trae y Chrome lo necesita para buscar dentro de un video).
uso: rangeserver.py PUERTO CARPETA"""
import functools
import http.server
import os
import re
import socketserver
import sys


class H(http.server.SimpleHTTPRequestHandler):
    _remaining = None

    def send_head(self):
        path = self.translate_path(self.path)
        rng = self.headers.get('Range')
        if not rng or not os.path.isfile(path):
            return super().send_head()
        m = re.match(r'bytes=(\d*)-(\d*)$', rng.strip())
        if not m or (m.group(1) == '' and m.group(2) == ''):
            return super().send_head()
        size = os.path.getsize(path)
        a, b = m.group(1), m.group(2)
        if a == '':
            n = int(b)
            start, end = max(0, size - n), size - 1
        else:
            start, end = int(a), (int(b) if b else size - 1)
        end = min(end, size - 1)
        if start >= size or start > end:
            self.send_error(416, 'Requested Range Not Satisfiable')
            return None
        f = open(path, 'rb')
        f.seek(start)
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(path))
        self.send_header('Content-Range', 'bytes %d-%d/%d' % (start, end, size))
        self.send_header('Content-Length', str(end - start + 1))
        self.end_headers()
        self._remaining = end - start + 1
        return f

    def copyfile(self, source, outputfile):
        try:
            rem = self._remaining
            if rem is None:
                return super().copyfile(source, outputfile)
            while rem > 0:
                chunk = source.read(min(65536, rem))
                if not chunk:
                    break
                outputfile.write(chunk)
                rem -= len(chunk)
            self._remaining = None
        except (BrokenPipeError, ConnectionResetError):
            pass

    def end_headers(self):
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def log_message(self, *a):
        pass


class S(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


port, folder = int(sys.argv[1]), os.path.abspath(sys.argv[2])
S(('127.0.0.1', port), functools.partial(H, directory=folder)).serve_forever()
