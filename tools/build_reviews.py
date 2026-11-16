#!/usr/bin/env python3
"""Отзывы читателей ЛитРес для книг Норы (у ЛитРес их во много раз больше, чем на Фантлабе).

Для каждой книги с известным номером на ЛитРес (books/lcovers.json и книги каталога ЛитРес) берём оценку,
число оценок и до 12 самых полезных отзывов. Пишем books/rv/<номер>.json:
{"r": средняя 1-5, "v": оценок, "n": отзывов на ЛитРес, "lr"/"lv": оценка и число оценок LiveLib, "L": [[имя, год, оценка 1-5 или 0, текст], ...]}.
Свежие файлы (моложе 30 дней) не обновляем. Запуск: python3 tools/build_reviews.py [часов]."""
import html, json, os, re, sys, time, urllib.request, urllib.error

ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(ROOT, "books", "rv")
HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 4.5
H = {"User-Agent": "moya-nora-books/1.0 (https://moya-nora.github.io)", "Accept": "application/json"}
os.makedirs(OUT, exist_ok=True)


def get(path):
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request("https://api.litres.ru/foundation/api/" + path, headers=H), timeout=30) as r:
                return json.load(r).get("payload") or {}
        except urllib.error.HTTPError as e:
            if e.code in (404, 422):
                return None
            time.sleep(3 * (i + 1))
        except Exception:  # noqa: BLE001
            time.sleep(3 * (i + 1))
    return None


def clean(t):
    t = re.sub(r"<br\s*/?>|</p>\s*<p>", "\n", t or "")
    t = html.unescape(re.sub(r"<[^>]+>", "", t)).strip()
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t[:6000].rsplit(" ", 1)[0] + "…" if len(t) > 6000 else t   # отзыв целиком (раньше обрезали на 900 знаках)


ids = []
try:
    L = json.load(open(os.path.join(ROOT, "books", "lcovers.json"), encoding="utf-8"))
    ids += [v for k, v in L.items() if v and k[0] != "_"]
except FileNotFoundError:
    pass
try:
    d = json.load(open(os.path.join(ROOT, "books", "litres.json"), encoding="utf-8"))
    rows = sorted(d["b"], key=lambda r: -(r[7] if len(r) > 7 and isinstance(r[7], (int, float)) else 0))
    ids += [int(str(r[0])[1:]) for r in rows if str(r[0]).startswith("l") and str(r[0])[1:].isdigit()]
except Exception as e:  # noqa: BLE001
    print("litres.json:", e)
seen, T0, n, got = set(), time.time(), 0, 0
for aid in ids:
    if aid in seen:
        continue
    seen.add(aid)
    fp = os.path.join(OUT, f"{aid}.json")
    if os.path.exists(fp) and time.time() - os.path.getmtime(fp) < 30 * 86400 and '"full"' in open(fp, encoding="utf-8").read(400):
        continue
    if time.time() - T0 > HOURS * 3600:
        break
    art = get(f"arts/{aid}")
    if not art:
        continue
    a = art.get("data") or {}
    rt = a.get("rating") or {}
    rv = get(f"arts/{aid}/reviews?limit=12&order=popular") or get(f"arts/{aid}/reviews?limit=12") or {}
    out = []
    for x in rv.get("data") or []:
        if x.get("is_removed_by_moderator"):
            continue
        t = clean(x.get("text"))
        if len(t) < 40:
            continue
        mk = x.get("item_rating") or 0
        out.append([x.get("user_display_name") or "Читатель", str(x.get("created_at") or "")[:4], mk if isinstance(mk, (int, float)) else 0, t])
    n += 1
    if out or rt.get("rated_total_count"):
        got += 1
        json.dump({"r": rt.get("rated_avg") or 0, "v": rt.get("rated_total_count") or 0, "n": a.get("reviews_count") or len(out),
                   "full": 1, "lr": a.get("livelib_rated_avg") or 0, "lv": a.get("livelib_rated_count") or 0, "L": out},
                  open(fp, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    if n % 200 == 0:
        print(f"  {n}: с отзывами {got}", flush=True)
    time.sleep(0.2)
print(f"готово: обработано {n}, сохранено {got}, всего файлов {len(os.listdir(OUT))}")
