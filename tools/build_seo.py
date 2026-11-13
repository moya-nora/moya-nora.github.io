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
SUPPORT = f'<a href="{BOT}">пиши в Telegram-бот @Wonderbookworld_bot</a>'
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
for name in ("books.json", "new.json", "litres.json"):
    d = load(name)
    if not d:
        continue
    for row in d["b"]:
        w, t, ai, y, gi, tg, q, sl, ci, aw, pg, rw, o = row[:13]
        im, an = (row[13], row[14]) if len(row) > 14 else ("", "")
        a = d["a"][ai]
        tags = [d["tg"][j] for j in tg]
        e = tagsx["m"].get(str(w))
        if e and len(e) > 2:
            tags += [tagsx["tg"][j] for j in e[2] if j < len(tagsx["tg"])]
        books.append({"t": t, "a": a[0], "y": y or None, "g": d["g"][gi], "c": d["c"][ci] if ci >= 0 else (d["c"][a[1]] if a[1] >= 0 else ""),
                      "tags": tags, "q": q, "ann": an or "", "acc": [d["aw"][j] for j in aw] if name == "books.json" else [], "cat": False, "sl": sl, "img": im or ""})
TM = re.search(r'const TROPE_M=\(\(\)=>\{const m=\{\};"([^"]+)"', app)
TROPES = {}
for r in (TM.group(1).split(";") if TM else []):
    if r.count("|") == 2:
        t_, a_, l_ = r.split("|")
        TROPES[re.sub(r"[^0-9a-zа-я]+", "", t_.lower().replace("ё", "е")) + "|" + a_.lower().replace("ё", "е")] = ["троп:" + x for x in l_.split()]
for b in books:
    k = re.sub(r"[^0-9a-zа-я]+", "", b["t"].lower().replace("ё", "е")) + "|" + b["a"].split(" ")[-1].lower().replace("ё", "е")
    if k in TROPES:
        b["tags"] = b["tags"] + [x for x in TROPES[k] if x not in b["tags"]]
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
     lambda b: (has(b, "уют", "тёплое") or (has(b, "светлое", "сказка") and not has(b, "исторический роман", "приключения", "динамичное")))
     and not has(b, "мрачное", "жутковатое", "хоррор", "война", "грустное")),
    ("strashnye", "Страшные книги", "Хоррор, мистика и готика — книги, после которых не выключишь свет.", lambda b: has(b, "жутковатое", "хоррор", "мистика", "готика")),
    ("zastavlyayut-zadumatsya", "Книги, которые заставляют задуматься", "Романы о главном — после них долго думаешь.",
     lambda b: has(b, "интеллектуальное", "философский роман", "психологический роман", "антиутопия")),
    ("trogatelnye", "Трогательные книги", "Истории, которые трогают до слёз.", lambda b: has(b, "грустное", "взросление")),
    ("antiutopii", "Антиутопии: лучшие книги", "Миры, в которые не хочется попасть, — и от которых не оторваться.", lambda b: has(b, "антиутопия")),
    ("novinki", f"Книжные новинки {YNOW - 1}–{YNOW}", "Новые книги последних двух лет — каталог обновляется каждый месяц.", lambda b: y(b) >= YNOW - 1 and not notnovel(b) and not re.search(r"словар|энциклопед|справочник|грамматик|учебник|атлас", b["t"], re.I)),
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
# мотивы для нарисованных обложек — те же линии, что в приложении
MOTIF = {"fantasy": '<path d="M50 20 L54 44 L78 48 L54 52 L50 76 L46 52 L22 48 L46 44Z"/><path d="M80 18l2 6 6 2-6 2-2 6-2-6-6-2 6-2Z"/>',
         "scifi": '<circle cx="50" cy="50" r="18"/><ellipse cx="50" cy="50" rx="36" ry="11" transform="rotate(-18 50 50)"/>',
         "detective": '<circle cx="44" cy="44" r="18"/><path d="M57 57l20 20"/>',
         "classic": '<path d="M26 78h48M30 72h40M34 72V40M50 72V40M66 72V40M28 40h44L50 24Z"/>',
         "modern": '<path d="M24 74V46M40 74V30M56 74V52M72 74V38"/>',
         "kids": '<path d="M64 26a24 24 0 1 0 10 34 20 20 0 0 1-10-34Z"/>',
         "nonfic": '<path d="M24 30c9-6 18-6 26 0 8-6 17-6 26 0v44c-9-6-18-6-26 0-8-6-17-6-26 0Z"/><path d="M50 30v44"/>'}
try:
    COVERS = json.load(open(os.path.join(ROOT, "books", "covers.json"), encoding="utf-8"))
except FileNotFoundError:
    COVERS = {}
