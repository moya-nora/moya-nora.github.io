#!/usr/bin/env python3
"""Страницы для поисковиков: «Нора» в Яндексе и Google.

Приложение — одна страница на JavaScript, и поисковики видят в нём мало текста. Этот сборщик делает обычные
HTML-страницы, которые поисковик читает целиком:
  /k/<книга>.html — книга из ручного каталога: описание, жанр, страна и «похожие книги»;
  /c/<подборка>.html — подборки по жанрам, настроениям, странам и новинки;
  sitemap.xml и robots.txt.
Главная index.html тоже собирается здесь. Каждая страница ведёт в приложение. Запуск: python3 tools/build_seo.py (GitHub Actions — после сборки новинок)."""
import html, json, os, re, time

ROOT = os.path.join(os.path.dirname(__file__), "..")
SITE = "https://moya-nora.github.io"
BOT = "https://t.me/Wonderbookworld_bot"
YNOW = time.gmtime().tm_year
esc = html.escape

TR = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя", ["a", "b", "v", "g", "d", "e", "e", "zh", "z", "i", "y", "k", "l", "m", "n", "o", "p", "r", "s", "t", "u", "f",
                                                  "h", "c", "ch", "sh", "sch", "", "y", "", "e", "yu", "ya"]))


def slug(s):
    s = "".join(TR.get(ch, ch) for ch in s.lower())
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:70] or "kniga"


GEN = {"classic": "Классика", "modern": "Современная проза", "detective": "Детективы", "fantasy": "Фэнтези", "scifi": "Фантастика",
       "kids": "Детские и подростковые книги", "nonfic": "Нон-фикшн"}

# ---------- данные: ручной каталог (с описаниями) + большой каталог + новинки ----------
app = open(os.path.join(ROOT, "app.html"), encoding="utf-8").read()
i = app.index("const CAT=") + len("const CAT=")
CAT, _ = json.JSONDecoder().raw_decode(app[i:])
books = []
for b in CAT:
    books.append({"t": b["t"], "a": b.get("a", ""), "y": b.get("y"), "g": b.get("g", "modern"), "c": b.get("c", ""), "tags": b.get("tags", []),
                  "q": b.get("q", 1) + 1, "ann": b.get("ann", ""), "acc": b.get("acclaim", []), "cat": True,
                  "when": b.get("when", ""), "f": b.get("f", [])})


def load(name):
    try:
        return json.load(open(os.path.join(ROOT, "books", name), encoding="utf-8"))
    except FileNotFoundError:
        return None


tagsx = load("tags.json") or {"tg": [], "m": {}}
for name in ("books.json", "new.json"):
    d = load(name)
    if not d:
        continue
    for w, t, ai, y, gi, tg, q, sl, ci, aw, pg, rw, o in d["b"]:
        a = d["a"][ai]
        tags = [d["tg"][j] for j in tg]
        e = tagsx["m"].get(str(w))
        if e and len(e) > 2:
            tags += [tagsx["tg"][j] for j in e[2] if j < len(tagsx["tg"])]
        books.append({"t": t, "a": a[0], "y": y or None, "g": d["g"][gi], "c": d["c"][ci] if ci >= 0 else (d["c"][a[1]] if a[1] >= 0 else ""),
                      "tags": tags, "q": q, "ann": "", "acc": [d["aw"][j] for j in aw] if name == "books.json" else [], "cat": False, "sl": sl})
seen, uniq = set(), []
for b in books:  # ручной каталог первым — у него есть описания
    k = re.sub(r"[^0-9a-zа-я]+", "", b["t"].lower().replace("ё", "е")) + "|" + b["a"].split(" ")[-1].lower()
    if k in seen or not re.search(r"[а-яё]", b["t"], re.I):
        continue
    seen.add(k)
    uniq.append(b)
books = uniq
print("книг с русским названием:", len(books), "из них с описанием:", sum(1 for b in books if b["ann"]))

