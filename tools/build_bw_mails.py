#!/usr/bin/env python3
"""Black Week ACHTI B2B 23–27.11.2026 — 5 maili (PL + EN w jednym, jak newsletter WITAJ15 v2).
Teksty PL: plan Adriana (21.11.2026); zmiana: rabat nalicza się automatycznie (bez kodów BW100…).
Wynik: docs/black-week/mail-<n>.html → Shopify Messaging → „Napisz własny kod”; temat i preheader w komentarzu na górze pliku."""
import os, html
OUT = os.path.join(os.path.dirname(__file__), '..', 'docs', 'black-week')
URL_PL, URL_EN = 'https://b2b.achti.com/pages/black-week', 'https://b2b.achti.com/en/pages/black-week'
F = "font-family:Helvetica,Arial,sans-serif;"
TIERS = [('5 000', '100'), ('10 000', '200'), ('15 000', '500'), ('25 000', '1 000'), ('35 000', '1 500'), ('50 000', '2 500')]

def tiers_table(rows, en=False):
    tr = []
    for a, b in rows:
        left = f"from PLN {a.replace(' ', ',')}" if en else f"od {a}&nbsp;zł"
        right = f"PLN {b.replace(' ', ',')} off" if en else f"{b}&nbsp;zł rabatu"
        tr.append(f'<tr><td style="padding:10px 16px;border-bottom:1px solid #ececec;{F}font-size:15px;color:#444444;">{left}</td>'
                  f'<td align="right" style="padding:10px 16px;border-bottom:1px solid #ececec;{F}font-size:15px;font-weight:bold;color:#111111;">{right}</td></tr>')
    head = ('Order value (net)', 'Your bonus') if en else ('Wartość zamówienia netto', 'Twój bonus')
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:8px 0 8px;">'
            f'<tr><td style="padding:10px 16px;background-color:#111111;{F}font-size:11px;letter-spacing:1.5px;text-transform:uppercase;color:#ffffff;">{head[0]}</td>'
            f'<td align="right" style="padding:10px 16px;background-color:#111111;{F}font-size:11px;letter-spacing:1.5px;text-transform:uppercase;color:#ffffff;">{head[1]}</td></tr>'
            + ''.join(tr) + '</table>')

def big(lines):
    return ''.join(f'<p style="margin:0 0 6px;font-family:Georgia,\'Times New Roman\',serif;font-size:22px;line-height:30px;color:#111111;">{l}</p>' for l in lines)

def p(t, size=16, color='#1a1a1a'):
    return f'<p style="margin:0 0 16px;{F}font-size:{size}px;line-height:{int(size*1.6)}px;color:{color};">{t}</p>'

def button(url, label):
    return (f'<!--[if mso]><v:rect xmlns:v="urn:schemas-microsoft-com:vml" href="{url}" style="height:52px;v-text-anchor:middle;width:320px;" stroke="f" fillcolor="#111111"><center style="color:#ffffff;font-family:Arial,sans-serif;font-size:14px;letter-spacing:1px;">{label.upper()}</center></v:rect><![endif]-->'
            f'<!--[if !mso]><!--><a href="{url}" target="_blank" style="display:inline-block;background-color:#111111;color:#ffffff;{F}font-size:14px;line-height:20px;letter-spacing:1.5px;text-transform:uppercase;text-decoration:none;padding:16px 40px;">{label}</a><!--<![endif]-->')

def section(lang, eyebrow, title, body, btn, small):
    url = URL_EN if lang == 'en' else URL_PL
    top = 'border-top:1px solid #ececec;' if lang == 'en' else ''
    anchor = '<div id="en"></div>' if lang == 'en' else ''
    tag = 'h2' if lang == 'en' else 'h1'
    return f'''
  <tr><td class="px" style="padding:44px 48px 8px;{top}{F}color:#1a1a1a;">
    {anchor}<p style="margin:0 0 14px;font-size:11px;line-height:16px;letter-spacing:2px;text-transform:uppercase;color:#8a8a8a;">{eyebrow}</p>
    <{tag} class="h1" style="margin:0 0 24px;font-family:Georgia,'Times New Roman',serif;font-size:30px;line-height:38px;font-weight:normal;color:#111111;">{title}</{tag}>
    {body}
  </td></tr>
  <tr><td align="center" class="px btn" style="padding:16px 48px 12px;">{button(url, btn)}</td></tr>
  <tr><td class="px" style="padding:8px 48px 40px;{F}"><p style="margin:0;font-size:13px;line-height:20px;color:#6b6b6b;text-align:center;">{small}</p></td></tr>'''