nk = lambda s: re.sub(r"[^0-9a-zа-я]+", "", str(s or "").lower().replace("ё", "е"))
img_of = lambda b: COVERS.get(nk(b["t"]) + "|" + nk(str(b["a"] or "").split(" ")[-1]), "") or b.get("img", "")


def hsh(t):
    h = 0
    for ch in t:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return h


def cv(b, lazy=True):
    pal = PAL.get(b["g"], PAL["modern"])
    c = pal[hsh(b["t"]) % len(pal)]
    light = int(c[1:3], 16) + int(c[3:5], 16) + int(c[5:7], 16) > 450
    f = "#3A2A1C" if light else ("#F1E2C2" if hsh(b["a"]) % 2 else "#E2B66B")
    u = img_of(b)
    im = (f'<img src="{esc(u)}" alt="Обложка книги «{esc(b["t"])}»" {"loading=lazy " if lazy else ""}decoding="async" referrerpolicy="no-referrer" onerror="this.remove()">' if u else "")
    m = f'<svg class="m" viewBox="0 0 100 100">{MOTIF.get(b["g"], MOTIF["modern"])}</svg>'
    return f'<div class="cv" style="--c:{c};--f:{f}">{im}<b>{esc(b["t"])}</b>{m}<i>{esc(b["a"])}</i></div>'


ICON = {"cam": '<path d="M8.2 6.5l1.1-1.7c.3-.5.8-.8 1.4-.8h2.6c.6 0 1.1.3 1.4.8l1.1 1.7H18a3 3 0 0 1 3 3V17a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3V9.5a3 3 0 0 1 3-3z"/><circle cx="12" cy="13" r="3.6"/>',
        "feed": '<path d="M8 3.5h8M6 6.5h12"/><rect x="4" y="9.5" width="16" height="11" rx="3"/>',
        "shur": '<path d="M5 20c-1-9 2-15 7-15s8 6 7 15l-2-1.5-2.5 1.5-2.5-1.5L9.5 20 7 18.5z"/><circle cx="10" cy="11" r=".8"/><circle cx="14" cy="11" r=".8"/>',
        "fr": '<circle cx="9" cy="8.5" r="3.2"/><path d="M3.5 19c.6-3.2 2.8-5 5.5-5s4.9 1.8 5.5 5"/><circle cx="16.5" cy="9.5" r="2.6"/><path d="M15.5 14.2c2.6-.3 4.6 1.3 5 4.3"/>',
        "sum": '<path d="M3.5 17.5l5.5-5.5 4 3.5 7.5-8"/><path d="M15.5 7.5h5v5"/>',
        "imp": '<path d="M12 4v10M8 10l4 4 4-4"/><path d="M4.5 14v3a3 3 0 0 0 3 3h9a3 3 0 0 0 3-3v-3"/>',
        "tg": '<path d="M21 4.5L3 11.5l6 2 2 6 3.5-4 4.5 3.5z"/><path d="M9 13.5l8.5-6"/>',
        "free": '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
        "ph": '<rect x="7" y="3" width="10" height="18" rx="2.5"/><path d="M11 18h2"/>',
        "arr": '<path d="M5 12h14M13 6l6 6-6 6"/>'}
ic = lambda k: f'<svg viewBox="0 0 24 24">{ICON[k]}</svg>'

SN = """<!-- Cloudflare Web Analytics --><script defer type='module' src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{"token": "572d5eebd0c442bda32887c9f80bb139"}'></script><!-- End Cloudflare Web Analytics -->"""
HEAD = f"""<link rel="icon" href="/icons/icon-192.png?v=4"><link rel="apple-touch-icon" href="/icons/icon-180.png?v=4"><meta name="theme-color" content="#05060A">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500;600&display=swap">
<link rel="stylesheet" href="/site.css?v={VER}">"""
NAV = [("/c/romantezi.html", "Ромэнтези"), ("/c/dark-roman.html", "Дарк роман"), ("/c/novinki.html", "Новинки"), ("/p/", "Похожие книги"), ("/c/", "Все подборки")]
APP = "/app.html?app=1"


def hdr(active=""):
    return ('<header class="hd"><div class="bar gl"><a class="logo" href="/"><img src="/icons/icon-512.png?v=4" alt="">Нора</a><nav class="nav">'
            + "".join(f'<a href="{u}"{" class=on" if u == active else ""}>{t}</a>' for u, t in NAV)
            + f'</nav><a class="btn sm open" id="openNora" href="{APP}">Открыть Нору</a></div></header>')


MINE = """<script>try{if(localStorage.getItem("zal.onb"))document.querySelectorAll("#openNora").forEach(function(a){a.textContent="Моя Нора"})}catch(e){}</script>"""


