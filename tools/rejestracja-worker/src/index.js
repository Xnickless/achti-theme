// Rejestracja firmy B2B (27.10.2026): formularz /pages/rejestracja → firma w Shopify (Klienci → Firmy).
// Firma powstaje z lokalizacją (adres, NIP) i kontaktem BEZ roli w lokalizacji = „czeka na akceptację”:
// klient może się zalogować, ale nie widzi cen (motyw: customer.b2b? == false → „Konto czeka na przypisanie do firmy”).
// Akceptacja Adriana: firma → kontakt → przypisz lokalizację z rolą „Kupujący z możliwością zamawiania”.
// Sekrety (wrangler secret put): SHOPIFY_CLIENT_ID, SHOPIFY_CLIENT_SECRET — aplikacja „Import Katalogu” (scope write_customers).

const SHOP = 'ccucsr-si.myshopify.com';
const API = '2026-07';
const ORIGINS = ['https://b2b.achti.com', 'https://ccucsr-si.myshopify.com'];
const TAG = 'wniosek-b2b';
// NIP/VAT wymagany tylko w UE; firmy spoza UE (np. Kanada) mogą nie mieć numeru — wtedy firma bez externalId.
const EU = 'AT BE BG CY CZ DE DK EE ES FI FR GR HR HU IE IT LT LU LV MT NL PL PT RO SE SI SK'.split(' ');

// 30.10.2026: mail do klienta „zgłoszenie przyjęte, konto czeka na zatwierdzenie” — wysyła Shopify (powiadomienie
// „Zaproszenie do konta klienta”, szablon w docs/mail-zgloszenie-przyjete.html wklejony w Ustawienia → Powiadomienia).
// Treść w języku formularza trafia do szablonu jako custom_message.
const MAIL = {
  pl: { subject: 'Achti B2B — zgłoszenie przyjęte, konto czeka na zatwierdzenie', lines: (f) => [
    `Dziękujemy za rejestrację firmy ${f}!`, 'Twoje konto firmowe czeka teraz na zatwierdzenie.', '',
    '1. Weryfikacja — sprawdzamy dane firmy, zwykle w ciągu jednego dnia roboczego.',
    '2. Aktywacja — po zatwierdzeniu konto zostaje przypisane do Twojej firmy i widzisz ceny hurtowe.',
    '3. Logowanie — logujesz się tym adresem e-mail. Wyślemy jednorazowy kod, bez hasła.', '',
    'Masz pytania? Napisz do nas: hello@achti.com'] },
  en: { subject: 'Achti B2B — application received, your account is awaiting approval', lines: (f) => [
    `Thank you for registering ${f}!`, 'Your business account is now awaiting approval.', '',
    '1. Verification — we check your company details, usually within one business day.',
    '2. Activation — once approved, your account is linked to your company and you see wholesale prices.',
    '3. Log in — use this email address. We will send you a one-time code, no password needed.', '',
    'Questions? Email us: hello@achti.com'] },
  de: { subject: 'Achti B2B — Anfrage erhalten, Ihr Konto wartet auf Freigabe', lines: (f) => [
    `Vielen Dank für die Registrierung von ${f}!`, 'Ihr Firmenkonto wartet jetzt auf die Freigabe.', '',
    '1. Prüfung — wir prüfen Ihre Firmendaten, in der Regel innerhalb eines Werktages.',
    '2. Freischaltung — nach der Freigabe wird Ihr Konto Ihrer Firma zugeordnet und Sie sehen die Großhandelspreise.',
    '3. Anmeldung — mit dieser E-Mail-Adresse. Sie erhalten einen Einmalcode, ohne Passwort.', '',
    'Fragen? Schreiben Sie uns: hello@achti.com'] },
  fr: { subject: 'Achti B2B — demande reçue, votre compte est en attente de validation', lines: (f) => [
    `Merci pour l’inscription de ${f} !`, 'Votre compte professionnel est en attente de validation.', '',
    '1. Vérification — nous vérifions les données de votre entreprise, généralement sous un jour ouvré.',
    '2. Activation — après validation, votre compte est rattaché à votre entreprise et vous voyez les prix de gros.',
    '3. Connexion — avec cette adresse e-mail. Nous vous enverrons un code à usage unique, sans mot de passe.', '',
    'Des questions ? Écrivez-nous : hello@achti.com'] },
};

