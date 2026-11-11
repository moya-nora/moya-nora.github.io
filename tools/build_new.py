#!/usr/bin/env python3
"""Новинки для «Норы» — books/new.json (формат как у books/books.json).

Источники: Фантлаб (раздел «Новинки издательств», api.fantlab.ru/pubnews) и Викиданные
(книги последних лет — без требования статьи в Википедии, у свежих книг её обычно ещё нет).
Режим PROBE=1 — только показать устройство ответов (для отладки)."""
import json, os, sys, time, urllib.error, urllib.parse, urllib.request

UA = {"User-Agent": "moya-nora-books/1.0 (https://github.com/moya-nora/moya-nora.github.io)", "Accept": "application/json"}
FL = "https://api.fantlab.ru"


def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa
            print(f"  {url}: {e!r}, повтор", flush=True)
            time.sleep(10 * (k + 1))
    return None


def show(x, n=1500):
    print("   ", json.dumps(x, ensure_ascii=False)[:n], flush=True)


if os.environ.get("PROBE"):
    for path in ("/pubnews?lang=2&sort=date&page=1", "/pubnews?lang=0&sort=popularity&page=1", "/pubplans?lang=2&sort=date&page=1"):
        d = get(FL + path)
        print("==", path, type(d).__name__, flush=True)
        if isinstance(d, dict):
            print("   ключи:", list(d.keys()), flush=True)
            for k, v in d.items():
                if not isinstance(v, list):
                    print("   ", k, "=", json.dumps(v, ensure_ascii=False)[:200])
            objs = d.get("objects") or []
            print("   объектов:", len(objs), flush=True)
            for o in objs[:2]:
                show(o, 3000)
            ids = [((o.get("the_only_work") or {}).get("work_id")) for o in objs]
            print("   the_only_work ids:", ids[:20], flush=True)
            wid = next((i for i in ids if i), None)
            if wid:
                w = get(f"{FL}/work/{wid}/extended")
                print("== /work/%s/extended ключи:" % wid, list((w or {}).keys()), flush=True)
                show(w, 4000)
            break_after = True
    sys.exit(0)

import re
YNOW = time.gmtime().tm_year
MAX_PAGES = int(os.environ.get("MAX_PAGES", "60"))
OUT = os.path.join(os.path.dirname(__file__), "..", "books", "new.json")
CYR = re.compile(r"[а-яё]", re.I)
BOOKISH = re.compile(r"авторская книга|сборник|антология|роман|повесть|книга", re.I)
GENRE_RX = [(r"детск|подростк|young adult|ya\b", "kids"), (r"детектив|триллер|нуар", "detective"),
            (r"^фантастика|научн|космос|киберпанк|антиутоп|постапокалип|твёрдая|социальная фантастика|альтернативная история", "scifi"),
            (r"фэнтези|магия|сказ|мистик|хоррор|ужас|городское", "fantasy"), (r"реализм|современн|историческ", "modern")]
GENRE_RX = [(re.compile(r, re.I), g) for r, g in GENRE_RX]
TAGS = ["хоррор", "мистика", "любовь", "приключения", "антиутопия", "постапокалипсис", "юмор", "напряжённое", "мрачное", "детектив",
        "динамичное", "смешное", "жутковатое", "грустное", "атмосферное", "тёплое", "интеллектуальное", "романтичное", "философский роман",
        "любовное фэнтези", "young adult", "любовный роман", "троп:enemies", "троп:academy", "троп:slow", "троп:fake", "троп:fated", "троп:gray",
        "троп:grumpy", "троп:forbid", "троп:triangle", "троп:chosen"]
TAG_RX = [(re.compile(r, re.I), t) for r, t in [(r"хоррор|ужас", "хоррор"), (r"мистик", "мистика"), (r"любов|роман[ст]", "любовь"),
          (r"приключ", "приключения"), (r"антиутоп", "антиутопия"), (r"постапокалип", "постапокалипсис"), (r"юмор|ирони", "юмор"),
          (r"триллер|напряж", "напряжённое"), (r"мрачн|тёмн|темн|готик", "мрачное"), (r"детектив", "детектив"),
          (r"приключенческ|боевик|динамичн", "динамичное"), (r"юмористич|ирони", "смешное"), (r"философ", "философский роман"),
          (r"психологич|интеллектуал|социальн", "интеллектуальное"), (r"романтич|любовн", "романтичное")]]
