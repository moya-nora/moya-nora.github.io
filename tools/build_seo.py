#!/usr/bin/env python3
"""Страницы для поисковиков: «Нора» в Яндексе и Google.

Приложение — одна страница на JavaScript, и поисковики видят в нём мало текста. Этот сборщик делает обычные
HTML-страницы, которые поисковик читает целиком:
  /k/<книга>.html — книга из ручного каталога: описание, жанр, страна и «похожие книги»;
  /c/<подборка>.html — подборки по жанрам, настроениям, странам и новинки;
  sitemap.xml и robots.txt.
Каждая страница ведёт в приложение. Запуск: python3 tools/build_seo.py (GitHub Actions — после сборки новинок)."""
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
                  "q": b.get("q", 1) + 1, "ann": b.get("ann", ""), "acc": b.get("acclaim", []), "cat": True})


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
    ("novinki", f"Книжные новинки {YNOW - 1}–{YNOW}", "Новые книги последних двух лет — каталог обновляется каждый месяц.", lambda b: y(b) >= YNOW - 1),
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
CSS = """body{margin:0;background:#05060A;color:#fff;font:16px/1.55 -apple-system,system-ui,'Segoe UI',sans-serif}
main{max-width:680px;margin:0 auto;padding:28px 20px 60px}a{color:#E2B66B}h1{font:600 32px/1.15 Georgia,serif;margin:8px 0 12px}
.lead{color:rgba(255,255,255,.75)}.cta{display:inline-block;margin:18px 10px 0 0;padding:12px 20px;border-radius:24px;background:#F5F5F7;color:#0B0C11;text-decoration:none;font-weight:600}
.cta.tg{background:none;color:#fff;box-shadow:inset 0 0 0 1px rgba(255,255,255,.3)}ol{padding-left:22px}li{margin:10px 0}li small{color:rgba(255,255,255,.55)}
.meta{color:rgba(255,255,255,.6);font-size:14px}nav{font-size:14px;color:rgba(255,255,255,.55)}h2{font:600 22px/1.2 Georgia,serif;margin:34px 0 8px}
footer{margin-top:40px;font-size:13px;color:rgba(255,255,255,.45)}"""


def page(path, title, desc, body):
    canon = f"{SITE}/{path}"
    doc = f"""<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} — Нора</title><meta name="description" content="{esc(desc[:200])}"><link rel="canonical" href="{canon}">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc[:200])}"><meta property="og:url" content="{canon}">
<meta property="og:image" content="{SITE}/icons/icon-512.png"><meta property="og:type" content="website"><meta property="og:site_name" content="Нора">
<link rel="icon" href="/icons/icon-192.png"><style>{CSS}</style></head><body><main>
<nav><a href="/">Нора</a> · <a href="/c/">подборки</a></nav>{body}
<p><a class="cta" href="/">Собрать свою полку в Норе</a><a class="cta tg" href="{BOT}">Открыть в Telegram</a></p>
<footer>Нора — все твои книги в одном месте: бумажные, из Литрес, Яндекс Книг и LiveLib. Шуршуня подскажет, что читать дальше.</footer>
</main></body></html>"""
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, "w", encoding="utf-8").write(doc)
    return canon


rank = lambda b: (-(b["q"] or 0), -(b.get("sl") or 0), not b["cat"])
urls = [SITE + "/"]
cat_books = [b for b in books if b["cat"]]
BOOK_URL = {}
used = set()
for b in cat_books:
    s = slug(b["t"] + "-" + b["a"].split(" ")[-1])
    while s in used:
        s += "-2"
    used.add(s)
    BOOK_URL[id(b)] = f"k/{s}.html"


def item(b):
    u = BOOK_URL.get(id(b))
    name = f'<a href="/{u}">{esc(b["t"])}</a>' if u else esc(b["t"])
    meta = ", ".join(x for x in [b["a"], str(b["y"]) if b["y"] and b["y"] > 0 else ""] if x)
    ann = f"<br><small>{esc(b['ann'])}</small>" if b["ann"] else ""
    return f"<li>{name} <small>— {esc(meta)}</small>{ann}</li>"


coll_links = []
for path, title, lead, pred in COLL:
    L = sorted([b for b in books if pred(b)], key=rank)[:60]
    if len(L) < 8:
        continue
    urls.append(page(f"c/{path}.html", title, lead + " " + ", ".join(b["t"] for b in L[:5]) + ".",
                     f"<h1>{esc(title)}</h1><p class='lead'>{esc(lead)}</p><ol>{''.join(item(b) for b in L)}</ol>"))
    coll_links.append((path, title))
urls.append(page("c/index.html", "Подборки книг", "Подборки книг по жанрам, настроениям и странам — от ромэнтези до классики.",
                 "<h1>Подборки книг</h1><ul>" + "".join(f'<li><a href="/c/{p}.html">{esc(t)}</a></li>' for p, t in coll_links) + "</ul>"))

pool = {}
for b in cat_books:
    pool.setdefault(b["g"], []).append(b)
for b in cat_books:
    tg = set(b["tags"])
    sim = sorted((x for x in pool.get(b["g"], []) if x is not b), key=lambda x: (-len(tg & set(x["tags"])), -(x["q"] or 0)))[:8]
    facts = " · ".join(x for x in [b["a"], GEN.get(b["g"], ""), b["c"], str(b["y"]) if b["y"] and b["y"] > 0 else ""] if x)
    desc = b["ann"] or f"«{b['t']}» — {b['a']}."
    body = (f"<h1>{esc(b['t'])}</h1><p class='meta'>{esc(facts)}</p><p class='lead'>{esc(b['ann'])}</p>"
            + (f"<p class='meta'>Премии: {esc(', '.join(b['acc']))}</p>" if b["acc"] else "")
            + (f"<h2>Похожие книги</h2><ol>{''.join(item(x) for x in sim)}</ol>" if sim else ""))
    urls.append(page(BOOK_URL[id(b)], f"«{b['t']}», {b['a']}: о чём книга и что почитать похожее", desc, body))

now = time.strftime("%Y-%m-%d")
open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8").write(
    '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    + "".join(f"<url><loc>{u}</loc><lastmod>{now}</lastmod></url>\n" for u in urls) + "</urlset>\n")
open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8").write(f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n")
print("страниц:", len(urls), "подборок:", len(coll_links))
