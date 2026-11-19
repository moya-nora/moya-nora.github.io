#!/usr/bin/env python3
"""Страницы для поисковиков: «Нора» в Яндексе и Google.

Приложение — одна страница на JavaScript, и поисковики видят в нём мало текста. Этот сборщик делает обычные
HTML-страницы, которые поисковик читает целиком:
  /k/<книга>.html — книга из ручного каталога: описание, жанр, страна и «похожие книги»;
  /c/<подборка>.html — подборки по жанрам, настроениям, странам и новинки;
  sitemap.xml и robots.txt.
Главная index.html тоже собирается здесь. Каждая страница ведёт в приложение. Запуск: python3 tools/build_seo.py (GitHub Actions — после сборки новинок)."""
import urllib.parse, html, json, os, re, time

ROOT = os.path.join(os.path.dirname(__file__), "..")
SITE = "https://nora-books.ru"
BOT = "https://t.me/Wonderbookworld_bot"
MAIL = "nora.books@mail.ru"
SUPPORT = f'<a href="{BOT}">пиши в Telegram-бот @Wonderbookworld_bot</a> или на почту <a href="mailto:{MAIL}">{MAIL}</a>'
YNOW = time.gmtime().tm_year
esc = html.escape

TR = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя", ["a", "b", "v", "g", "d", "e", "e", "zh", "z", "i", "y", "k", "l", "m", "n", "o", "p", "r", "s", "t", "u", "f",
                                                  "h", "c", "ch", "sh", "sch", "", "y", "", "e", "yu", "ya"]))


def slug(s):
    s = "".join(TR.get(ch, ch) for ch in s.lower())
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:70] or "kniga"


GEN = {"classic": "Классика", "modern": "Современная проза", "detective": "Детективы", "fantasy": "Фэнтези", "scifi": "Фантастика",
       "kids": "Детские и подростковые книги", "nonfic": "Нон-фикшн"}

GEN1 = {"classic": "Классика", "modern": "Современная проза", "detective": "Детектив", "fantasy": "Фэнтези", "scifi": "Фантастика", "kids": "Детская литература", "nonfic": "Нон-фикшн"}


def lit_id(b):
    if _lk(b) in LCOV:
        return LCOV[_lk(b)]
    m_ = re.search(r"litres\.ru/pub/c/cover(?:_\d+)?/(\d+)\.jpg", b.get("img") or "")
    return int(m_.group(1)) if m_ else None


def lrv(b):
    """отзывы ЛитРес и оценки LiveLib из books/rv (собирает tools/build_reviews.py)"""
    i_ = lit_id(b)
    fp_ = os.path.join(ROOT, "books", "rv", f"{i_}.json") if i_ else ""
    try:
        return json.load(open(fp_, encoding="utf-8")) if fp_ and os.path.exists(fp_) else None
    except Exception:  # noqa: BLE001
        return None


def plur(n, a, b_, c):
    n = abs(n) % 100; m = n % 10
    return c if 10 < n < 20 else b_ if 1 < m < 5 else a if m == 1 else c


def gname(b):
    for t_, n_ in (("ромэнтези", "Ромэнтези"), ("любовное фэнтези", "Любовное фэнтези"), ("хоррор", "Ужасы"), ("young adult", "Young adult"),
                   ("антиутопия", "Антиутопия"), ("любовный роман", "Любовный роман"), ("триллер", "Триллер")):
        if t_ in b["tags"]:
            return n_
    return GEN1.get(b["g"], "")


# ---------- данные: ручной каталог (с описаниями) + большой каталог + новинки ----------
app = open(os.path.join(ROOT, "app.html"), encoding="utf-8").read()
i = app.index("const CAT=") + len("const CAT=")
try:
    CAT, _ = json.JSONDecoder().raw_decode(app[i:])
except ValueError:  # каталог вынесен из app.html в books/cat.json
    CAT = json.load(open(os.path.join(ROOT, "books", "cat.json"), encoding="utf-8"))
books = []
for b in CAT:
    books.append({"t": b["t"], "a": b.get("a", ""), "y": b.get("y"), "g": b.get("g", "modern"), "c": b.get("c", ""), "tags": b.get("tags", []),
                  "q": b.get("q", 1) + 1, "ann": b.get("ann", ""), "acc": b.get("acclaim", []), "cat": True,
                  "pg": {"short": 220, "mid": 380, "long": 650}.get(b.get("len"), 0),
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
                      "tags": tags, "q": q, "ann": an or "", "acc": [d["aw"][j] for j in aw] if name == "books.json" else [], "cat": False, "sl": sl, "img": im or "", "pg": pg or 0})
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
seen, uniq = {}, []
for b in books:  # ручной каталог первым — у него есть описания
    k = re.sub(r"[^0-9a-zа-я]+", "", b["t"].lower().replace("ё", "е")) + "|" + b["a"].split(" ")[-1].lower()
    if not re.search(r"[а-яё]", b["t"], re.I):
        continue
    if k in seen:  # та же книга из другого каталога: забираем у копии то, чего не хватает (описание, обложку, год)
        kb = seen[k]
        for f_ in ("ann", "img"):
            if not kb.get(f_) and b.get(f_):
                kb[f_] = b[f_]
        if not kb.get("y") and b.get("y"):
            kb["y"] = b["y"]
        continue
    seen[k] = b
    uniq.append(b)
books = uniq
# описания, найденные отдельно (tools/fill_ann.py); книги, для которых описание искали и не нашли, на сайт не попадают
_ak = lambda b: re.sub(r"[^0-9a-zа-я]+", "", str(b["t"]).lower().replace("ё", "е")) + "|" + re.sub(r"[^0-9a-zа-я]+", "", str(b["a"] or "").split(" ")[-1].lower().replace("ё", "е"))
try:
    ANNX = json.load(open(os.path.join(ROOT, "books", "ann_extra.json"), encoding="utf-8"))
except Exception:  # noqa: BLE001
    ANNX = {}
for b in books:
    if not b["ann"] and ANNX.get(_ak(b)):
        b["ann"] = ANNX[_ak(b)]
_n0 = len(books)
books = [b for b in books if b["ann"] or ANNX.get(_ak(b)) != ""]
import sys as _sys; _sys.path.insert(0, os.path.dirname(__file__)); from ban import is_ban  # нет в продаже в России - страниц не делаем
books = [b for b in books if not is_ban(b["t"], b["a"])]
print("описаний добавлено:", sum(1 for v in ANNX.values() if v), "книг убрано (описание не нашлось):", _n0 - len(books))
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
    ("na-odin-vecher", "Книги на один вечер", "Короткие книги, которые проглатываешь за вечер.",
     lambda b: not notnovel(b) and b["g"] != "kids" and 0 < (b.get("pg") or 0) <= 260 and not has(b, "мрачное", "война", "поэзия", "стихи") and not re.search(r"стихотворен|поэм|^камень$", b["t"].lower())),
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
AIOK = set(json.load(open(os.path.join(ROOT, "books", "ai_ok.json"), encoding="utf-8"))) if os.path.exists(os.path.join(ROOT, "books", "ai_ok.json")) else set()
try:
    AIC = {k: v for k, v in json.load(open(os.path.join(ROOT, "books", "ai_covers.json"), encoding="utf-8"))["m"].items() if v and os.path.exists(os.path.join(ROOT, "img", "ai", v)) and (v in AIOK or v.endswith("v.webp"))}
except (FileNotFoundError, KeyError):
    AIC = {}
try:
    LCOV = {k: v for k, v in json.load(open(os.path.join(ROOT, "books", "lcovers.json"), encoding="utf-8")).items() if v and k[0] != "_"}
except FileNotFoundError:
    LCOV = {}
_lk = lambda b: nk(b["t"]) + "|" + nk(str(b["a"] or "").split(" ")[-1])
img_of = lambda b: (f"https://cv0.litres.ru/pub/c/cover_415/{LCOV[_lk(b)]}.jpg" if _lk(b) in LCOV else "") \
    or COVERS.get(_lk(b), "") or re.sub(r"^https://www\.litres\.ru/pub/c/cover/(\d+)\.jpg$", r"https://cv0.litres.ru/pub/c/cover_415/\1.jpg", b.get("img") or "") \
    or (("/img/ai/" + AIC[nk(b["t"]) + "|" + nk(b["a"] or "")]) if nk(b["t"]) + "|" + nk(b["a"] or "") in AIC else "")


def RATE(b):
    L_ = lrv(b)
    vv = (L_ and (L_.get("v", 0) + L_.get("lv", 0))) or 0
    if not vv:
        return f'<div class="frate" id="frate" data-t="{esc(b["t"])}" data-a="{esc(b["a"].split(" ")[-1])}"></div>'
    avg = (L_.get("r", 0) * L_.get("v", 0) + L_.get("lr", 0) * L_.get("lv", 0)) / vv
    n_ = L_.get("n", 0)
    return (f'<div class="frate on"><a href="#otzyvy">★ {avg:.1f} · {vv:,} {plur(vv, "оценка", "оценки", "оценок")}</a>'.replace(",", " ").replace(".", ",", 1)
            + (f'<a href="#otzyvy">{n_} {plur(n_, "отзыв", "отзыва", "отзывов")}</a>' if n_ else "") + "</div>")


def _uniq(L):
    """один отзыв от одного читателя (ЛитРес отдаёт по несколько от одного автора)"""
    seen, out = set(), []
    for r in L:
        if r[0] in seen:
            continue
        seen.add(r[0]); out.append(r)
    return out


def _exc(t, n=300):
    """короткая выдержка из отзыва: чужой текст целиком не перепечатываем"""
    t = " ".join(str(t or "").split())
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0].rstrip(" ,.;:-") + "…"


_more = '<button class="rv-more" onclick="this.previousElementSibling.classList.add(\'open\');this.remove()">читать далее</button>'


def RVS(b):
    L_ = lrv(b)
    if not L_ or not L_.get("L"):
        return ""
    it = "".join(f'<div class="rv gl"><div class="rv-h"><b>{esc(r[0])}</b>{f"<span>★ {r[2]}</span>" if r[2] else ""}<small>{esc(r[1])}</small></div><p>{esc(r[3])}</p>{_more if len(r[3]) > 330 else ""}</div>' for r in _uniq(L_["L"])[:6])
    return f'<section class="rvs" id="otzyvy"><h2>Отзывы читателей</h2>{it}<p class="rv-src">Отзывы читателей ЛитРес. <a href="https://www.litres.ru/pages/biblio_book/?art={lit_id(b)}" rel="nofollow noopener" target="_blank">Все отзывы на ЛитРес</a></p><a class="btn ghost" href="{BOT}?startapp=site">Написать свой отзыв в Норе</a></section>'


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
        "arr": '<path d="M5 12h14M13 6l6 6-6 6"/>',
        "search": '<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/>'}
ic = lambda k: f'<svg viewBox="0 0 24 24">{ICON[k]}</svg>'

# всплывающее окно посреди визита: главное — советы лично тебе (не всем и не в Telegram-приложении)
POPUP = """<div class="pop" id="pop" hidden><div class="pop-in gl"><button class="pop-x" aria-label="Закрыть">×</button>
<h3>Шуршуня подберёт книги под твой вкус</h3>
<p>Отметь три любимые книги, и советы будут лично для тебя, а не из общего топа.</p>
<div class="ctas"><a class="btn" href="/app.html?app=1">Открыть в браузере</a><a class="btn ghost" href="https://t.me/Wonderbookworld_bot?startapp=site">Открыть в Telegram</a></div></div></div>
<script>(function(){try{var L=localStorage,now=Date.now();if(L.getItem("zal.onb")||/tgWebApp/.test(location.hash))return;var off=+L.getItem("nora.pop")||0;if(now-off<3*864e5)return;
var v=(+sessionStorage.getItem("nora.pv")||0)+1;sessionStorage.setItem("nora.pv",v);var p=document.getElementById("pop"),shown=0;
function show(){if(shown)return;shown=1;p.hidden=false;requestAnimationFrame(function(){p.classList.add("on")});L.setItem("nora.pop",now)}
function hide(){p.classList.remove("on");setTimeout(function(){p.hidden=true},300)}
p.addEventListener("click",function(e){if(e.target===p||e.target.closest(".pop-x"))hide()});
setTimeout(show,v>=2?9000:28000);addEventListener("scroll",function(){if(scrollY>document.body.scrollHeight*.55&&(+sessionStorage.getItem("nora.pv")||0)>=1)setTimeout(show,1500)},{passive:true})}catch(e){}})();</script>"""
# реклама Норы в углу экрана, пока человек читает страницу: появляется, когда прочитана четверть, фишки меняются сами.
# Не показываем тем, у кого уже есть Нора, внутри Telegram и 3 дня после закрытия; на время большого окна - прячем
CORNER = """<aside class="nad gl" id="nad" hidden aria-label="Приложение Нора - что умеет"><button class="nad-x" aria-label="Закрыть">×</button>
<a class="nad-a" href="/app.html?app=1&amp;utm_source=site&amp;utm_medium=corner"><img src="/icons/icon-192.png?v=5" alt="" width="44" height="44"><span class="nad-t"><span class="nad-s"><b>Читательский дневник</b><span>Записывай мысли о книгах и смотри, сколько прочитано</span></span><span class="nad-s"><b>Книжный клуб</b><span>Читайте книги с друзьями</span></span><span class="nad-s"><b>Шуршуня советует</b><span>Подберёт книги под твой вкус, а не из общего топа</span></span><span class="nad-s"><b>Цель на год</b><span>Поставь цель и следи, успеваешь ли</span></span><span class="nad-s"><b>Твои полки</b><span>«Хочу прочитать» и «Прочитано» - все книги под рукой</span></span><span class="nad-s"><b>Перенос книг</b><span>Из ЛитРес и Заметок за минуту</span></span></span><span class="nad-b">Открыть</span></a></aside>
<script>(function(){try{var L=localStorage,n=document.getElementById("nad");if(!n||L.getItem("zal.onb")||/tgWebApp/.test(location.hash))return;if(Date.now()-(+L.getItem("nora.nad")||0)<3*864e5)return;
var F=n.querySelectorAll(".nad-s"),k=Math.floor(Math.random()*F.length),on=0,t=null;function pop(){var p=document.getElementById("pop");return p&&!p.hidden}
function show(){if(on||pop())return;on=1;F[k].classList.add("on");n.hidden=false;requestAnimationFrame(function(){n.classList.add("on")});t=setInterval(function(){if(document.hidden)return;F[k].classList.remove("on");k=(k+1)%F.length;F[k].classList.add("on")},15000)}
function hide(){n.classList.remove("on");clearInterval(t);setTimeout(function(){n.hidden=true},300)}
n.querySelector(".nad-x").addEventListener("click",function(e){e.preventDefault();L.setItem("nora.nad",Date.now());on=2;hide()});
addEventListener("scroll",function(){if(on===2)return;var h=document.body.scrollHeight-innerHeight;if(h>0&&scrollY>h*.25)show();if(on===1&&pop())hide(),on=0},{passive:true});setTimeout(function(){if(scrollY>200)show()},1500)}catch(e){}})();</script>"""
# оценки и отзывы читателей Фантлаба — подгружаются на странице книги; отзывы открываются списком
REVIEWS_JS = r"""<script>(function(){var el=document.getElementById("frate");if(!el)return;var F="https://api.fantlab.ru",t=el.dataset.t,a=(el.dataset.a||"").toLowerCase().replace(/ё/g,"е");
var nm=function(s){return String(s||"").toLowerCase().replace(/ё/g,"е")},cl=function(s){return String(s||"").replace(/\[[^\]]*\]/g,"").replace(/<[^>]+>/g,"").replace(/\s+/g," ").trim()},
pl=function(n,a,b,c){n=Math.abs(n)%100;var m=n%10;return n>10&&n<20?c:m>1&&m<5?b:m==1?a:c},esc=function(s){return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;")};
fetch(F+"/search-works?q="+encodeURIComponent(t)+"&page=1&onlymatches=1").then(function(r){return r.json()}).then(function(L){L=Array.isArray(L)?L:[];
 var w=L.filter(function(x){return !a||nm(x.autor_rusname).indexOf(a)>=0||nm(x.autor_name).indexOf(a)>=0})[0];if(!w)return;
 return fetch(F+"/work/"+w.work_id).then(function(r){return r.json()}).then(function(j){var r=j.rating||{},v=+r.voters||0,rc=+j.val_responsecount||0,h="";
  var u="/r/?w="+w.work_id+"&b="+encodeURIComponent(location.pathname);
  if(v>=5)h+='<a href="'+u+'">★ '+(r.rating/2).toFixed(1).replace(".",",")+' · '+v.toLocaleString("ru-RU")+' '+pl(v,"оценка","оценки","оценок")+'</a>';
  if(rc)h+='<a href="'+u+'">'+rc+' '+pl(rc,"отзыв","отзыва","отзывов")+'</a>';el.innerHTML=h;if(h)el.classList.add("on")})}).catch(function(){})})();</script>"""