# что чаще всего пишут читатели в отзывах — по этим словам ставим настроение книги
REVIEW_RX = [(re.compile(r, re.I), t) for r, t in [
    (r"захватыва|не оторват|на одном дыхании|не отпуска|проглотил|залпом|держит в напряжении|интрига", "напряжённое"),
    (r"динамичн|экшен|экшн|не даёт заскучать|не дает заскучать", "динамичное"),
    (r"смешн|хохот|смеял|юмор|забавн", "смешное"), (r"страшн|жутк|мурашк|пугающ|криповат", "жутковатое"),
    (r"трогател|до слёз|до слез|плакал|грустн|щемящ", "грустное"), (r"атмосфер", "атмосферное"),
    (r"уютн|тёпл|тепл[аоы][яеи] книг|светл", "тёплое"), (r"заставля\w* задуматься|философ|глубок\w* книг|пища для ума", "интеллектуальное"),
    (r"романтик|романтичн|любовн\w* лини", "романтичное")]]

# тропы — по описанию книги и отзывам читателей
TROPE_RX = [(re.compile(r, re.I), "троп:" + t) for r, t in [
    (r"от врагов к (возлюбленн|любовник|любв)|enemies to lovers|из врагов в (любовник|возлюбленн)", "enemies"),
    (r"академи\w* (магии|драконов|ведьм|магов)|магическ\w* академи|магическ\w* (школ|университет)", "academy"),
    (r"сло[уо]?б[её]рн|slow ?burn|медленн\w* (сближен|разгора)", "slow"),
    (r"фиктивн\w* (брак|отношен|помолвк|невест)|фальшив\w* (отношен|свидан|помолвк|невест)|притвор\w* (пар|влюбл)", "fake"),
    (r"истинн\w* пар|предназначен\w* (друг другу|судьбой)|связь душ", "fated"),
    (r"морально сер|антигеро", "gray"), (r"grumpy|хмур\w* и солнечн|ворчун", "grumpy"),
    (r"запретн\w* (любов|чувств|страст|роман)", "forbid"), (r"любовн\w* треугольник", "triangle"),
    (r"избранн(ая|ой|ую|ица)|древн\w* пророчеств", "chosen")]]
EXTRA_LABEL = [(re.compile(r, re.I), t) for r, t in [
    (r"любовн\w* фэнтези|романтическ\w* фэнтези|ромэнтези|ромфант", "любовное фэнтези"),
    (r"подростк|young adult|юношеск|молод[её]жн", "young adult"), (r"любовн\w* роман|женский роман", "любовный роман")]]

REVIEWS_TXT = {}


def review_tags(wid):
    """настроения по отзывам Фантлаба: тег ставим, если о нём пишут хотя бы в двух отзывах и в трети всех"""
    d = get(f"{FL}/work/{wid}/responses?page=1&sort=rating", tries=2) or {}
    items = d.get("items") or []
    if not items:
        return []
    cnt = {}
    REVIEWS_TXT[wid] = " ".join((it.get("response_text") or "")[:1500] for it in items[:20])
    for it in items[:20]:
        txt = it.get("response_text") or ""
        for rx, t in REVIEW_RX:
            if rx.search(txt):
                cnt[t] = cnt.get(t, 0) + 1
    n = min(len(items), 20)
    return [t for t, k in sorted(cnt.items(), key=lambda x: -x[1]) if k >= 2 and k >= n / 3]


def strip_tags(s):
    return re.sub(r"\[/?[a-z]+(=\d+)?\]", "", s or "").strip()


def labels_of(cls):
    """все текстовые подписи из классификатора Фантлаба (жанры, места, время…)"""
    out = []
    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in ("label", "name", "title") and isinstance(v, str):
                    out.append(v)
                else:
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(cls)
    return out


def pages_of(w):
    for blk in (w.get("editions_blocks") or {}).values():
        for e in blk.get("list") or []:
            if e.get("pages"):
                return int(e["pages"])
    return 0


print("1. Фантлаб: новинки издательств", flush=True)
seen, cand = set(), []
for lang in (0, 1):
    for page in range(1, MAX_PAGES + 1):
        d = get(f"{FL}/pubnews?lang={lang}&sort=popularity&page={page}")
        objs = (d or {}).get("objects") or []
        if not objs:
            break
        for o in objs:
            w = o.get("the_only_work") or {}
            wid, name = w.get("work_id"), (o.get("name") or "").strip()
            if not wid or wid in seen or not CYR.search(name) or not BOOKISH.search((o.get("type_name") or "") + " " + (w.get("name_show_im") or "")):
                continue
            seen.add(wid)
            cand.append({"w": wid, "t": name, "a": strip_tags(o.get("autors")).split(",")[0].strip(), "pop": o.get("popularity") or 0,
                         "y": int((o.get("release_date") or o.get("approx_release_date") or "0")[:4] or 0), "ser": o.get("series") or "",
                         "lang": lang})
        print(f"   lang={lang} стр. {page}: всего {len(cand)}", flush=True)
        if page >= (d.get("page_count") or 0):
            break
        time.sleep(0.4)
