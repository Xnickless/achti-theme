#!/usr/bin/env python3
"""Black Week ACHTI B2B 23–27.11.2026 — 5 maili (PL + EN w jednym, jak newsletter WITAJ15 v2).
Teksty PL: plan Adriana (21.11.2026); zmiana: rabat nalicza się automatycznie (bez kodów BW100…).
Wynik: docs/black-week/mail-<n>.html → Shopify Messaging → „Napisz własny kod”; temat i preheader w komentarzu na górze pliku."""
import os, html
OUT = os.path.join(os.path.dirname(__file__), '..', 'docs', 'black-week')
URL_PL, URL_EN = 'https://b2b.achti.com/pages/black-week', 'https://b2b.achti.com/en/pages/black-week'
F = "font-family:Helvetica,Arial,sans-serif;"
# 22.11.2026 (Adrian, ostatecznie): rabat procentowy od liczby sztuk, maks. 15%
TIERS = [(100, 4), (200, 7), (350, 10), (500, 15)]

def tiers_table(rows=TIERS, en=False):
    tr = []
    for i, (n, pct) in enumerate(rows):
        nxt = rows[i + 1][0] if i + 1 < len(rows) else None
        if en:
            left = f"from {n} pcs" if nxt is None else f"{n}–{nxt - 1} pcs"
            right = f"{pct}% off"
        else:
            left = f"od {n}&nbsp;szt." if nxt is None else f"{n}–{nxt - 1}&nbsp;szt."
            right = f"−{pct}%"
        tr.append(f'<tr><td style="padding:10px 16px;border-bottom:1px solid #ececec;{F}font-size:15px;color:#444444;">{left}</td>'
                  f'<td align="right" style="padding:10px 16px;border-bottom:1px solid #ececec;{F}font-size:15px;font-weight:bold;color:#111111;">{right}</td></tr>')
    head = ('Pieces in your order', 'Discount on the whole order') if en else ('Liczba sztuk w zamówieniu', 'Rabat na całe zamówienie')
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
    # 22.11.2026 (Adrian): treść na odwrót — najpierw EN, pod spodem PL
    top = 'border-top:1px solid #ececec;' if lang == 'pl' else ''
    anchor = '<div id="pl"></div>' if lang == 'pl' else ''
    tag = 'h2' if lang == 'pl' else 'h1'
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
<html lang="en" xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<meta name="x-apple-disable-message-reformatting">
<meta name="format-detection" content="telephone=no, address=no, email=no">
<title>{html.escape(subject[0])}</title>
<!-- Black Week ACHTI B2B, mail {n}/6 (tools/build_bw_mails.py). Shopify Messaging → „Napisz własny kod”, odbiorcy: Wszyscy subskrybenci.
     Temat: {subject[0]}
     Preheader: {pre[1]} / {pre[0]}  (22.11.2026, Adrian: najpierw EN, potem PL) -->
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
<div style="display:none;font-size:1px;line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden;mso-hide:all;">{pre[1]} / {pre[0]}&#8199;&#847;&#8199;&#847;&#8199;&#847;&#8199;&#847;&#8199;&#847;&#8199;&#847;</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f2f1ef;">
<tr><td align="center" style="padding:32px 12px;">
<!--[if mso]><table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0"><tr><td><![endif]-->
<table role="presentation" class="wrap" width="600" cellpadding="0" cellspacing="0" border="0" style="width:600px;max-width:600px;background-color:#ffffff;">
  <tr><td align="center" style="padding:14px 48px;background-color:#111111;{F}font-size:12px;letter-spacing:3px;text-transform:uppercase;color:#ffffff;">Black Week · 23–27.11.2026</td></tr>
  <tr><td align="right" class="px" style="padding:14px 48px 0;{F}font-size:11px;letter-spacing:1px;text-transform:uppercase;">
    <a href="#pl" style="color:#8a8a8a;text-decoration:none;">Wersja polska niżej&nbsp;&darr;</a>
  </td></tr>
  <tr><td align="center" style="padding:20px 48px 28px;border-bottom:1px solid #ececec;">
    <a href="https://b2b.achti.com" target="_blank"><img src="https://cdn.shopify.com/s/files/1/1032/7841/2118/files/achti_poziom_jpg.jpg?v=1780476571&amp;width=360" width="140" alt="Achti" style="display:block;width:140px;height:auto;"></a>
  </td></tr>
{section('en', *en)}
{section('pl', *pl)}
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
    Wypisz się / Unsubscribe: {{{{ unsubscribe_link }}}}
  </td></tr>