FUZ_JS = r'''var KE="qwertyuiop[]asdfghjkl;'zxcvbnm,.`",KR="йцукенгшщзхъфывапролджэячсмитьбюё";
function NM(s){return String(s||"").toLowerCase().replace(/ё/g,"е").replace(/[^a-zа-я0-9]+/g," ").trim()}
function SW(q){return /[а-я]/.test(q)||!/[a-z]/.test(q)?"":q.split("").map(function(c){var i=KE.indexOf(c);return i<0?c:KR[i]}).join("")}
function LV(a,b){if(Math.abs(a.length-b.length)>2)return 9;var p=[],i,j;for(j=0;j<=b.length;j++)p[j]=j;for(i=1;i<=a.length;i++){var c=[i];for(j=1;j<=b.length;j++)c[j]=Math.min(p[j]+1,c[j-1]+1,p[j-1]+(a[i-1]===b[j-1]?0:1));p=c}return p[b.length]}
function SC(ws,words){var s=0;for(var k=0;k<ws.length;k++){var w=ws[k],best=0;for(var m=0;m<words.length;m++){var x=words[m],v=0;
 if(x.indexOf(w)===0)v=3;else if(w.length>=4&&x.indexOf(w)>0)v=1.5;else if(w.length>=4&&/[a-zа-я]/.test(w)){var d=Math.min(LV(w,x.slice(0,w.length+1)),LV(w,x));if(d<=1||(d<=2&&w.length>=7))v=d<=1?2:1.2}
 if(v>best)best=v}if(!best)return 0;s+=best}return s-words.length*0.02}
function FIND(list,txt,q,lim){var v=NM(q);if(v.length<2)return [];var go=function(v){var ws=v.split(" "),out=[];for(var i=0;i<list.length;i++){var sc=SC(ws,txt(i));if(sc)out.push([sc,i])}
 out.sort(function(a,b){return b[0]-a[0]||a[1]-b[1]});return out};var r=go(v),alt=SW(v);if(alt&&(!r.length||r[0][0]<v.split(" ").length*2)){var r2=go(alt);if(r2.length)r=r2}
 return r.slice(0,lim).map(function(z){return z[1]})}
'''
SEARCH_JS = r"""<script>(function(){var q=document.getElementById("q"),box=document.getElementById("sres");if(!q)return;var D=null,nm=function(s){return String(s||"").toLowerCase().replace(/ё/g,"е").replace(/[^a-zа-я0-9 ]+/g," ")};
""" + FUZ_JS + r"""
function load(){if(D)return Promise.resolve(D);return fetch("/books/search.json").then(function(r){return r.json()}).then(function(j){D=j.map(function(x){var t=NM(x[0]+" "+x[1]);return [x,t,t.split(" ")]});return D})}
q.addEventListener("focus",load,{once:true});if(location.hash==="#poisk")setTimeout(function(){q.focus()},300);
var u=new URLSearchParams(location.search).get("q");if(u){q.value=u;load().then(function(){q.dispatchEvent(new Event("input"))})}
q.addEventListener("input",function(){var v=nm(q.value).trim();if(v.length<2){box.innerHTML="";return}load().then(function(){var out=FIND(D,function(i){return D[i][2]},q.value,8).map(function(i){return D[i][0]});
box.innerHTML=out.map(function(x){return '<a href="'+x[2]+'"><b>'+x[0].replace(/</g,"&lt;")+'</b><span>'+x[1].replace(/</g,"&lt;")+(x[3]?" · "+x[3]:"")+'</span></a>'}).join("")+'<a class="sall" href="/app.html?app=1">Искать среди 100 000 книг в Норе</a>'})})})();</script>"""
SN = """<!-- Cloudflare Web Analytics --><script defer type='module' src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{"token": "572d5eebd0c442bda32887c9f80bb139"}'></script><!-- End Cloudflare Web Analytics -->"""
HEAD = f"""<link rel="icon" href="/icons/icon-192.png?v=5"><link rel="apple-touch-icon" href="/icons/icon-180.png?v=5"><meta name="theme-color" content="#05060A">
<link rel="preload" href="/fonts/manrope-cyrillic-400-normal.woff2" as="font" type="font/woff2" crossorigin><link rel="preload" href="/fonts/literata-cyrillic-wght-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/site.css?v={VER}">"""
NAV = [("/c/romantezi.html", "Ромэнтези"), ("/c/dark-roman.html", "Дарк роман"), ("/c/novinki.html", "Новинки"), ("/p/", "Похожие книги"), ("/c/", "Все подборки")]
APP = "/app.html?app=1"


def hdr(active=""):
    # значок входа в правом верхнем углу на всех страницах
    return ('<a class="enter gl" href="/app.html?app=1" aria-label="Войти в Нору" title="Войти"><svg viewBox="0 0 24 24" aria-hidden="true">'
            '<circle cx="12" cy="8.5" r="3.6"/><path d="M5 19.5c1.2-3.4 4-5 7-5s5.8 1.6 7 5"/></svg></a>')  # шапка не нужна: главное — книги, вход в Нору — во всплывающем окне и внизу страницы


MINE = """<script>try{if(localStorage.getItem("zal.onb"))document.querySelectorAll("#openNora").forEach(function(a){a.textContent="Моя Нора"})}catch(e){}</script>"""


def footer(colls):
    """подвал как на обычных сайтах: логотип и короткая строка ссылок, ниже - почта и конфиденциальность"""
    L = [("/c/", "Подборки"), ("/knizhnyy-klub.html", "Книжный клуб"), ("/voprosy/", "Вопросы для обсуждения"), ("/poryadok/", "Порядок чтения серий"), ("/test.html", "Тест: что почитать"),
         (APP, "Открыть в браузере"), (BOT, "Открыть в Telegram")]
    return (f'<footer class="ft ft2"><div class="wrap"><div class="ft2-in"><a class="logo" href="/"><img src="/icons/icon-192.png?v=5" alt="">Нора</a>'
            '<nav>' + "".join(f'<a href="{u}">{t}</a>' for u, t in L) + '</nav></div>'
            f'<div class="ft2-b"><span>© {YNOW} Нора</span><a href="mailto:{MAIL}">{MAIL}</a><a href="/privacy.html">Конфиденциальность</a></div></div></footer>')


FOOT = ""


def dash(h):
    """в текстах сайта - дефисы вместо длинных тире (как в приложении)"""
    return h.replace(", — ", ", ").replace(",— ", ", ").replace(" — ", " - ").replace("—", "-").replace("–", "-")


def page(path, title, desc, body, full_title=None, active="", img=None, ld=None):
    canon = f"{SITE}/{path}".replace("/index.html", "/")
    ldj = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in (ld or []))
    doc = f"""<!doctype html><html lang="ru"><head><meta charset="utf-8"><script src="/ym.js"></script><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{esc(full_title or title + " — Нора")}</title><meta name="description" content="{esc(desc[:200])}"><link rel="canonical" href="{canon}">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc[:200])}"><meta property="og:url" content="{canon}">
<meta property="og:image" content="{esc(img or SITE + '/icons/icon-512.png?v=5')}"><meta property="og:type" content="website"><meta property="og:site_name" content="Нора">{HEAD}{ldj}</head><body>
{hdr(active)}<main>{body}</main>{FOOT}{MINE}{POPUP}{CORNER}{SN}</body></html>"""
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, "w", encoding="utf-8").write(dash(doc))
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
    inner = (cv(b) + f'<div class="t">{esc(b["t"])}</div><div class="a">{esc(meta)}</div>'
             + (f'<p>{esc(b["ann"])}</p>' if ann and b["ann"] else ""))
    return f'<a class="bk" href="/{u}">{inner}</a>' if u else f'<div class="bk">{inner}</div>'


LR_T = "https://litres.onelink.me/1566260005?pid=advcake_int&c=affiliate&af_siteid=eda80252&af_ad=&clickid=&af_sub1=nora&af_sub2=&af_sub3=&af_sub4=&af_sub5=&af_adset=&is_retargeting=true&af_dp=litresread%3A%2F%2F&af_reengagement_window=30d&af_click_lookback=7d&deep_link_value={url}&af_web_dp={url}&af_ios_url={url}&af_android_url={url}&utm_source=advcake&utm_medium=cpa&utm_campaign=affiliate&utm_content=eda80252&advcake_params=&utm_term=&sub1=nora&ab_test_value=&erid=2VfnxyNkZrY&advcake_method=1&m=1"


def WHERE(b):
    q = urllib.parse.quote(b["t"] + " " + b["a"].split(" ")[-1]); qt = urllib.parse.quote(b["t"])
    icon = lambda d: f'<img src="/img/where/{d}.png" alt="" width="22" height="22" loading="lazy">'
    PIN = '<svg viewBox="0 0 24 24"><path d="M12 21s-6-5.6-6-10.5a6 6 0 0 1 12 0C18 15.4 12 21 12 21z"/><circle cx="12" cy="10.5" r="2.2"/></svg>'
    ON = [("litres.ru", "ЛитРес", LR_T.replace("{url}", urllib.parse.quote((f"https://www.litres.ru/pages/biblio_book/?art={lit_id(b)}" if lit_id(b) else f"https://www.litres.ru/search/?q={q}"), safe=""))), ("books.yandex.ru", "Яндекс Книги", f"/ya.html?q={q}"),
          ("ozon.ru", "Ozon", f"https://www.ozon.ru/search/?text={q}&category=16500")]
    OFF = [("", "Книжные рядом", "https://yandex.ru/maps/?text=" + urllib.parse.quote("книжный магазин")), ("chitai-gorod.ru", "Читай-город", f"https://www.chitai-gorod.ru/search?phrase={qt}&partnerId=1006702&utm_source=affiliate&utm_medium=cpa&utm_campaign=1006702&sub_3=2W5zFJkZEDg&erid=2W5zFJkZEDg"),
           ("bookvoed.ru", "Буквоед", f"https://www.bookvoed.ru/search?q={qt}")]
    a = lambda d, n, u: f'<a href="{u}" rel="nofollow noopener" target="_blank">{icon(d) if d else PIN}{n}</a>'
    return ('<div class="whr"><b>Где прочитать</b><div>' + "".join(a(*x) for x in ON) + '</div><b class="w2">Купить в магазине</b><div>'
            + "".join(a(*x) for x in OFF) + '</div><small class="erid">Реклама · ООО ЛИТРЕС, ИНН 7719571260, erid: 2VfnxyNkZrY · Читай-город, erid: 2W5zFJkZEDg</small></div>')


def rail(L, bare=False):
    return '<div class="rail' + (' bare' if bare else '') + '">' + "".join(card(b) for b in L) + "</div>"


def shelf(title, href, ds, L, all_txt="Все"):
    return (f'<section class="shelf"><div class="shd"><h2><a href="{href}">{esc(title)}</a></h2><a class="all" href="{href}">{esc(all_txt)}</a></div>'
            + (f'<p class="ds">{esc(ds)}</p>' if ds else "") + rail(L, bare=True) + "</section>")


CTA = (f'<div class="ctas"><a class="btn" href="{APP}">Открыть в браузере</a>'
       f'<a class="btn ghost" href="{BOT}">{ic("tg")}Открыть в Telegram</a></div>')
FINAL = (f'<section class="final gl"><h2>Шуршуня знает, что тебе понравится</h2>'
         f'<p>Отметь три любимые книги, и он подберёт книги под твой вкус.</p>{CTA}</section>')
coll_data = []
for path, title, lead, pred in COLL:
    L = sorted([b for b in books if pred(b)], key=rank)[:60]
    if len(L) < 8:
        continue
    L = sorted(L, key=lambda b: (not (b["ann"] or img_of(b)), L.index(b)))  # с описанием и обложкой — вперёд
    coll_data.append((path, title, lead, L))
# «Читают в этом месяце»: самые обсуждаемые книги последних лет из всех жанров (не только ромэнтези) — по числу оценок, один автор — одна книга
MON_PREP = ["январе", "феврале", "марте", "апреле", "мае", "июне", "июле", "августе", "сентябре", "октябре", "ноябре", "декабре"][time.gmtime().tm_mon - 1]
_hot = sorted([b for b in books if (b["y"] or 0) >= YNOW - 4 and (b.get("sl") or 0) >= 300 and (b["ann"] or img_of(b))], key=lambda b: -(b.get("sl") or 0))
_lit = sorted([b for b in books if (b["y"] or 0) >= YNOW - 8 and not love(b) and b["g"] in ("modern", "detective", "scifi", "nonfic", "fantasy")
               and (b["acc"] or b["cat"]) and (b["ann"] or img_of(b))], key=lambda b: (-len(b["acc"]), -(b["q"] or 0), -(b["y"] or 0)))
_g, _au, A_, B_ = {}, set(), [], []
for b in _hot:  # то, что массово читают: не больше 4 книг одного жанра
    k = "love" if love(b) else b["g"]
    if nk(b["a"]) in _au or _g.get(k, 0) >= 4:
        continue
    _au.add(nk(b["a"])); _g[k] = _g.get(k, 0) + 1; A_.append(b)
    if len(A_) >= 18:
        break
for b in _lit:  # и то, о чём говорят: премии и громкая проза последних лет
    if nk(b["a"]) in _au:
        continue
    _au.add(nk(b["a"])); B_.append(b)
    if len(B_) >= 18:
        break
# «В тренде сейчас» - тот же ручной список громких книг, что в приложении (const TREND)
def app_list(name):
    m = re.search(r'const ' + name + r'="([^"]+)"', open(os.path.join(ROOT, "app.html"), encoding="utf-8").read())
    out = []
    for pr in (m.group(1).split(";") if m else []):
        t_, s_ = (pr.split("|") + [""])[:2]
        c_ = [b for b in books if nk(b["t"]) == nk(t_) and nk(s_) in nk(b["a"])] or [b for b in books if nk(b["t"]).startswith(nk(t_)) and nk(s_) in nk(b["a"])]
        if c_: out.append(sorted(c_, key=lambda b: (not b["cat"], not img_of(b)))[0])
    return out
def pairs_list(txt):
    out = []
    for pr in txt.split(";"):
        t_, s_ = (pr.split("|") + [""])[:2]
        c_ = [b for b in books if nk(b["t"]) == nk(t_) and nk(s_) in nk(b["a"])] or [b for b in books if nk(b["t"]).startswith(nk(t_)) and nk(s_) in nk(b["a"])]
        if c_: out.append(sorted(c_, key=lambda b: (not b["cat"], not img_of(b)))[0])
        else: print("  нет в каталоге:", t_, s_)
    return out