print("   кандидатов:", len(cand), flush=True)

print("2. Подробности произведений", flush=True)
recs = []
for k, c in enumerate(cand):
    w = get(f"{FL}/work/{c['w']}/extended") or {}
    time.sleep(0.25)
    if w.get("work_type_name") and not BOOKISH.search(w.get("work_type_name") + " роман"):
        continue
    au = (w.get("authors") or [{}])[0]
    a = au.get("pseudoname") if au.get("real_name") == 0 and au.get("pseudoname") else au.get("name")
    a = strip_tags(a or c["a"]) or "Разные авторы"
    cls = w.get("classificatory") or {}
    labs = " ".join(labels_of(cls) + [c["ser"], w.get("work_description") or ""])
    # жанр: главный жанр по голосам читателей Фантлаба, затем серия и подписи, в последнюю очередь — описание
    main = ""
    for grp in (cls.get("genre_group") or []) if isinstance(cls, dict) else []:
        if str(grp.get("label", "")).startswith("Жанры"):
            top = sorted(grp.get("genre") or [], key=lambda x: -(x.get("percent") or 0))
            main = top[0].get("label", "") if top else ""
            break
    g = next((g for txt in (main, " ".join(labels_of(cls)) + " " + c["ser"], w.get("work_description") or "")
              for rx, g in GENRE_RX if txt and rx.search(txt)), "fantasy")
    tags = [t for rx, t in TAG_RX if rx.search(labs)]
    if int(w.get("val_responsecount") or 0) >= 2:
        time.sleep(0.25)
        tags += [t for t in review_tags(c["w"]) if t not in tags]
    tags = tags[:6]
    tags += [t for rx, t in EXTRA_LABEL if rx.search(labs) and t not in tags]
    tags += [t for rx, t in TROPE_RX if rx.search(labs + " " + REVIEWS_TXT.get(c["w"], ""))][:4]
    y = int(w.get("work_year") or 0) or c["y"] or YNOW
    if y < YNOW - 3:
        continue  # переиздание старой книги — в большом каталоге она и так есть
    voters = int(w.get("val_voters") or 0)
    s = (c["pop"] or 0) + voters * 2
    recs.append({"w": "f%d" % c["w"], "t": (w.get("work_name") or c["t"]).strip(), "a": a, "y": y, "g": g, "tags": tags,
                 "s": s, "pg": pages_of(w), "o": (w.get("work_name_orig") or "").strip(), "c": "Россия" if c["lang"] == 0 else ""})
    if k % 100 == 0:
        print(f"   {k}/{len(cand)}", flush=True)
# ---------- новинки не-фантастики: Викиданные (книги последних лет с русским названием) ----------
WD_ENDPOINTS = ["https://qlever.dev/api/wikidata", "https://qlever.cs.uni-freiburg.de/api/wikidata"]
WD_Q = """PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?w ?t ?a ?d (GROUP_CONCAT(DISTINCT ?gl; separator="|") AS ?g) WHERE {
  { ?w wdt:P31/wdt:P279* wd:Q7725634 } UNION { ?w wdt:P31/wdt:P279* wd:Q47461344 }
  ?w wdt:P577 ?d . FILTER(YEAR(?d) >= %d)
  ?w rdfs:label ?t . FILTER(LANG(?t) = "ru")
  ?w wdt:P50 ?au . ?au rdfs:label ?a . FILTER(LANG(?a) = "ru")
  OPTIONAL { ?w wdt:P136 ?ge . ?ge rdfs:label ?gl . FILTER(LANG(?gl) = "ru") }
} GROUP BY ?w ?t ?a ?d LIMIT 5000""" % (YNOW - 2)