</table>
</td></tr>
</table>
{{{{ open_tracking_block }}}}
</body>
</html>
'''

PL_RULES = 'Promocja trwa do 27.11.2026, godz. 23:59. Bez kodu — rabat nalicza się automatycznie w&nbsp;koszyku. Rabaty nie łączą się. <a href="' + URL_PL + '" style="color:#6b6b6b;text-decoration:underline;">Regulamin akcji</a>'
EN_RULES = 'Valid until 27.11.2026, 23:59 (Polish time). No code needed — the discount is applied automatically in the cart. Discounts cannot be combined. <a href="' + URL_EN + '" style="color:#6b6b6b;text-decoration:underline;">Terms</a>'
def link(url, txt): return f'<a href="{url}" style="color:#6b6b6b;text-decoration:underline;">{txt}</a>'

MAILS = [
 dict(subject=('BLACK WEEK ACHTI: up to 15% off your whole order | do −15% na całe zamówienie', ''),
      pre=('Tylko 5 dni, bez kodu.', 'Only 5 days: up to 15% off your B2B order, no code needed.'),
      pl=('Black Week ACHTI B2B wystartował', 'Do −15% na całe zamówienie',
          p('Od 23 do 27 listopada dajemy rabat na <strong>całe zamówienie</strong> — tym większy, im więcej sztuk zamawiasz:') + tiers_table() +
          p('<br>Wybierz produkty, osiągnij próg — <strong>bez kodu</strong>, rabat naliczy się sam w koszyku.'), 'Zamów i odbierz rabat', PL_RULES),
      en=('Black Week ACHTI B2B is on', 'Up to 15% off your whole order',
          p('From 23 to 27 November you get a discount on your <strong>whole order</strong> — the more pieces, the bigger it gets:') + tiers_table(en=True) +
          p('<br>Choose your products and reach a threshold — <strong>no code needed</strong>, the discount is applied automatically in the cart.'), 'Order and get your discount', EN_RULES)),
 dict(subject=('From 500 pcs: 15% off your whole order | Od 500 szt. aż −15%', ''),
      pre=('Przy 500 szt. rabat rośnie z −10% do −15%.', 'At 500 pcs your discount goes up from 10% to 15%.'),
      pl=('Black Week · dzień 2', 'Większe zamówienie = większy rabat',
          p('W Black Week warto sprawdzić, czy nie opłaca Ci się dobrać jeszcze kilku modeli.') + big(['350 szt. → −10% na całe zamówienie', '500 szt. → <strong>−15% na całe zamówienie</strong>']) +
          p('<br>Koszyk pokazuje, ile sztuk brakuje do kolejnego progu.'), 'Sprawdź ofertę Black Week', 'Promocja trwa do piątku 27 listopada. Jeden rabat na zamówienie. ' + link(URL_PL, 'Regulamin akcji')),
      en=('Black Week · day 2', 'A bigger order = a bigger discount',
          p('During Black Week it is worth checking whether a few more models pay off.') + big(['350 pcs → 10% off your whole order', '500 pcs → <strong>15% off your whole order</strong>']) +
          p('<br>The cart shows how many pieces are missing to the next threshold.'), 'See the Black Week offer', 'Valid until Friday, 27 November. One discount per order. ' + link(URL_EN, 'Terms'))),
 dict(subject=('Restock and get up to 15% off | Uzupełnij asortyment — do −15%', ''),
      pre=('Dobierz modele i kolory, żeby osiągnąć wyższy próg rabatowy.', 'Restock and reach a higher discount threshold.'),
      pl=('Black Week · półmetek', 'Czas na uzupełnienie zamówienia',
          p('Planujesz kolejne zatowarowanie? Sprawdź, czy masz już w koszyku wszystkie potrzebne modele i kolory.') + p('Podczas Black Week rabat zależy od łącznej liczby sztuk w zamówieniu:') + tiers_table() +
          p('<br>Dobierz asortyment odpowiedni dla swoich klientów i skorzystaj z progu, który osiągnie Twoje zamówienie.'), 'Uzupełnij zamówienie', 'Promocja obowiązuje do 27 listopada. Rabaty nie sumują się. ' + link(URL_PL, 'Regulamin akcji')),
      en=('Black Week · halfway', 'Time to complete your order',
          p('Planning your next restock? Check whether your cart already has all the models and colours you need.') + p('During Black Week the discount depends on the total number of pieces in your order:') + tiers_table(en=True) +
          p('<br>Pick the range that suits your customers and get the threshold your order reaches.'), 'Complete your order', 'Valid until 27 November. Discounts do not add up. ' + link(URL_EN, 'Terms'))),
 dict(subject=('Black Week ACHTI ends tomorrow | Black Week kończy się jutro', ''),
      pre=('Masz czas tylko do piątku, do 23:59.', 'You have until Friday, 23:59.'),
      pl=('Black Week · zostały 2 dni', 'Zostały tylko 2 dni Black Week ACHTI',
          p('Jeżeli planujesz zamówienie B2B, warto złożyć je jeszcze podczas naszej akcji.') + p('Do końca piątku możesz otrzymać:') +
          big(['−4%, −7%, −10% lub nawet <strong>−15%</strong> na całe zamówienie']) +
          p('<br>W zależności od liczby sztuk. Rabat naliczamy na aktualne zamówienie, a nie dopiero przy kolejnych zakupach.'), 'Skorzystaj z Black Week', 'Promocja kończy się 27.11.2026 o godz. 23:59. ' + link(URL_PL, 'Regulamin akcji')),
      en=('Black Week · 2 days left', 'Only 2 days of Black Week ACHTI left',
          p('If you are planning a B2B order, place it while the promotion is still on.') + p('Until Friday you can get:') +
          big(['4%, 7%, 10% or even <strong>15%</strong> off your whole order']) +
          p('<br>Depending on the number of pieces. The discount applies to your current order, not to future purchases.'), 'Use Black Week', 'The promotion ends on 27.11.2026 at 23:59 (Polish time). ' + link(URL_EN, 'Terms'))),
 dict(subject=('LAST DAY: up to 15% off | OSTATNI DZIEŃ: do −15% rabatu', ''),
      pre=('Ostatni dzień: do −15% na całe zamówienie.', 'Last day: up to 15% off your whole order.'),
      pl=('Black Week · ostatni dzień', 'To już ostatni dzień Black Week ACHTI',
          p('Dzisiaj o 23:59 kończymy promocję B2B. To ostatnia okazja, aby otrzymać rabat na bieżące zamówienie:') + tiers_table() +
          p('<br>Złóż zamówienie przed zakończeniem promocji.'), 'Odbierz rabat Black Week', 'Promocja kończy się 27.11.2026 o godz. 23:59 czasu polskiego. ' + link(URL_PL, 'Regulamin akcji')),
      en=('Black Week · last day', 'It is the last day of Black Week ACHTI',
          p('Tonight at 23:59 (Polish time) our B2B promotion ends. Last chance to get a discount on your current order:') + tiers_table(en=True) +
          p('<br>Place your order before the promotion ends.'), 'Get your Black Week discount', 'The promotion ends on 27.11.2026 at 23:59 Polish time (CET). ' + link(URL_EN, 'Terms'))),
 # 22.11.2026 (Adrian): w piątek wieczorem jeszcze krótkie przypomnienie — 27.11 18:00
 dict(subject=('LAST HOURS: Black Week ends at 23:59 | OSTATNIE GODZINY: Black Week do 23:59', ''),
      pre=('Dziś do 23:59 do −15% na całe zamówienie, bez kodu.', 'Tonight until 23:59: up to 15% off, no code needed.'),
      pl=('Black Week · ostatnie godziny', 'Zostało tylko kilka godzin',
          p('Dziś o 23:59 kończymy Black Week ACHTI.') + big(['Do <strong>−15%</strong> na całe zamówienie']) +
          p('<br><strong>Bez kodu</strong> — rabat nalicza się sam w koszyku. Jeśli planujesz zamówienie, to ostatni moment.'), 'Zamów przed 23:59', 'Promocja kończy się 27.11.2026 o godz. 23:59 czasu polskiego. ' + link(URL_PL, 'Regulamin akcji')),
      en=('Black Week · last hours', 'Only a few hours left',
          p('Black Week ACHTI ends tonight at 23:59 (Polish time).') + big(['Up to <strong>15%</strong> off your whole order']) +
          p('<br><strong>No code needed</strong> — the discount is applied automatically in the cart. If you were planning an order, now is the moment.'), 'Order before 23:59', 'The promotion ends on 27.11.2026 at 23:59 Polish time (CET). ' + link(URL_EN, 'Terms'))),
]
os.makedirs(OUT, exist_ok=True)
for i, m in enumerate(MAILS, 1):
    path = os.path.join(OUT, f'mail-{i}.html')
    open(path, 'w', encoding='utf-8').write(page(i, m['subject'], m['pre'], m['pl'], m['en']))
    print(path)
