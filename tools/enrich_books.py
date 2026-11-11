#!/usr/bin/env python3
"""Настроения для большого каталога по отзывам и голосам читателей Фантлаба — books/tags.json.

Каждый запуск берёт следующую порцию книг из books/books.json (сначала самые известные, с русским названием),
находит каждую на Фантлабе, читает классификатор (голоса читателей) и до 20 отзывов и ставит метки настроения.
Результаты накапливаются: books/tags.json = {"meta":…, "tg":[метки], "m":{QID:[id на Фантлабе или 0, "ГГГГ-ММ", [№ меток]]}}.
Книга перепроверяется раз в год. Порция — ENRICH_N книг (по умолчанию 2500)."""
import json, os, re, sys, time, urllib.error, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(__file__))
N = int(os.environ.get("ENRICH_N", "2500"))
MAX_MIN = int(os.environ.get("ENRICH_MINUTES", "200"))  # не выходить за лимит времени GitHub
ROOT = os.path.join(os.path.dirname(__file__), "..", "books")
OUT = os.path.join(ROOT, "tags.json")
FL = "https://api.fantlab.ru"
UA = {"User-Agent": "moya-nora-books/1.0 (https://github.com/moya-nora/moya-nora.github.io)", "Accept": "application/json"}
YM = time.strftime("%Y-%m")
T0 = time.time()


def get(url, tries=3):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(5 * (k + 1))
        except Exception:  # noqa
            time.sleep(5 * (k + 1))
    return None


norm = lambda s: re.sub(r"[^0-9a-zа-я]+", "", str(s or "").lower().replace("ё", "е"))
CYR = re.compile(r"[а-яё]", re.I)

# метки — те же слова, на которые смотрят фильтры «Норы»
LABEL_RX = [(re.compile(r, re.I), t) for r, t in [
    (r"приключенческ|боевик|динамичн", "динамичное"), (r"приключ", "приключения"), (r"юмористич|ирони|сатир", "смешное"),
    (r"философ", "философский роман"), (r"психологич", "психологический роман"), (r"интеллектуал|социальн", "интеллектуальное"),
    (r"романтич|любовн", "романтичное"), (r"хоррор|ужас", "хоррор"), (r"мистик", "мистика"), (r"мрачн|готик|нуар", "мрачное"),
    (r"триллер|напряж|остросюжет", "напряжённое"), (r"детектив", "детектив"), (r"антиутоп", "антиутопия"), (r"постапокалип", "постапокалипсис"),
    (r"сказ", "сказка"), (r"трагич|драматич", "грустное")]]
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


def labels_of(x, out):
    if isinstance(x, dict):
        for k, v in x.items():
            if k == "label" and isinstance(v, str):
                out.append(v)
            else:
                labels_of(v, out)
    elif isinstance(x, list):
        for v in x:
            labels_of(v, out)
    return out


def find_work(title, author):
    sur = norm(author.split()[-1]) if author else ""
    q = title + (" " + author.split()[-1] if author else "")
    res = get(f"{FL}/search-works?q={urllib.parse.quote(q)}&page=1&onlymatches=1")
    L = res if isinstance(res, list) else (res or {}).get("matches") or []
    nt = norm(title)
    for w in L[:8]:
        au = norm(" ".join(str(w.get(k) or "") for k in ("autor_rusname", "autor_name", "all_autor_rusname", "all_autor_name")))
        names = [norm(w.get(k)) for k in ("rusname", "name", "work_name", "altname")]
        if sur and sur not in au:
            continue
        if any(n and (n == nt or (len(nt) > 6 and (n.startswith(nt) or nt.startswith(n)))) for n in names) or not any(names):
            return w.get("work_id")
    return None


def tags_for(fid):
    w = get(f"{FL}/work/{fid}/extended") or {}
    time.sleep(0.2)
    labs = " ".join(labels_of(w.get("classificatory") or {}, []))
    tags = [t for rx, t in LABEL_RX if rx.search(labs)] + [t for rx, t in EXTRA_LABEL if rx.search(labs)]
    revtxt = ""
    if int(w.get("val_responsecount") or 0) >= 2:
        d = get(f"{FL}/work/{fid}/responses?page=1&sort=rating") or {}
        time.sleep(0.2)
        items = (d.get("items") or [])[:20]
        revtxt = " ".join((it.get("response_text") or "")[:1500] for it in items)
        cnt = {}
        for it in items:
            for rx, t in REVIEW_RX:
                if rx.search(it.get("response_text") or ""):
                    cnt[t] = cnt.get(t, 0) + 1
        n = len(items)
        tags += [t for t, k in sorted(cnt.items(), key=lambda x: -x[1]) if n and k >= 2 and k >= n / 3 and t not in tags]
    tags = tags[:8]
    desc = w.get("work_description") or ""
    return tags + [t for rx, t in TROPE_RX if rx.search(desc + " " + revtxt)][:4]


cat = json.load(open(os.path.join(ROOT, "books.json"), encoding="utf-8"))
try:
    prev = json.load(open(OUT, encoding="utf-8"))
except FileNotFoundError:
    prev = {"tg": [], "m": {}}
TG = list(prev.get("tg") or [])
M = prev.get("m") or {}
tix = lambda t: TG.index(t) if t in TG else (TG.append(t) or len(TG) - 1)
year_ago = time.strftime("%Y-%m", time.gmtime(time.time() - 365 * 864e2))

todo = []
for r in cat["b"]:  # каталог уже отсортирован: сначала самые известные
    q, t = str(r[0]), r[1]
    if not CYR.search(t):
        continue
    if q in M and M[q][1] >= year_ago:
        continue
    todo.append(r)
    if len(todo) >= N:
        break
print(f"В очереди: {len(todo)}; уже размечено: {len(M)}", flush=True)

found = tagged = 0
for k, r in enumerate(todo):
    if (time.time() - T0) / 60 > MAX_MIN:
        print("Время вышло — остальное в следующий раз", flush=True)
        break
    q, t, au = str(r[0]), r[1], cat["a"][r[2]][0] if r[2] < len(cat["a"]) else ""
    fid = find_work(t, au)
    time.sleep(0.2)
    tags = tags_for(fid) if fid else []
    found += bool(fid)
    tagged += bool(tags)
    M[q] = [fid or 0, YM, [tix(x) for x in tags]]
    if k % 100 == 0:
        print(f"  {k}/{len(todo)}: найдено на Фантлабе {found}, с метками {tagged} — «{t}»: {tags}", flush=True)
        json.dump({"meta": {"built": time.strftime("%Y-%m-%d"), "n": len(M)}, "tg": TG, "m": M},
                  open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

json.dump({"meta": {"built": time.strftime("%Y-%m-%d"), "n": len(M), "tagged": sum(1 for v in M.values() if v[2])}, "tg": TG, "m": M},
          open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(f"Готово: найдено {found}, с метками {tagged}; всего в файле {len(M)}", flush=True)
