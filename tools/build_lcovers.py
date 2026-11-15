#!/usr/bin/env python3
"""Настоящие обложки из ЛитРес для книг каталога, у которых своей обложки нет.

Для каждой книги (ручной каталог, популярные книги большого каталога, новинки) ищем её на ЛитРес
по названию и фамилии автора и берём обложку совпавшей книги. Результат — books/lcovers.json
{"название|фамилия": id обложки ЛитРес или 0, если не нашли}. Найденные не ищем снова,
ненайденные перепроверяем раз в месяц. Запуск: python3 tools/build_lcovers.py [часов на работу]."""
import json, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(ROOT, "books", "lcovers.json")
HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 4.5
H = {"User-Agent": "moya-nora-books/1.0 (https://moya-nora.github.io)", "Accept": "application/json"}
BAD = re.compile(r"кратк|пересказ|анализ|сочинени|аудио|комикс|манга|рабочая тетрадь|читательский дневник|summary")


def norm(s):
    return re.sub(r"[^0-9a-zа-я]+", "", str(s or "").lower().replace("ё", "е"))


def key(t, a):
    return norm(t) + "|" + norm(str(a or "").split(" ")[-1])


def search(q):
    u = "https://api.litres.ru/foundation/api/search?q=" + urllib.parse.quote(q) + "&types=text_book&limit=12"
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=30) as r:
                return (json.load(r).get("payload") or {}).get("data") or []
        except Exception as e:  # noqa: BLE001
            if i == 3:
                print("  ошибка поиска:", q, e)
                return None
            time.sleep(3 * (i + 1))


def persons(x):
    return " ".join(str(p.get("full_name") or "") + " " + str(p.get("full_name_rodit") or "") for p in (x.get("persons") or []))


def find(t, a):
    nt, sur = norm(t), norm(str(a or "").split(" ")[-1])
    if len(nt) < 2:
        return 0
    L = search(t + " " + str(a or "").split(" ")[-1])
    if L is None:
        return None
    best = None
    for d in L:
        x = d.get("instance") or {}
        tt = str(x.get("title") or "")
        if not x.get("cover_url") or x.get("is_draft") or BAD.search(tt.lower()):
            continue
        n = norm(tt)
        if not (n == nt or (len(nt) >= 6 and n.startswith(nt))):
            continue
        pn = norm(persons(x))
        if sur and pn and sur[:5] not in pn:
            continue
        if not pn and n != nt:
            continue
        sc = (2 if n == nt else 0) + (1 if x.get("art_type") == 0 else 0) + min((x.get("rating") or {}).get("rated_total_count") or 0, 5000) / 5000
        if not best or sc > best[0]:
            best = (sc, x["id"])
    return best[1] if best else 0


def main():
    app = open(os.path.join(ROOT, "app.html"), encoding="utf-8").read()
    i = app.index("const CAT=") + len("const CAT=")
    CAT, _ = json.JSONDecoder().raw_decode(app[i:])
    todo = [(b["t"], b.get("a") or "") for b in CAT]
    for fn, top in (("new.json", 100000), ("books.json", 9000)):
        d = json.load(open(os.path.join(ROOT, "books", fn), encoding="utf-8"))
        A = d["a"]
        rows = sorted(d["b"], key=lambda r: -(r[7] if len(r) > 7 and isinstance(r[7], (int, float)) else 0))[:top]
        for r in rows:
            if len(r) > 13 and r[13]:
                continue
            a = A[r[2]][0] if isinstance(r[2], int) and r[2] < len(A) else ""
            todo.append((r[1], a))
    for m in re.finditer(r'const (?:TREND|BOOKTOK|COZY_L|NIGHT_L|MAND_L|MONTH_L)="([^"]+)"', app):
        for p in m.group(1).split(";"):
            if "|" in p:
                t, s = p.split("|", 1)
                todo.insert(0, (t, s))
    try:
        res = json.load(open(OUT, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        res = {}
    meta = res.pop("_checked", {}) if isinstance(res.get("_checked"), dict) else {}
    now = int(time.time())
    seen, T0, n, found = set(), time.time(), 0, 0
    for t, a in todo:
        k = key(t, a)
        if k in seen or not k.split("|")[0]:
            continue
        seen.add(k)
        if res.get(k) or (k in res and now - meta.get(k, 0) < 30 * 86400):
            continue
        if time.time() - T0 > HOURS * 3600:
            break
        v = find(t, a)
        if v is None:
            continue
        res[k] = v
        if not v:
            meta[k] = now
        n += 1
        found += 1 if v else 0
        if n % 200 == 0:
            print(f"  {n}: найдено {found} — «{t}» {v}", flush=True)
            json.dump({**res, "_checked": meta}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        time.sleep(0.25)
    json.dump({**res, "_checked": meta}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"готово: проверено {n}, найдено {found}; всего с обложкой {sum(1 for v in res.values() if v)} из {len(res)}")


if __name__ == "__main__":
    main()