def footer(colls):
    return (f'<footer class="ft"><div class="wrap"><div class="in gl"><div><div class="logo"><img src="/icons/icon-192.png?v=4" alt="">Нора</div><p>Все твои книги в одном месте — бумажные, '
            f'из Литрес, Яндекс Книг и LiveLib. Шуршуня подскажет, что читать дальше.</p></div><div><h4>Подборки</h4>'
            + "".join(f'<a href="/c/{p}.html">{esc(t.split(":")[0])}</a>' for p, t in colls[:7])
            + f'</div><div><h4>Нора</h4><a href="{APP}">Открыть в браузере</a><a href="{BOT}">Открыть в Telegram</a><a href="/c/">Все подборки</a>'
            f'<a href="/privacy.html">Конфиденциальность</a></div><div class="copy"><span>© {YNOW} Нора</span><span>Сделано с любовью к книгам</span></div></div></div></footer>')


FOOT = ""


def page(path, title, desc, body, full_title=None, active="", img=None):
    canon = f"{SITE}/{path}".replace("/index.html", "/")
    doc = f"""<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{esc(full_title or title + " — Нора")}</title><meta name="description" content="{esc(desc[:200])}"><link rel="canonical" href="{canon}">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc[:200])}"><meta property="og:url" content="{canon}">
<meta property="og:image" content="{esc(img or SITE + '/icons/icon-512.png?v=4')}"><meta property="og:type" content="website"><meta property="og:site_name" content="Нора">{HEAD}</head><body>
{hdr(active)}<main>{body}</main>{FOOT}{MINE}{SN}</body></html>"""
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, "w", encoding="utf-8").write(doc)
    return canon


rank = lambda b: (-(b["q"] or 0), -(b.get("sl") or 0), not b["cat"], not img_of(b))
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
    inner = (cv(b) + (f'<div class="num">№ {n}</div>' if n else "") + f'<div class="t">{esc(b["t"])}</div><div class="a">{esc(meta)}</div>'
             + (f'<p>{esc(b["ann"])}</p>' if ann and b["ann"] else ""))
    return f'<a class="bk" href="/{u}">{inner}</a>' if u else f'<div class="bk">{inner}</div>'


def rail(L):
    return '<div class="rail">' + "".join(card(b) for b in L) + "</div>"


def shelf(title, href, ds, L, all_txt="Все"):
    return (f'<section class="shelf"><div class="hd"><h2><a href="{href}">{esc(title)}</a></h2><a class="all" href="{href}">{esc(all_txt)} →</a></div>'
            + (f'<p class="ds">{esc(ds)}</p>' if ds else "") + rail(L) + "</section>")


CTA = (f'<div class="ctas"><a class="btn" href="{APP}">Собрать свою полку</a>'
       f'<a class="btn ghost" href="{BOT}">{ic("tg")}Открыть в Telegram</a></div>')
FINAL = (f'<section class="final gl"><div class="kick">Бесплатно</div><h2 style="margin-top:14px">Собери свою Нору</h2>'
         f'<p>Отметь пару любимых книг — и Шуршуня сразу подскажет, что читать дальше.</p>{CTA}</section>')
coll_data = []
for path, title, lead, pred in COLL:
    L = sorted([b for b in books if pred(b)], key=rank)[:60]
    if len(L) < 8:
        continue
    L = sorted(L, key=lambda b: (not (b["ann"] or img_of(b)), L.index(b)))  # с описанием и обложкой — вперёд
    coll_data.append((path, title, lead, L))
FOOT = footer([(p, t) for p, t, _, _ in coll_data])
# книги из подборок без обложки — их обложки найдёт tools/build_covers.py в следующий раз
want, seenw = [], set()
for _, _, _, L in coll_data:
    for b in L:
        k = nk(b["t"]) + "|" + nk(str(b["a"] or "").split(" ")[-1])
        if not b["cat"] and k not in COVERS and k not in seenw:
            seenw.add(k)
            want.append([b["t"], b["a"]])
json.dump(want[:4000], open(os.path.join(ROOT, "books", "covers_want.json"), "w", encoding="utf-8"), ensure_ascii=False)
QUICK = [p for p in ("romantezi", "dark-roman", "lyubovnye-romany", "young-adult", "zhanr-fantasy", "uyutnye", "zahvatyvayuschie", "strashnye", "smeshnye", "novinki", "zhanr-classic", "zhanr-detective")
         if any(q == p for q, _, _, _ in coll_data)]