def page(n, subject, pre, pl, en):
    return f'''<!DOCTYPE html>
<html lang="pl" xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<meta name="x-apple-disable-message-reformatting">
<meta name="format-detection" content="telephone=no, address=no, email=no">
<title>{html.escape(subject[0])}</title>
<!-- Black Week ACHTI B2B, mail {n}/5 (tools/build_bw_mails.py). Shopify Messaging → „Napisz własny kod”, odbiorcy: Wszyscy subskrybenci.
     Temat: {subject[0]} / {subject[1]}
     Preheader: {pre[0]} / {pre[1]} -->
<!--[if mso]><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml><![endif]-->
<style>
  body{{margin:0!important;padding:0!important;width:100%!important;-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%}}
  table,td{{mso-table-lspace:0;mso-table-rspace:0;border-collapse:collapse}}
  img{{border:0;outline:none;text-decoration:none;-ms-interpolation-mode:bicubic}}
  a{{text-decoration:none}}
  @media only screen and (max-width:620px){{
    .wrap{{width:100%!important}}
    .px{{padding-left:24px!important;padding-right:24px!important}}
    .h1{{font-size:26px!important;line-height:32px!important}}
    .btn a{{display:block!important}}
  }}
</style>
</head>
<body style="margin:0;padding:0;background-color:#f2f1ef;">
<div style="display:none;font-size:1px;line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden;mso-hide:all;">{pre[0]} / {pre[1]}&#8199;&#847;&#8199;&#847;&#8199;&#847;&#8199;&#847;&#8199;&#847;&#8199;&#847;</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f2f1ef;">
<tr><td align="center" style="padding:32px 12px;">
<!--[if mso]><table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0"><tr><td><![endif]-->
<table role="presentation" class="wrap" width="600" cellpadding="0" cellspacing="0" border="0" style="width:600px;max-width:600px;background-color:#ffffff;">
  <tr><td align="center" style="padding:14px 48px;background-color:#111111;{F}font-size:12px;letter-spacing:3px;text-transform:uppercase;color:#ffffff;">Black Week · 23–27.11.2026</td></tr>
  <tr><td align="right" class="px" style="padding:14px 48px 0;{F}font-size:11px;letter-spacing:1px;text-transform:uppercase;">
    <a href="#en" style="color:#8a8a8a;text-decoration:none;">English below&nbsp;&darr;</a>
  </td></tr>
  <tr><td align="center" style="padding:20px 48px 28px;border-bottom:1px solid #ececec;">
    <a href="https://b2b.achti.com" target="_blank"><img src="https://cdn.shopify.com/s/files/1/1032/7841/2118/files/achti_poziom_jpg.jpg?v=1780476571&amp;width=360" width="140" alt="Achti" style="display:block;width:140px;height:auto;"></a>
  </td></tr>
{section('pl', *pl)}
{section('en', *en)}
  <tr><td align="center" class="px" style="padding:28px 48px;background-color:#111111;{F}font-size:13px;line-height:22px;color:#bdbdbd;">
    <a href="mailto:hello@achti.com" style="color:#ffffff;text-decoration:none;">hello@achti.com</a>&nbsp;&nbsp;|&nbsp;&nbsp;<a href="tel:+48784900094" style="color:#ffffff;text-decoration:none;">+48&nbsp;784&nbsp;900&nbsp;094</a>&nbsp;&nbsp;|&nbsp;&nbsp;<a href="https://b2b.achti.com" style="color:#ffffff;text-decoration:none;">b2b.achti.com</a>
  </td></tr>
</table>
<!--[if mso]></td></tr></table><![endif]-->
<table role="presentation" class="wrap" width="600" cellpadding="0" cellspacing="0" border="0" style="width:600px;max-width:600px;">
  <tr><td align="center" class="px" style="padding:20px 48px 0;{F}font-size:11px;line-height:18px;color:#8a8a8a;">
    Achti sp. z o.o. sp.k. · Bieńkowice 152, 32-410 Dobczyce<br>
    Otrzymujesz tę wiadomość, bo zgodziłeś się na wiadomości marketingowe od Achti.<br>
    You receive this email because you agreed to receive marketing emails from Achti.<br>
    <a href="{{{{ unsubscribe_link }}}}" style="color:#8a8a8a;text-decoration:underline;">Wypisz się / Unsubscribe</a>
  </td></tr>
</table>
</td></tr>
</table>
{{{{ open_tracking_block }}}}
</body>
</html>
'''