# подборки по настроению собраны вручную: по тегам туда попадали случайные книги («Я, робот» в уютных, «Солярис» в страшных)
HAND = {
 "smeshnye": "Трое в лодке, не считая собаки|Джером;Автостопом по Галактике|Адамс;Понедельник начинается в субботу|Стругацк;Двенадцать стульев|Ильф;Золотой телёнок|Ильф;Похождения бравого солдата Швейка|Гашек;Благие знамения|Пратчетт;Стража! Стража!|Пратчетт;Клуб убийств по четвергам|Осман;Дневник Бриджит Джонс|Филдинг;Уловка-22|Хеллер;Собачье сердце|Булгаков;Приключения Тома Сойера|Твен;Мой дедушка был вишней|Нанетти;Дживс и Вустер|Вудхауз;Кот, который ходил сам по себе|Киплинг",
 "uyutnye": "Хоббит, или Туда и обратно|Толкин;Маленькие женщины|Олкотт;Аня из Зелёных Мезонинов|Монтгомери;Энциклопедия фей Эмили Уайлд|Фосетт;Пока не остыл кофе|Кавагути;Клуб убийств по четвергам|Осман;Зимнее солнцестояние|Пилчер;Рождество и красный кардинал|Флэгг;Жареные зелёные помидоры в кафе «Полустанок»|Флэгг;Вино из одуванчиков|Брэдбери;Трое в лодке, не считая собаки|Джером;Тайная жизнь пчёл|Кидд;Мой дедушка был вишней|Нанетти;Легенды и латте|Бэрри;Дом в лазурном море|Клун;Ветер в ивах|Грэм",
 "strashnye": "Оно|Кинг;Сияние|Кинг;Кладбище домашних животных|Кинг;Мизери|Кинг;Дракула|Стокер;Франкенштейн|Шелли;Призрак дома на холме|Джексон;Мы всегда жили в замке|Джексон;Поворот винта|Джеймс;Мексиканская готика|Морено-Гарсия;Пищеблок|Иванов;Вий|Гоголь;Упырь|Толстой;Зов Ктулху|Лавкрафт;Женщина в чёрном|Хилл;Дом листьев|Данилевский;Ребекка|дю Морье",
 "trogatelnye": "Цветы для Элджернона|Киз;Книжный вор|Зусак;Бегущий за ветром|Хоссейни;Тысяча сияющих солнц|Хоссейни;Не отпускай меня|Исигуро;Три товарища|Ремарк;Зелёная миля|Кинг;Пока не остыл кофе|Кавагути;До встречи с тобой|Мойес;Виноваты звёзды|Грин;Белый Бим Чёрное ухо|Троепольский;Маленький принц|Сент-Экзюпери;Пятеро, что ждут тебя на небесах|Элбом;Вторники с Морри|Элбом;Остаток дня|Исигуро;Мальчик в полосатой пижаме|Бойн",
 "zahvatyvayuschie": "Исчезнувшая|Флинн;Девушка в поезде|Хокинс;Безмолвный пациент|Михаэлидес;Код да Винчи|Браун;Молчание ягнят|Харрис;Девушка с татуировкой дракона|Ларссон;Голодные игры|Коллинз;Шестёрка воронов|Бардуго;Проект «Аве Мария»|Вейер;Граф Монте-Кристо|Дюма;Тень ветра|Сафон;Загадка номера 622|Диккер;Правда о деле Гарри Квеберта|Диккер;Внутри убийцы|Омер;Снеговик|Несбё;Остров проклятых|Лихэйн",
 "zastavlyayut-zadumatsya": "1984|Оруэлл;О дивный новый мир|Хаксли;Мы|Замятин;Цветы для Элджернона|Киз;Не отпускай меня|Исигуро;Сто лет одиночества|Маркес;Мастер и Маргарита|Булгаков;Преступление и наказание|Достоевский;Посторонний|Камю;Чума|Камю;Сказать жизни «Да!»|Франкл;Sapiens|Харари;Убить пересмешника|Ли;Повелитель мух|Голдинг;Пикник на обочине|Стругацк;Солярис|Лем",
 "na-odin-vecher": "Маленький принц|Сент-Экзюпери;Старик и море|Хемингуэй;Собачье сердце|Булгаков;Превращение|Кафка;Пока не остыл кофе|Кавагути;Завтрак у Тиффани|Капоте;Посторонний|Камю;Шинель|Гоголь;Скотный двор|Оруэлл;Великий Гэтсби|Фицджеральд;Шахматная новелла|Цвейг;Письмо незнакомки|Цвейг;Кентервильское привидение|Уайльд;Дама с собачкой|Чехов;Трое в лодке, не считая собаки|Джером;Кот, который ходил сам по себе|Киплинг",
 "young-adult": "Голодные игры|Коллинз;Виноваты звёзды|Грин;Над пропастью во ржи|Сэлинджер;Дивергент|Рот;Бегущий в лабиринте|Дэшнер;Шестёрка воронов|Бардуго;Жестокий принц|Блэк;Хорошая девочка должна умереть|Джексон;Мы - лжецы|Локхарт;Хорошо быть тихоней|Чбоски;Тринадцать причин почему|Эшер;Книжный вор|Зусак;Дом, в котором…|Петросян;Вафельное сердце|Парр;Чучело|Железников;Дикая собака динго|Фраерман",
}
_cd = {p_: i_ for i_, (p_, _, _, _) in enumerate(coll_data)}
for _p, _txt in HAND.items():
    _L = pairs_list(_txt)
    if _p in _cd and len(_L) >= 8:
        p0, t0, l0, _ = coll_data[_cd[_p]]
        coll_data[_cd[_p]] = (p0, t0, l0, _L)
# «Современные любовные романы» на деле - большие романы о любви
coll_data = [(p_, "Романы о любви" if p_ == "lyubovnye-romany" else t_, "Большие истории любви - от классики до наших дней." if p_ == "lyubovnye-romany" else l_, L_) for p_, t_, l_, L_ in coll_data]
# новинки: без самиздата и продолжений серий, одна книга автора
if "novinki" in _cd:
    _au, _nv = set(), []
    for b in sorted([b for b in books if (b["y"] or 0) >= YNOW - 1 and "самиздат" not in b["tags"] and not re.search(r"(книга|том|часть)\s*\d|\d\s*$|-\s*\d+|\d+\.", b["t"].lower()) and not notnovel(b) and (img_of(b) or b["ann"]) and not has(b, "любовное фэнтези", "троп:popadan", "любовный роман", "боевое фэнтези", "литрпг")], key=lambda b: -(b.get("sl") or 0)):
        if nk(b["a"]) in _au: continue
        _au.add(nk(b["a"])); _nv.append(b)
        if len(_nv) >= 40: break
    if len(_nv) >= 8:
        p0, t0, l0, _ = coll_data[_cd["novinki"]]; coll_data[_cd["novinki"]] = (p0, t0, l0, _nv)
# дарк роман: только книги с тегом «дарк роман»/«тёмный роман» или их тропами; если таких мало - подборки нет
if "dark-roman" in _cd:
    _dk = [b for b in books if has(b, "дарк роман", "троп:dark") and "самиздат" not in b["tags"]]
    if len(_dk) < 8:
        coll_data = [c for c in coll_data if c[0] != "dark-roman"]
hot = app_list("TREND")
if len(hot) >= 8:
    coll_data.insert(0, ("chitayut-seychas", "В тренде сейчас", "Громкие книги, о которых сейчас говорят: премии, экранизации, бестселлеры.", hot))
# «Новогоднее настроение»: зима, Рождество, снег и сказка
NY_T = re.compile(r"рождеств|нов\w* год|новогодн|сочельник|(?<![а-яё])[её]лк|снегуроч|щелкунчик|метель|снежн\w* королев|зимн|(?<![а-яё])зима\b|декабр", re.I)
NY_A = re.compile(r"рождеств|новогодн|нов\w* год[а-я]*\b|сочельник|под ёлк|наряжа\w* ёлк", re.I)
ny = [b for b in books if not notnovel(b) and (NY_T.search(b["t"]) or NY_A.search(b["ann"] or "")) and (b["ann"] or img_of(b))]
_man = app_list("MAND_L"); _mn = {id(b) for b in _man}
ny = _man + [b for b in sorted({id(b): b for b in ny}.values(), key=lambda b: (-(b["q"] or 0), -(b.get("sl") or 0))) if b["cat"] and id(b) not in _mn][:26]
if len(ny) >= 8:
    coll_data.insert(1, ("novogodnee-nastroenie", "Книги с запахом мандаринов", "Тёплые истории для длинных вечеров - с пледом, чаем и чудом.", ny))