def wd_rows():
    body = urllib.parse.urlencode({"query": WD_Q}).encode()
    for k in range(4):
        url = WD_ENDPOINTS[k % 2]
        try:
            req = urllib.request.Request(url, data=body, headers={**UA, "Accept": "text/tab-separated-values", "Content-Type": "application/x-www-form-urlencoded"})
            try:
                r = urllib.request.urlopen(req, timeout=300)
            except urllib.error.HTTPError as e:
                if e.code in (307, 308) and e.headers.get("Location"):
                    req = urllib.request.Request(urllib.parse.urljoin(url, e.headers["Location"]), data=body, headers=req.headers)
                    r = urllib.request.urlopen(req, timeout=300)
                else:
                    raise
            lines = r.read().decode("utf-8").split("\n")[1:]
            def cell(x):
                x = x.strip()
                if x.startswith("<"):
                    return x[1:-1].rsplit("/", 1)[-1]
                if x.startswith('"'):
                    return x[1:x.rfind('"')]
                return x
            return [[cell(x) for x in ln.split("\t")] for ln in lines if ln]
        except Exception as e:  # noqa
            print("   Викиданные:", repr(e), "— повтор", flush=True)
            time.sleep(30 * (k + 1))
    return []


print("3. Викиданные: книги последних лет", flush=True)
have_t = {re.sub(r"[^0-9a-zа-я]+", "", r["t"].lower().replace("ё", "е")) + "|" + r["a"] for r in recs}
wd_n = 0
for row in wd_rows():
    if len(row) < 4:
        continue
    qid, t, a, d = row[:4]
    glab = row[4] if len(row) > 4 else ""
    if not CYR.search(t) or not a:
        continue
    key = re.sub(r"[^0-9a-zа-я]+", "", t.lower().replace("ё", "е")) + "|" + a
    if key in have_t:
        continue
    have_t.add(key)
    g = next((g for rx, g in GENRE_RX if rx.search(glab)), "modern")
    tags = [x for rx, x in TAG_RX if rx.search(glab)] + [x for rx, x in EXTRA_LABEL if rx.search(glab)]
    recs.append({"w": "w" + qid.lstrip("Q"), "t": t, "a": a, "y": int(d[:4]) if d[:4].isdigit() else YNOW, "g": g, "tags": tags[:6],
                 "s": 0, "pg": 0, "o": "", "c": ""})
    wd_n += 1
print("   добавлено из Викиданных:", wd_n, flush=True)

# прошлые новинки не теряем: Фантлаб показывает только последние ~150 дней, а «Норе» нужна история за 3 года
try:
    prev = json.load(open(OUT, encoding="utf-8"))
    have = {r["w"] for r in recs}
    kept = 0
    for w, t, ai, y, gi, tg, q, sl, ci, aw, pg, rw, o in prev["b"]:
        if w in have or (y and y < YNOW - 3):
            continue
        au = prev["a"][ai]
        recs.append({"w": w, "t": t, "a": au[0], "y": y, "g": prev["g"][gi], "tags": [prev["tg"][j] for j in tg if prev["tg"][j] in TAGS],
                     "s": -1 + q, "pg": pg, "o": o or "", "c": prev["c"][au[1]] if au[1] >= 0 else "", "q0": q})
        kept += 1
    print("   из прошлых сборок сохранено:", kept, flush=True)
except FileNotFoundError:
    pass
recs.sort(key=lambda r: -r["s"])
if recs:
    srt = sorted(r["s"] for r in recs)
    p60, p90 = srt[int(len(srt) * .6)], srt[int(len(srt) * .9)]
    for r in recs:
        r["q"] = r["q0"] if "q0" in r else 3 if r["s"] >= p90 and r["s"] > 0 else 2 if r["s"] >= p60 and r["s"] > 0 else 1

GEN = ["classic", "modern", "detective", "fantasy", "scifi", "kids", "nonfic"]
CT = ["Россия"]
AU, AUI, rows = [], {}, []
for r in recs:
    if r["a"] not in AUI:
        AUI[r["a"]] = len(AU)
        AU.append([r["a"], 0 if r["c"] else -1])
    rows.append([r["w"], r["t"], AUI[r["a"]], r["y"], GEN.index(r["g"]), [TAGS.index(t) for t in r["tags"]], r["q"], 0, -1,
                 [], r["pg"], 0, r["o"] or 0])
out = {"meta": {"source": "Фантлаб: новинки издательств", "built": time.strftime("%Y-%m-%d"), "n": len(rows)},
       "c": CT, "g": GEN, "tg": TAGS, "aw": [], "a": AU, "b": rows}
print("   новинок:", len(rows), "первые:", [(r["t"], r["a"], r["y"]) for r in recs[:25]], flush=True)
if len(rows) < 50:
    raise SystemExit(f"Подозрительно мало новинок ({len(rows)}) — файл не перезаписан")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
print("   записано:", OUT, os.path.getsize(OUT) // 1024, "КБ", flush=True)
