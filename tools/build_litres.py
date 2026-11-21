#!/usr/bin/env python3
"""Современные книги из ЛитРес (включая «Черновики» — самиздат) — books/litres.json, формат как books/new.json
плюс две колонки: обложка и короткая аннотация. Берём самые популярные книги в нужных жанрах ЛитРес
и переводим их жанры в жанры и метки Норы (ромэнтези, любовный роман, young adult, тропы…).
Книги 18+ тоже берём (с 21.11.2026): у них метка «18+», в приложении - значок на обложке, в ленту новичкам они не попадают.
Средняя оценка ЛитРес - последняя колонка (×10), её видно на обложке в списках."""
import json, os, re, sys, time, urllib.parse, urllib.request
START = time.time()

ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(ROOT, "books", "litres.json")
API = "https://api.litres.ru/foundation/api/"
H = {"User-Agent": "moya-nora-books/1.0 (https://moya-nora.github.io)", "Accept": "application/json"}
PER = int(os.environ.get("PER_GENRE", "1500"))

# жанр ЛитРес (часть названия) → (жанр Норы, метки Норы)
# сколько книг брать из жанра: в ромэнтези, любовных романах и young adult — намного больше (это их главная аудитория)
BIG = int(os.environ.get("PER_BIG", "6000"))
MAP = [
    (r"^магические академии", "fantasy", ["любовное фэнтези", "троп:academy", "школа и университет"]),
    (r"^фэнтези про драконов", "fantasy", ["троп:dragons", "драконы"]),
    (r"^любовно-фантастическ|^любовное фэнтези|романтическое фэнтези", "fantasy", ["любовное фэнтези", "любовь", "романтичное"]),
    (r"^зарубежные любовные романы", "modern", ["любовный роман", "любовь", "романтичное"]),
    (r"^зарубежное фэнтези|^русское фэнтези|^историческое фэнтези|^детективное фэнтези", "fantasy", ["магия"]),
    (r"^книги для подростков", "kids", ["young adult", "взросление"]),
    (r"^попаданцы", "fantasy", ["троп:popadan", "приключения"]),
    (r"^городское фэнтези", "fantasy", ["магия", "большой город"]),
    (r"^боевое фэнтези|^героическое фэнтези", "fantasy", ["приключения", "магия", "динамичное"]),
    (r"^юмористическое фэнтези", "fantasy", ["смешное", "магия"]),
    (r"^мистика|^ужасы", "fantasy", ["мистика", "жутковатое"]),
    (r"^современные любовные романы", "modern", ["любовный роман", "любовь", "романтичное"]),
    (r"^короткие любовные романы", "modern", ["любовный роман", "любовь"]),
    (r"^исторические любовные романы", "modern", ["любовный роман", "любовь", "история"]),
    (r"^остросюжетные любовные романы", "modern", ["любовный роман", "любовь", "напряжённое"]),
    (r"^young adult|^подростковая литература|^книги для подростков", "kids", ["young adult", "взросление"]),
    (r"^триллеры", "detective", ["напряжённое", "триллер"]),
    (r"^современные детективы", "detective", ["детектив"]),
    (r"^иронические детективы", "detective", ["детектив", "смешное"]),
    (r"^космическая фантастика|^боевая фантастика|^социальная фантастика", "scifi", ["приключения"]),
    (r"^современная русская литература", "modern", []),
    (r"^современная зарубежная литература", "modern", []),
    (r"^психология|^саморазвитие|^личностный рост", "nonfic", ["психология"]),
    (r"^бизнес-книги|^бизнес|^маркетинг|^менеджмент|^управление|^стартап|^личная эффективность|^продажи|^лидерство|^карьера|^тайм-менеджмент|^переговоры", "nonfic", ["бизнес"]),
    (r"^финанс|^экономика|^инвестиции|^личные финансы", "nonfic", ["бизнес", "экономика"]),
    (r"^научно-популярн|^научпоп|^естественные науки|^физика|^биология|^химия|^астрономия|^математика|^медицина и здоровье|^медицина|^науки о земле|^техника", "nonfic", ["наука"]),
    (r"^история|^всемирная история|^история россии", "nonfic", ["история"]),
    (r"^биографии|^мемуары", "nonfic", ["биография", "мемуары"]),
    (r"^философия|^культурология|^социология|^политология", "nonfic", ["интеллектуальное", "общество"]),
    (r"^образование|^педагогика|^воспитание детей|^детская психология", "nonfic", ["образование"]),
    (r"^публицистика|^документальная литература", "nonfic", ["реальные истории"]),
    (r"^зарубежная классика|^русская классика|^классическая проза|^литература 19 века|^литература 20 века|^советская литература", "classic", []),
    (r"^зарубежная драматургия|^драматургия|^пьесы", "classic", []),
    (r"^поэзия|^зарубежная поэзия|^русская поэзия", "classic", ["поэзия"]),
]
MAP = [(re.compile(r, re.I), g, t) for r, g, t in MAP]
BIGRX = re.compile(r"любов|академ|дракон|young adult|подрост|попадан", re.I)
# метки и жанры книги на ЛитРес → тропы Норы
TROPES = [(r"академи", "academy"), (r"попад", "popadan"), (r"истинн", "fated"), (r"отбор", "selection"), (r"дракон", "dragons"),
          (r"от ненависти|враги|врагов", "enemies"), (r"фиктивн|договорн|брак по (договору|расчёту|расчету)|брак поневоле", "marriage"),
          (r"вампир|оборот", "vamp"), (r"фейри|фэйри|феи|эльф", "fae"), (r"второй шанс", "second"), (r"треугольник", "triangle"),
          (r"тёмная академия|темная академия", "darkacad"), (r"соперни", "rivals"), (r"запретн", "forbid"), (r"избранн", "chosen"),
          (r"дворцов|интриги при дворе", "court"), (r"путешеств[а-я]* во времени", "time"), (r"из друзей|дружба переросла", "friends"),
          (r"медленн[а-я]* (сближение|разгорание)|slow burn", "slow"), (r"найденн[а-я]* семь", "found"), (r"пересказ|по мотивам сказ|сказка на новый лад", "retell")]