tname = lambda p: next(t for q, t, _, _ in coll_data if q == p).split(":")[0]
chips = lambda cur: '<nav class="chips">' + "".join(f'<a href="/c/{p}.html"{" class=on" if p == cur else ""}>{esc(tname(p))}</a>' for p in QUICK) + "</nav>"
for path, title, lead, L in coll_data:
    body = (f'<div class="wrap"><div class="crumbs"><a href="/">Нора</a><span>/</span><a href="/c/">Подборки</a></div>'
            f'<div class="ph"><div><div class="kick">Подборка</div><h1>{esc(title)}</h1><p class="lead">{esc(lead)}</p></div><div class="cnt gl">{len(L)} книг</div></div>'
            f'{chips(path)}<div class="grid">{"".join(card(b, i + 1, True) for i, b in enumerate(L))}</div>{FINAL}</div>')
    urls.append(page(f"c/{path}.html", title, lead + " " + ", ".join(b["t"] for b in L[:5]) + ".", body, active=f"/c/{path}.html",
                     img=img_of(L[0]) or None))


def coll_card(p, t, L):
    st = sorted(L[:12], key=lambda b: not img_of(b))[:3]
    return (f'<a class="coll gl" href="/c/{p}.html"><div class="st">{"".join(cv(b) for b in st)}</div><h3>{esc(t.split(":")[0])}</h3>'
            f'<small>{len(L)} книг</small></a>')


urls.append(page("c/index.html", "Подборки книг", "Подборки книг по жанрам, настроениям и странам — от ромэнтези до классики.",
                 '<div class="wrap"><div class="crumbs"><a href="/">Нора</a></div><div class="ph"><div><div class="kick">Что почитать</div><h1>Подборки книг</h1>'
                 '<p class="lead">По жанрам, настроениям и странам — от ромэнтези до классики.</p></div></div><div style="display:none">'
                 + "</div>" + "".join(shelf(t.split(":")[0], f"/c/{p}.html", lead, sorted(L[:24], key=lambda b: not img_of(b))[:14], f"Все {len(L)}") for p, t, lead, L in coll_data)
                 + f"{FINAL}</div>", active="/c/"))

pool = {}
for b in cat_books:
    pool.setdefault(b["g"], []).append(b)
GEN_URL = {g: f"/c/zhanr-{g}.html" for g in GEN}
for b in cat_books:
    tg = set(b["tags"])
    sim = sorted((x for x in pool.get(b["g"], []) if x is not b), key=lambda x: (-len(tg & set(x["tags"])), -(x["q"] or 0), not img_of(x)))[:6]
    u = img_of(b)
    facts = ([f'<a href="{GEN_URL[b["g"]]}">{esc(GEN[b["g"]])}</a>'] if b["g"] in GEN_URL else []) + \
            [f"<span>{esc(x)}</span>" for x in [b["c"], str(b["y"]) if b["y"] and b["y"] > 0 else ""] + b["tags"][:4] if x]
    desc = b["ann"] or f"«{b['t']}» — {b['a']}."
    fl = [f for f in b.get("f", [])[:4] if len(f) > 1]
    body = (f'<div class="wrap"><div class="crumbs"><a href="/">Нора</a><span>/</span><a href="{GEN_URL.get(b["g"], "/c/")}">{esc(GEN.get(b["g"], "Книги"))}</a></div>'
            f'<article class="book">{f"<div class=amb style=background-image:url({esc(u)})></div>" if u else ""}<div class="cvw">{cv(b, lazy=False)}</div><div>'
            f'<h1>{esc(b["t"])}</h1><p class="by">{esc(b["a"])}</p><div class="facts">{"".join(facts)}</div>'
            + (f'<p class="ann">{esc(b["ann"])}</p>' if b["ann"] else "")
            + (f'<p class="when">{esc(b["when"])}</p>' if b.get("when") else "")
            + (f'<div class="fgrid">{"".join(f"<div class=\"fact gl\"><b>{esc(f[0])}</b><span>{esc(f[1])}</span></div>" for f in fl)}</div>' if fl else "")
            + (f'<p class="acc">Признание: {esc(", ".join(b["acc"]))}</p>' if b["acc"] else "")
            + CTA + "</div></article>"
            + (f'<section class="sec"><div class="kick">Похожие книги</div><h2>Если понравилась эта</h2><p class="sub">Шуршуня подобрала книги того же жанра с похожим настроением.</p>'
               f'<div class="row">{"".join(card(x) for x in sim)}</div></section>' if sim else "")
            + "</div>")
    urls.append(page(BOOK_URL[id(b)], f"«{b['t']}», {b['a']}: о чём книга и что почитать похожее", desc, body, img=u or None))

# ---------- «Книги, похожие на…»: страницы под поисковые запросы «что почитать после X» ----------
TROPE_RU = dict(re.findall(r'\["(\w+)","([^"]+)"\]', app[app.index("const B_TROPE="):app.index("];", app.index("const B_TROPE="))]))
GENERIC = {"любовь", "романтичное", "атмосферное", "грустное", "женская судьба", "большой город", "взросление", "психологический роман", "интеллектуальное",
           "философский роман", "приключения", "светлое", "тёплое", "мрачное", "динамичное", "напряжённое", "смешное", "медленное", "история", "семья", "дружба",
           "социальный роман", "классика", "магия", "мистика", "жутковатое", "уют", "детектив", "триллер", "психология", "самиздат"}