has = lambda b, *t: any(x in b["tags"] for x in t)
love = lambda b: has(b, "любовь", "романтичное", "любовный роман", "любовное фэнтези")
notnovel = lambda b: b["g"] == "nonfic" or has(b, "мифология", "наука", "история", "биография", "мемуары", "психология")
y = lambda b: b["y"] or 0
COLL = [  # (адрес, заголовок, вступление, отбор)
    *[(f"zhanr-{g}", f"{n}: лучшие книги", f"{n} — книги, которые читатели «Норы» ставят на полку чаще всего.", (lambda g: lambda b: b["g"] == g)(g)) for g, n in GEN.items()],
    ("romantezi", "Ромэнтези: лучшие книги любовного фэнтези", "Магия, драконы и большая любовь — ромэнтези, которое читают запоем.",
     lambda b: not notnovel(b) and (has(b, "любовное фэнтези") or (b["g"] == "fantasy" and love(b) and y(b) >= 2000))),
    ("lyubovnye-romany", "Современные любовные романы", "Любовные романы последних десятилетий: от лёгких историй до серьёзной прозы.",
     lambda b: not notnovel(b) and (has(b, "любовный роман") or (love(b) and b["g"] not in ("fantasy", "scifi", "detective", "kids") and y(b) >= 1990))),
    ("dark-roman", "Дарк роман: тёмные истории о любви", "Мрачные, напряжённые истории любви — дарк роман и готика.",
     lambda b: not notnovel(b) and love(b) and has(b, "мрачное", "жутковатое", "хоррор", "готика") and y(b) >= 1990),
    ("young-adult", "Young adult: книги о взрослении", "Young adult — истории о первой любви, дружбе и поиске себя.",
     lambda b: has(b, "young adult") or (has(b, "взросление") and y(b) >= 1995)),
    ("zahvatyvayuschie", "Захватывающие книги, от которых не оторваться", "Книги, которые читатели проглатывают за пару вечеров.",
     lambda b: has(b, "напряжённое", "динамичное", "триллер", "приключения") or b["g"] == "detective"),
    ("smeshnye", "Смешные книги", "Книги, над которыми смеёшься вслух.", lambda b: has(b, "смешное", "юмор", "сатира")),
    ("uyutnye", "Уютные книги для вечера", "Тёплые и светлые книги — для пледа и чая.",
     lambda b: has(b, "уют", "тёплое", "светлое", "сказка") and not has(b, "мрачное", "жутковатое", "хоррор", "война")),
    ("strashnye", "Страшные книги", "Хоррор, мистика и готика — книги, после которых не выключишь свет.", lambda b: has(b, "жутковатое", "хоррор", "мистика", "готика")),
    ("zastavlyayut-zadumatsya", "Книги, которые заставляют задуматься", "Романы о главном — после них долго думаешь.",
     lambda b: has(b, "интеллектуальное", "философский роман", "психологический роман", "антиутопия")),
    ("trogatelnye", "Трогательные книги", "Истории, которые трогают до слёз.", lambda b: has(b, "грустное", "взросление")),
    ("antiutopii", "Антиутопии: лучшие книги", "Миры, в которые не хочется попасть, — и от которых не оторваться.", lambda b: has(b, "антиутопия")),
    ("novinki", f"Книжные новинки {YNOW - 1}–{YNOW}", "Новые книги последних двух лет — каталог обновляется каждый месяц.", lambda b: y(b) >= YNOW - 1 and not notnovel(b)),
    ("s-premiyami", "Книги с литературными премиями", "Книги, получившие главные литературные премии.", lambda b: len(b["acc"]) > 0),
]
cty = {}
for b in books:
    if b["c"]:
        cty[b["c"]] = cty.get(b["c"], 0) + 1
CTY_RP = {"Россия": "русских", "США": "американских", "Англия": "английских", "Франция": "французских", "Германия": "немецких", "Япония": "японских",
          "Италия": "итальянских", "Испания": "испанских", "Швеция": "шведских", "Канада": "канадских", "Ирландия": "ирландских", "Норвегия": "норвежских",
          "Польша": "польских", "Китай": "китайских", "Бразилия": "бразильских", "Колумбия": "колумбийских", "Аргентина": "аргентинских",
          "Австрия": "австрийских", "Чехия": "чешских", "Израиль": "израильских", "Индия": "индийских", "Южная Корея": "корейских", "Турция": "турецких"}
for c, n in sorted(cty.items(), key=lambda x: -x[1]):
    if c in CTY_RP:
        COLL.append((f"strana-{slug(c)}", f"Лучшие книги {CTY_RP[c]} авторов", f"Самые известные книги {CTY_RP[c]} писателей.", (lambda c: lambda b: b["c"] == c)(c)))

