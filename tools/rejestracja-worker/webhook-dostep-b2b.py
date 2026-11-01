# Jednorazowo (30.10.2026): rejestruje w Shopify webhook company_contact_roles/assign → funkcja achti-rejestracja
# wysyła klientowi „E-mail z dostępem B2B” po akceptacji firmy. Uruchomić: /usr/bin/python3 tools/rejestracja-worker/webhook-dostep-b2b.py
import json, os, urllib.request
c = lambda f: open(os.path.expanduser('~/.config/achti/' + f)).read().strip()
S = 'ccucsr-si.myshopify.com'
t = json.load(urllib.request.urlopen(urllib.request.Request(f'https://{S}/admin/oauth/access_token', json.dumps({'client_id': c('client_id'), 'client_secret': c('client_secret'), 'grant_type': 'client_credentials'}).encode(), {'Content-Type': 'application/json'})))['access_token']
q = 'mutation{webhookSubscriptionCreate(topic:COMPANY_CONTACT_ROLES_ASSIGN,webhookSubscription:{callbackUrl:"https://achti-rejestracja.achti.workers.dev/webhook/role-assign",format:JSON}){webhookSubscription{id topic} userErrors{field message}}}'
r = json.load(urllib.request.urlopen(urllib.request.Request(f'https://{S}/admin/api/2026-07/graphql.json', json.dumps({'query': q}).encode(), {'Content-Type': 'application/json', 'X-Shopify-Access-Token': t})))
print(json.dumps(r.get('data') or r, ensure_ascii=False, indent=1))
