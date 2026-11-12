#!/usr/bin/env python3
"""Обложки для страниц сайта: настоящие обложки книг ручного каталога с Фантлаба.

Та же логика, что в приложении (findImg): ищем произведение на Фантлабе, берём самое свежее
русское издание с картинкой (не старше 1995 года). Если такого нет — пусто, сайт нарисует обложку сам.
Результат — books/covers.json {"название|фамилия": "адрес картинки" или ""}. Уже найденные не ищем снова,
пустые перепроверяем раз в полгода. Запуск: python3 tools/build_covers.py [сколько за раз]."""
import json, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(ROOT, "books", "covers.json")
LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
IMG = "https://fantlab.ru/images/editions/big/"


def norm(s):
    return re.sub(r"[^0-9a-zа-я]+", "", str(s or "").lower().replace("ё", "е"))


def key(t, a):
    return norm(t) + "|" + norm(str(a or "").split(" ")[-1])


def flj(path, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request("https://api.fantlab.ru" + path, headers={"User-Agent": "nora-covers/1.0 (moya-nora.github.io)"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


def find(t, a):
    sur = norm(str(a or "").split(" ")[-1])
    pic = lambda w: w.get("pic_edition_id") or w.get("pic_edition_id_auto")

    def pick(L):
        L = [w for w in (L if isinstance(L, list) else []) if pic(w)]
        return next((w for w in L if not sur or sur in norm(w.get("autor_rusname")) or sur in norm(w.get("autor_name"))), None) or \
            next((w for w in L if norm(w.get("rusname") or w.get("name")) == norm(t)), None)

    w = pick(flj("/search-works?q=" + urllib.parse.quote(t) + "&page=1&onlymatches=1"))
    if not w:
        t2 = re.sub(r"\s+", " ", re.sub(r"[«»\"'’.,:;!?()—–-]+", " ", t)).strip()
        w = pick(flj("/search-works?q=" + urllib.parse.quote(t2 + (" " + str(a).split(" ")[-1] if a else "")) + "&page=1"))
    if not w:
        return ""
    j = flj(f"/work/{w['work_id']}/extended")
    eds = [e for b in (j.get("editions_blocks") or {}).values() for e in (b.get("list") or [])]
    eds = [e for e in eds if (e.get("pic_num") or 0) > 0 and (not e.get("lang_code") or e.get("lang_code") == "ru") and not e.get("plandate")]
    eds.sort(key=lambda e: (-(e.get("year") or 0), 0 if e.get("type") == 10 else 1))
    if not eds:
        return IMG + str(pic(w))
    fresh = [e for e in eds if (e.get("year") or 0) >= 1995]
    if not fresh:
        return ""
    single = [e for e in fresh if e.get("type") == 10]
    return IMG + str((single or fresh)[0]["edition_id"])


app = open(os.path.join(ROOT, "app.html"), encoding="utf-8").read()
i = app.index("const CAT=") + len("const CAT=")
CAT, _ = json.JSONDecoder().raw_decode(app[i:])
try:  # плюс книги из подборок сайта, которых нет в ручном каталоге (список готовит build_seo.py)
    CAT += [{"t": t, "a": a} for t, a in json.load(open(os.path.join(ROOT, "books", "covers_want.json"), encoding="utf-8"))]
except FileNotFoundError:
    pass
try:
    have = json.load(open(OUT, encoding="utf-8"))
except FileNotFoundError:
    have = {}
meta = have.pop("_t", {})
now = int(time.time())
todo = [b for b in CAT if key(b["t"], b.get("a")) not in have or (have[key(b["t"], b.get("a"))] == "" and now - meta.get(key(b["t"], b.get("a")), 0) > 180 * 86400)]
print("в каталоге", len(CAT), "уже есть", sum(1 for v in have.values() if v), "к поиску", len(todo))
found = 0
for n, b in enumerate(todo[:LIMIT]):
    k = key(b["t"], b.get("a"))
    try:
        u = find(b["t"], b.get("a", ""))
    except Exception as e:  # noqa: BLE001
        print("  ошибка", b["t"], e)
        continue
    have[k] = u
    meta[k] = now
    found += bool(u)
    if n % 100 == 0:
        print(f"  {n}/{min(len(todo), LIMIT)}: найдено {found} — «{b['t']}» {u[-12:] if u else '—'}", flush=True)
        json.dump({**have, "_t": meta}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    time.sleep(0.25)
json.dump({**have, "_t": meta}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("готово: с обложкой", sum(1 for k, v in have.items() if v), "из", len(have))