# сезонные подборки под зимний поисковый спрос (ноябрь-январь)
SEASON = [
 ("chto-pochitat-na-novogodnie-kanikuly", "Что почитать на новогодние каникулы", "Каникулы длинные, а вкусы разные. Найди свой раздел: фэнтези и ромэнтези, современная проза, детективы или классика - в каждом книги, в которые можно уйти на все праздники.",
  [("Если любишь фэнтези и ромэнтези", "Драконы, фейри, академии и любовь, от которой не оторваться до утра.",
    "Четвёртое крыло|Яррос;Королевство шипов и роз|Маас;Шестёрка воронов|Бардуго;Жестокий принц|Блэк;Ночной цирк|Моргенштерн;Цирцея|Миллер;Медведь и соловей|Арден;Гарри Поттер и философский камень|Роулинг;Хоббит, или Туда и обратно|Толкин;Энциклопедия фей Эмили Уайлд|Фосетт;Божественные соперники|Росс;Мара и Морок|Арден;Шесть алых журавлей|Лим"),
   ("Если читаешь современную прозу", "Истории про обычных людей, после которых хочется помолчать или позвонить близким.",
    "Тень ветра|Сафон;Тайная история|Тартт;Там, где раки поют|Оуэнс;Полночная библиотека|Хейг;Пока не остыл кофе|Кавагути;Вторая жизнь Уве|Бакман;Маленькая жизнь|Янагихара;Зимний сад|Ханна;Голландский дом|Пэтчетт;Четыре ветра|Ханна;Книжный вор|Зусак;Добро пожаловать в «Книжный в Хюнамдоне»|Хван;Чагин|Водолазкин"),
   ("Если хочется детектива и приключений", "Загадки, погони и сюжеты, из-за которых забываешь про оливье.",
    "Клуб убийств по четвергам|Осман;Исчезнувшая|Флинн;Загадка номера 622|Диккер;Убийство в «Восточном экспрессе»|Кристи;Граф Монте-Кристо|Дюма;Проект «Аве Мария»|Вейер;Голодные игры|Коллинз;Охотничий дом|Фоли;Список гостей|Фоли;Безмолвный пациент|Михаэлидес;Девы|Михаэлидес"),
   ("Если соскучилась по классике", "Большие романы, на которые в обычные дни не хватает времени.",
    "Мастер и Маргарита|Булгаков;Анна Каренина|Толстой;Джейн Эйр|Бронте;Сто лет одиночества|Маркес;Маленькие женщины|Олкотт;Ребекка|дю Морье;Гордость и предубеждение|Остин;Три товарища|Ремарк;Унесённые ветром|Митчелл;Доктор Живаго|Пастернак;Война и мир|Толстой")],
  "Что почитать на новогодние каникулы: фэнтези, ромэнтези, проза, детективы"),
 ("knigi-dlya-zimnih-vecherov", "Книги для зимних вечеров", "Снег за окном, плед и чай: книги, в которых зима - почти отдельный герой.",
  "Зимний сад|Ханна;Медведь и соловей|Арден;Снежная королева|Андерсен;Рождественская песнь в прозе|Диккенс;Щелкунчик и мышиный король|Гофман;Зимнее солнцестояние|Пилчер;Ночь перед Рождеством|Гоголь;Анна Каренина|Толстой;Доктор Живаго|Пастернак;Джейн Эйр|Бронте;Грозовой перевал|Бронте;Ребекка|дю Морье;Убийство в «Восточном экспрессе»|Кристи;Террор|Симмонс;Дом в лазурном море|Клун;Энциклопедия фей Эмили Уайлд|Фосетт;Маленькие женщины|Олкотт;Рождество и красный кардинал|Флэгг",
  "Книги для зимних вечеров: что почитать зимой под пледом"),
 ("knigi-v-podarok-na-novyy-god", "Книги в подарок на Новый год", "Выбирай по человеку, а не по обложке: подруге, маме, тому, кто читает редко, или тому, у кого всё есть.",
  [("Свежее: книги последних лет", "То, что сейчас читают и обсуждают, - скорее всего, этого у человека ещё нет.",
    "Полночная библиотека|Хейг;Проект «Аве Мария»|Вейер;Энциклопедия фей Эмили Уайлд|Фосетт;Клуб убийств по четвергам|Осман;Голландский дом|Пэтчетт;Четыре ветра|Ханна;Шесть алых журавлей|Лим;Птичий город за облаками|Дорр;Тело. Руководство пользователя|Брайсон;Магазин снов мистера Талергута|Ли"),
   ("Тому, кто любит фэнтези", "Волшебные миры, в которые уходят на все каникулы.",
    "Ночной цирк|Моргенштерн;Медведь и соловей|Арден;Шестёрка воронов|Бардуго;Мара и Морок|Арден;Невеста Ноября|Арден;Божественные соперники|Росс;Однажды разбитое сердце|Гарбер;Десять тысяч дверей Января|Харроу;Тень и кость|Бардуго;Хоббит, или Туда и обратно|Толкин"),
   ("Тому, кто читает редко", "Короткие и добрые книги, которые легко начать и приятно дочитать.",
    "Маленький принц|Сент-Экзюпери;Пока не остыл кофе|Кавагути;Кафе на краю земли|Стрелеки;Добро пожаловать в «Книжный в Хюнамдоне»|Хван;Магазин шаговой недоступности|Ким;Манюня|Абгарян;Миссис Харрис едет в Париж|Гэллико;Марсианин|Вейер;Автостопом по галактике|Адамс;Трое в лодке|Джером"),
   ("Маме, сестре, близкому человеку", "Тёплые истории, которые потом захочется обсудить вместе.",
    "Зимний сад|Ханна;Соловей|Ханна;Книжный вор|Зусак;Маленькие женщины|Олкотт;Чагин|Водолазкин;Хамнет|Фаррелл;Эшелон на Самарканд|Яхина;Зулейха открывает глаза|Яхина;Лавр|Водолазкин;Вино из одуванчиков|Брэдбери"),
   ("Тому, у кого всё есть", "Большие книги-события: такие дарят в красивом издании.",
    "Мастер и Маргарита|Булгаков;Война и мир|Толстой;Властелин колец|Толкин;Дюна|Герберт;Граф Монте-Кристо|Дюма;Sapiens|Харари;Nexus|Харари;Ружья, микробы и сталь|Даймонд;Краткая история времени|Хокинг;Хроники Нарнии|Льюис")],
  "Какую книгу подарить на Новый год: подруге, маме, тому, кто читает редко"),
 ("kniga-v-podarok-podruge", "Какую книгу подарить подруге", "Выбирай по тому, что она читает сейчас, - тогда книга не уйдёт пылиться на полку.",
  [("Свежее: книги последних лет", "Новые романы, о которых говорят, - скорее всего, их у неё ещё нет.",
    "Энциклопедия фей Эмили Уайлд|Фосетт;Божественные соперники|Росс;Однажды разбитое сердце|Гарбер;Уроки химии|Гармус;Полночная библиотека|Хейг;Добро пожаловать в «Книжный в Хюнамдоне»|Хван;Голландский дом|Пэтчетт;Магазин снов мистера Талергута|Ли;Четыре ветра|Ханна;Список гостей|Фоли"),
   ("Если она читает ромэнтези", "Драконы, фейри и любовь. В этих книгах есть откровенные сцены.",
    "Четвёртое крыло|Яррос;Дом земли и крови|Маас;Из крови и пепла|Арментроут;Жестокий принц|Блэк;Цирцея|Миллер;Мара и Морок|Арден;Невеста Ноября|Арден;Ночной цирк|Моргенштерн;Медведь и соловей|Арден;Шестёрка воронов|Бардуго"),
   ("Если любит истории про любовь", "Тёплые и красивые романы, которые хочется перечитывать.",
    "Люди, которых мы встречаем в отпуске|Генри;Пляжное чтение|Генри;Гипотеза любви|Хейзелвуд;Квартира на двоих|Лири;Малибу в огне|Рид;Там, где раки поют|Оуэнс;До встречи с тобой|Мойес;Дневник памяти|Спаркс;Гордость и предубеждение|Остин;Джейн Эйр|Бронте"),
   ("Если любит детективы", "Сюжеты, из-за которых она забудет про телефон.",
    "Клуб убийств по четвергам|Осман;Загадка номера 622|Диккер;Охотничий дом|Фоли;Девы|Михаэлидес;Безмолвный пациент|Михаэлидес;Дело Аляски Сандерс|Диккер;Тайная жизнь писателей|Мюссо;Посмотри, отвернись, посмотри|Михалкова;Большое небо|Аткинсон;Убийство в «Восточном экспрессе»|Кристи")],
  "Какую книгу подарить подруге на Новый год и день рождения"),
 ("kniga-v-podarok-mame", "Какую книгу подарить маме", "Тёплые истории, после которых захочется позвонить и обсудить.",
  [("Свежее: книги последних лет", "Новые романы, которые читают и советуют друг другу.",
    "Четыре ветра|Ханна;Сад|Степнова;Эшелон на Самарканд|Яхина;Голландский дом|Пэтчетт;Хамнет|Фаррелл;О, Уильям|Страут;Клара и Солнце|Исигуро;Чагин|Водолазкин;Добро пожаловать в «Книжный в Хюнамдоне»|Хван;Полночная библиотека|Хейг"),
   ("Добрые и светлые", "Книги, от которых становится уютно.",
    "Пока не остыл кофе|Кавагути;Магазин шаговой недоступности|Ким;Магазин снов мистера Талергута|Ли;Люди, которые всегда со мной|Абгарян;Манюня|Абгарян;Бабушка велела кланяться|Бакман;Кафе на краю земли|Стрелеки;Шоколад|Харрис;Миссис Харрис едет в Париж|Гэллико;Вино из одуванчиков|Брэдбери"),
   ("Большие истории о семье и судьбе", "Романы, в которых живёшь несколько вечеров подряд.",
    "Зимний сад|Ханна;Соловей|Ханна;Дети мои|Яхина;Зулейха открывает глаза|Яхина;Авиатор|Водолазкин;Лавр|Водолазкин;Книжный вор|Зусак;Там, где раки поют|Оуэнс;Брисбен|Водолазкин;Маленькие женщины|Олкотт"),
   ("Если она любит классику", "Красивое издание любимой книги - подарок, который остаётся надолго.",
    "Мастер и Маргарита|Булгаков;Анна Каренина|Толстой;Ребекка|дю Морье;Унесённые ветром|Митчелл;Гордость и предубеждение|Остин;Джейн Эйр|Бронте;Три товарища|Ремарк;Доктор Живаго|Пастернак;Война и мир|Толстой;Грозовой перевал|Бронте")],
  "Какую книгу подарить маме: тёплые романы и красивая классика"),
 ("kniga-v-podarok-muzhchine", "Какую книгу подарить мужчине", "Мужу, папе, брату или другу - по тому, что он любит.",
  [("Свежее: книги последних лет", "То, о чём сейчас спорят и что советуют, - скорее всего, у него этого ещё нет.",
    "Проект «Аве Мария»|Вейер;Рекурсия|Крауч;Выдох|Чан;Сорока на виселице|Веркин;Граф Аверин|Дашкевич;Королевство|Несбё;Дикий зверь|Диккер;Бронепароходы|Иванов;Институт|Кинг;Птичий город за облаками|Дорр"),
   ("Если любит фантастику", "Большие идеи и сюжеты, от которых не оторваться.",
    "Марсианин|Вейер;Задача трёх тел|Лю;Тёмный лес|Лю;Дюна|Герберт;Гиперион|Симмонс;Игра Эндера|Кард;Пикник на обочине|Стругацкие;Солярис|Лем;Стрелок|Кинг;Автостопом по галактике|Адамс"),
   ("Если любит приключения и детективы", "Погони, загадки и герои, за которых переживаешь.",
    "Пищеблок|Иванов;Филэллин|Юзефович;Сердце пармы|Иванов;Террор|Симмонс;Шантарам|Робертс;Тень ветра|Сафон;Девушка с татуировкой дракона|Ларссон;Имя розы|Эко;Граф Монте-Кристо|Дюма;Хоббит, или Туда и обратно|Толкин"),
   ("Если читает нон-фикшн", "Книги, которые потом цитируют за ужином.",
    "Nexus|Харари;Всё решено|Сапольски;Шум|Канеман;Необъятный мир|Йонг;Тело. Руководство пользователя|Брайсон;Атомные привычки|Клир;Sapiens|Харари;Думай медленно|Канеман;Ружья, микробы и сталь|Даймонд;Краткая история времени|Хокинг")],
  "Какую книгу подарить мужчине, мужу или папе"),
 ("kniga-v-podarok-podrostku", "Какую книгу подарить подростку", "Книги, которые читают не по списку, а потому что интересно.",
  [("Свежее: книги последних лет", "То, что сейчас читают и обсуждают с друзьями.",
    "Баллада о змеях и певчих птицах|Коллинз;Рассвет жатвы|Коллинз;Невеста Ноября|Арден;Мара и Морок|Арден;Шесть алых журавлей|Лим;Однажды разбитое сердце|Гарбер;Божественные соперники|Росс;Десять тысяч дверей Января|Харроу;Смертельное образование|Новик;Проект «Аве Мария»|Вейер"),
   ("Фэнтези и приключения", "Миры, в которые уходят с головой.",
    "Гарри Поттер и философский камень|Роулинг;Шестёрка воронов|Бардуго;Тень и кость|Бардуго;Жестокий принц|Блэк;Перси Джексон и похититель молний|Риордан;Дети крови и костей|Адейеми;Алая королева|Авеярд;Хроники Нарнии|Льюис;Сумерки|Майер;Хоббит, или Туда и обратно|Толкин"),
   ("Антиутопии и истории о взрослении", "Книги, которые потом обсуждают с друзьями.",
    "Голодные игры|Коллинз;Бегущий в лабиринте|Дэшнер;Дивергент|Рот;Дающий|Лоури;Виноваты звёзды|Грин;Чудо|Паласио;451 градус по Фаренгейту|Брэдбери;Повелитель мух|Голдинг;Убить пересмешника|Ли;Над пропастью во ржи|Сэлинджер")],
  "Какую книгу подарить подростку: фэнтези, антиутопии, книги о взрослении"),
 ("kniga-v-podarok-kollege", "Какую книгу подарить коллеге", "Когда человека знаешь не очень близко: книги, которые нравятся почти всем.",
  [("Свежее: книги последних лет", "То, что сейчас советуют друг другу.",
    "Полночная библиотека|Хейг;Клуб убийств по четвергам|Осман;Проект «Аве Мария»|Вейер;Добро пожаловать в «Книжный в Хюнамдоне»|Хван;Магазин шаговой недоступности|Ким;Магазин снов мистера Талергута|Ли;Голландский дом|Пэтчетт;Тело. Руководство пользователя|Брайсон;Цифровой минимализм|Ньюпорт;Выгорание|Нагоски"),
   ("Лёгкие и добрые", "Можно прочитать за пару вечеров.",
    "Маленький принц|Сент-Экзюпери;Пока не остыл кофе|Кавагути;Кафе на краю земли|Стрелеки;Манюня|Абгарян;Бабушка велела кланяться|Бакман;Шоколад|Харрис;Миссис Харрис едет в Париж|Гэллико;Трое в лодке|Джером;Марсианин|Вейер;Автостопом по галактике|Адамс"),
   ("Полезные", "Нон-фикшн без занудства.",
    "Атомные привычки|Клир;Шум|Канеман;Думай медленно|Канеман;Мозг материален|Казанцева;Магия утра|Элрод;Эссенциализм|Маккеон;Сила воли|Макгонигал;Поток|Чиксентмихайи;Кругом одни идиоты|Эриксон;Sapiens|Харари")],
  "Какую книгу подарить коллеге или начальнику на Новый год"),
]
GIFT = {"knigi-v-podarok-na-novyy-god", "kniga-v-podarok-podruge", "kniga-v-podarok-mame", "kniga-v-podarok-muzhchine", "kniga-v-podarok-podrostku", "kniga-v-podarok-kollege"}
SECTS = {}
SEO_T = {"novogodnee-nastroenie": "Книги с новогодней атмосферой: что почитать под Новый год"}
for _i, (_p, _t, _l, _txt, _ft) in enumerate(SEASON):
    if isinstance(_txt, list):  # подборка с разделами «для кого»
        _S = [(h_, sub_, pairs_list(t_)) for h_, sub_, t_ in _txt]
        _S = [x for x in _S if len(x[2]) >= 3]
        SECTS[_p] = _S
        _L, _sn = [], set()
        for _, _, l_ in _S:
            for b in l_:
                if id(b) not in _sn:
                    _sn.add(id(b)); _L.append(b)
    else:
        _L = pairs_list(_txt)
    if len(_L) >= 8:
        coll_data.insert(2 + _i, (_p, _t, _l, _L)); SEO_T[_p] = _ft
# строгий отбор (books/curate.json): ЛГБТ - ни в одну подборку; книги 18+ - не в подборки «всем», для детей, подростков, маме и коллеге
CUR = json.load(open(os.path.join(ROOT, "books", "curate.json"), encoding="utf-8"))
def _curset(name):
    out = []
    for pr in CUR.get(name, []):
        t_, s_ = (pr.split("|") + [""])[:2]
        out.append((nk(t_), nk(s_)))
    return out
_CS = {k: _curset(k) for k in ("adult", "lgbt", "notkids", "notteen")}
def inlist(b, name):
    t_, a_ = nk(b["t"]), nk(b["a"])
    return any((t_ == t or t_.startswith(t)) and s in a_ for t, s in _CS[name])
SAFE = {"knigi-v-podarok-na-novyy-god", "kniga-v-podarok-podrostku", "kniga-v-podarok-kollege", "kniga-v-podarok-mame",
        "chto-pochitat-na-novogodnie-kanikuly", "knigi-dlya-zimnih-vecherov", "uyutnye", "zhanr-kids", "young-adult"}
TEEN = {"zhanr-kids", "young-adult", "kniga-v-podarok-podrostku"}
def curate_ok(b, path):
    if inlist(b, "lgbt"):
        return False
    if path in SAFE and inlist(b, "adult"):
        return False
    if path in TEEN and inlist(b, "notteen"):
        return False
    if path == "zhanr-kids" and inlist(b, "notkids"):
        return False
    return True
_drop = {}
for _p in list(SECTS):
    SECTS[_p] = [(h_, sub_, [b for b in l_ if curate_ok(b, _p) or _drop.setdefault(_p, []).append(b["t"])]) for h_, sub_, l_ in SECTS[_p]]
coll_data = [(p_, t_, l_, [b for b in L_ if curate_ok(b, p_) or _drop.setdefault(p_, []).append(b["t"])]) for p_, t_, l_, L_ in coll_data]
for _p, _l in _drop.items():
    print("  отбор убрал из", _p + ":", ", ".join(dict.fromkeys(_l)))
# в подборках только книги с описанием: карточка без описания никому не помогает выбрать
coll_data = [(p_, t_, l_, [b for b in L_ if b["ann"]]) for p_, t_, l_, L_ in coll_data]
coll_data = [c for c in coll_data if len(c[3]) >= 6]
# у каждой книги из подборок - своя страница (раньше их получали только книги ручного каталога, и «1984» на сайте не находилась)
for _, _, _, L in coll_data:
    for b in L:
        if id(b) in BOOK_URL or not (b["ann"] or img_of(b)):
            continue
        s_ = slug(b["t"] + "-" + str(b["a"] or "").split(" ")[-1])
        while s_ in used:
            s_ += "-2"
        used.add(s_)
        BOOK_URL[id(b)] = f"k/{s_}.html"
        cat_books.append(b)
_aw, _as = [], set()
for b in cat_books + [b for _, _, _, L in coll_data for b in L]:
    if not b["ann"] and _ak(b) not in _as and _ak(b) not in ANNX:
        _as.add(_ak(b)); _aw.append([b["t"], b["a"], _ak(b)])
