#!/usr/bin/env python3
"""Scala identyczne obrazki w PDF (Chrome osadza ten sam obrazek osobno przy każdym użyciu — palety przędzy
w katalogu powtarzają się przy wielu produktach). Wymaga pikepdf: python -m venv … && pip install pikepdf.
Użycie: python dedupe_pdf_images.py WEJŚCIE.pdf [WYJŚCIE.pdf]  (bez WYJŚCIA nadpisuje plik)"""
import hashlib, os, sys
import pikepdf

def main(src, dst):
    pdf = pikepdf.open(src, allow_overwriting_input=True)
    seen, merged = {}, 0
    for page in pdf.pages:
        res = page.obj.get('/Resources')
        stack = [res] if res is not None else []
        while stack:
            r = stack.pop()
            xo = r.get('/XObject')
            if xo is None: continue
            for name in list(xo.keys()):
                obj = xo[name]
                if obj.get('/Subtype') == '/Form':
                    if obj.get('/Resources') is not None: stack.append(obj['/Resources'])
                    continue
                if obj.get('/Subtype') != '/Image': continue
                key = hashlib.sha1(obj.read_raw_bytes() + repr(sorted((k, str(v)) for k, v in obj.items() if k != '/SMask')).encode()
                                   + (obj['/SMask'].read_raw_bytes() if obj.get('/SMask') is not None else b'')).hexdigest()
                if key in seen:
                    if seen[key].objgen != obj.objgen: xo[name] = seen[key]; merged += 1
                else:
                    seen[key] = obj
    pdf.remove_unreferenced_resources()
    pdf.save(dst, compress_streams=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)
    print(f'{os.path.basename(dst)}: scalone {merged} powtórzeń, {os.path.getsize(src if src != dst else dst) / 1e6:.1f} MB')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else sys.argv[1])