async function sendPendingMail(env, customerId, f) {
  const m = MAIL[(f.locale || 'pl').slice(0, 2)] || MAIL.pl;
  try {
    const d = await gql(env, `mutation($id:ID!,$e:EmailInput){customerSendAccountInviteEmail(customerId:$id,email:$e){userErrors{message}}}`, {
      id: customerId, e: { subject: m.subject, customMessage: m.lines(f.firma).join('\n') },
    });
    const e = d.customerSendAccountInviteEmail.userErrors;
    if (e.length) console.error('mail do klienta:', JSON.stringify(e));
  } catch (e) {
    console.error('mail do klienta:', e.message); // brak maila nie blokuje rejestracji
  }
}

let tokenCache = { value: null, exp: 0 };

async function token(env) {
  if (tokenCache.value && Date.now() < tokenCache.exp - 300e3) return tokenCache.value;
  const r = await fetch(`https://${SHOP}/admin/oauth/access_token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ client_id: env.SHOPIFY_CLIENT_ID, client_secret: env.SHOPIFY_CLIENT_SECRET, grant_type: 'client_credentials' }),
  });
  if (!r.ok) throw new Error(`token HTTP ${r.status}`);
  const d = await r.json();
  tokenCache = { value: d.access_token, exp: Date.now() + (d.expires_in || 86400) * 1000 };
  return tokenCache.value;
}

async function gql(env, query, variables) {
  const r = await fetch(`https://${SHOP}/admin/api/${API}/graphql.json`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Shopify-Access-Token': await token(env) },
    body: JSON.stringify({ query, variables }),
  });
  const d = await r.json();
  if (d.errors) throw new Error(JSON.stringify(d.errors).slice(0, 300));
  return d.data;
}

function userErrors(d) {
  const e = Object.values(d)[0]?.userErrors || [];
  if (e.length) throw Object.assign(new Error(e.map((x) => x.message).join('; ')), { userErrors: e });
  return Object.values(d)[0];
}

const clean = (v, max = 200) => String(v ?? '').replace(/[\u0000-\u001f]/g, ' ').trim().slice(0, max);

function nipOk(nip, country) {
  if (!nip) return !EU.includes(country);
  const n = nip.replace(/\D/g, '');
  if (country !== 'PL') return nip.replace(/[\s.-]/g, '').length >= 6;
  if (n.length !== 10) return false;
  const w = [6, 5, 7, 2, 3, 4, 5, 6, 7];
  return w.reduce((s, x, i) => s + x * +n[i], 0) % 11 === +n[9];
}

function vatId(nip, country) {
  const raw = nip.toUpperCase().replace(/[\s.-]/g, '');
  return /^[A-Z]{2}/.test(raw) ? raw : country + raw;
}