json.dump(_aw, open(os.path.join(ROOT, "books", "ann_want.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("книг без описания (в очередь на поиск):", len(_aw))
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
QUICK = [p for p in ("chitayut-seychas", "novogodnee-nastroenie", "chto-pochitat-na-novogodnie-kanikuly", "knigi-dlya-zimnih-vecherov", "knigi-v-podarok-na-novyy-god", "romantezi", "dark-roman", "lyubovnye-romany", "young-adult", "zhanr-fantasy", "uyutnye", "zahvatyvayuschie", "strashnye", "smeshnye", "novinki", "zhanr-classic", "zhanr-detective")
         if any(q == p for q, _, _, _ in coll_data)]
tname = lambda p: next(t for q, t, _, _ in coll_data if q == p).split(":")[0]
chips = lambda cur: '<nav class="chips"><a class="find" href="/poisk.html">Найти книгу по жанру и настроению</a>' + "".join(f'<a href="/c/{p}.html"{" class=on" if p == cur else ""}>{esc(tname(p))}</a>' for p in QUICK) + "</nav>"
GIFT_NAV = [("kniga-v-podarok-podruge", "Подруге"), ("kniga-v-podarok-mame", "Маме"), ("kniga-v-podarok-muzhchine", "Мужчине"),
            ("kniga-v-podarok-podrostku", "Подростку"), ("kniga-v-podarok-kollege", "Коллеге"), ("knigi-v-podarok-na-novyy-god", "Всем на Новый год")]
GIFT_NAV = [(p_, t_) for p_, t_ in GIFT_NAV if any(q == p_ for q, _, _, _ in coll_data)]
GIFT_ERID = '<p class="erid gerid">Реклама · Читай-город, erid: 2W5zFJkZEDg · ООО ЛИТРЕС, ИНН 7719571260, erid: 2VfnxyNkZrY</p>'


def BUY(b):  # под книгой в подарочных подборках: сразу купить бумажную или электронную
    qt = urllib.parse.quote(b["t"]); q = urllib.parse.quote(b["t"] + " " + b["a"].split(" ")[-1])
    cg = f"https://www.chitai-gorod.ru/search?phrase={qt}&partnerId=1006702&utm_source=affiliate&utm_medium=cpa&utm_campaign=1006702&sub_3=2W5zFJkZEDg&erid=2W5zFJkZEDg"
    lr = LR_T.replace("{url}", urllib.parse.quote((f"https://www.litres.ru/pages/biblio_book/?art={lit_id(b)}" if lit_id(b) else f"https://www.litres.ru/search/?q={q}"), safe=""))
    g = lambda k: f"try{{ym(114237349,'reachGoal','gift_buy',{{store:'{k}'}})}}catch(e){{}}"
    return (f'<div class="buy"><a href="{cg}" rel="nofollow noopener sponsored" target="_blank" onclick="{g("chitai")}">Купить книгу</a>'
            f'<a href="{lr}" rel="nofollow noopener sponsored" target="_blank" onclick="{g("litres")}">Электронная</a></div>')


def gchips(cur):
    return '<nav class="chips gnav">' + "".join(f'<a href="/c/{p_}.html"{" class=on" if p_ == cur else ""}>{esc(t_)}</a>' for p_, t_ in GIFT_NAV) + "</nav>"


def gcard(b, n, path):
    return f'<div class="gk">{card(b, n, True)}{BUY(b)}</div>' if path in GIFT else card(b, n, True)


for path, title, lead, L in coll_data:
    body = (f'<div class="wrap"><div class="crumbs"><a href="/">Нора</a><span>/</span><a href="/c/">Подборки</a></div>'
            f'<div class="ph"><div><h1>{esc(title)}</h1><p class="lead">{esc(lead)}</p></div><div class="cnt gl">{len(L)} книг</div></div>'
            f'{gchips(path) if path in GIFT else chips(path)}' + ('<nav class="chips whonav">' + "".join(f'<a href="#who{n_}">{esc(h_)}</a>' for n_, (h_, _, _) in enumerate(SECTS[path])) + '</nav>' + "".join(f'<section class="who" id="who{n_}"><h2>{esc(h_)}</h2><p class="lead">{esc(sub_)}</p><div class="grid">{"".join(gcard(b, i + 1, path) for i, b in enumerate(l_))}</div></section>' for n_, (h_, sub_, l_) in enumerate(SECTS[path])) if path in SECTS else f'<div class="grid">{"".join(card(b, i + 1, True) for i, b in enumerate(L))}</div>')
            + (GIFT_ERID if path in GIFT else "")
            + '<div class="hook gl"><div><b>Хочешь ещё таких же?</b><p>Отметь в Норе пару книг из этой подборки - и Шуршуня будет приносить похожие, которых ещё нет на твоей полке.</p></div>'
              '<div class="ctas"><a class="btn" href="/app.html?app=1" onclick="try{ym(114237349,\'reachGoal\',\'site_to_app\')}catch(e){}">Подобрать под мой вкус</a><a class="btn ghost" href="/test.html">Пройти тест</a></div></div>'
            + f'{FINAL}</div>')
    urls.append(page(f"c/{path}.html", title, lead + " " + ", ".join(b["t"] for b in L[:5]) + ".", body, active=f"/c/{path}.html",
                     img=img_of(L[0]) or None, full_title=(SEO_T[path] + " — Нора") if path in SEO_T else None))


def coll_card(p, t, L):
    st = sorted(L[:12], key=lambda b: not img_of(b))[:3]
    return (f'<a class="coll gl" href="/c/{p}.html"><div class="st">{"".join(cv(b) for b in st)}</div><h3>{esc(t.split(":")[0])}</h3>'
            f'<small>{len(L)} книг</small></a>')


urls.append(page("c/index.html", "Подборки книг", "Подборки книг по жанрам, настроениям и странам — от ромэнтези до классики.",
                 '<div class="wrap"><div class="crumbs"><a href="/">Нора</a></div><div class="ph"><div><h1>Подборки книг</h1>'
                 '<p class="lead">По жанрам, настроениям и странам — от ромэнтези до классики.</p></div></div><div style="display:none">'
                 + "</div>" + "".join(shelf(t.split(":")[0], f"/c/{p}.html", "", sorted(L[:24], key=lambda b: not img_of(b))[:14], f"Все {len(L)}") for p, t, lead, L in coll_data)
                 + f"{FINAL}</div>", active="/c/"))

VQ = json.load(open(os.path.join(ROOT, "tools", "voprosy.json"), encoding="utf-8"))
_vq_by = {nk(b["t"]): b for b in reversed(cat_books)}
VQ_BOOKS = [(_vq_by[nk(t)], qs) for t, qs in VQ.items() if nk(t) in _vq_by]
VQ_URL = {id(b): "voprosy/" + BOOK_URL[id(b)].split("/", 1)[1] for b, _ in VQ_BOOKS}


def WHO(b, sim):
    """«Кому понравится»: по настроениям и темам книги и по двум самым близким книгам"""
    tg = [t for t in b["tags"] if not re.search(r"век|страна|премия", t)][:4]
    near = [x for x in sim[:6] if id(x) in BOOK_URL and len(set(x["tags"]) & set(b["tags"])) >= 2][:2]
    if len(tg) < 2 and not near:
        return ""
    out = "<b>Кому понравится.</b> "
    if len(tg) >= 2:
        out += "Тем, кому близко такое: " + ", ".join(esc(t) for t in tg) + ". "
    if near:
        out += "Стоит попробовать, если понравились " + " и ".join(f'<a href="/{BOOK_URL[id(x)]}">«{esc(x["t"])}»</a>' for x in near) + "."
    return f'<p class="who2">{out}</p>'


def VQLINK(b):
    return f'<p class="vql"><a href="/{VQ_URL[id(b)]}">Вопросы для обсуждения этой книги</a></p>' if id(b) in VQ_URL else ""


def HOOK(b):
    """приманка на странице книги: поставить эту книгу на свою полку в Норе (открывает приложение сразу на её карточке)"""
    href = "/app.html?app=1&bk=" + urllib.parse.quote(b["t"] + "|" + b["a"])
    go = 'onclick="try{ym(114237349,\'reachGoal\',\'site_to_app\')}catch(e){}"'
    return (f'<div class="hook gl"><div><b>Не потеряй эту книгу</b><p>Поставь её на свою полку в Норе - и Шуршуня подберёт похожие книги лично тебе. Бесплатно, прямо в браузере.</p></div>'
            f'<div class="ctas"><a class="btn" href="{href}" {go}>Хочу прочитать</a><a class="btn ghost" href="{href}" {go}>Уже прочитано</a></div></div>')


pool = {}
for b in cat_books:
    pool.setdefault(b["g"], []).append(b)
GEN_URL = {g: f"/c/zhanr-{g}.html" for g in GEN}
for b in cat_books:
    tg = set(b["tags"])
    sim = sorted((x for x in pool.get(b["g"], []) if x is not b), key=lambda x: (-len(tg & set(x["tags"])), -(x["q"] or 0), not img_of(x)))[:12]
    u = img_of(b)
    facts = ([f'<a href="{GEN_URL[b["g"]]}">{esc(GEN[b["g"]])}</a>'] if b["g"] in GEN_URL else []) + \
            [f"<span>{esc(x)}</span>" for x in [b["c"], str(b["y"]) if b["y"] and b["y"] > 0 else ""] + b["tags"][:4] if x]
    desc = b["ann"] or f"«{b['t']}», {b['a']}: оценки и отзывы читателей, похожие книги и где прочитать."
    fl = [f for f in b.get("f", [])[:4] if len(f) > 1]
    body = (f'<div class="wrap"><div class="crumbs"><a href="/">Нора</a><span>/</span><a href="{GEN_URL.get(b["g"], "/c/")}">{esc(GEN.get(b["g"], "Книги"))}</a></div>'
            f'<article class="book">{f"<div class=amb style=background-image:url({esc(u)})></div>" if u else ""}<div class="cvw">{cv(b, lazy=False)}</div><div>'
            f'<h1>{esc(b["t"])}</h1><p class="by">{esc(b["a"])}</p>{f'<p class="gn">{esc(gname(b))}</p>' if gname(b) else ""}{RATE(b)}'
            + (f'<p class="ann">{esc(b["ann"])}</p>' if b["ann"] else "") + WHO(b, sim)
            + (f'<div class="fgrid">{"".join(f"<div class=\"fact gl\"><b>{esc(f[0])}</b><span>{esc(f[1])}</span></div>" for f in fl)}</div>' if fl else "")
            + WHERE(b) + HOOK(b) + VQLINK(b) + RVS(b)
            + (f'<section class="like"><div class="shd"><h2>Похожие книги</h2><a class="all" data-sim href="/p/">Ещё похожие</a></div>{rail(sim, bare=True)}</section>' if sim else "")
            + "</div></article>" + REVIEWS_JS
            + "</div>")
    bld = {"@context": "https://schema.org", "@type": "Book", "name": b["t"], "author": {"@type": "Person", "name": b["a"]}, "inLanguage": "ru",
           "url": f"{SITE}/{BOOK_URL[id(b)]}", **({"description": b["ann"]} if b["ann"] else {}), **({"image": (SITE + u) if u.startswith("/") else u} if u else {}),
           **({"datePublished": str(b["y"])} if b["y"] and b["y"] > 0 else {}), **({"genre": GEN[b["g"]]} if b["g"] in GEN else {})}
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "Нора", "item": SITE + "/"},
              {"@type": "ListItem", "position": 2, "name": GEN.get(b["g"], "Книги"), "item": SITE + GEN_URL.get(b["g"], "/c/")}, {"@type": "ListItem", "position": 3, "name": b["t"]}]}
    urls.append(page(BOOK_URL[id(b)], f"«{b['t']}», {b['a']}: о чём книга и что почитать похожее", desc, body, img=u or None, ld=[bld, crumbs]))

# ---------- «Книги, похожие на…»: страницы под поисковые запросы «что почитать после X» ----------
TROPE_RU = dict(re.findall(r'\["(\w+)","([^"]+)"\]', app[app.index("const B_TROPE="):app.index("];", app.index("const B_TROPE="))]))
GENERIC = {"любовь", "романтичное", "атмосферное", "грустное", "женская судьба", "большой город", "взросление", "психологический роман", "интеллектуальное",
           "философский роман", "приключения", "светлое", "тёплое", "мрачное", "динамичное", "напряжённое", "смешное", "медленное", "история", "семья", "дружба",
           "социальный роман", "классика", "магия", "мистика", "жутковатое", "уют", "детектив", "триллер", "психология", "самиздат"}
lab = lambda t: TROPE_RU.get(t[5:], t[5:]).lower() if t.startswith("троп:") else t
LOVEY = lambda b: has(b, "любовное фэнтези", "любовный роман", "ромэнтези") or (love(b) and any(t.startswith("троп:") for t in b["tags"]))
SEQ = re.compile(r"(книга|том|часть)\s*\d|\b\d+\s*$|–\s*\d|-\s*\d+\s*$", re.I)
SPOOL = [b for b in books if (b["q"] or 0) >= 2 and len(b["tags"]) >= 2 and (b["ann"] or img_of(b)) and not notnovel(b) and "самиздат" not in b["tags"] and not SEQ.search(b["t"])]
print("книг для «похожих»:", len(SPOOL))


def simscore(a, x):
    if x is a or nk(x["t"]) == nk(a["t"]) or SER(x) == SER(a):
        return None, []
    ta, tx = set(a["tags"]), set(x["tags"])
    sh = sorted(ta & tx)   # в одном и том же порядке при каждой сборке, иначе сотни страниц меняются без причины
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


SEQ = re.compile(r"(книга|том|часть)\s*\d|\b\d+\s*$|–\s*\d|-\s*\d+\s*$", re.I)
SER = lambda b: nk(b["a"]) + "|" + nk(re.split(r"[.:—–(]|\s\d|\sкнига|\sтом", b["t"].lower())[0])
seeds = [b for b in books if ((b["q"] or 0) >= 3 or ((b["q"] or 0) >= 2 and (LOVEY(b) or b["g"] == "fantasy"))) and (b["y"] or 0) >= 1980 and not notnovel(b)
         and len(b["tags"]) >= 3 and (img_of(b) or b["ann"]) and "самиздат" not in b["tags"] and not SEQ.search(b["t"])]
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
    inner = (cv(x) + f'<div class="t">{esc(x["t"])}</div><div class="a">{esc(meta)}</div>'
             + (f'<p class="why">Тоже: {esc(w)}</p>' if w else "") + (f'<p>{esc(ann)}</p>' if ann else ""))
    return f'<a class="bk" href="/{u}">{inner}</a>' if u else f'<div class="bk">{inner}</div>'


for a_, out in sim_pages:
    au_ = a_["a"]
    tops = ", ".join(f"«{x['t']}»" for x, _ in out[:4])
    lead = f"Если понравилась «{a_['t']}» ({au_}), вот книги с похожим настроением и сюжетом. Шуршуня подобрал их по жанру, тропам и отзывам читателей." 
    back = BOOK_URL.get(id(a_))
    body = (f'<div class="wrap"><div class="crumbs"><a href="/">Нора</a><span>/</span><a href="/p/">Что почитать после</a></div>'
            f'<div class="ph"><div><h1>Книги, похожие на «{esc(a_["t"])}»</h1><p class="lead">{esc(lead)}</p>'
            + (f'<p class="lead" style="margin-top:8px"><a href="/{back}">О книге «{esc(a_["t"])}»</a></p>' if back else "")
            + f'</div></div>'
            f'<div class="grid">{"".join(sim_card(x, w, i + 1) for i, (x, w) in enumerate(out))}</div>{FINAL}</div>')
    urls.append(page(SIM_URL[id(a_)], f"Книги, похожие на «{a_['t']}»",
                     f"Что почитать после «{a_['t']}» ({au_}): {', '.join(x['t'] for x, _ in out[:6])} и ещё {max(0, len(out) - 6)} похожих книг.", body,
                     full_title=f"Книги, похожие на «{a_['t']}» ({a_['a'].split(' ')[-1]}): что почитать после — Нора", img=img_of(a_) or None))

# ссылка «Ещё похожие» на странице книги — на страницу «Книги, похожие на…», если она есть
SIMB = {BOOK_URL[id(a_)]: SIM_URL[id(a_)] for a_, _ in sim_pages if id(a_) in BOOK_URL}
for b in cat_books:
    fp = os.path.join(ROOT, BOOK_URL[id(b)])
    h = open(fp, encoding="utf-8").read()
    su = SIMB.get(BOOK_URL[id(b)])
    h = h.replace('<a class="all" data-sim href="/p/">Ещё похожие</a>', f'<a class="all" href="/{su}">Ещё похожие</a>' if su else "")
    open(fp, "w", encoding="utf-8").write(dash(h))
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
                 f'<div class="wrap"><div class="crumbs"><a href="/">Нора</a></div><div class="ph"><div><h1>Что почитать после любимой книги</h1>'
                 f'<p class="lead">Выбери книгу, которая понравилась, — Шуршуня покажет похожие по настроению и сюжетным ходам.</p></div></div>{toc}{FINAL}</div>', active="/p/"))
print("страниц «похожие на»:", len(sim_pages))

# индекс для поиска на сайте: книги со своей страницей и страницы «похожие на…»
SIDX, sseen = [], set()
for b in cat_books:
    k = nk(b["t"]) + "|" + nk(b["a"])
    if k not in sseen:
        sseen.add(k); SIDX.append([b["t"], b["a"], "/" + BOOK_URL[id(b)], b["y"] or ""])
for a_, _ in sim_pages:
    k = nk(a_["t"]) + "|" + nk(a_["a"])
    if k not in sseen:
        sseen.add(k); SIDX.append([a_["t"], a_["a"], "/" + SIM_URL[id(a_)], "похожие"])