# ---------- страницы ----------
VER = time.strftime("%Y%m%d")
PAL = {"fantasy": ["#2E2450", "#1F3A3A", "#4A2140", "#263552"], "scifi": ["#142B3D", "#1E2C4F", "#2A2A2A"], "detective": ["#2B2B30", "#3A1F1F", "#1C2630"],
       "classic": ["#5A2232", "#22344A", "#2F3B2A", "#E8DDC8"], "modern": ["#C9B79A", "#2D3A4A", "#6B3A2E", "#E3D6C1"], "kids": ["#2F5A4A", "#7A4A2A", "#3B4F7A"],
       "nonfic": ["#E8E1D3", "#23303A", "#3D2F25"]}


def hsh(t):
    h = 0
    for ch in t:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return h


def cv(b):
    pal = PAL.get(b["g"], PAL["modern"])
    c = pal[hsh(b["t"]) % len(pal)]
    light = int(c[1:3], 16) + int(c[3:5], 16) + int(c[5:7], 16) > 450
    f = "#3A2A1C" if light else ("#F1E2C2" if hsh(b["a"]) % 2 else "#E2B66B")
    return f'<div class="cv" style="--c:{c};--f:{f}"><b>{esc(b["t"])}</b><i>{esc(b["a"])}</i></div>'


HEAD = f"""<link rel="icon" href="/icons/icon-192.png"><link rel="apple-touch-icon" href="/icons/icon-180.png"><meta name="theme-color" content="#08080D">
<link rel="preload" href="/fonts/cormorant-garamond-cyrillic-600-normal.woff2" as="font" type="font/woff2" crossorigin><link rel="stylesheet" href="/site.css?v={VER}">"""
NAV = [("/c/romantezi.html", "Ромэнтези"), ("/c/novinki.html", "Новинки"), ("/c/zhanr-fantasy.html", "Фэнтези"), ("/c/", "Все подборки"), ("/#kak", "Как это работает")]
HDR = ('<header class="hd"><div class="wrap"><a class="logo" href="/"><img src="/icons/icon-192.png" alt="">Нора</a><nav class="nav">'
       + "".join(f'<a href="{u}">{t}</a>' for u, t in NAV)
       + '</nav><a class="btn sm open" id="openNora" href="/app.html">Открыть Нору</a></div></header>')
MINE = """<script>try{if(localStorage.getItem("zal.onb"))document.querySelectorAll("#openNora").forEach(function(a){a.textContent="Моя Нора"})}catch(e){}</script>"""


def footer(colls):
    pick = colls[:8]
    return (f'<footer class="ft"><div class="wrap"><div><div class="logo">Нора</div><p>Все твои книги в одном месте — бумажные, из Литрес, Яндекс Книг и LiveLib. '
            f'Шуршуня подскажет, что читать дальше.</p></div><div><h4>Подборки</h4>' + "".join(f'<a href="/c/{p}.html">{esc(t.split(":")[0])}</a>' for p, t in pick)
            + f'</div><div><h4>Нора</h4><a href="/app.html">Открыть в браузере</a><a href="{BOT}">Открыть в Telegram</a><a href="/c/">Все подборки</a></div></div></footer>')


FOOT = ""  # заполняется после сборки подборок


def page(path, title, desc, body, full_title=None):
    canon = f"{SITE}/{path}".replace("/index.html", "/")
    doc = f"""<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{esc(full_title or title + " — Нора")}</title><meta name="description" content="{esc(desc[:200])}"><link rel="canonical" href="{canon}">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc[:200])}"><meta property="og:url" content="{canon}">
<meta property="og:image" content="{SITE}/icons/icon-512.png"><meta property="og:type" content="website"><meta property="og:site_name" content="Нора">{HEAD}</head><body>
{HDR}<main>{body}</main>{FOOT}{MINE}</body></html>"""
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, "w", encoding="utf-8").write(doc)
    return canon


rank = lambda b: (-(b["q"] or 0), -(b.get("sl") or 0), not b["cat"])
urls = []
cat_books = [b for b in books if b["cat"]]
BOOK_URL = {}
used = set()
for b in cat_books:
    s = slug(b["t"] + "-" + b["a"].split(" ")[-1])
    while s in used:
        s += "-2"
    used.add(s)
    BOOK_URL[id(b)] = f"k/{s}.html"


def card(b, n=None, ann=False):
    u = BOOK_URL.get(id(b))
    meta = ", ".join(x for x in [b["a"], str(b["y"]) if b["y"] and b["y"] > 0 else ""] if x)
    inner = (cv(b) + (f'<div class="num">{n}</div>' if n else "") + f'<div class="t">{esc(b["t"])}</div><div class="a">{esc(meta)}</div>'
             + (f'<p>{esc(b["ann"])}</p>' if ann and b["ann"] else ""))
    return f'<a class="bk" href="/{u}">{inner}</a>' if u else f'<div class="bk">{inner}</div>'


