#!/usr/bin/env python3
"""Сборка большого книжного каталога «Норы».

Источник — Викиданные (через QLever, без лимитов по времени; запасной адрес — qlever.dev).
Берутся все литературные произведения и книги, у которых есть автор и хотя бы одна статья
в Википедии на любом языке (это отсекает мусор вроде отдельных изданий и научных статей).

Результат — books/books.json:
  {"meta": {...},
   "c": [страны], "g": [жанры], "tg": [теги], "aw": [премии],
   "a": [[имя автора, № страны], ...],
   "b": [[QID без Q, название, № автора, год, № жанра, [№ тегов], качество 1–3,
          число статей в Википедиях, № страны или -1 (как у автора), [№ премий], страниц,
          статья в рувики (0 — нет, 1 — как название, иначе её заголовок),
          оригинальное название или 0], ...]}
Описания и обложки приложение подтягивает само (Фантлаб, Википедия), когда книгу открывают.
Запуск: python3 tools/build_books.py  (GitHub Actions — .github/workflows/books.yml, ежемесячно)."""
import collections, json, os, re, sys, time, urllib.parse, urllib.request

MIN_SL = int(os.environ.get("MIN_SL", "1"))          # минимум статей в Википедиях
SOFT_SL = int(os.environ.get("SOFT_SL", "12"))       # стихи/рассказы/эссе — только очень известные
OUT = os.path.join(os.path.dirname(__file__), "..", "books", "books.json")
UA = {"User-Agent": "moya-nora-books/1.0 (https://github.com/moya-nora/moya-nora.github.io)"}
ENDPOINTS = ["https://qlever.cs.uni-freiburg.de/api/wikidata", "https://qlever.dev/api/wikidata"]
PFX = """PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wikibase: <http://wikiba.se/ontology#>
PREFIX schema: <http://schema.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""

# ---------- запросы ----------
def unq(v):
    v = v.strip()
    if not v:
        return None
    if v[0] == "<":
        v = v[1:-1]
        return v.rsplit("/", 1)[-1] if "wikidata.org/entity/" in v else v
    if v[0] == '"':
        j = v.rfind('"')
        s = v[1:j]
        return s.replace('\\"', '"').replace("\\n", " ").replace("\\t", " ").replace("\\\\", "\\")
    return v


def sparql(q, what):
    body = urllib.parse.urlencode({"query": PFX + q}).encode()
    last = None
    for attempt in range(6):
        url = ENDPOINTS[attempt % len(ENDPOINTS)]
        t0 = time.time()
        try:
            req = urllib.request.Request(url, data=body, headers={**UA, "Accept": "text/tab-separated-values",
                                                                  "Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(req, timeout=1800) as r:
                text = r.read().decode("utf-8")
            lines = text.split("\n")
            rows = [[unq(x) for x in ln.split("\t")] for ln in lines[1:] if ln]
            print(f"  {what}: {len(rows)} строк за {time.time() - t0:.0f} с ({url.split('/')[2]})", flush=True)
            return rows
        except Exception as e:  # noqa
            last = e
            print(f"  {what}: ошибка {e!r} ({url}), повтор", flush=True)
            time.sleep(20 * (attempt + 1))
    raise SystemExit(f"Не удалось выполнить запрос «{what}»: {last!r}")


WORKSET = f"""{{ SELECT DISTINCT ?w WHERE {{
  {{ ?w wdt:P31/wdt:P279* wd:Q7725634 }} UNION {{ ?w wdt:P31/wdt:P279* wd:Q571 }}
  ?w wdt:P50 ?anyAuthor .
  ?w wikibase:sitelinks ?wsl . FILTER(?wsl >= {MIN_SL})
}} }}"""


def per_work(pattern, what):
    return sparql(f"SELECT ?w ?v WHERE {{ {WORKSET} {pattern} }}", what)


def year_of(v):
    m = re.match(r"^(-?\d{1,4})-", v or "")
    return int(m.group(1)) if m else None


print("1. Произведения", flush=True)
SL = {w: int(float(v)) for w, v in per_work("?w wikibase:sitelinks ?v .", "статьи в Википедиях") if v}
print("   всего произведений:", len(SL), flush=True)
hist = collections.Counter(min(v, 50) // 5 * 5 for v in SL.values())
print("   по числу статей:", sorted(hist.items()), flush=True)

multi = collections.defaultdict(lambda: collections.defaultdict(list))
for prop, key in (("wdt:P31", "type"), ("wdt:P50", "auth"), ("wdt:P495", "cty"), ("wdt:P136", "genre"),
                  ("wdt:P921", "subj"), ("wdt:P166", "award"), ("wdt:P577", "date"), ("wdt:P571", "inc"),
                  ("wdt:P1104", "pages"), ("wdt:P1476", "title")):
    for w, v in per_work(f"?w {prop} ?v .", key):
        if w in SL and v:
            multi[w][key].append(v)
lab = {"ru": {}, "en": {}}
for lg in ("ru", "en"):
    for w, v in per_work(f'?w rdfs:label ?v . FILTER(LANG(?v) = "{lg}")', "названия " + lg):
        if w in SL and v:
            lab[lg][w] = v
RW = {}
for w, v in per_work("?art schema:about ?w ; schema:isPartOf <https://ru.wikipedia.org/> ; schema:name ?v .", "статьи рувики"):
    if w in SL and v:
        RW[w] = v

# ---------- типы, которые не нужны ----------
def subclasses(roots, what):
    vals = " ".join("wd:" + r for r in roots)
    return {r[0] for r in sparql(f"SELECT DISTINCT ?c WHERE {{ VALUES ?root {{ {vals} }} ?c wdt:P279* ?root }}", what) if r[0]}

HARD = subclasses(["Q13442814", "Q191067", "Q8274", "Q14406742", "Q838795", "Q1004", "Q7366", "Q482994",
                   "Q1980247", "Q1266946", "Q2188189", "Q105543609", "Q1172284", "Q732577", "Q871232"], "лишние типы")
SOFT = subclasses(["Q5185279", "Q49084", "Q35760", "Q133492", "Q1318295", "Q699", "Q12131"], "стихи и рассказы")
KEEP = {"Q8261", "Q7725634", "Q571", "Q149537", "Q1279564", "Q47461344", "Q25379", "Q12106333", "Q37484"}
HARD -= KEEP
SOFT -= KEEP | HARD

# ---------- авторы ----------
print("2. Авторы", flush=True)
authors = {a for w in multi for a in multi[w]["auth"]}
AUTH_SET = f"""{{ SELECT DISTINCT ?a WHERE {{ {WORKSET} ?w wdt:P50 ?a . }} }}"""
alab = {"ru": {}, "en": {}}
for lg in ("ru", "en"):
    for a, v in sparql(f'SELECT ?a ?v WHERE {{ {AUTH_SET} ?a rdfs:label ?v . FILTER(LANG(?v) = "{lg}") }}', "авторы " + lg):
        if a in authors and v:
            alab[lg][a] = v
acty = collections.defaultdict(list)
for a, v in sparql(f"SELECT ?a ?v WHERE {{ {AUTH_SET} ?a wdt:P27 ?v . }}", "гражданство авторов"):
    if a in authors and v:
        acty[a].append(v)
asl = {a: int(float(v)) for a, v in sparql(f"SELECT ?a ?v WHERE {{ {AUTH_SET} ?a wikibase:sitelinks ?v . }}", "известность авторов") if v}

# ---------- подписи к странам, жанрам, премиям ----------
def labels(ids, lg, what):
    ids = sorted(i for i in ids if re.match(r"^Q\d+$", i or ""))
    out = {}
    for i in range(0, len(ids), 4000):
        vals = " ".join("wd:" + x for x in ids[i:i + 4000])
        for e, v in sparql(f'SELECT ?e ?v WHERE {{ VALUES ?e {{ {vals} }} ?e rdfs:label ?v . FILTER(LANG(?v) = "{lg}") }}', what):
            if v:
                out[e] = v
    return out

print("3. Подписи", flush=True)
cty_ids = {c for w in multi for c in multi[w]["cty"]} | {c for a in acty for c in acty[a]}
CTY_RU = labels(cty_ids, "ru", "страны")
gs_ids = {g for w in multi for k in ("genre", "subj") for g in multi[w][k]}
G_EN, G_RU = labels(gs_ids, "en", "жанры en"), labels(gs_ids, "ru", "жанры ru")
aw_count = collections.Counter(x for w in multi for x in set(multi[w]["award"]))
AW_RU = labels({a for a, n in aw_count.items() if n >= 3}, "ru", "премии")

# ---------- страны: как на полках «Норы» ----------
CMAP = {
    "Соединённые Штаты Америки": "США", "США": "США", "Соединённое Королевство": "Англия", "Великобритания": "Англия",
    "Королевство Великобритания": "Англия", "Королевство Англия": "Англия", "Англия": "Англия",
    "Соединённое Королевство Великобритании и Ирландии": "Англия",
    "Российская империя": "Россия", "СССР": "Россия", "Союз Советских Социалистических Республик": "Россия",
    "Россия": "Россия", "РСФСР": "Россия", "Русское царство": "Россия", "Российская Федерация": "Россия",
    "Российская Советская Федеративная Социалистическая Республика": "Россия", "Российская республика": "Россия",
    "Королевство Франция": "Франция", "Французская империя": "Франция", "Вторая французская империя": "Франция",
    "Германская империя": "Германия", "Веймарская республика": "Германия", "Нацистская Германия": "Германия",
    "Третий рейх": "Германия", "ФРГ": "Германия", "ГДР": "Германия", "Германская Демократическая Республика": "Германия",
    "Федеративная Республика Германия": "Германия", "Королевство Пруссия": "Германия", "Пруссия": "Германия",
    "Священная Римская империя": "Германия", "Германский союз": "Германия", "Королевство Бавария": "Германия",
    "Королевство Саксония": "Германия", "Австро-Венгрия": "Австрия", "Австрийская империя": "Австрия",
    "Первая Австрийская Республика": "Австрия", "Королевство Италия": "Италия", "Итальянская Республика": "Италия",
    "Японская империя": "Япония", "Китайская Республика": "Китай", "Китайская Народная Республика": "Китай",
    "КНР": "Китай", "Империя Цин": "Китай", "Республика Корея": "Корея", "Южная Корея": "Корея",
    "Корейская империя": "Корея", "Чехословакия": "Чехия", "Чехия": "Чехия", "Королевство Богемия": "Чехия",
    "Османская империя": "Турция", "Турция": "Турция", "Украинская ССР": "Украина", "Белорусская ССР": "Беларусь",
    "Белоруссия": "Беларусь", "Республика Ирландия": "Ирландия", "Ирландия": "Ирландия", "Ирландское Свободное государство": "Ирландия",
    "Королевство Испания": "Испания", "Испанская империя": "Испания", "Испанское государство": "Испания",
    "Королевство Нидерландов": "Нидерланды", "Голландская республика": "Нидерланды", "Королевство Шотландия": "Шотландия",
    "Королевство Дания": "Дания", "Королевство Швеция": "Швеция", "Королевство Норвегия": "Норвегия",
    "Великое княжество Финляндское": "Финляндия", "Польская Народная Республика": "Польша", "Вторая Речь Посполитая": "Польша",
    "Речь Посполитая": "Польша", "Царство Польское": "Польша", "Армянская ССР": "Армения", "Грузинская ССР": "Грузия",
    "Азербайджанская ССР": "Азербайджан", "Казахская ССР": "Казахстан", "Узбекская ССР": "Узбекистан",
    "Литовская ССР": "Литва", "Латвийская ССР": "Латвия", "Эстонская ССР": "Эстония", "Киргизская ССР": "Киргизия",
    "Социалистическая Федеративная Республика Югославия": "Югославия", "Королевство Югославия": "Югославия",
    "Королевство Венгрия": "Венгрия", "Венгерская Народная Республика": "Венгрия", "Королевство Румыния": "Румыния",
    "Социалистическая Республика Румыния": "Румыния", "Царство Болгария": "Болгария", "Народная Республика Болгария": "Болгария",
    "Королевство Греция": "Греция", "Британская Индия": "Индия", "Доминион Индия": "Индия", "Королевство Португалия": "Португалия",
    "Каджарский Иран": "Иран", "Пехлевийский Иран": "Иран", "Королевство Египет": "Египет", "Мандатная Палестина": "Израиль",
    "Южно-Африканский Союз": "ЮАР", "Южно-Африканская Республика": "ЮАР", "Доминион Канада": "Канада",
    "Провинция Канада": "Канада", "Доминион Новая Зеландия": "Новая Зеландия", "Колония Новая Зеландия": "Новая Зеландия",
    "Австралийский Союз": "Австралия", "Бразильская империя": "Бразилия", "Мексиканская империя": "Мексика",
    "Древний Рим": "Древний Рим", "Римская империя": "Древний Рим", "Римская республика": "Древний Рим",
    "Древняя Греция": "Древняя Греция", "Византийская империя": "Византия",
}


def cname(q):
    s = CTY_RU.get(q)
    if not s:
        return None
    return CMAP.get(s, s)

# ---------- жанры и теги ----------
TAGS = ["грустное", "атмосферное", "любовь", "интеллектуальное", "психологический роман", "мрачное", "юмор", "напряжённое",
        "общество", "взросление", "женская судьба", "приключения", "философский роман", "смешное", "семейная сага",
        "большой город", "медленное", "дружба", "детектив", "исторический роман", "динамичное", "война", "тёплое",
        "сатира", "светлое", "магия", "деревня", "история", "путешествия", "романтичное", "вдохновляющее",
        "природа и животные", "научная фантастика", "искусство", "сказка", "социальный роман", "мистика", "наука",
        "триллер", "уют", "школа и университет", "мемуары", "жутковатое", "космос", "море", "мифология", "психология",
        "готика", "антиутопия", "викторианская эпоха", "музыка", "эпическое фэнтези", "магический реализм", "биография",
        "тёмное фэнтези", "ЛГБТ", "путешествия во времени", "драконы", "искусственный интеллект", "хоррор", "ромэнтези",
        "постапокалипсис", "еда", "городское фэнтези"]
TI = {t: i for i, t in enumerate(TAGS)}
GENRES = ["classic", "modern", "detective", "fantasy", "scifi", "kids", "nonfic"]
GI = {g: i for i, g in enumerate(GENRES)}
# (регулярка по англ. и рус. подписи жанра/темы, жанр приложения или None, теги)
GRULES = [
    (r"romantasy|romantic fantasy|ромэнтези", "fantasy", ["ромэнтези", "любовь", "магия"]),
    (r"dark fantasy|тёмное фэнтези|темное фэнтези", "fantasy", ["тёмное фэнтези", "мрачное", "магия"]),
    (r"epic fantasy|high fantasy|heroic fantasy|эпическое фэнтези|высокое фэнтези|героическое фэнтези", "fantasy", ["эпическое фэнтези", "магия", "приключения"]),
    (r"urban fantasy|городское фэнтези", "fantasy", ["городское фэнтези", "магия", "большой город"]),
    (r"fantasy|фэнтези|sword and sorcery", "fantasy", ["магия"]),
    (r"dragon|дракон", None, ["драконы"]),
    (r"cyberpunk|киберпанк|artificial intelligence|искусственный интеллект|robot|робот", "scifi", ["искусственный интеллект", "научная фантастика"]),
    (r"space opera|космическая опера|outer space|космос|military science fiction", "scifi", ["космос", "научная фантастика"]),
    (r"time travel|путешеств\w* во времени", "scifi", ["путешествия во времени"]),
    (r"post-apocalyptic|apocalyptic|постапокалип|апокалип", "scifi", ["постапокалипсис", "мрачное"]),
    (r"dystopia|антиутопи", "scifi", ["антиутопия", "общество"]),
    (r"science fiction|научная фантастика|sci-fi|фантастик|hard science", "scifi", ["научная фантастика"]),
    (r"gothic|готическ", None, ["готика", "мрачное", "атмосферное"]),
    (r"horror|ужас|хоррор", None, ["хоррор", "жутковатое"]),
    (r"supernatural|сверхъестеств|occult|мистик|ghost|призрак|paranormal", None, ["мистика", "жутковатое"]),
    (r"magic realism|magical realism|магический реализм", None, ["магический реализм"]),
    (r"cozy mystery|cosy mystery", "detective", ["детектив", "уют"]),
    (r"detective|детектив|mystery|crime|криминал|whodunit|police procedural|hardboiled|нуар|noir", "detective", ["детектив"]),
    (r"thriller|триллер|suspense|spy|шпион|espionage", "detective", ["триллер", "напряжённое", "динамичное"]),
    (r"psychological|психологическ", None, ["психологический роман"]),
    (r"philosophical|философ|existential", None, ["философский роман", "интеллектуальное"]),
    (r"historical|историческ|history|истори", None, ["исторический роман", "история"]),
    (r"war novel|war fiction|military fiction|world war|военн|войн", None, ["война"]),
    (r"romance|romantic|любовн|роман о любви|love", None, ["любовь", "романтичное"]),
    (r"satire|сатир", None, ["сатира", "юмор"]),
    (r"humou?r|comic novel|comedy|юмор|комеди|смешн", None, ["юмор", "смешное"]),
    (r"bildungsroman|coming-of-age|coming of age|роман воспитания|взросле", None, ["взросление"]),
    (r"family saga|семейн\w* сага|семейн\w* роман", None, ["семейная сага"]),
    (r"adventure|приключен|picaresque|плутовск|western|вестерн|swashbuckler", None, ["приключения", "динамичное"]),
    (r"nautical|sea story|морск|\bsea\b|море", None, ["море"]),
    (r"travel|путешеств", None, ["путешествия"]),
    (r"social novel|социальн", None, ["социальный роман", "общество"]),
    (r"political|политич", None, ["общество"]),
    (r"fairy tale|сказк|fable|басн|folk tale", "kids", ["сказка"]),
    (r"myth|миф|legend|легенд|epic poetry|эпос", None, ["мифология"]),
    (r"children|детск|young adult|подростк|picture book", "kids", ["взросление"]),
    (r"school story|campus novel|школ|университет", None, ["школа и университет"]),
    (r"memoir|мемуар|autobiograph|автобиограф|diary|дневник", "nonfic", ["мемуары"]),
    (r"biograph|биограф", "nonfic", ["биография"]),
    (r"popular science|научно-популяр|science|наук|physics|физик|biology|биолог|mathematic|математ|astronomy|астроном",
     "nonfic", ["наука"]),
    (r"psychology|психологи", "nonfic", ["психология"]),
    (r"non-fiction|nonfiction|нон-фикшн|документальн|essay|эссе|treatise|трактат|self-help|economics|экономик|"
     r"philosophy\b|философия$|sociology|социолог|journalism|публицист|textbook|учебник|religio|религи", "nonfic", ["интеллектуальное"]),
    (r"lgbt|gay|lesbian|queer|гомосексуал|лгбт", None, ["ЛГБТ"]),
    (r"music|музык", None, ["музыка"]),
    (r"\bart\b|painting|painter|искусств|живопис|художник", None, ["искусство"]),
    (r"animal|животн|nature|природ|dog|собак|\bcat\b|кошк", None, ["природа и животные"]),
    (r"food|cooking|кулинар|еда", None, ["еда"]),
    (r"victorian|викториан", None, ["викторианская эпоха"]),
    (r"tragedy|трагеди", None, ["грустное", "мрачное"]),
    (r"friendship|дружб", None, ["дружба"]),
    (r"city|urban|город", None, ["большой город"]),
    (r"village|rural|countryside|деревн|сельск", None, ["деревня"]),
    (r"women|feminis|женск", None, ["женская судьба"]),
]
GRULES = [(re.compile(r, re.I), g, t) for r, g, t in GRULES]
GENRE_CACHE = {}


def genre_hits(q):
    if q not in GENRE_CACHE:
        s = (G_EN.get(q, "") + " | " + G_RU.get(q, "")).lower()
        GENRE_CACHE[q] = [(g, t) for rx, g, t in GRULES if s.strip(" |") and rx.search(s)]
    return GENRE_CACHE[q]


# ---------- сборка ----------
print("4. Сборка", flush=True)
CT, CI = [], {}
def cix(name):
    if not name:
        return -1
    if name not in CI:
        CI[name] = len(CT)
        CT.append(name)
    return CI[name]

AW, AWI = [], {}
def awix(q):
    if q not in AWI:
        AWI[q] = len(AW)
        AW.append(AW_RU[q])
    return AWI[q]

recs, skipped = [], collections.Counter()
for w, sl in SL.items():
    m = multi[w]
    types = set(m["type"])
    if types and types <= HARD | SOFT:
        if types & HARD and not (types - HARD):
            skipped["тип"] += 1
            continue
        if sl < SOFT_SL:
            skipped["малоизвестный стих/рассказ"] += 1
            continue
    ru, en = lab["ru"].get(w), lab["en"].get(w)
    title = ru or en or (m["title"][0] if m["title"] else None)
    if not title or re.match(r"^Q\d+$", title):
        skipped["без названия"] += 1
        continue
    auth = [a for a in m["auth"] if alab["ru"].get(a) or alab["en"].get(a)]
    if not auth:
        skipped["без автора"] += 1
        continue
    auth.sort(key=lambda a: -asl.get(a, 0))
    a = auth[0]
    years = [y for y in map(year_of, m["date"]) if y and -3000 < y < 2100] or \
            [y for y in map(year_of, m["inc"]) if y and -3000 < y < 2100]
    y = min(years) if years else None
    # жанр и теги
    gc, tags = collections.Counter(), []
    for g in m["genre"] + m["subj"]:
        for gg, tt in genre_hits(g):
            if gg:
                gc[gg] += 1
            for t in tt:
                if t not in tags:
                    tags.append(t)
    if gc:
        order = ["kids", "detective", "fantasy", "scifi", "nonfic"]
        g = max(gc, key=lambda k: (gc[k], -order.index(k) if k in order else 0))
    else:
        g = "classic" if (y and y < 1950) else "modern"
    # страна: страна происхождения произведения, иначе гражданство автора
    wc = next((cname(c) for c in m["cty"] if cname(c)), None)
    ac = next((cname(c) for c in acty.get(a, []) if cname(c)), None)
    awards = [awix(x) for x in dict.fromkeys(m["award"]) if x in AW_RU]
    pages = 0
    for p in m["pages"]:
        try:
            pages = int(float(p))
            break
        except ValueError:
            pass
    rw = RW.get(w)
    orig = en if ru and en and en.lower() != ru.lower() else 0
    recs.append({"w": int(w[1:]), "t": title.strip(), "a": a, "ac": ac, "wc": wc, "y": y, "g": g, "tags": tags[:6],
                 "sl": sl, "aw": awards[:6], "pg": pages if 20 <= pages <= 5000 else 0,
                 "rw": 0 if not rw else (1 if rw == title else rw), "o": orig, "ru": bool(ru)})
print("   отброшено:", dict(skipped), flush=True)

# повторы: одно и то же произведение несколькими элементами
best = {}
norm = lambda s: re.sub(r"[^0-9a-zа-я]+", "", s.lower().replace("ё", "е"))
for r in recs:
    k = norm(r["t"]) + "|" + r["a"]
    if k not in best or r["sl"] > best[k]["sl"]:
        best[k] = r
recs = list(best.values())
# качество 1–3: известность в Википедиях и премии, на русском — чуть выше
for r in recs:
    r["s"] = r["sl"] + 4 * len(r["aw"]) + (6 if r["rw"] else 0)
srt = sorted(r["s"] for r in recs)
p70, p93 = srt[int(len(srt) * .70)], srt[int(len(srt) * .93)]
for r in recs:
    r["q"] = 3 if r["s"] >= p93 else 2 if r["s"] >= p70 else 1
recs.sort(key=lambda r: -r["s"])

AU, AUI = [], {}
def auix(a, ac):
    if a not in AUI:
        AUI[a] = len(AU)
        AU.append([alab["ru"].get(a) or alab["en"].get(a), cix(ac)])
    return AUI[a]

rows = []
for r in recs:
    ai = auix(r["a"], r["ac"])
    ci = cix(r["wc"]) if r["wc"] and r["wc"] != r["ac"] else -1
    rows.append([r["w"], r["t"], ai, r["y"] or 0, GI[r["g"]], [TI[t] for t in r["tags"]], r["q"], r["sl"], ci,
                 r["aw"], r["pg"], r["rw"], r["o"]])

out = {"meta": {"source": "Wikidata (QLever)", "built": time.strftime("%Y-%m-%d"), "n": len(rows),
                "ru": sum(1 for r in recs if r["ru"]), "min_sitelinks": MIN_SL},
       "c": CT, "g": GENRES, "tg": TAGS, "aw": AW, "a": AU, "b": rows}
print("   книг:", len(rows), "с русским названием:", out["meta"]["ru"], "авторов:", len(AU), "стран:", len(CT), flush=True)
print("   жанры:", collections.Counter(r["g"] for r in recs).most_common(), flush=True)
print("   страны:", collections.Counter(r["wc"] or r["ac"] for r in recs).most_common(40), flush=True)
print("   первые:", [(r["t"], AU[AUI[r["a"]]][0]) for r in recs[:30]], flush=True)
if len(rows) < 20000:
    raise SystemExit(f"Подозрительно мало книг ({len(rows)}) — файл не перезаписан")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
print("   записано:", OUT, os.path.getsize(OUT) // 1024, "КБ", flush=True)