lab = lambda t: TROPE_RU.get(t[5:], t[5:]).lower() if t.startswith("троп:") else t
LOVEY = lambda b: has(b, "любовное фэнтези", "любовный роман", "ромэнтези") or (love(b) and any(t.startswith("троп:") for t in b["tags"]))
SPOOL = [b for b in books if (b["q"] or 0) >= 2 and len(b["tags"]) >= 2 and (b["ann"] or img_of(b)) and not notnovel(b)]
print("книг для «похожих»:", len(SPOOL))


def simscore(a, x):
    if x is a or nk(x["t"]) == nk(a["t"]) or SER(x) == SER(a):
        return None, []
    ta, tx = set(a["tags"]), set(x["tags"])
    sh = ta & tx
    tro = [t for t in sh if t.startswith("троп:")]
    spec = [t for t in sh if not t.startswith("троп:") and t not in GENERIC]
    gen = len(sh) - len(tro) - len(spec)
    same_g = a["g"] == x["g"]
    if not same_g and not (LOVEY(a) and LOVEY(x)):
        return None, []
    if len(tro) * 2 + len(spec) < 2:
        return None, []
    sc = 3 * len(tro) + 1.6 * len(spec) + 0.4 * gen + (1.5 if same_g else 0) + (1.2 if LOVEY(a) == LOVEY(x) else -2)
    if a["y"] and x["y"]:
        sc -= min(abs(a["y"] - x["y"]), 120) / 60
    sc += min(x["q"] or 0, 4) * 0.5 + (0.6 if img_of(x) else 0) + (0.4 if x["ann"] else 0)
    return sc, tro + spec


SER = lambda b: nk(b["a"]) + "|" + nk(re.split(r"[.:—–(]|\s\d|\sкнига|\sтом", b["t"].lower())[0])
seeds = [b for b in books if ((b["q"] or 0) >= 3 or ((b["q"] or 0) >= 2 and (LOVEY(b) or b["g"] == "fantasy"))) and (b["y"] or 0) >= 1980 and not notnovel(b)
         and len(b["tags"]) >= 3 and (img_of(b) or b["ann"])]
_ss = set()
seeds = [b for b in sorted(seeds, key=lambda b: (not b["cat"], -(b["q"] or 0))) if not (SER(b) in _ss or _ss.add(SER(b)))]
seeds = sorted(seeds, key=lambda b: (not LOVEY(b), not (b["g"] in ("fantasy", "kids") and (b["y"] or 0) >= 2000), -(b["q"] or 0), -(b.get("sl") or 0)))[:int(os.environ.get("SIM_N", "700"))]
SIM_URL, sim_pages, usedp = {}, [], set()
for a_ in seeds:
    cand = []
    for x in SPOOL:
        sc, why = simscore(a_, x)
        if sc is not None:
            cand.append((sc, x, why))
    cand.sort(key=lambda z: -z[0])
    out, au, sers = [], {}, set()
    for sc, x, why in cand:
        if SER(x) in sers:
            continue
        k = nk(x["a"])
        if k == nk(a_["a"]) and au.get(k, 0) >= 1 or au.get(k, 0) >= 2:
            continue
        au[k] = au.get(k, 0) + 1
        sers.add(SER(x))
        out.append((x, why))
        if len(out) >= 12:
            break
    if len(out) < 6:
        continue
    sl_ = slug("pohozhie-na-" + a_["t"] + "-" + a_["a"].split(" ")[-1])
    while sl_ in usedp:
        sl_ += "-2"
    usedp.add(sl_)
    SIM_URL[id(a_)] = f"p/{sl_}.html"
    sim_pages.append((a_, out))


def sim_card(x, why, n):
    u = BOOK_URL.get(id(x))
    meta = ", ".join(v for v in [x["a"], str(x["y"]) if x["y"] and x["y"] > 0 else ""] if v)
    w = ", ".join(list(dict.fromkeys(lab(t) for t in why if t != "ромэнтези"))[:3])
    ann = x["ann"] if len(x["ann"]) <= 240 else x["ann"][:240].rsplit(" ", 1)[0] + "…"
    inner = (cv(x) + f'<div class="num">№ {n}</div><div class="t">{esc(x["t"])}</div><div class="a">{esc(meta)}</div>'
             + (f'<p class="why">Тоже: {esc(w)}</p>' if w else "") + (f'<p>{esc(ann)}</p>' if ann else ""))
    return f'<a class="bk" href="/{u}">{inner}</a>' if u else f'<div class="bk">{inner}</div>'