CTA = f'<div class="ctas"><a class="btn" href="/app.html">Собрать свою полку</a><a class="btn ghost" href="{BOT}">Открыть в Telegram</a></div>'
coll_data = []
for path, title, lead, pred in COLL:
    L = sorted([b for b in books if pred(b)], key=rank)[:60]
    if len(L) < 8:
        continue
    # книги с описанием — вперёд, чтобы витрина подборки была живой
    L = sorted(L, key=lambda b: (not b["ann"], L.index(b)))
    coll_data.append((path, title, lead, L))
FOOT = footer([(p, t) for p, t, _, _ in coll_data])
for path, title, lead, L in coll_data:
    body = (f'<div class="wrap"><div class="crumbs"><a href="/">Нора</a> · <a href="/c/">Подборки</a></div><div class="ph"><h1>{esc(title)}</h1><p class="lead">{esc(lead)}</p></div>'
            f'<div class="grid">{"".join(card(b, i + 1, True) for i, b in enumerate(L))}</div>'
            f'<section class="final"><h2>Отмечай прочитанное —<br>Нора подберёт следующее</h2><p>Собери все свои книги на одной полке и получай советы по своему вкусу.</p>{CTA}</section></div>')
    urls.append(page(f"c/{path}.html", title, lead + " " + ", ".join(b["t"] for b in L[:5]) + ".", body))


def coll_card(p, t, L):
    return (f'<a class="coll" href="/c/{p}.html"><div class="st">{"".join(cv(b) for b in L[:3])}</div><h3>{esc(t.split(":")[0])}</h3>'
            f'<small>{len(L)} книг</small></a>')


urls.append(page("c/index.html", "Подборки книг", "Подборки книг по жанрам, настроениям и странам — от ромэнтези до классики.",
                 '<div class="wrap"><div class="crumbs"><a href="/">Нора</a></div><div class="ph"><h1>Подборки книг</h1>'
                 '<p class="lead">По жанрам, настроениям и странам — от ромэнтези до классики.</p></div><div class="colls" style="padding-bottom:70px">'
                 + "".join(coll_card(p, t, L) for p, t, _, L in coll_data) + "</div></div>"))

pool = {}
for b in cat_books:
    pool.setdefault(b["g"], []).append(b)
for b in cat_books:
    tg = set(b["tags"])
    sim = sorted((x for x in pool.get(b["g"], []) if x is not b), key=lambda x: (-len(tg & set(x["tags"])), -(x["q"] or 0)))[:6]
    facts = [x for x in [GEN.get(b["g"], ""), b["c"], str(b["y"]) if b["y"] and b["y"] > 0 else ""] + b["tags"][:4] if x]
    desc = b["ann"] or f"«{b['t']}» — {b['a']}."
    body = (f'<div class="wrap"><div class="crumbs"><a href="/">Нора</a> · <a href="/c/zhanr-{b["g"]}.html">{esc(GEN.get(b["g"], "Книги"))}</a></div>'
            f'<article class="book">{cv(b)}<div><h1>{esc(b["t"])}</h1><p class="by">{esc(b["a"])}</p>'
            f'<div class="facts">{"".join(f"<span>{esc(x)}</span>" for x in facts)}</div>'
            + (f'<p class="ann">{esc(b["ann"])}</p>' if b["ann"] else "")
            + (f'<p class="when">{esc(b["when"])}</p>' if b.get("when") else "")
            + "".join(f'<div class="fact"><b>{esc(f[0])}</b><span>{esc(f[1])}</span></div>' for f in b.get("f", [])[:3] if len(f) > 1)
            + (f'<p class="acc">Признание: {esc(", ".join(b["acc"]))}</p>' if b["acc"] else "")
            + CTA + "</div></article>"
            + (f'<section class="sec"><h2>Похожие книги</h2><p class="sub">Если понравилась «{esc(b["t"])}», попробуй эти.</p>'
               f'<div class="row">{"".join(card(x) for x in sim)}</div></section>' if sim else "")
            + "</div>")
    urls.append(page(BOOK_URL[id(b)], f"«{b['t']}», {b['a']}: о чём книга и что почитать похожее", desc, body))

