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
MAP = [
    (r"^любовно-фантастическ|^любовное фэнтези|романтическое фэнтези", "fantasy", ["любовное фэнтези", "любовь", "романтичное"]),
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
    for off in range(0, PER, 50):
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
    if len(ann) > 1500:  # обрезаем по концу предложения, без многоточия
        cut = ann[:1500]; k = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
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