async function register(env, f) {
  const country = /^[A-Z]{2}$/.test(f.kraj) ? f.kraj : 'PL';
  const vat = f.nip ? vatId(f.nip, country) : null;
  const [first, ...rest] = f.osoba.split(/\s+/);
  const note = [
    `Wniosek z formularza rejestracji (${new Date().toISOString().slice(0, 10)})`,
    `NIP/VAT: ${f.nip || 'brak (firma spoza UE)'}`,
    `Rodzaj działalności: ${f.rodzaj}${f.opis ? ` — ${f.opis}` : ''}`,
    f.ilosci && `Przewidywane ilości: ${f.ilosci}`,
    `Adres: ${f.ulica}, ${f.kod} ${f.miasto}, ${country}`,
    f.dostawa && `Adres dostawy: ${f.dostawa}`,
    `Osoba: ${f.osoba}, tel. ${f.telefon}, ${f.email}`,
  ].filter(Boolean).join('\n');

  // Ten sam NIP drugi raz = nie zakładamy duplikatu (externalId jest unikalny w sklepie).
  // Wyszukiwarka Shopify bez cudzysłowu dopasowuje „podobne” numery (PL…63 trafiało w PL…05) — cudzysłów + dokładne porównanie.
  const dup = vat && (await gql(env, `query($q:String!){companies(first:5,query:$q){nodes{id externalId}}}`, { q: `external_id:"${vat}"` }))
    .companies.nodes.find((c) => c.externalId === vat);
  if (dup) return { status: 'exists', companyId: dup.id };

  // Klient: istniejący (np. zalogował się wcześniej) albo nowy, z tagiem do filtrowania wniosków.
  const found = await gql(env, `query($q:String!){customers(first:5,query:$q){nodes{id email companyContactProfiles{id}}}}`, { q: `email:"${f.email}"` });
  let customer = found.customers.nodes.find((c) => (c.email || '').toLowerCase() === f.email);
  if (customer?.companyContactProfiles?.length) return { status: 'has_company' };
  if (customer) {
    await gql(env, `mutation($id:ID!,$tags:[String!]!){tagsAdd(id:$id,tags:$tags){userErrors{message}}}`, { id: customer.id, tags: [TAG] });
  } else {
    customer = userErrors(await gql(env, `mutation($i:CustomerInput!){customerCreate(input:$i){customer{id} userErrors{field message}}}`, {
      i: { email: f.email, firstName: first, lastName: rest.join(' ') || null, tags: [TAG], note, locale: f.locale || 'pl' },
    })).customer;
  }

  // 30.10.2026: polski kod pocztowy NN-NNN (inaczej Shopify odrzuca adres i firma powstaje bez adresu)
  const zipDigits = f.kod.replace(/\D/g, '');
  const zip = country === 'PL' && zipDigits.length === 5 ? `${zipDigits.slice(0, 2)}-${zipDigits.slice(2)}` : f.kod;
  const address = { address1: f.ulica, zip, city: f.miasto, countryCode: country, recipient: f.firma };
  // 30.10.2026 (Kamil): klient może w checkoucie wpisać inny adres dostawy niż adres firmy
  const location = { name: `${f.firma} — ${f.miasto}`.slice(0, 255), billingSameAsShipping: true, shippingAddress: address, note,
    buyerExperienceConfiguration: { editableShippingAddress: true, checkoutToDraft: false } };
  if (vat) location.taxRegistrationId = vat;
  const create = (loc) => gql(env, `mutation($i:CompanyCreateInput!){companyCreate(input:$i){company{id locations(first:1){nodes{id}}} userErrors{field message}}}`, {
    i: { company: { name: f.firma, note, ...(vat && { externalId: vat }) }, companyLocation: loc },
  });
  const errIs = (re) => res.companyCreate.userErrors.some((e) => re.test((e.field || []).join('.') + ' ' + e.message));
  let res = await create(location);
  // Shopify odrzuca niektóre numery VAT (format) — wtedy bez taxRegistrationId; NIP i tak jest w notatce i externalId.
  if (errIs(/tax/i)) {
    delete location.taxRegistrationId;
    res = await create(location);
  }
  // 27.10.2026: Kanada/USA wymagają prowincji/stanu (zoneCode), których formularz nie zbiera — firma powstaje bez adresu,
  // adres jest w notatce (Adrian uzupełnia go przy akceptacji).
  if (res.companyCreate.userErrors.length && !errIs(/external/i)) {
    console.error('companyCreate z adresem:', JSON.stringify(res.companyCreate.userErrors));
    delete location.shippingAddress;
    delete location.billingSameAsShipping;
    delete location.taxRegistrationId;
    res = await create(location);
  }
  const company = userErrors(res).company;

  const contact = userErrors(await gql(env, `mutation($c:ID!,$u:ID!){companyAssignCustomerAsContact(companyId:$c,customerId:$u){companyContact{id} userErrors{field message}}}`, {
    c: company.id, u: customer.id,
  })).companyContact;
  userErrors(await gql(env, `mutation($c:ID!,$k:ID!){companyAssignMainContact(companyId:$c,companyContactId:$k){company{id} userErrors{field message}}}`, {
    c: company.id, k: contact.id,
  }));
  await sendPendingMail(env, customer.id, f);
  return { status: 'created', companyId: company.id };
}

// 30.10.2026: po akceptacji (Adrian przypisuje kontaktowi rolę w lokalizacji) Shopify wysyła webhook
// company_contact_roles/assign → wysyłamy klientowi „E-mail z dostępem B2B” (szablon Shopify company_contact_welcome_email).
// Shopify sam nic nie wysyła przy akceptacji. Tag DOSTEP chroni przed drugim mailem (np. rola w kolejnej lokalizacji).
const DOSTEP = 'dostep-b2b-wyslany';