for a_, out in sim_pages:
    au_ = a_["a"]
    tops = ", ".join(f"«{x['t']}»" for x, _ in out[:4])
    lead = (f"Если понравилась «{a_['t']}» ({au_}), вот {len(out)} книг с похожим настроением и сюжетными ходами — Шуршуня подобрала их по жанру, "
            f"тропам и тому, что ценят читатели. Самые близкие: {tops}.")
    back = BOOK_URL.get(id(a_))
    body = (f'<div class="wrap"><div class="crumbs"><a href="/">Нора</a><span>/</span><a href="/p/">Что почитать после</a></div>'
            f'<div class="ph"><div><div class="kick">Что почитать после</div><h1>Книги, похожие на «{esc(a_["t"])}»</h1><p class="lead">{esc(lead)}</p>'
            + (f'<p class="lead" style="margin-top:8px"><a href="/{back}">О книге «{esc(a_["t"])}» →</a></p>' if back else "")
            + f'</div><div class="cnt gl">{len(out)} книг</div></div>'
            f'<div class="grid">{"".join(sim_card(x, w, i + 1) for i, (x, w) in enumerate(out))}</div>{FINAL}</div>')
    urls.append(page(SIM_URL[id(a_)], f"Книги, похожие на «{a_['t']}»",
                     f"Что почитать после «{a_['t']}» ({au_}): {', '.join(x['t'] for x, _ in out[:6])} и ещё {max(0, len(out) - 6)} похожих книг.", body,
                     full_title=f"Книги, похожие на «{a_['t']}» — что почитать после | Нора", img=img_of(a_) or None))

# ссылка «Ещё похожие» на странице книги
for a_, _ in sim_pages:
    bu = BOOK_URL.get(id(a_))
    if bu:
        fp = os.path.join(ROOT, bu)
        h = open(fp, encoding="utf-8").read()
        h = h.replace('<p class="sub">Шуршуня подобрала книги того же жанра с похожим настроением.</p>',
                      f'<p class="sub">Шуршуня подобрала книги того же жанра с похожим настроением. <a href="/{SIM_URL[id(a_)]}">Все похожие книги →</a></p>', 1)
        open(fp, "w", encoding="utf-8").write(h)
# оглавление «Что почитать после»
groups = {}
for a_, out in sim_pages:
    groups.setdefault("Ромэнтези и любовные романы" if LOVEY(a_) else GEN.get(a_["g"], "Другое"), []).append(a_)
SIMS = {id(a_): out for a_, out in sim_pages}
TORD = {k: i for i, k in enumerate(TROPES)}
onepa = lambda L: [b for i, b in enumerate(L) if nk(b["a"]) not in {nk(x["a"]) for x in L[:i]}]  # на оглавлении — одна книга автора  # популярные современные книги из ручной разметки — первыми


def sim_ds(a_, out):
    from collections import Counter
    c = Counter(lab(t) for _, w in out for t in w if t != "ромэнтези")
    top = [k for k, _ in c.most_common(3)]
    return (f"Книги того же настроения, что и «{a_['t']}» ({a_['a']})" + (f": {', '.join(top)}." if top else "."))


toc = "".join(f'<div class="kick" style="margin-top:56px">{esc(g)}</div>'
              + "".join(shelf(f"Если понравилась «{b['t']}»", "/" + SIM_URL[id(b)], sim_ds(b, SIMS[id(b)]), [x for x, _ in SIMS[id(b)]][:12], "Все похожие") for b in L)
              for g, L in sorted(groups.items(), key=lambda z: -len(z[1])) for L in [onepa(sorted(L, key=lambda b: (TORD.get(nk(b["t"]) + "|" + b["a"].split(" ")[-1].lower().replace("ё", "е"), 999), not b["cat"], -(b["q"] or 0), -(b.get("sl") or 0))))])
urls.append(page("p/index.html", "Что почитать после любимой книги", "Книги, похожие на популярные романы: ромэнтези, любовные романы, фэнтези, детективы и современная проза.",
                 f'<div class="wrap"><div class="crumbs"><a href="/">Нора</a></div><div class="ph"><div><div class="kick">Похожие книги</div><h1>Что почитать после любимой книги</h1>'
                 f'<p class="lead">Выбери книгу, которая понравилась, — Шуршуня покажет похожие по настроению и сюжетным ходам.</p></div></div>{toc}{FINAL}</div>', active="/p/"))
print("страниц «похожие на»:", len(sim_pages))

