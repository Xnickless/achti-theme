#!/usr/bin/env python3
"""Import produktów Achti do Shopify przez Admin GraphQL API.
Użycie:
  python3 tools/shopify_import.py --dry-run          # tylko pokazuje, co zrobi
  python3 tools/shopify_import.py                    # tworzy produkty ze zdjęciami
  python3 tools/shopify_import.py --limit 3          # pierwsze 3 (test)
Poświadczenia (Dev Dashboard): ~/.config/achti/client_id + ~/.config/achti/client_secret (skrypt sam pobiera token),
  albo gotowy token w ~/.config/achti/admin_token. Uprawnienia aplikacji: write_products, read_products, write_files, read_files, write_publications, read_publications.
Skrypt pomija kody, które już istnieją w sklepie (po SKU/tagu kodu), więc można go uruchamiać wielokrotnie.
"""
import argparse, json, mimetypes, os, ssl, sys, time, urllib.request, urllib.error
# Python z python.org na macOS nie ma certyfikatów CA -> użyj certifi albo systemowego pęku
def _ssl_ctx():
    try:
        import certifi; return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context(cafile='/etc/ssl/cert.pem') if os.path.exists('/etc/ssl/cert.pem') else ssl.create_default_context()
_CTX=_ssl_ctx()
SHOP='ccucsr-si.myshopify.com'; API='2025-07'
TOKEN_FILE=os.path.expanduser('~/.config/achti/admin_token')
DATA=os.path.join(os.path.dirname(__file__),'achti-produkty.json')

CLIENT_ID_FILE=os.path.expanduser('~/.config/achti/client_id')
CLIENT_SECRET_FILE=os.path.expanduser('~/.config/achti/client_secret')
_token_cache={'value':None,'exp':0}
def token():
    """Token Admin API: z pliku admin_token (shpat_...) albo wymieniany z client_id+client_secret (Dev Dashboard)."""
    t=os.environ.get('SHOPIFY_ADMIN_TOKEN') or (open(TOKEN_FILE).read().strip() if os.path.exists(TOKEN_FILE) else '')
    if t: return t
    if _token_cache['value'] and time.time()<_token_cache['exp']-300: return _token_cache['value']
    if not (os.path.exists(CLIENT_ID_FILE) and os.path.exists(CLIENT_SECRET_FILE)):
        sys.exit(f'Brak poświadczeń: zapisz ID klienta w {CLIENT_ID_FILE} i klucz tajny w {CLIENT_SECRET_FILE}')
    cid=open(CLIENT_ID_FILE).read().strip(); sec=open(CLIENT_SECRET_FILE).read().strip()
    req=urllib.request.Request(f'https://{SHOP}/admin/oauth/access_token',
        data=json.dumps({'client_id':cid,'client_secret':sec,'grant_type':'client_credentials'}).encode(),
        headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=30,context=_CTX) as r: d=json.load(r)
    except urllib.error.HTTPError as e: sys.exit(f'Nie udało się pobrać tokenu (HTTP {e.code}): {e.read()[:300]}')
    _token_cache['value']=d['access_token']; _token_cache['exp']=time.time()+int(d.get('expires_in',86400))
    return _token_cache['value']

def gql(query, variables=None, _retry=0):
    req=urllib.request.Request(f'https://{SHOP}/admin/api/{API}/graphql.json',
        data=json.dumps({'query':query,'variables':variables or {}}).encode(),
        headers={'Content-Type':'application/json','X-Shopify-Access-Token':token()})
    try:
        with urllib.request.urlopen(req,timeout=60,context=_CTX) as r: out=json.load(r)
    except urllib.error.HTTPError as e:
        if e.code==429 and _retry<5: time.sleep(2); return gql(query,variables,_retry+1)
        sys.exit(f'HTTP {e.code}: {e.read()[:300]}')
    if 'errors' in out: sys.exit('GraphQL errors: '+json.dumps(out['errors'],ensure_ascii=False)[:800])
    cost=out.get('extensions',{}).get('cost',{}).get('throttleStatus',{})
    if cost and cost.get('currentlyAvailable',1000)<200: time.sleep(2)
    return out['data']

def existing_skus():
    skus=set(); cursor=None
    while True:
        d=gql('''query($c:String){ productVariants(first:250, after:$c){ edges{ node{ sku } } pageInfo{ hasNextPage endCursor } } }''',{'c':cursor})
        for e in d['productVariants']['edges']:
            if e['node']['sku']: skus.add(e['node']['sku'].strip().upper())
        pi=d['productVariants']['pageInfo']
        if not pi['hasNextPage']: return skus
        cursor=pi['endCursor']

_pub_cache={}
def online_store_publication():
    if 'id' in _pub_cache: return _pub_cache['id']
    d=gql('{ publications(first:20){ nodes{ id name } } }')
    for n in d['publications']['nodes']:
        if n['name'] in ('Online Store','Sklep online'): _pub_cache['id']=n['id']; return n['id']
    sys.exit('Nie znaleziono publikacji Online Store: '+str(d))

def publish(product_id):
    d=gql('''mutation($id:ID!, $input:[PublicationInput!]!){ publishablePublish(id:$id, input:$input){ userErrors{ field message } } }''',
        {'id':product_id,'input':[{'publicationId':online_store_publication()}]})
    if d['publishablePublish']['userErrors']: print('  uwaga publikacja:',d['publishablePublish']['userErrors'])