async function hmacOk(env, raw, sig) {
  if (!sig) return false;
  const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(env.SHOPIFY_CLIENT_SECRET), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const mac = btoa(String.fromCharCode(...new Uint8Array(await crypto.subtle.sign('HMAC', key, raw))));
  return mac.length === sig.length && crypto.subtle.timingSafeEqual
    ? crypto.subtle.timingSafeEqual(new TextEncoder().encode(mac), new TextEncoder().encode(sig))
    : mac === sig;
}

async function onRoleAssign(env, payload) {
  const id = (JSON.stringify(payload).match(/gid:\/\/shopify\/CompanyContact\/\d+/) || [])[0];
  if (!id) return 'brak kontaktu';
  const d = await gql(env, `query($id:ID!){companyContact(id:$id){customer{id tags}}}`, { id });
  const customer = d.companyContact?.customer;
  if (!customer) return 'brak klienta';
  if (customer.tags.includes(DOSTEP)) return 'już wysłany';
  userErrors(await gql(env, `mutation($id:ID!){companyContactSendWelcomeEmail(companyContactId:$id){companyContact{id} userErrors{field message}}}`, { id }));
  await gql(env, `mutation($id:ID!,$t:[String!]!){tagsAdd(id:$id,tags:$t){userErrors{message}}}`, { id: customer.id, t: [DOSTEP] });
  return 'wysłany';
}

function cors(origin) {
  return {
    'Access-Control-Allow-Origin': ORIGINS.includes(origin) ? origin : ORIGINS[0],
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Vary': 'Origin',
  };
}

export default {
  async fetch(req, env) {
    if (req.method === 'POST' && new URL(req.url).pathname === '/webhook/role-assign') {
      const raw = await req.arrayBuffer();
      if (!(await hmacOk(env, raw, req.headers.get('X-Shopify-Hmac-Sha256')))) return new Response('unauthorized', { status: 401 });
      try {
        console.log('role-assign:', await onRoleAssign(env, JSON.parse(new TextDecoder().decode(raw))));
      } catch (e) {
        console.error('role-assign:', e.message);
      }
      return new Response('ok'); // zawsze 200, żeby Shopify nie ponawiał w kółko
    }
    const origin = req.headers.get('Origin') || '';
    const h = { ...cors(origin), 'Content-Type': 'application/json' };
    if (req.method === 'OPTIONS') return new Response(null, { headers: h });
    if (req.method !== 'POST' || !ORIGINS.includes(origin)) return new Response('{"status":"forbidden"}', { status: 403, headers: h });
    let b;
    try { b = await req.json(); } catch { return new Response('{"status":"bad_request"}', { status: 400, headers: h }); }
    if (b.hp) return new Response('{"status":"created"}', { headers: h }); // pułapka na boty: udajemy sukces

    const f = {
      nip: clean(b.nip, 30).replace(/"/g, ''), firma: clean(b.firma), ulica: clean(b.ulica), kod: clean(b.kod, 12), miasto: clean(b.miasto, 80),
      kraj: clean(b.kraj, 2).toUpperCase(), dostawa: clean(b.dostawa), osoba: clean(b.osoba, 120), telefon: clean(b.telefon, 30),
      email: clean(b.email, 120).toLowerCase().replace(/"/g, ''), rodzaj: clean(b.rodzaj, 80), opis: clean(b.opis, 1000), ilosci: clean(b.ilosci, 200),
      locale: clean(b.locale, 5),
    };
    const missing = ['firma', 'ulica', 'kod', 'miasto', 'osoba', 'telefon', 'email'].filter((k) => !f[k]);
    if (missing.length || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(f.email) || !nipOk(f.nip, f.kraj || 'PL')) {
      return new Response(JSON.stringify({ status: 'invalid', missing }), { status: 422, headers: h });
    }
    try {
      const out = await register(env, f);
      const id = out.companyId?.split('/').pop();
      if (id) out.adminUrl = `https://admin.shopify.com/store/ccucsr-si/companies/${id}`;
      return new Response(JSON.stringify(out), { headers: h });
    } catch (e) {
      console.error(e.message);
      return new Response(JSON.stringify({ status: 'error' }), { status: 502, headers: h });
    }
  },
};
