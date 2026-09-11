"""Tagi składu: `welna` (skład zawiera wełnę, także merino) i `merino` (wełna merino).
Źródło: metapole custom.sklad w sklepie (tekst). Uruchamiać ponownie po zmianie składów.
  python3 tools/set_fibre_tags.py [--dry-run]
"""
import re, sys
import shopify_import as si

DRY = '--dry-run' in sys.argv
WOOL = re.compile(r'we[łl]n|wool|laine|wolle', re.I)
MERINO = re.compile(r'merino', re.I)

def fetch():
    out, cursor = [], None
    while True:
        r = si.gql('''query($c:String){ products(first:100, after:$c){ nodes{ id title tags
            sklad: metafield(namespace:"custom", key:"sklad"){ value type } }
            pageInfo{ hasNextPage endCursor } } }''', {'c': cursor})['products']
        out += r['nodes']
        if not r['pageInfo']['hasNextPage']: break
        cursor = r['pageInfo']['endCursor']
    return out

def main():
    stats = {'welna': 0, 'merino': 0, 'zmienione': 0}
    for p in fetch():
        sklad = (p['sklad'] or {}).get('value') or ''
        tags = set(p['tags']) - {'welna', 'merino'}
        if WOOL.search(sklad): tags.add('welna'); stats['welna'] += 1
        if MERINO.search(sklad): tags.add('merino'); stats['merino'] += 1
        if sorted(tags) != sorted(p['tags']):
            stats['zmienione'] += 1
            print(('[dry] ' if DRY else '') + p['title'], '->', sorted(tags & {'welna', 'merino'}), '|', sklad[:40])
            if not DRY:
                si.gql('mutation($p:ProductInput!){ productUpdate(input:$p){ userErrors{ message } } }',
                       {'p': {'id': p['id'], 'tags': sorted(tags)}})
    print(stats)

if __name__ == '__main__':
    main()