def publish_all_unpublished(tag='cena-do-uzupelnienia'):
    """Publikuje w Sklepie online wszystkie produkty z tagiem, które nie są jeszcze opublikowane."""
    pub=online_store_publication(); cursor=None; n=0
    while True:
        d=gql('''query($c:String,$q:String){ products(first:100, after:$c, query:$q){ nodes{ id title publishedOnPublication(publicationId:"%s") } pageInfo{ hasNextPage endCursor } } }'''%pub,{'c':cursor,'q':'tag:'+tag})
        for pr in d['products']['nodes']:
            if not pr['publishedOnPublication']: publish(pr['id']); n+=1; print('  opublikowano:',pr['title'])
        pi=d['products']['pageInfo']
        if not pi['hasNextPage']: break
        cursor=pi['endCursor']
    print('opublikowano łącznie:',n)

def metafield_defs():
    d=gql('''{ metafieldDefinitions(first:50, ownerType:PRODUCT, namespace:"custom"){ edges{ node{ key type{ name } } } } }''')
    return {e['node']['key']:e['node']['type']['name'] for e in d['metafieldDefinitions']['edges']}

def mf_value(type_name, text):
    if type_name=='rich_text_field':
        return json.dumps({'type':'root','children':[{'type':'paragraph','children':[{'type':'text','value':text}]}]},ensure_ascii=False)
    return text

def staged_upload(path):
    name=os.path.basename(path); mime=mimetypes.guess_type(path)[0] or 'image/jpeg'
    d=gql('''mutation($input:[StagedUploadInput!]!){ stagedUploadsCreate(input:$input){ stagedTargets{ url resourceUrl parameters{ name value } } userErrors{ message } } }''',
        {'input':[{'resource':'IMAGE','filename':name,'mimeType':mime,'httpMethod':'POST','fileSize':str(os.path.getsize(path))}]})
    su=d['stagedUploadsCreate']
    if su['userErrors']: sys.exit('stagedUploads: '+str(su['userErrors']))
    t=su['stagedTargets'][0]
    boundary='----achti'+str(int(time.time()*1000))
    body=b''
    for p in t['parameters']:
        body+=f'--{boundary}\r\nContent-Disposition: form-data; name="{p["name"]}"\r\n\r\n{p["value"]}\r\n'.encode()
    body+=f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\nContent-Type: {mime}\r\n\r\n'.encode()+open(path,'rb').read()+f'\r\n--{boundary}--\r\n'.encode()
    req=urllib.request.Request(t['url'],data=body,headers={'Content-Type':f'multipart/form-data; boundary={boundary}'})
    with urllib.request.urlopen(req,timeout=120,context=_CTX) as r: r.read()
    return t['resourceUrl']

def create_product(p, defs):
    metafields=[]
    for key,text in (('rozmiar',p['size']),('sklad',', '.join(p['materials']) if p['materials'] else '')):
        if key in defs and text: metafields.append({'namespace':'custom','key':key,'type':defs[key],'value':mf_value(defs[key],text)})
    media=[]
    if p.get('photo'):
        media.append({'originalSource':staged_upload(p['photo']),'alt':p['title'],'mediaContentType':'IMAGE'})
    d=gql('''mutation($product:ProductCreateInput!, $media:[CreateMediaInput!]){ productCreate(product:$product, media:$media){ product{ id handle variants(first:1){ nodes{ id } } } userErrors{ field message } } }''',
        {'product':{'title':p['title'],'descriptionHtml':p['body_html'],'vendor':p['vendor'],'productType':p['product_type'],'tags':p['tags'],'status':'ACTIVE','metafields':metafields},'media':media})
    pc=d['productCreate']
    if pc['userErrors']: sys.exit(f"productCreate {p['code']}: {pc['userErrors']}")
    prod=pc['product']; vid=prod['variants']['nodes'][0]['id']
    d=gql('''mutation($pid:ID!, $v:[ProductVariantsBulkInput!]!){ productVariantsBulkUpdate(productId:$pid, variants:$v){ userErrors{ field message } } }''',
        {'pid':prod['id'],'v':[{'id':vid,'price':p['price'],'inventoryItem':{'sku':p['code'],'tracked':False}}]})
    if d['productVariantsBulkUpdate']['userErrors']: print('  uwaga wariant:',d['productVariantsBulkUpdate']['userErrors'])
    publish(prod['id'])
    return prod['handle']

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--dry-run',action='store_true'); ap.add_argument('--limit',type=int,default=0); ap.add_argument('--publish-only',action='store_true',help='tylko opublikuj istniejące produkty z tagiem w Sklepie online'); a=ap.parse_args()
    if a.publish_only: publish_all_unpublished(); return
    products=json.load(open(DATA))
    if a.limit: products=products[:a.limit]
    if a.dry_run:
        for p in products: print(p['code'],'|',p['title'],'|',', '.join(p['tags']),'|',os.path.basename(p['photo'] or 'BRAK ZDJĘCIA'))
        print(len(products),'produktów (dry-run, nic nie wysłano)'); return
    have=existing_skus(); defs=metafield_defs(); print('metapola custom:',defs); print('istniejące SKU:',len(have))
    done=skipped=0; log=open(os.path.join(os.path.dirname(__file__),'import.log'),'a')
    for i,p in enumerate(products,1):
        if p['code'].upper() in have: skipped+=1; continue
        h=create_product(p,defs); done+=1
        print(f'[{i}/{len(products)}] {p["code"]} -> /products/{h}'); log.write(f'{p["code"]}\t{h}\n'); log.flush()
    print(f'utworzono {done}, pominięto (już były) {skipped}')
if __name__=='__main__': main()