TROPES = [(re.compile(r, re.I), t) for r, t in TROPES]


def get(path, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(API + path, headers=H), timeout=40) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            print("  !", path, e, flush=True)
            time.sleep(5 * (k + 1))
    return None


def walk(nodes, out):
    for n in nodes or []:
        out.append(n)
        walk(n.get("subgenres"), out)


def clean(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", s).strip()


tree = (get("genres?limit=500") or {}).get("payload", {}).get("data", [])
G = []
walk(tree, G)
pick, _seen = [], set()
for g in G:
    if g["id"] in _seen or re.search(r"\d+\s*класс|журнал|справочник", g.get("name", ""), re.I):  # школьные учебники и журналы не берём, жанр - один раз
        continue
    for rx, ng, tags in MAP:
        if rx.search(g.get("name", "")):
            pick.append((g["id"], g["name"], ng, tags)); _seen.add(g["id"])
            break
print("жанров ЛитРес:", len(G), "берём:", [(p[1], p[0]) for p in pick], flush=True)

books = {}


def add(x, ng, tags):
    """книга из ответа ЛитРес -> в каталог; True, если подошла"""
    if x.get("art_type") not in (0, None):
        return False
    adult = bool(x.get("is_adult_content") or (x.get("min_age") or 0) >= 18)
    au = next((p.get("full_name") for p in x.get("persons") or [] if p.get("role") == "author"), "")
    if not au or not x.get("title") or not x.get("id"):
        return False
    k = re.sub(r"[^0-9a-zа-я]", "", (x["title"] + au).lower())
    rt = x.get("rating") or {}
    b = books.setdefault(k, {"id": x["id"], "t": x["title"].strip(), "a": au.strip(), "g": ng, "tags": [], "n": rt.get("rated_total_count") or 0,
                             "r": rt.get("rated_avg") or 0, "y": int(str(x.get("date_written_at") or x.get("available_from") or "0")[:4] or 0),
                             "cv": x.get("cover_url") or "", "pg": round((x.get("symbols_count") or 0) / 2000) or 0, "dr": 1 if x.get("is_draft") else 0})
    if adult and "18+" not in b["tags"]:
        b["tags"].append("18+")
    for t in tags:
        if t not in b["tags"]:
            b["tags"].append(t)
    return True


for gid, gname, ng, tags in pick:
    got = 0
    per = BIG if BIGRX.search(gname) else PER
    for off in range(0, per, 50):
        d = get(f"genres/{gid}/arts?limit=50&offset={off}&o=popular&art_types=text_book")
        L = ((d or {}).get("payload") or {}).get("data") or []
        if not L:
            break
        for x in L:
            got += add(x, ng, tags)
        time.sleep(0.4)
    print(f"  {gname}: {got}", flush=True)

# все книги популярных авторов: в популярных по жанру попадает только часть (у Мари Милас было 7 книг из ~15).
# Ищем по имени автора, берём книги, где он автор, - жанр и метки как у его книги, которая уже есть.
_byau = {}
for b in books.values():
    _byau.setdefault(b["a"], []).append(b)
AUS = sorted(_byau, key=lambda a: -sum(x["n"] for x in _byau[a]))[:int(os.environ.get("AUTHORS", "3000"))]
_added = 0
for i, a in enumerate(AUS):
    if time.time() - START > 2.6 * 3600:
        print("  авторы: не успели, остановились на", i, flush=True); break
    ref = max(_byau[a], key=lambda x: x["n"])
    tags = [t for t in ref["tags"] if t not in ("18+", "самиздат") and not t.startswith("троп:")]
    for off in (0, 50):
        d = get("search?q=" + urllib.parse.quote(a) + f"&types=text_book&limit=50&offset={off}")
        L = ((d or {}).get("payload") or {}).get("data") or []
        n0 = len(books)
        for it in L:
            x = it.get("instance") or it
            if any(p.get("role") == "author" and (p.get("full_name") or "").strip() == a for p in x.get("persons") or []):
                add(x, ref["g"], tags)
        _added += len(books) - n0
        time.sleep(0.3)
        if len(L) < 50:
            break
    if i % 300 == 0:
        print("  авторы:", i, "/", len(AUS), "добавлено книг:", _added, flush=True)
print("  книг авторов добавлено:", _added, flush=True)

DRUG = []
# прошлые аннотации и тропы берём из прежнего файла - заново запрашиваем только новые книги (иначе не успеваем за 5,5 часа)
OLD = {}
try:
    _o = json.load(open(OUT, encoding="utf-8"))
    for r in _o["b"]:
        if len(r) > 14 and r[14]:
            OLD[r[0]] = (r[14], [_o["tg"][k] for k in r[5] if _o["tg"][k].startswith("троп:")])
    for t_, a_ in json.load(open(os.path.join(os.path.dirname(OUT), "drugmark.json"), encoding="utf-8")):
        DRUG.append([t_, a_])
except Exception as e:  # noqa: BLE001
    print("  нет прежнего файла:", e)
T0 = time.time()
# аннотации — отдельным запросом к книге (целиком, до 1500 знаков по концу предложения)
L = sorted(books.values(), key=lambda b: -b["n"])
for i, b in enumerate(L):
    old = OLD.get("l" + str(b["id"]))
    if old:
        b["d"] = old[0]
        for tr in old[1]:
            if tr not in b["tags"]:
                b["tags"].append(tr)
        continue
    if time.time() - START > 4.9 * 3600:  # не хватает времени - остальные книги без аннотации, допишутся в следующий раз
        continue
    d = get(f"arts/{b['id']}")
    x = ((d or {}).get("payload") or {}).get("data") or {}
    ann = clean(x.get("html_annotation") or x.get("annotation") or "")
    # предупреждение о наркотиках по закону (с 1 марта 2026) убираем из текста описания, но запоминаем книгу - в Норе оно показывается мелко внизу карточки
    if re.search(r"НЕЗАКОННОЕ ПОТРЕБЛЕНИЕ НАРКОТИЧЕСКИХ СРЕДСТВ", ann, re.I) and [b["t"], b["a"]] not in DRUG:
        DRUG.append([b["t"], b["a"]])
    ann = re.sub(r"НЕЗАКОННОЕ ПОТРЕБЛЕНИЕ НАРКОТИЧЕСКИХ СРЕДСТВ[^.]*?ОТВЕТСТВЕННОСТЬ\.?\s*", "", ann, flags=re.I).strip()
    lab = " | ".join([t.get("name", "") for t in x.get("tags") or []] + [g.get("name", "") for g in x.get("genres") or []])
    for rx, tid in TROPES:
        if rx.search(lab) and "троп:" + tid not in b["tags"]:
            b["tags"].append("троп:" + tid)
    if len(ann) > 700:  # обрезаем по концу предложения, без многоточия
        cut = ann[:700]; k = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
        ann = cut[:k + 1] if k > 200 else cut
    b["d"] = ann
    if i % 200 == 0:
        print("  аннотации:", i, "/", len(L), flush=True)
    time.sleep(0.25)

G_ = ["classic", "modern", "detective", "fantasy", "scifi", "kids", "nonfic"]
TG, A, rows = [], [], []
ti = lambda t: TG.index(t) if t in TG else (TG.append(t) or len(TG) - 1)
ai_ = {}
for b in L:
    if b["a"] not in ai_:
        ai_[b["a"]] = len(A); A.append([b["a"], -1])
    q = 3 if b["n"] >= 1000 else 2 if b["n"] >= 150 else 1
    if b["dr"]:
        b["tags"].append("самиздат")
    rows.append(["l" + str(b["id"]), b["t"], ai_[b["a"]], b["y"] or 0, G_.index(b["g"]), [ti(t) for t in b["tags"]], q, b["n"], -1, [], b["pg"], 0, 0,
                 ("https://www.litres.ru" + b["cv"]) if b["cv"] else "", b.get("d") or "", round((b["r"] or 0) * 10) if b["n"] >= 5 else 0])
json.dump({"meta": {"source": "ЛитРес", "built": time.strftime("%Y-%m-%d"), "n": len(rows)}, "c": [], "g": G_, "tg": TG, "aw": [], "a": A, "b": rows},
          open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
json.dump(DRUG, open(os.path.join(os.path.dirname(OUT), "drugmark.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("готово:", len(rows), "книг, самиздат:", sum(1 for b in L if b["dr"]))