# ---------- главная ----------
get = lambda p: next((L for q, _, _, L in coll_data if q == p), [])
hero = [b for b in get("romantezi") if b["ann"]][:5] or cat_books[:5]
show = [p for p in ("romantezi", "dark-roman", "lyubovnye-romany", "zhanr-fantasy", "young-adult", "zahvatyvayuschie", "uyutnye", "zhanr-detective") if get(p)]
TG_REDIRECT = """<script>(function(){try{var s=location.search,h=location.hash,sa=(window.matchMedia&&matchMedia("(display-mode: standalone)").matches)||navigator.standalone;
if(/tgWebApp/.test(h+s)||sa||/[?&]app(=|&|$)/.test(s)){location.replace("app.html?v="+Math.floor(Date.now()/6e5)+(s?"&"+s.slice(1):"")+h)}}catch(e){}})()</script>"""
home = f"""<div class="wrap"><section class="hero"><div><div class="kick">Книжная полка с советником</div><h1>Все твои книги —<br>в одной <em>Норе</em></h1>
<p>Бумажные, из Литрес, Яндекс Книг и LiveLib — на одной полке. Сфотографируй шкаф, и полка соберётся сама. А Шуршуня подскажет, что читать дальше.</p>{CTA}
<div class="where">Бесплатно · в браузере, в Telegram и на экране телефона</div></div><div class="fan">{"".join(cv(b) for b in hero)}</div></section>
<section class="sec" id="kak"><div class="kick">Как это работает</div><h2>Три шага до своей библиотеки</h2><p class="sub">Никаких таблиц и ручного ввода — Нора делает скучную часть за тебя.</p>
<div class="steps"><div class="step"><div class="n">1</div><h3>Сфотографируй шкаф</h3><p>Нора узнает книги по корешкам и поставит их на полку. Или отметь прочитанное в ленте — одним свайпом.</p></div>
<div class="step"><div class="n">2</div><h3>Оцени и напиши отзыв</h3><p>Для себя или для друзей. Чем больше оценок, тем точнее Нора понимает твой вкус.</p></div>
<div class="step"><div class="n">3</div><h3>Получи совет</h3><p>Шуршуня подберёт следующую книгу — по настроению, жанру, тропам и тому, что ты любишь.</p></div></div></section>
<section class="sec"><div class="shead"><div><div class="kick">Подборки</div><h2>Что почитать</h2><p class="sub">Ромэнтези, дарк роман, фэнтези и книги на любое настроение.</p></div><a class="more" href="/c/">Все подборки →</a></div>
<div class="colls">{"".join(coll_card(p, next(t for q, t, _, _ in coll_data if q == p), get(p)) for p in show)}</div></section>
<section class="sec"><div class="shead"><div><div class="kick">Новинки</div><h2>Новые книги</h2><p class="sub">Каталог обновляется каждый месяц.</p></div><a class="more" href="/c/novinki.html">Все новинки →</a></div>
<div class="row">{"".join(card(b) for b in get("novinki")[:6])}</div></section>
<section class="sec"><div class="shur"><div class="ava">Ш</div><div><p class="q">«Знаю, что ты прочитала прошлым летом. И что тебе понравится этой осенью».</p>
<p>Шуршуня — хранительница Норы. Она помнит каждую твою книгу и советует новые без занудства.</p></div></div></section>
<section class="final"><h2>Собери свою Нору</h2><p>Это бесплатно и занимает пару минут.</p>{CTA}</section></div>"""
home_path = page("index.html", "Нора — твоя книжная библиотека", "Нора — личная книжная полка в Telegram и браузере: собери все прочитанные книги (бумажные, из Литрес, Яндекс Книг и LiveLib), "
                 "сфотографируй шкаф, получай советы, что читать дальше, — ромэнтези, фэнтези, детективы, классика.", home,
                 full_title="Нора — твоя книжная библиотека: все книги в одном месте и советы, что почитать")
idx = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
idx = idx.replace('<meta charset="utf-8">', '<meta charset="utf-8"><meta name="google-site-verification" content="s2CdXU7z22CJQ7fqwqJNwf2nyq4VN3Jk2UEHofqjoXc">'
                  '<link rel="manifest" href="/manifest.webmanifest"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="Моя Нора">' + TG_REDIRECT, 1)
open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(idx)
urls.insert(0, home_path)

now = time.strftime("%Y-%m-%d")
open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8").write(
    '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    + "".join(f"<url><loc>{u}</loc><lastmod>{now}</lastmod></url>\n" for u in urls) + "</urlset>\n")
open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8").write(f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n")
print("страниц:", len(urls), "подборок:", len(coll_data))