PL_RULES = 'Promocja trwa do 27.11.2026, godz. 23:59. Rabat nalicza się automatycznie w&nbsp;koszyku. Rabaty nie łączą się. <a href="' + URL_PL + '" style="color:#6b6b6b;text-decoration:underline;">Regulamin akcji</a>'
EN_RULES = 'Valid until 27.11.2026, 23:59 (Polish time). The discount is applied automatically in the cart. Discounts cannot be combined. In EUR/USD orders amounts are converted at the platform’s rate. <a href="' + URL_EN + '" style="color:#6b6b6b;text-decoration:underline;">Terms</a>'

MAILS = [
 dict(subject=('BLACK WEEK ACHTI: dokładamy nawet 2 500 zł do Twojego zamówienia!', 'BLACK WEEK ACHTI: up to PLN 2,500 off your order!'),
      pre=('Tylko 5 dni. Odbierz dodatkowy bonus na zamówienie B2B.', 'Only 5 days. Get an extra bonus on your B2B order.'),
      pl=('Black Week ACHTI B2B wystartował', 'Dokładamy nawet 2&nbsp;500&nbsp;zł do Twojego zamówienia',
          p('Od 23 do 27 listopada dokładamy do Twojego zamówienia nawet <strong>2&nbsp;500&nbsp;zł netto</strong>.') + p('Im większe zamówienie, tym większy bonus:') + tiers_table(TIERS) +
          p('<br>Wybierz produkty, osiągnij próg — rabat naliczy się sam na aktualne zamówienie.'), 'Zamów i odbierz bonus', PL_RULES),
      en=('Black Week ACHTI B2B is on', 'Up to PLN 2,500 off your order',
          p('From 23 to 27 November we take up to <strong>PLN 2,500 net</strong> off your order.') + p('The bigger the order, the bigger the bonus:') + tiers_table(TIERS, True) +
          p('<br>Choose your products and reach a threshold — the discount is applied automatically to your current order.'), 'Order and get your bonus', EN_RULES)),
 dict(subject=('Brakuje Ci do 15 000 zł? ACHTI dołoży aż 500 zł', 'Close to PLN 15,000? ACHTI adds PLN 500'),
      pre=('Przy 15 000 zł netto otrzymasz 500 zł rabatu zamiast 200 zł.', 'At PLN 15,000 net you get PLN 500 off instead of PLN 200.'),
      pl=('Black Week · dzień 2', 'Większe zamówienie = większy bonus',
          p('W Black Week warto sprawdzić, czy nie opłaca Ci się dobrać jeszcze kilku modeli.') + big(['10&nbsp;000&nbsp;zł netto → 200&nbsp;zł rabatu', '15&nbsp;000&nbsp;zł netto → <strong>500&nbsp;zł rabatu</strong>']) +
          p('<br>To aż 300&nbsp;zł więcej rabatu na aktualne zamówienie. Koszyk pokazuje, ile brakuje do kolejnego progu.'), 'Sprawdź ofertę Black Week', 'Promocja trwa do piątku 27 listopada. Jeden rabat na zamówienie. <a href="' + URL_PL + '" style="color:#6b6b6b;text-decoration:underline;">Regulamin akcji</a>'),
      en=('Black Week · day 2', 'A bigger order = a bigger bonus',
          p('During Black Week it is worth checking whether a few more models pay off.') + big(['PLN 10,000 net → PLN 200 off', 'PLN 15,000 net → <strong>PLN 500 off</strong>']) +
          p('<br>That is PLN 300 more off your current order. The cart shows how much is missing to the next threshold.'), 'See the Black Week offer', 'Valid until Friday, 27 November. One discount per order. <a href="' + URL_EN + '" style="color:#6b6b6b;text-decoration:underline;">Terms</a>')),
 dict(subject=('Uzupełnij asortyment i odbierz bonus od ACHTI', 'Restock your range and get a bonus from ACHTI'),
      pre=('Dobierz modele i warianty, żeby osiągnąć wyższy próg rabatowy.', 'Add models and colours to reach a higher discount threshold.'),
      pl=('Black Week · półmetek', 'Czas na uzupełnienie zamówienia',
          p('Planujesz kolejne zatowarowanie? Sprawdź, czy masz już w koszyku wszystkie potrzebne modele i kolory.') + p('Podczas Black Week dodatkowy rabat zależy od łącznej wartości zamówienia:') +
          big(['15&nbsp;000&nbsp;zł netto = 500&nbsp;zł bonusu', '25&nbsp;000&nbsp;zł netto = 1&nbsp;000&nbsp;zł bonusu', '50&nbsp;000&nbsp;zł netto = 2&nbsp;500&nbsp;zł bonusu']) +
          p('<br>Dobierz asortyment odpowiedni dla swoich klientów i skorzystaj z progu, który osiągnie Twoje zamówienie.'), 'Uzupełnij zamówienie', 'Promocja obowiązuje do 27 listopada. Rabaty nie sumują się. <a href="' + URL_PL + '" style="color:#6b6b6b;text-decoration:underline;">Regulamin akcji</a>'),
      en=('Black Week · halfway', 'Time to complete your order',
          p('Planning your next restock? Check whether your cart already has all the models and colours you need.') + p('During Black Week the extra discount depends on the total order value:') +
          big(['PLN 15,000 net = PLN 500 bonus', 'PLN 25,000 net = PLN 1,000 bonus', 'PLN 50,000 net = PLN 2,500 bonus']) +
          p('<br>Pick the range that suits your customers and get the threshold your order reaches.'), 'Complete your order', 'Valid until 27 November. Discounts do not add up. <a href="' + URL_EN + '" style="color:#6b6b6b;text-decoration:underline;">Terms</a>')),
 dict(subject=('Black Week ACHTI kończy się jutro — wykorzystaj bonus', 'Black Week ACHTI ends tomorrow — use your bonus'),
      pre=('Masz czas tylko do piątku, do 23:59.', 'You have until Friday, 23:59.'),
      pl=('Black Week · zostały 2 dni', 'Zostały tylko 2 dni Black Week ACHTI',
          p('Jeżeli planujesz zamówienie B2B, warto złożyć je jeszcze podczas naszej akcji.') + p('Do końca piątku możesz otrzymać:') +
          big(['100, 200, 500, 1&nbsp;000, 1&nbsp;500 lub nawet <strong>2&nbsp;500&nbsp;zł</strong> rabatu netto']) +
          p('<br>W zależności od wartości zamówienia. Rabat naliczamy na aktualne zamówienie, a nie dopiero przy kolejnych zakupach.'), 'Skorzystaj z Black Week', 'Promocja kończy się 27.11.2026 o godz. 23:59. <a href="' + URL_PL + '" style="color:#6b6b6b;text-decoration:underline;">Regulamin akcji</a>'),
      en=('Black Week · 2 days left', 'Only 2 days of Black Week ACHTI left',
          p('If you are planning a B2B order, place it while the promotion is still on.') + p('Until Friday you can get:') +
          big(['PLN 100, 200, 500, 1,000, 1,500 or even <strong>PLN 2,500</strong> off (net)']) +
          p('<br>Depending on the order value. The discount applies to your current order, not to future purchases.'), 'Use Black Week', 'The promotion ends on 27.11.2026 at 23:59 (Polish time). <a href="' + URL_EN + '" style="color:#6b6b6b;text-decoration:underline;">Terms</a>')),
 dict(subject=('OSTATNI DZIEŃ: nawet 2 500 zł rabatu ACHTI kończy się dziś', 'LAST DAY: up to PLN 2,500 off ends today'),
      pre=('Ostatnie godziny na bonus do 2 500 zł netto.', 'Last hours for a bonus of up to PLN 2,500 net.'),
      pl=('Black Week · ostatni dzień', 'To już ostatni dzień Black Week ACHTI',
          p('Dzisiaj o 23:59 kończymy promocję B2B. To ostatnia okazja, aby otrzymać dodatkowy rabat na bieżące zamówienie:') + tiers_table([TIERS[0], TIERS[2], TIERS[3], TIERS[5]]) +
          p('<br>Złóż zamówienie przed zakończeniem promocji.'), 'Odbierz bonus Black Week', 'Promocja kończy się 27.11.2026 o godz. 23:59 czasu polskiego. <a href="' + URL_PL + '" style="color:#6b6b6b;text-decoration:underline;">Regulamin akcji</a>'),
      en=('Black Week · last day', 'It is the last day of Black Week ACHTI',
          p('Tonight at 23:59 (Polish time) our B2B promotion ends. Last chance to get an extra discount on your current order:') + tiers_table([TIERS[0], TIERS[2], TIERS[3], TIERS[5]], True) +
          p('<br>Place your order before the promotion ends.'), 'Get your Black Week bonus', 'The promotion ends on 27.11.2026 at 23:59 Polish time (CET). <a href="' + URL_EN + '" style="color:#6b6b6b;text-decoration:underline;">Terms</a>')),
]
os.makedirs(OUT, exist_ok=True)
for i, m in enumerate(MAILS, 1):
    path = os.path.join(OUT, f'mail-{i}.html')
    open(path, 'w', encoding='utf-8').write(page(i, m['subject'], m['pre'], m['pl'], m['en']))
    print(path)