# ---------- политика конфиденциальности ----------
POLICY = [
    ("Что мы храним", "<ul><li>Почту и пароль — чтобы ты могла войти с любого устройства. Пароль зашифрован, его не видим даже мы.</li><li>Если ты включишь новости о книгах в Telegram — ещё твой Telegram ID, названия из избранного, любимых авторов и список друзей в Норе, чтобы бот мог прислать новости. Выключишь — удалим.</li>"
     "<li>Имя и твои полки: книги, оценки, отзывы и заметки.</li></ul>"),
    ("Что мы не делаем", "<ul><li>Не продаём и не передаём данные рекламодателям.</li><li>Не показываем полки посторонним — только друзьям, которых ты добавишь.</li>"
     "<li>Не отправляем никуда фото шкафа: книги распознаются прямо на телефоне.</li></ul>"),
    ("Где это хранится", "В облаке Google Firebase — его серверы за пределами России. Создавая аккаунт, ты соглашаешься на такое хранение. "
     "Для статистики посещений сайта используем Cloudflare Web Analytics — без cookies и без привязки к тебе."),
    ("Как удалить данные", "Напиши в бот Норы — удалим аккаунт и все полки в течение 30 дней."),
    ("Связаться с нами", f'Вопросы и просьбы — {SUPPORT}.'),
]
pol = ('<div class="wrap"><div class="crumbs"><a href="/">Нора</a></div><div class="ph"><div><div class="kick">Документы</div><h1>Политика конфиденциальности</h1>'
       f'<p class="lead">Коротко: что Нора знает о тебе и как это удалить. Обновлено {time.strftime("%d.%m.%Y")}.</p></div></div><div class="legal">'
       + "".join(f"<section class='gl'><h2>{h}</h2>{t if t.startswith('<') else '<p>' + t + '</p>'}</section>" for h, t in POLICY) + "</div></div>")
urls.append(page("privacy.html", "Политика конфиденциальности", "Какие данные хранит «Нора», зачем и как их удалить.", pol))

# ---------- главная ----------
get = lambda p: next((L for q, _, _, L in coll_data if q == p), [])
hero = [b for b in get("romantezi") if img_of(b)][:2] or get("romantezi")[:2] or cat_books[:2]
show = [p for p in ("romantezi", "dark-roman", "lyubovnye-romany", "young-adult", "zhanr-fantasy", "zahvatyvayuschie", "uyutnye", "zhanr-detective") if get(p)]
TG_REDIRECT = """<script>(function(){try{var s=location.search,h=location.hash,sa=(window.matchMedia&&matchMedia("(display-mode: standalone)").matches)||navigator.standalone;
if(/tgWebApp/.test(h+s)||sa||/[?&]app(=|&|$)/.test(s)||/^#.*=/.test(h)){location.replace("app.html?v="+Math.floor(Date.now()/6e5)+(s?"&"+s.slice(1):"")+h)}}catch(e){}})()</script>"""
FEATS = [("cam", "Шкаф — за одно фото", "Сфотографируй полку, и Нора узнает книги по корешкам. Фото не уходят с телефона."),
         ("imp", "Всё в одном месте", "Перенеси прочитанное из Литрес, Яндекс Книг и LiveLib — и бумажные книги туда же."),
         ("shur", "Шуршуня советует", "Подбирает следующую книгу по твоим оценкам, настроению, жанрам и тропам."),
         ("feed", "Лента находок", "Свайпай книги, как в знакомствах: «читала», «хочу», «не моё» — и вкус уточняется сам."),
         ("fr", "Полки друзей", "Смотри, что читают подруги, и делись отзывами — для себя или для них."),
         ("sum", "Читательский паспорт", "Страны, века, любимые авторы и итоги года — красиво и без таблиц.")]
SHOTS = [("home", "Твоя Нора", "Полки и совет Шуршуни"), ("feed", "Лента", "Свайпай находки"), ("search", "Поиск и фильтры", "Жанры, настроения, тропы"), ("sum", "Статистика", "Паспорт читателя")]
FAQ = [("Это бесплатно?", "Да. Все полки, советы, фото шкафа и перенос книг — бесплатно."),
       ("Чем Нора отличается от LiveLib и Литрес?", "Нора не магазин и не соцсеть с рейтингами. Это твоя личная полка, куда собираются все книги — из любых приложений и бумажные, — и советник, "
        "который знает именно твой вкус. Читать можно где удобно: Нора подскажет, где найти книгу."),
       ("Нужен ли Telegram?", "Нет. Нора работает в браузере на телефоне и компьютере, а её можно поставить на экран «Домой» как обычное приложение. В Telegram она тоже есть — полки одни и те же."),
       ("Как перенести книги из Литрес, Яндекс Книг или LiveLib?", "В Норе нажми «Поставить книгу на полку» → «Перенести книги»: можно вставить список или выгрузку, и Нора разложит книги сама."),
       ("Мои данные кто-то увидит?", "Только друзья, которых ты добавишь, и только то, что ты разрешишь. Подробнее — в политике конфиденциальности.")]
