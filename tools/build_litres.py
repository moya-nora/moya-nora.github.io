#!/usr/bin/env python3
"""Современные книги из ЛитРес (включая «Черновики» — самиздат) — books/litres.json, формат как books/new.json
плюс две колонки: обложка и короткая аннотация. Берём самые популярные книги в нужных жанрах ЛитРес
и переводим их жанры в жанры и метки Норы (ромэнтези, любовный роман, young adult, тропы…). 18+ не берём."""
import json, os, re, sys, time, urllib.request

ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(ROOT, "books", "litres.json")
API = "https://api.litres.ru/foundation/api/"
H = {"User-Agent": "moya-nora-books/1.0 (https://moya-nora.github.io)", "Accept": "application/json"}
PER = int(os.environ.get("PER_GENRE", "300"))

# жанр ЛитРес (часть названия) → (жанр Норы, метки Норы)
# сколько книг брать из жанра: в ромэнтези, любовных романах и young adult — намного больше (это их главная аудитория)
BIG = int(os.environ.get("PER_BIG", "1200"))
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
pick = []
for g in G:
    for rx, ng, tags in MAP:
        if rx.search(g.get("name", "")):
            pick.append((g["id"], g["name"], ng, tags))
            break
print("жанров ЛитРес:", len(G), "берём:", [(p[1], p[0]) for p in pick], flush=True)

books = {}
for gid, gname, ng, tags in pick:
    got = 0
    per = BIG if BIGRX.search(gname) else PER
    for off in range(0, per, 50):
        d = get(f"genres/{gid}/arts?limit=50&offset={off}&o=popular&art_types=text_book")
        L = ((d or {}).get("payload") or {}).get("data") or []
        if not L:
            break
        for x in L:
            if x.get("is_adult_content") or (x.get("min_age") or 0) >= 18 or x.get("art_type") not in (0, None):
                continue
            au = next((p.get("full_name") for p in x.get("persons") or [] if p.get("role") == "author"), "")
            if not au or not x.get("title"):
                continue
            k = re.sub(r"[^0-9a-zа-я]", "", (x["title"] + au).lower())
            rt = x.get("rating") or {}
            b = books.setdefault(k, {"id": x["id"], "t": x["title"].strip(), "a": au.strip(), "g": ng, "tags": [], "n": rt.get("rated_total_count") or 0,
                                     "r": rt.get("rated_avg") or 0, "y": int(str(x.get("date_written_at") or x.get("available_from") or "0")[:4] or 0),
                                     "cv": x.get("cover_url") or "", "pg": round((x.get("symbols_count") or 0) / 2000) or 0, "dr": 1 if x.get("is_draft") else 0})
            for t in tags:
                if t not in b["tags"]:
                    b["tags"].append(t)
            got += 1
        time.sleep(0.4)
    print(f"  {gname}: {got}", flush=True)

# аннотации — отдельным запросом к книге (целиком, до 1500 знаков по концу предложения)
L = sorted(books.values(), key=lambda b: -b["n"])
for i, b in enumerate(L):
    d = get(f"arts/{b['id']}")
    x = ((d or {}).get("payload") or {}).get("data") or {}
    ann = clean(x.get("html_annotation") or x.get("annotation") or "")
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
                 ("https://www.litres.ru" + b["cv"]) if b["cv"] else "", b.get("d") or ""])
json.dump({"meta": {"source": "ЛитРес", "built": time.strftime("%Y-%m-%d"), "n": len(rows)}, "c": [], "g": G_, "tg": TG, "aw": [], "a": A, "b": rows},
          open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("готово:", len(rows), "книг, самиздат:", sum(1 for b in L if b["dr"]))
