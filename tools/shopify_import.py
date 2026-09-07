#!/usr/bin/env python3
"""Import produktów Achti do Shopify przez Admin GraphQL API.
Użycie:
  python3 tools/shopify_import.py --dry-run          # tylko pokazuje, co zrobi
  python3 tools/shopify_import.py                    # tworzy produkty ze zdjęciami
  python3 tools/shopify_import.py --limit 3          # pierwsze 3 (test)
Token: plik ~/.config/achti/admin_token (shpat_...), uprawnienia: write_products, write_files.
Skrypt pomija kody, które już istnieją w sklepie (po SKU/tagu kodu), więc można go uruchamiać wielokrotnie.
"""
import argparse, json, mimetypes, os, sys, time, urllib.request, urllib.error
SHOP='ccucsr-si.myshopify.com'; API='2025-07'
TOKEN_FILE=os.path.expanduser('~/.config/achti/admin_token')
DATA=os.path.join(os.path.dirname(__file__),'achti-produkty.json')

def token():
    t=os.environ.get('SHOPIFY_ADMIN_TOKEN') or (open(TOKEN_FILE).read().strip() if os.path.exists(TOKEN_FILE) else '')
    if not t: sys.exit(f'Brak tokenu: zapisz go w {TOKEN_FILE} lub w zmiennej SHOPIFY_ADMIN_TOKEN')
    return t

def gql(query, variables=None, _retry=0):
    req=urllib.request.Request(f'https://{SHOP}/admin/api/{API}/graphql.json',
        data=json.dumps({'query':query,'variables':variables or {}}).encode(),
        headers={'Content-Type':'application/json','X-Shopify-Access-Token':token()})
    try:
        with urllib.request.urlopen(req,timeout=60) as r: out=json.load(r)
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
    with urllib.request.urlopen(req,timeout=120) as r: r.read()
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
    return prod['handle']

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--dry-run',action='store_true'); ap.add_argument('--limit',type=int,default=0); a=ap.parse_args()
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