home = f"""<div class="wrap"><section class="hero"><div><div class="kick">Книжная полка с советником</div><h1>Все твои книги<br>в одной <em>Норе</em></h1>
<p class="lead">Бумажные, из Литрес, Яндекс Книг и LiveLib — на одной полке. Сфотографируй шкаф, и полка соберётся сама. А Шуршуня подскажет, что читать дальше.</p>{CTA}
</div>
<div class="stage"><div class="glow"></div>{"".join(cv(b, lazy=False) for b in hero)}<div class="phone"><img src="/img/app-home.webp" alt="Главный экран Норы: полки и совет Шуршуни" width="520" height="1125"></div></div></section>
<section class="sec" id="kak"><div class="kick">Что умеет Нора</div><h2>Библиотека, которая<br>знает твой вкус</h2><p class="sub">Без таблиц и ручного ввода — скучную часть Нора делает сама.</p>
<div class="feats">{"".join(f'<div class="feat gl"><div class="ic">{ic(k)}</div><h3>{h}</h3><p>{p}</p></div>' for k, h, p in FEATS)}</div></section>
<section class="sec"><div class="kick">Как это выглядит</div><h2>Нора изнутри</h2><p class="sub">Тёмная, спокойная и красивая — чтобы хотелось возвращаться к своим книгам.</p>
<div class="shots">{"".join(f'<div class="shot"><div class="phone"><img src="/img/app-{k}.webp" alt="{esc(h)}" loading="lazy" width="520" height="1125"></div><p><b>{h}</b>{p}</p></div>' for k, h, p in SHOTS)}</div></section>
<section class="sec"><div class="shead"><div><div class="kick">Подборки</div><h2>Что почитать</h2><p class="sub">Ромэнтези, дарк роман, фэнтези и книги на любое настроение.</p></div><a class="more" href="/c/">Все подборки {ic("arr").replace("<svg ", "<svg width=18 height=18 fill=none stroke=currentColor stroke-width=1.8 ")}</a></div>
<div class="colls">{"".join(coll_card(p, next(t for q, t, _, _ in coll_data if q == p), get(p)) for p in show)}</div></section>
<section class="sec"><div class="shead"><div><div class="kick">Новинки</div><h2>Новые книги</h2><p class="sub">Каталог обновляется каждый месяц.</p></div><a class="more" href="/c/novinki.html">Все новинки {ic("arr").replace("<svg ", "<svg width=18 height=18 fill=none stroke=currentColor stroke-width=1.8 ")}</a></div>
<div class="row">{"".join(card(b) for b in get("novinki")[:6])}</div></section>
<section class="sec"><div class="shur"><div class="ava">{ic("shur")}</div><div><div class="kick">Знакомься</div><p class="q">«Знаю, что ты прочитала прошлым летом. И что тебе понравится этой осенью».</p>
<p>Шуршуня — хранительница Норы. Помнит каждую твою книгу и советует новые без занудства.</p></div><a class="btn" href="{APP}">Спросить Шуршуню</a></div></section>
<section class="sec"><div class="kick">Вопросы</div><h2>Коротко о главном</h2><div class="faq" style="margin-top:30px">{"".join(f'<details class="gl"><summary>{q}</summary><p>{a}</p></details>' for q, a in FAQ)}</div></section>
{FINAL}</div>"""
home_path = page("index.html", "Нора — твоя книжная библиотека", "Нора — личная книжная полка в Telegram и браузере: собери все прочитанные книги (бумажные, из Литрес, Яндекс Книг и LiveLib), "
                 "сфотографируй шкаф, получай советы, что читать дальше, — ромэнтези, фэнтези, детективы, классика.", home,
                 full_title="Нора — твоя книжная библиотека: все книги в одном месте и советы, что почитать")
idx = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
idx = idx.replace('<meta charset="utf-8">', '<meta charset="utf-8"><meta name="google-site-verification" content="s2CdXU7z22CJQ7fqwqJNwf2nyq4VN3Jk2UEHofqjoXc"><meta name="yandex-verification" content="6a85060ff8390b92">'
                  '<link rel="manifest" href="/manifest.webmanifest"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="Моя Нора">' + TG_REDIRECT, 1)
open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(idx)
urls.insert(0, home_path)

now = time.strftime("%Y-%m-%d")
open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8").write(
    '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    + "".join(f"<url><loc>{u}</loc><lastmod>{now}</lastmod></url>\n" for u in urls) + "</urlset>\n")
open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8").write(f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n")
print("страниц:", len(urls), "подборок:", len(coll_data))