json.dump(SIDX, open(os.path.join(ROOT, "books", "search.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
# «Найти книгу»: фильтры по жанру и настроению, как в приложении
MOODS = [("fun", "Смешное", ("юмор", "смешное", "сатира")), ("cozy", "Уютное", ("уют", "тёплое", "светлое")), ("scary", "Страшное", ("хоррор", "жутковатое", "мистика", "готика")),
         ("sad", "Трогательное", ("грустное",)), ("page", "Не оторваться", ("напряжённое", "динамичное", "триллер")), ("deep", "Заставляет задуматься", ("философский роман", "интеллектуальное", "антиутопия")),
         ("love", "Про любовь", ("любовь", "романтичное", "ромэнтези", "любовный роман")), ("magic", "Магия и драконы", ("магия", "драконы")), ("short", "На один вечер", ())]
FL = []
for b in cat_books:
    if id(b) not in BOOK_URL:
        continue
    pal = PAL.get(b["g"], PAL["modern"]); c_ = pal[hsh(b["t"]) % len(pal)]
    light = int(c_[1:3], 16) + int(c_[3:5], 16) + int(c_[5:7], 16) > 450
    f_ = "#3A2A1C" if light else ("#F1E2C2" if hsh(b["a"]) % 2 else "#E2B66B")
    md = "".join(k for k, _, tg_ in MOODS if (has(b, *tg_) if tg_ else 0 < (b.get("pg") or 0) <= 260))
    FL.append([b["t"], b["a"], "/" + BOOK_URL[id(b)], b["y"] if b["y"] and b["y"] > 0 else "", gname(b), b["g"], c_, f_, img_of(b), md, b["q"] or 0])
FL.sort(key=lambda r: (-r[10], not r[8]))
json.dump(FL, open(os.path.join(ROOT, "books", "filter.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
_GL = sorted({r[4] for r in FL if r[4]}, key=lambda g: -sum(1 for r in FL if r[4] == g))
FIND_JS = ("<script>(function(){var MO=" + json.dumps(MOTIF, ensure_ascii=False) + r""",G="",M="",Q="",D=null;""" + FUZ_JS + r"""var _x=0,box=document.getElementById("fres"),cnt=document.getElementById("fcnt");
function esc(s){return String(s).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]})}
function nm(s){return String(s||"").toLowerCase().replace(/ё/g,"е")}
function card(r){var im=r[8]?'<img src="'+esc(r[8])+'" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer" onerror="this.remove()">':"";
 return '<a class="bk" href="'+r[2]+'"><div class="cv" style="--c:'+r[6]+';--f:'+r[7]+'">'+im+'<b>'+esc(r[0])+'</b><svg class="m" viewBox="0 0 100 100">'+(MO[r[5]]||MO.modern)+'</svg><i>'+esc(r[1])+'</i></div><div class="t">'+esc(r[0])+'</div><div class="a">'+esc(r[1])+(r[4]?' · '+esc(r[4]):'')+'</div></a>'}
function draw(){if(!D)return;var F=D.filter(function(r){return (!G||r[4]===G)&&(!M||r[9].indexOf(M)>=0)}),L=F;
 if(NM(Q).length>=2){var W=F.map(function(r){return NM(r[0]+" "+r[1]).split(" ")});L=FIND(F,function(i){return W[i]},Q,200).map(function(i){return F[i]})}
 cnt.textContent=L.length?"":"Ничего не нашлось - попробуй убрать один из фильтров";box.innerHTML=L.slice(0,60).map(card).join("")}
document.querySelectorAll("[data-g]").forEach(function(b){b.onclick=function(){G=G===b.dataset.g?"":b.dataset.g;document.querySelectorAll("[data-g]").forEach(function(x){x.classList.toggle("on",x.dataset.g===G)});draw()}});
document.querySelectorAll("[data-m]").forEach(function(b){b.onclick=function(){M=M===b.dataset.m?"":b.dataset.m;document.querySelectorAll("[data-m]").forEach(function(x){x.classList.toggle("on",x.dataset.m===M)});draw()}});
var qi=document.getElementById("fq");qi.oninput=function(){Q=qi.value;draw()};
fetch("/books/filter.json").then(function(r){return r.json()}).then(function(d){D=d;draw()})})()</script>""")
find_body = (f'<div class="wrap"><div class="crumbs"><a href="/">Нора</a></div><div class="ph"><div><h1>Найти книгу</h1>'
             f'<p class="lead">Выбери жанр и настроение - Шуршуня покажет, что подойдёт.</p></div></div>'
             f'<div class="sbox gl">{ic("search")}<input id="fq" type="search" placeholder="Название или автор" autocomplete="off" enterkeyhint="search"></div>'
             f'<h3 class="fh">Жанр</h3><div class="fchips">' + "".join(f'<button data-g="{esc(g)}">{esc(g)}</button>' for g in _GL[:14]) + '</div>'
             f'<h3 class="fh">Настроение</h3><div class="fchips">' + "".join(f'<button data-m="{k}">{esc(n_)}</button>' for k, n_, _ in MOODS) + '</div>'
             f'<p class="fcnt" id="fcnt"></p><div class="grid" id="fres"></div>{FINAL}</div>' + FIND_JS)
urls.append(page("poisk.html", "Найти книгу по жанру и настроению", "Подбор книг по жанру и настроению: смешные, уютные, страшные, трогательные, на один вечер и другие.", find_body))
print("в поиске сайта:", len(SIDX))

# ---------- книжный клуб: страница для поисковиков ----------
CLUB_TG = BOT + "?startapp=club"
CLUB_WEB = "/app.html?app=1&club=1"
CLUB_CTA = f'<div class="ctas"><a class="btn" href="{CLUB_WEB}">Создать клуб</a></div>'
_cl_t = ["Маленькая жизнь", "Тайная история", "Щегол", "Нормальные люди", "Сто лет одиночества", "Зулейха открывает глаза", "Убить пересмешника",
         "Цветы для Элджернона", "Над пропастью во ржи", "Мастер и Маргарита", "Бегущий за ветром", "Книжный вор", "Дом, в котором…", "Пикник на обочине", "Шантарам", "Вино из одуванчиков"]
_cl_by = {}
for b in cat_books:
    k = nk(b["t"])
    if k in {nk(x) for x in _cl_t} and k not in _cl_by:
        _cl_by[k] = b
CLUB_BOOKS = sorted([_cl_by[nk(x)] for x in _cl_t if nk(x) in _cl_by], key=lambda b: not img_of(b))
CLUB_STEPS = [("Создай клуб", "Придумай название - у клуба появится своя печать."),
              ("Позови друзей", "Отправь ссылку в любой мессенджер или позови друзей прямо из Норы."),
              ("Выберите книгу", "Каждый может предложить книгу, а потом голосуете за понравившуюся. Книги, которые кто-то в клубе уже читал, Шуршуня видит и предлагает не брать."),
              ("Читайте к общему сроку", "В Норе видно, кто на каком этапе книги."),
              ("Обсуждайте", "Шуршуня готовит вопросы к книге, можно добавить свои - все вопросы видны в клубе. Каждый отмечает, когда удобно встретиться, лучшее время Нора показывает сама, а Шуршуня напомнит о встрече."),
              ("Соберите полку клуба", "Прочитанное встаёт на общую полку с оценкой клуба. Можно соревноваться с другими клубами.")]
CLUB_TIPS = ["Оптимально 4-10 человек: всем хватает времени высказаться.",
             "Ритм - одна книга в 3-4 недели. Слишком быстро - кто-то не успеет, слишком медленно - пропадёт азарт.",
             "Выбирайте книгу голосованием.",
             "Договоритесь о встрече заранее: онлайн-созвон, кафе или дома у кого-то из клуба - Шуршуня напомнит о встрече.",
             "Готовьте 3-5 вопросов к книге - разговор пойдёт сам. Начните с простого: что понравилось и что раздражало."]
CLUB_Q = ["Что зацепило тебя на первых страницах?", "Кому из героев ты веришь, а кому нет?", "Чей поступок труднее всего оправдать?",
          "Какая сцена запомнилась сильнее всего - и почему?", "Изменилось ли твоё отношение к главному герою к концу книги?",
          "Понравился ли тебе финал? Каким он мог бы быть ещё?", "Что из этой книги останется с тобой надолго?",
          "Кому ты посоветуешь эту книгу, а кому - нет?", "Хочется ли читать этого автора дальше?"]
CLUB_FAQ = [("Это бесплатно?", "Да. Создать клуб, позвать друзей, голосовать за книги и вести полку клуба можно бесплатно."),
            ("Где клуб общается?", "Прямо в Норе: книга, вопросы к ней, голосование и время встречи - всё в клубе. А напоминания о сроках и встречах Шуршуня присылает каждому участнику."),
            ("Сколько человек может быть в клубе?", "Ограничений нет. Для живого обсуждения лучше всего 4-10 человек."),
            ("Чем Нора помогает, кроме клуба?", "Нора хранит твои книжные полки, переносит прочитанное из Литрес, Яндекс Книг и LiveLib, а Шуршуня подбирает книги под твой вкус.")]
club_body = ('<div class="wrap"><div class="crumbs"><a href="/">Нора</a></div><div class="ph"><div><h1>Книжный клуб онлайн с друзьями</h1>'
             '<p class="lead">Одна книга на всех, общий срок, голосование за следующую книгу, вопросы для обсуждения и полка прочитанного вместе. Бесплатно - в приложении.</p></div></div>'
             + CLUB_CTA + '<div class="legal">'
             + "<section class='gl'><h2>Как устроен книжный клуб в Норе</h2><ol>" + "".join(f"<li><b>{esc(h)}.</b> {esc(t)}</li>" for h, t in CLUB_STEPS) + "</ol></section>"
             + "<section class='gl'><h2>Как организовать книжный клуб</h2><ul>" + "".join(f"<li>{esc(t)}</li>" for t in CLUB_TIPS) + "</ul></section>"
             + "<section class='gl'><h2>Вопросы для обсуждения книги</h2><p>Подходят почти к любому роману - Шуршуня подбирает такие вопросы к каждой книге клуба.</p><ul>"
             + "".join(f"<li>{esc(q)}</li>" for q in CLUB_Q) + '</ul><p><a href="/voprosy/">Готовые вопросы к популярным книгам</a></p></section></div>'
             + '<div class="clubsh">' + (shelf("Что почитать с книжным клубом", "/c/", "Книги, о которых хочется спорить и говорить после последней страницы.", CLUB_BOOKS[:14]) if len(CLUB_BOOKS) >= 4 else "") + '</div>'
             + '<div class="legal">' + "".join(f"<section class='gl'><h2>{esc(q)}</h2><p>{esc(a)}</p></section>" for q, a in CLUB_FAQ)
             + f'<section class="gl clubend"><h2>Соберите свой книжный клуб</h2><p>Создай клуб за минуту и позови друзей ссылкой.</p>{CLUB_CTA}</section></div></div>')
CLUB_LD = [{"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in CLUB_FAQ]},
           {"@context": "https://schema.org", "@type": "HowTo", "name": "Как создать книжный клуб с друзьями", "step": [{"@type": "HowToStep", "name": h, "text": t} for h, t in CLUB_STEPS]}]
urls.append(page("knizhnyy-klub.html", "Книжный клуб онлайн с друзьями",
                 "Создай книжный клуб с друзьями в Норе: голосование за книгу, общий срок, вопросы для обсуждения и общая полка клуба. Бесплатно, в приложении.",
                 club_body, full_title="Книжный клуб онлайн: создать с друзьями, вопросы для обсуждения книги — Нора", ld=CLUB_LD))

# ---------- вопросы для обсуждения книг: страницы под запрос «вопросы для обсуждения книги ...» ----------
VQ_HOW = ["Начните с простого: кому понравилось, кому нет и почему - это разогревает разговор.",
          "Не идите по списку подряд. Выберите три-четыре вопроса, которые зацепили, остальные оставьте про запас.",
          "Спорьте с книгой, а не друг с другом: «мне показалось» вместо «ты не понял».",
          "Закончите вопросом: кому вы посоветуете эту книгу, а кому - нет."]
def vq_card(b):
    return f'<a class="bk" href="/{VQ_URL[id(b)]}">{cv(b)}<div class="t">{esc(b["t"])}</div><div class="a">вопросы для обсуждения</div></a>'
for n_, (b, qs) in enumerate(VQ_BOOKS):
    others = [x for x, _ in VQ_BOOKS if x is not b]
    near = sorted(others, key=lambda x: (x["g"] != b["g"], -len(set(x["tags"]) & set(b["tags"]))))[:10]
    go = 'onclick="try{ym(114237349,\'reachGoal\',\'site_to_app\')}catch(e){}"'
    body = (f'<div class="wrap"><div class="crumbs"><a href="/">Нора</a><span>/</span><a href="/voprosy/">Вопросы для обсуждения</a></div>'
            f'<div class="ph"><div><h1>«{esc(b["t"])}»: вопросы для обсуждения</h1>'
            f'<p class="lead">{esc(b["a"])}. {len(qs)} вопросов для книжного клуба, разговора с друзьями или урока. Осторожно: вопросы раскрывают сюжет.</p></div></div>'
            f'<div class="legal"><section class="gl"><h2>Вопросы к книге</h2><ol>' + "".join(f"<li>{esc(q)}</li>" for q in qs) + '</ol></section>'
            + (f'<section class="gl"><h2>О чём книга</h2><p>{esc(b["ann"])}</p><p><a href="/{BOOK_URL[id(b)]}">Оценки, отзывы и где прочитать</a></p></section>' if b["ann"] else "")
            + f'<section class="gl"><h2>Как провести обсуждение</h2><ul>' + "".join(f"<li>{esc(x)}</li>" for x in VQ_HOW) + '</ul></section></div>'
            + f'<div class="hook gl"><div><b>Обсудите эту книгу своим клубом</b><p>В Норе клуб выбирает книгу голосованием, читает к общему сроку и получает вопросы для разговора. Бесплатно, прямо в браузере.</p></div>'
              f'<div class="ctas"><a class="btn" href="{CLUB_WEB}" {go}>Создать клуб</a><a class="btn ghost" href="/knizhnyy-klub.html">Как это устроено</a></div></div>'
            + f'<section class="shelf"><div class="shd"><h2>Вопросы к другим книгам</h2><a class="all" href="/voprosy/">Все</a></div><div class="rail bare">' + "".join(vq_card(x) for x in near) + '</div></section></div>')
    ld = [{"@context": "https://schema.org", "@type": "Article", "headline": f"«{b['t']}»: вопросы для обсуждения", "about": {"@type": "Book", "name": b["t"], "author": {"@type": "Person", "name": b["a"]}},
           "inLanguage": "ru", "publisher": {"@type": "Organization", "name": "Нора"}}]
    urls.append(page(VQ_URL[id(b)], f"«{b['t']}» - вопросы для обсуждения книги",
                     f"Вопросы для обсуждения книги «{b['t']}» ({b['a']}): {qs[0]} {qs[1]}", body,
                     full_title=f"«{b['t']}», {b['a'].split(' ')[-1]}: вопросы для обсуждения книги в книжном клубе — Нора", img=img_of(b) or None, ld=ld))
vq_idx = ('<div class="wrap"><div class="crumbs"><a href="/">Нора</a></div><div class="ph"><div><h1>Вопросы для обсуждения книг</h1>'
          '<p class="lead">Готовые вопросы к популярным книгам - для книжного клуба, встречи с друзьями или урока литературы.</p></div></div>'
          '<div class="grid">' + "".join(vq_card(b) for b, _ in VQ_BOOKS) + '</div>' + f'<section class="final gl"><h2>Соберите свой книжный клуб</h2><p>Голосование за книгу, общий срок и вопросы для разговора - в Норе.</p>{CLUB_CTA}</section></div>')
urls.append(page("voprosy/index.html", "Вопросы для обсуждения книг", "Готовые вопросы для обсуждения популярных книг: «Мастер и Маргарита», «1984», «Тайная история» и другие - для книжного клуба и друзей.", vq_idx,
                 full_title="Вопросы для обсуждения книг в книжном клубе — Нора"))
print("страниц с вопросами:", len(VQ_BOOKS))

# вопросы - ещё и в приложение: клуб, который читает эту книгу, получает их вместо общих
json.dump(VQ, open(os.path.join(ROOT, "books", "voprosy.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

# ---------- в каком порядке читать серию ----------
SERIES = [
    ("empirey-yarros", "«Эмпирей» Ребекки Яррос", "Ребекка Яррос", "Цикл о военной академии Басгиат и всадниках драконов. Читать строго по порядку выхода: каждая книга начинается там, где закончилась предыдущая. Автор обещала пять книг - вышло три.",
     [("Четвёртое крыло", 2023, ""), ("Железное пламя", 2023, ""), ("Ониксовый шторм", 2025, "")]),
    ("korolevstvo-shipov-i-roz-maas", "«Королевство шипов и роз» Сары Дж. Маас", "Сара Дж. Маас", "История Фейры и Дворов фэйри. Первые три книги - основная трилогия, четвёртая - короткая повесть-мостик, пятая рассказывает уже о Несте и Кассиане.",
     [("Королевство шипов и роз", 2015, ""), ("Королевство гнева и тумана", 2016, "встречается и под названием «Королевство тумана и ярости»"), ("Королевство крыльев и руин", 2017, ""),
      ("Королевство стужи и звёздного света", 2018, "небольшая повесть между трилогией и следующим романом"), ("Королевство серебряного пламени", 2021, "главные герои - Неста и Кассиан")]),
    ("garri-potter", "«Гарри Поттер» Джоан Роулинг", "Джоан Роулинг", "Семь книг - семь лет в Хогвартсе. Читать по порядку: герои взрослеют вместе с читателем, а история становится темнее с каждым томом.",
     [("Гарри Поттер и философский камень", 1997, ""), ("Гарри Поттер и Тайная комната", 1998, ""), ("Гарри Поттер и узник Азкабана", 1999, ""), ("Гарри Поттер и Кубок огня", 2000, ""),
      ("Гарри Поттер и Орден Феникса", 2003, ""), ("Гарри Поттер и Принц-полукровка", 2005, ""), ("Гарри Поттер и Дары Смерти", 2007, "")]),
    ("vedmak-sapkovskiy", "«Ведьмак» Анджея Сапковского", "Анджей Сапковский", "Начинать нужно с двух сборников рассказов - в них завязка всей саги и знакомство с Геральтом, Йеннифэр и Цири. Дальше идут пять романов, а «Сезон гроз» - отдельная история, которую лучше читать последней.",
     [("Последнее желание", 1993, "сборник рассказов, с него начинается всё"), ("Меч Предназначения", 1992, "сборник рассказов"), ("Кровь эльфов", 1994, "первый роман саги"), ("Час Презрения", 1995, ""),
      ("Крещение огнём", 1996, ""), ("Башня Ласточки", 1997, ""), ("Владычица Озера", 1999, "финал саги"), ("Сезон гроз", 2013, "отдельный роман о более ранних событиях")]),
    ("golodnye-igry-kollinz", "«Голодные игры» Сьюзен Коллинз", "Сьюзен Коллинз", "Сначала трилогия о Китнисс, потом приквелы: они рассказывают о прошлом Панема и раскрывают то, что в трилогии остаётся загадкой.",
     [("Голодные игры", 2008, ""), ("И вспыхнет пламя", 2009, ""), ("Сойка-пересмешница", 2010, ""), ("Баллада о змеях и певчих птицах", 2020, "приквел о молодом Сноу"), ("Рассвет жатвы", 2025, "приквел о Хеймитче")]),
    ("pesn-lda-i-plameni-martin", "«Песнь льда и пламени» Джорджа Мартина", "Джордж Р. Р. Мартин", "Пять вышедших романов читаются по порядку. Цикл не закончен: шестую книгу, «Ветра зимы», автор пишет много лет.",
     [("Игра престолов", 1996, ""), ("Битва королей", 1998, ""), ("Буря мечей", 2000, ""), ("Пир стервятников", 2005, ""), ("Танец с драконами", 2011, "")]),
    ("sredizemye-tolkin", "Книги Толкина о Средиземье", "Джон Р. Р. Толкин", "Проще всего начать с «Хоббита», потом читать три части «Властелина колец», а «Сильмариллион» оставить напоследок: это предыстория мира, написанная как свод легенд.",
     [("Хоббит, или Туда и обратно", 1937, ""), ("Братство Кольца", 1954, "первая часть «Властелина колец»"), ("Две крепости", 1954, "вторая часть"), ("Возвращение короля", 1955, "третья часть"), ("Сильмариллион", 1977, "предыстория Средиземья")]),
    ("hroniki-narnii-lyuis", "«Хроники Нарнии» Клайва Льюиса", "Клайв Стейплз Льюис", "Есть два порядка. Мы советуем тот, в котором книги выходили: так тайны Нарнии раскрываются постепенно. По времени действия первой идёт «Племянник чародея».",
     [("Лев, колдунья и платяной шкаф", 1950, ""), ("Принц Каспиан", 1951, ""), ("Покоритель зари, или Плавание на край света", 1952, ""), ("Серебряное кресло", 1953, ""),
      ("Конь и его мальчик", 1954, ""), ("Племянник чародея", 1955, "о том, как появилась Нарния"), ("Последняя битва", 1956, "")]),
    ("grishavers-barduго".replace("го", "go"), "Гришаверс Ли Бардуго", "Ли Бардуго", "Три истории в одном мире. Начать можно с трилогии «Тень и кость» или сразу с дилогии «Шестёрка воронов» - она понятна и без трилогии. «Король шрамов» читают последним: в нём сходятся герои обеих историй.",
     [("Тень и кость", 2012, "трилогия, книга 1"), ("Штурм и буря", 2013, "трилогия, книга 2"), ("Крах и восход", 2014, "трилогия, книга 3"), ("Шестёрка воронов", 2015, "дилогия, книга 1"),
      ("Продажное королевство", 2016, "дилогия, книга 2"), ("Король шрамов", 2019, "дилогия о Николае, книга 1"), ("Правление волков", 2021, "дилогия о Николае, книга 2")]),
    ("sumerki-mayer", "«Сумерки» Стефани Майер", "Стефани Майер", "Четыре романа читаются по порядку. «Солнце полуночи» - первая книга, рассказанная от лица Эдварда: её читают после всей саги.",
     [("Сумерки", 2005, ""), ("Новолуние", 2006, ""), ("Затмение", 2007, ""), ("Рассвет", 2008, ""), ("Солнце полуночи", 2020, "события первой книги глазами Эдварда")]),
    ("dyuna-herbert", "«Дюна» Фрэнка Герберта", "Фрэнк Герберт", "Шесть романов самого Герберта читаются по порядку. Первые три - история Пола Атрейдеса и его детей, дальше действие уходит на тысячи лет вперёд.",
     [("Дюна", 1965, ""), ("Мессия Дюны", 1969, ""), ("Дети Дюны", 1976, ""), ("Бог-император Дюны", 1981, ""), ("Еретики Дюны", 1984, ""), ("Капитул Дюны", 1985, "")]),
    ("vozdushnyy-narod-blek", "«Воздушный народ» Холли Блэк", "Холли Блэк", "Трилогия о Джуд и принце Кардане читается по порядку выхода.",
     [("Жестокий принц", 2018, ""), ("Злой король", 2019, ""), ("Королева ничего", 2019, "")]),
]
_bt = {}
for b in cat_books:
    _bt.setdefault(nk(b["t"]), b)
_bt.setdefault(nk("Королевство гнева и тумана"), _bt.get(nk("Королевство тумана и ярости")))
def ser_row(i, t, y, note):
    b = _bt.get(nk(t))
    name = f'<a href="/{BOOK_URL[id(b)]}">{esc(t)}</a>' if b is not None and id(b) in BOOK_URL else esc(t)
    return f'<li><b>{name}</b> <span class="yr">{y}</span>' + (f'<br><span class="nt">{esc(note)}</span>' if note else "") + "</li>"
SER_URL = [(f"poryadok/{sl}.html", ti) for sl, ti, *_ in SERIES]
for sl, ti, au, intro, L in SERIES:
    first = _bt.get(nk(L[0][0]))
    href = "/app.html?app=1" + ("&bk=" + urllib.parse.quote(first["t"] + "|" + first["a"]) if first is not None else "")
    go = 'onclick="try{ym(114237349,\'reachGoal\',\'site_to_app\')}catch(e){}"'
    cov = [b for b in (_bt.get(nk(t)) for t, _, _ in L) if b is not None and id(b) in BOOK_URL]
    body = (f'<div class="wrap"><div class="crumbs"><a href="/">Нора</a><span>/</span><a href="/poryadok/">Порядок чтения</a></div>'
            f'<div class="ph"><div><h1>{esc(ti)}: в каком порядке читать</h1><p class="lead">{esc(intro)}</p></div></div>'
            f'<div class="legal"><section class="gl"><h2>Порядок чтения</h2><ol class="ser">' + "".join(ser_row(i, *x) for i, x in enumerate(L)) + '</ol></section></div>'
            f'<div class="hook gl"><div><b>Отмечай прочитанные части</b><p>В Норе видно, что из серии уже прочитано и что дальше. А когда серия закончится, Шуршуня подберёт похожую. Бесплатно, прямо в браузере.</p></div>'
            f'<div class="ctas"><a class="btn" href="{href}" {go}>Начать с первой книги</a></div></div>'
            + (f'<section class="shelf"><div class="shd"><h2>Книги серии</h2></div>{rail(cov, bare=True)}</section>' if len(cov) >= 2 else "")
            + '<section class="shelf"><div class="shd"><h2>Другие серии</h2><a class="all" href="/poryadok/">Все</a></div><div class="fchips">'
            + "".join(f'<a href="/{u}">{esc(t2)}</a>' for u, t2 in SER_URL if u != f"poryadok/{sl}.html") + '</div></section></div>')
    ld = [{"@context": "https://schema.org", "@type": "ItemList", "name": f"{ti}: порядок чтения", "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": t} for i, (t, _, _) in enumerate(L)]}]
    urls.append(page(f"poryadok/{sl}.html", f"{ti}: в каком порядке читать", f"{ti} - порядок чтения книг: " + ", ".join(t for t, _, _ in L) + ". " + intro, body,
                     full_title=f"{ti}: в каком порядке читать книги — Нора", ld=ld))
urls.append(page("poryadok/index.html", "В каком порядке читать серии книг", "Порядок чтения популярных книжных серий: «Гарри Поттер», «Ведьмак», «Королевство шипов и роз», «Эмпирей» и другие.",
                 '<div class="wrap"><div class="crumbs"><a href="/">Нора</a></div><div class="ph"><div><h1>В каком порядке читать</h1><p class="lead">Популярные серии: с какой книги начать и что читать дальше.</p></div></div>'
                 '<div class="legal">' + "".join(f'<section class="gl"><h2><a href="/{u}">{esc(t2)}</a></h2></section>' for u, t2 in SER_URL) + f'</div>{FINAL}</div>',
                 full_title="В каком порядке читать книжные серии — Нора"))

# ---------- тест «Какая книга тебе сейчас подойдёт» ----------
TEST_JS = r"""<script>(function(){var A={},D=null,S=document.getElementById("tst"),Q=[
["Какое сейчас настроение?",[["fun","Для хорошего настроения"],["cozy","Хочу уюта"],["page","Чтобы не оторваться"],["love","Про любовь"],["deep","Подумать о важном"],["scary","Пощекотать нервы"]]],
["Какой жанр ближе?",[["fantasy","Фэнтези"],["detective","Детектив"],["modern","Современная проза"],["classic","Классика"],["scifi","Фантастика"],["","Неважно"]]],
["Насколько известную книгу?",[["hit","Проверенный хит"],["new","Что-то менее очевидное"],["","Неважно"]]]],i=0;
function esc(s){return String(s).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]})}
function card(r){var im=r[8]?'<img src="'+esc(r[8])+'" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.remove()">':"";
 return '<a class="bk" href="'+r[2]+'"><div class="cv" style="--c:'+r[6]+';--f:'+r[7]+'">'+im+'<b>'+esc(r[0])+'</b><i>'+esc(r[1])+'</i></div><div class="t">'+esc(r[0])+'</div><div class="a">'+esc(r[1])+'</div></a>'}
function step(){if(i>=Q.length)return res();var q=Q[i];S.innerHTML='<p class="tn">Вопрос '+(i+1)+' из '+Q.length+'</p><h2>'+q[0]+'</h2><div class="tq">'+q[1].map(function(o,j){return '<button data-j="'+j+'">'+o[1]+'</button>'}).join("")+'</div>';
 S.querySelectorAll("button").forEach(function(b){b.onclick=function(){A[i]=q[1][+b.dataset.j][0];i++;step()}})}
function res(){if(!D){S.innerHTML='<p class="tn">Подбираю…</p>';return setTimeout(res,300)}
 var f=function(g,h){return D.filter(function(r){return (!A[0]||r[9].indexOf(A[0])>=0)&&(!g||r[5]===g)&&(!h||(h==="hit"?r[10]>=4:r[10]<4))&&r[8]})};
 var L=f(A[1],A[2]);if(L.length<4)L=f(A[1],"");if(L.length<4)L=f("","");var d=new Date(),sd=d.getDate()+d.getMonth()*31;L=L.map(function(r,k){return [((k*7919+sd*104729)%1009),r]}).sort(function(a,b){return a[0]-b[0]}).slice(0,6).map(function(x){return x[1]});
 var bk=L[0]?"&bk="+encodeURIComponent(L[0][0]+"|"+L[0][1]):"";try{ym(114237349,"reachGoal","test_done")}catch(e){}
 S.innerHTML='<h2>Тебе подойдут эти книги</h2><div class="grid">'+L.map(card).join("")+'</div><div class="hook gl"><div><b>Сохрани подборку</b><p>Поставь книги на свою полку в Норе - и Шуршуня будет подбирать такие же каждый день, уже зная твой вкус.</p></div><div class="ctas"><a class="btn" href="/app.html?app=1'+bk+'" onclick="try{ym(114237349,\'reachGoal\',\'site_to_app\')}catch(e){}">Открыть в Норе</a><button class="btn ghost" id="tagain">Пройти ещё раз</button></div></div>';
 document.getElementById("tagain").onclick=function(){i=0;A={};step()}}
fetch("/books/filter.json").then(function(r){return r.json()}).then(function(d){D=d});step()})()</script>"""
urls.append(page("test.html", "Тест: какая книга тебе сейчас подойдёт", "Три вопроса - и подборка книг под твоё настроение: смешные, уютные, захватывающие, про любовь. Без регистрации.",
                 '<div class="wrap"><div class="crumbs"><a href="/">Нора</a></div><div class="ph"><div><h1>Какая книга тебе сейчас подойдёт</h1><p class="lead">Три вопроса - и подборка под твоё настроение.</p></div></div>'
                 '<div class="tst gl" id="tst"></div></div>' + TEST_JS, full_title="Тест: какую книгу почитать - подбор по настроению — Нора"))

# ---------- итоги года: страница-приглашение ----------
urls.append(page("itogi-goda.html", "Книжные итоги года", "Собери свои книжные итоги года в Норе: сколько книг и страниц прочитано, любимый жанр, книга года и читательский тип - красивой картинкой для сторис.",
                 f'<div class="wrap"><div class="crumbs"><a href="/">Нора</a></div><div class="ph"><div><h1>Твои книжные итоги года</h1><p class="lead">Сколько книг и страниц, самый читающий месяц, любимый жанр, книга года и твой читательский тип - карточками, как сторис, и картинкой, которой можно поделиться.</p></div></div>'
                 f'<p class="itg"><img src="/img/itogi/primer.jpg" alt="Пример картинки «Мой год в книгах»" width="270" height="480" loading="lazy"></p>'
                 f'<div class="legal"><section class="gl"><h2>Как собрать свои</h2><ol><li>Открой Нору и отметь книги, прочитанные в этом году, - можно перенести списком из Литрес, Яндекс Книг или LiveLib.</li><li>Зайди в «Статистику» и нажми «Итоги года».</li><li>Листай карточки и жми «Поделиться» на последней.</li></ol></section></div>'
                 f'<section class="final gl"><h2>Собери свои итоги</h2><p>Бесплатно, прямо в браузере.</p>{CTA}</section></div>',
                 full_title=f"Книжные итоги {YNOW} года: сколько я прочитала — Нора"))

# ---------- политика конфиденциальности ----------
POLICY = [
    ("Что мы храним", "<ul><li>Почту и пароль — чтобы ты могла войти с любого устройства. Пароль зашифрован, его не видим даже мы.</li><li>Если ты включишь новости о книгах в Telegram — ещё твой Telegram ID, названия из избранного, любимых авторов, список друзей в Норе и твой книжный клуб, чтобы бот мог прислать новости и напомнить о сроке книги и встрече клуба. Выключишь — удалим.</li>"
     "<li>Имя и твои полки: книги, оценки, отзывы и заметки.</li></ul>"),
    ("Что мы не делаем", "<ul><li>Не продаём и не передаём данные рекламодателям.</li><li>Не показываем полки посторонним — только друзьям, которых ты добавишь.</li>"
     "<li>Не отправляем никуда фото шкафа: книги распознаются прямо на телефоне.</li></ul>"),
    ("Где это хранится", "В облаке Google Firebase — его серверы за пределами России. Создавая аккаунт, ты соглашаешься на такое хранение. "
     "Для статистики посещений сайта и приложения используем Яндекс Метрику и Cloudflare Web Analytics: считаем, сколько людей заходит и какие кнопки нажимают. Метрика использует cookies, но не получает твоё имя, почту и полки, а запись экрана в ней выключена. Ещё приложение без имени, ника и почты записывает, что в нём делают (открытые разделы, поиск, книги), чтобы делать Нору удобнее; такие записи хранятся не дольше 30 дней."),
    ("Как удалить данные", f"Напиши в бот Норы или на {MAIL} — удалим аккаунт и все полки в течение 30 дней."),
    ("Связаться с нами", f'Вопросы и просьбы — {SUPPORT}.'),
]
pol = ('<div class="wrap"><div class="crumbs"><a href="/">Нора</a></div><div class="ph"><div><h1>Политика конфиденциальности</h1>'
       f'<p class="lead">Коротко: что Нора знает о тебе и как это удалить. Обновлено {time.strftime("%d.%m.%Y")}.</p></div></div><div class="legal">'
       + "".join(f"<section class='gl'><h2>{h}</h2>{t if t.startswith('<') else '<p>' + t + '</p>'}</section>" for h, t in POLICY) + "</div></div>")
RV_JS = r"""<script>(function(){var q=new URLSearchParams(location.search),w=+q.get("w")||0,b=q.get("b")||"",F="https://api.fantlab.ru",L=document.getElementById("rvl"),M=document.getElementById("rvmore"),pg=1;
var bk=document.getElementById("rvback");if(/^\/k\/[a-z0-9-]+\.html$/.test(b))bk.href=b;else bk.onclick=function(e){if(history.length>1){e.preventDefault();history.back()}};
var pl=function(n,a,b,c){n=Math.abs(n)%100;var m=n%10;return n>10&&n<20?c:m>1&&m<5?b:m==1?a:c},esc=function(s){return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;")},
cl=function(s){return String(s||"").replace(/\[[^\]]*\]/g,"").replace(/<[^>]+>/g,"").replace(/\r/g,"").replace(/[ \t]+/g," ").replace(/\n{2,}/g,"\n").trim()},
dt=function(s){var d=new Date(String(s||"").replace(" ","T"));return isNaN(d)?"":d.toLocaleDateString("ru-RU",{day:"numeric",month:"long",year:"numeric"})};
if(!w){L.innerHTML='<p class="rve">Отзывы не нашлись.</p>';return}
fetch(F+"/work/"+w).then(function(r){return r.json()}).then(function(j){var r=j.rating||{},v=+r.voters||0,rc=+j.val_responsecount||0,t=j.work_name||"",a=(j.authors||[]).map(function(x){return x.name}).join(", ");
 document.title="Отзывы о книге «"+t+"» — Нора";document.getElementById("rvt").textContent="«"+t+"»";document.getElementById("rva").textContent=a;
 document.getElementById("rvs").innerHTML=(v>=5?'<b>★ '+(r.rating/2).toFixed(1).replace(".",",")+'</b> '+v.toLocaleString("ru-RU")+' '+pl(v,"оценка","оценки","оценок")+' · ':"")+rc+' '+pl(rc,"отзыв","отзыва","отзывов")}).catch(function(){});
function more(){M.disabled=true;M.textContent="Загружаю…";fetch(F+"/work/"+w+"/responses?page="+pg+"&sort=rating").then(function(r){return r.json()}).then(function(R){var it=R.items||[];if(pg==1)L.innerHTML="";
 it.forEach(function(x){if(!x)return;var d=document.createElement("article");d.className="rvi";var tx=cl(x.response_text||x.text);
  d.innerHTML='<header><b>'+esc(x.user_name||"Читатель")+'</b>'+(x.mark?'<span class="mk">★ '+(x.mark/2).toFixed(1).replace(".",",")+'</span>':"")+'</header>'+(dt(x.response_date)?'<time>'+dt(x.response_date)+'</time>':"")+'<p>'+esc(tx).replace(/\n/g,"</p><p>")+'</p>';
  L.appendChild(d);var ps=d.querySelectorAll("p");if(tx.length>600){d.classList.add("cut");var m=document.createElement("button");m.type="button";m.className="rvm";m.textContent="Читать полностью";m.onclick=function(){d.classList.remove("cut");m.remove()};d.after(m)}});
 if(pg==1&&!it.length)L.innerHTML='<p class="rve">Пока без отзывов.</p>';pg++;var tot=+R.total_count||+R.count||0;M.hidden=!it.length||it.length<10||(tot&&L.querySelectorAll(".rvi").length>=tot);M.disabled=false;M.textContent="Показать ещё"}).catch(function(){M.disabled=false;M.textContent="Показать ещё"})}
M.onclick=more;more()})();</script>"""
rvbody = ('<div class="rvw"><a class="rvback" id="rvback" href="/" aria-label="Назад к книге"><svg viewBox="0 0 24 24"><path d="M15 5l-7 7 7 7"/></svg>К книге</a>'
          '<h1>Отзывы</h1><p class="rvh"><span id="rvt"></span> <span id="rva"></span></p><p class="rvs" id="rvs"></p>'
          '<div id="rvl"><p class="rve">Загружаю отзывы…</p></div><button type="button" class="rvmore" id="rvmore" hidden>Показать ещё</button>'
          '<p class="rvsrc">Отзывы и оценки — с сайта <a href="https://fantlab.ru" rel="nofollow noopener" target="_blank">Фантлаб</a></p></div>' + RV_JS)
page("r/index.html", "Отзывы о книге", "Отзывы читателей о книге.", rvbody)
_rp = os.path.join(ROOT, "r/index.html"); _rs = open(_rp, encoding="utf-8").read().replace("<head>", '<head><meta name="robots" content="noindex">', 1)
open(_rp, "w", encoding="utf-8").write(_rs)
urls.append(page("privacy.html", "Политика конфиденциальности", "Какие данные хранит «Нора», зачем и как их удалить.", pol))

# ---------- главная ----------
get = lambda p: next((L for q, _, _, L in coll_data if q == p), [])
hero = [b for b in get("romantezi") if img_of(b)][:2] or get("romantezi")[:2] or cat_books[:2]
show = [p for p in ("romantezi", "dark-roman", "lyubovnye-romany", "young-adult", "zhanr-fantasy", "zahvatyvayuschie", "uyutnye", "zhanr-detective") if get(p)]
# в приложение с главной уводим только: из Telegram, с иконки на экране «Домой» и по ссылке ?app=1. В обычном Safari/Chrome - всегда сайт.
# На iPhone «с иконки» - только navigator.standalone (matchMedia в Safari иногда отвечает «да»); ?site=1 - никогда не уводить
TG_REDIRECT = """<script>(function(){try{var s=location.search,h=location.hash,ios=/iPhone|iPad|iPod/.test(navigator.userAgent)||(navigator.platform==="MacIntel"&&navigator.maxTouchPoints>1),
sa=ios?navigator.standalone===true:!!(window.matchMedia&&matchMedia("(display-mode: standalone)").matches);if(/[?&]site=1/.test(s))return;
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
def seed_card(b):
    return f'<a class="bk" href="/{SIM_URL[id(b)]}">{cv(b)}<div class="t">{esc(b["t"])}</div><div class="a">похожие книги</div></a>'


after = [b for g in groups.values() for b in g]
after = onepa(sorted(after, key=lambda b: (TORD.get(nk(b["t"]) + "|" + b["a"].split(" ")[-1].lower().replace("ё", "е"), 999), not b["cat"], -(b["q"] or 0))))[:16]
HOME_SHELVES = [("chitayut-seychas", None), ("novogodnee-nastroenie", "Книги с запахом мандаринов"), ("knigi-v-podarok-na-novyy-god", "Что подарить на Новый год"), ("zhanr-fantasy", "Популярное фэнтези")]
HOME_SHELVES = [(p, t) for p, t in HOME_SHELVES if get(p)]
lead_of = lambda p: next(l for q, _, l, _ in coll_data if q == p)
title_of = lambda p: next(t for q, t, _, _ in coll_data if q == p).split(":")[0]
# книга дня: одна из сильных книг с обложкой, меняется каждый день (выбор - в браузере, по дате)
_bod = [b for b in sorted(cat_books, key=rank) if img_of(b) and b["ann"] and id(b) in BOOK_URL and b["g"] != "kids"][:90]
BOD = ('<section class="bod gl" id="bod" hidden></section><script>(function(){var L=' + json.dumps([[b["t"], b["a"], "/" + BOOK_URL[id(b)], img_of(b), b["ann"]] for b in _bod], ensure_ascii=False)
       + r""",d=new Date(),r=L[Math.floor((d.getTime()-d.getTimezoneOffset()*6e4)/864e5)%L.length],e=document.getElementById("bod"),x=function(s){return String(s).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]})};
if(!r)return;e.innerHTML='<a class="bodc" href="'+r[2]+'"><img src="'+x(r[3])+'" alt="" referrerpolicy="no-referrer" onerror="this.remove()"></a><div><span class="bodk">Книга дня</span><h2><a href="'+r[2]+'">'+x(r[0])+'</a></h2><p class="boda">'+x(r[1])+'</p><p>'+x(r[4])+'</p><div class="ctas"><a class="btn" href="/app.html?app=1&bk='+encodeURIComponent(r[0]+"|"+r[1])+'" onclick="try{ym(114237349,\'reachGoal\',\'site_to_app\')}catch(e){}">На мою полку</a><a class="btn ghost" href="'+r[2]+'">О книге</a></div></div>';e.hidden=false})()</script>""")
home = (f'<div class="wrap"><section class="hero2" id="poisk"><h1>Найди свою следующую книгу</h1>'
        f'<p class="lead">Подборки по настроению и книги, похожие на любимые.</p>'
        f'<div class="sbox gl">{ic("search")}<input id="q" type="search" placeholder="Название или автор" autocomplete="off" enterkeyhint="search"></div><div class="sres" id="sres"></div>'
        f'{chips("")}</section>{BOD}'
        + "".join(shelf(t or title_of(p), f"/c/{p}.html", "", sorted(get(p)[:28], key=lambda b: not img_of(b))[:14]) for p, t in HOME_SHELVES)
        + '<a class="morec" href="/c/">Посмотреть все подборки</a><a class="morec mtest" href="/test.html"><span>Тест: какая книга тебе подойдёт</span><small>3 вопроса - и Шуршуня подберёт книги под настроение</small></a><a class="morec" href="/poryadok/">В каком порядке читать серии</a>'
        + '<a class="morec" href="/knizhnyy-klub.html">Книжный клуб с друзьями</a>'
        + f'{FINAL}</div>' + SEARCH_JS)
HOME_LD = [{"@context": "https://schema.org", "@type": "WebSite", "name": "Нора", "alternateName": ["Моя Нора", "Нора — книжный советник", "Нора книги", "moya-nora"],
            "url": SITE + "/", "inLanguage": "ru", "potentialAction": {"@type": "SearchAction", "target": SITE + "/?q={search_term_string}", "query-input": "required name=search_term_string"}},
           {"@context": "https://schema.org", "@type": "Organization", "name": "Нора", "alternateName": "Моя Нора", "url": SITE + "/", "logo": SITE + "/icons/icon-512.png",
            "sameAs": [BOT]}]
home_path = page("index.html", "Нора — что почитать", "Что почитать: подборки книг по настроению, новинки, книги, похожие на любимые, — ромэнтези, дарк роман, любовные романы, фэнтези, детективы. "
                 "А Шуршуня подберёт книги лично тебе.", home,
                 full_title="Нора (Моя Нора) — книжный советник: что почитать, подборки и похожие книги", ld=HOME_LD)
idx = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
idx = idx.replace('<meta charset="utf-8">', '<meta charset="utf-8"><script src="/ym.js"></script><meta name="google-site-verification" content="s2CdXU7z22CJQ7fqwqJNwf2nyq4VN3Jk2UEHofqjoXc"><meta name="yandex-verification" content="6a85060ff8390b92"><meta name="yandex-verification" content="zy7yffs4ru1bcbt0">'
                  '<link rel="manifest" href="/manifest.webmanifest"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="Моя Нора">' + TG_REDIRECT, 1)
open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(dash(idx))
urls.insert(0, home_path)

now = time.strftime("%Y-%m-%d")
open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8").write(
    '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    + "".join(f"<url><loc>{u}</loc><lastmod>{now}</lastmod></url>\n" for u in urls) + "</urlset>\n")
open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8").write(f"User-agent: *\nAllow: /\nDisallow: /old/\nDisallow: /v2/\nDisallow: /v3/\nDisallow: /v4/\nDisallow: /v5/\nDisallow: /v6/\nDisallow: /tools/\nDisallow: /app-dev.html\nDisallow: /notes/\nDisallow: /mockups/\nSitemap: {SITE}/sitemap.xml\n")
print("страниц:", len(urls), "подборок:", len(coll_data))
# старые страницы, которых больше нет в сборке: не оставляем устаревший текст - ведём на раздел (страницы-переадресации из REDIR не трогаем)
_live = {u.replace(SITE + "/", "") for u in urls}
for _d, _to in (("p", "/p/"), ("k", "/"), ("c", "/c/")):
    for _f in os.listdir(os.path.join(ROOT, _d)):
        _rel = f"{_d}/{_f}"
        if not _f.endswith(".html") or _f == "index.html" or _rel in _live:
            continue
        _fp = os.path.join(ROOT, _rel)
        if 'http-equiv="refresh"' in open(_fp, encoding="utf-8").read(2000):
            continue
        open(_fp, "w", encoding="utf-8").write(f'<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="robots" content="noindex">'
                                               f'<meta http-equiv="refresh" content="0;url={_to}"><link rel="canonical" href="{SITE}{_to}"></head><body></body></html>')
