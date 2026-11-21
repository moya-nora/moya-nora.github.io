#!/usr/bin/env python3
"""Весь ЛитРес для поиска Норы (кроме аудио, учебников, журналов и черновиков самиздата).

Сбор идёт частями: python3 tools/litres_all.py crawl <часть> <всего частей>  -> books/lr/part-<часть>.json
Каждая часть обходит свои жанры ЛитРес (самые мелкие, без вложенных) целиком, страница за страницей.
Потом: python3 tools/litres_all.py merge  -> books/lrall/<ключ>.json и books/lrall/index.json
Ключ - первые буквы названия («t_за») или фамилии автора («a_ми»); большие кусочки делятся на 3 буквы.
Приложение при поиске скачивает только нужные кусочки (по 50-300 КБ).
Строка книги: [номер ЛитРес, название, автор, год, жанр Норы, оценка×10, оценок, 18+, страниц]."""
import json, os, re, sys, time, urllib.request

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
API = "https://api.litres.ru/foundation/api/"
H = {"User-Agent": "moya-nora-books/1.0 (https://nora-books.ru)", "Accept": "application/json"}
START = time.time()
SKIP_G = re.compile(r"\d+\s*класс|егэ|огэ|впр|учебн|пособи|методич|журнал|газет|справочн|словар|рабочая тетрадь|контурн|школьн|для вузов|экзамен|аудиоспектакл|подкаст", re.I)
G_MAP = [(r"фэнтези|попадан|магическ", "fantasy"), (r"фантастик|киберпанк|постапокал|космическ", "scifi"), (r"детектив|триллер|боевик|криминал", "detective"),
         (r"классик|19 века|20 века|советская|драматург|пьес|поэзи", "classic"), (r"детск|подрост|сказк|young adult", "kids"),
         (r"бизнес|психолог|саморазв|наук|научпоп|финанс|экономик|маркетинг|менеджмент|медицин|здоров|истори[яи]|биограф|мемуар|философ|религ|эзотер|кулинар|хобби|дом и семья|спорт|путешеств|политик|право|культурол|документальн|публицист|педагог|воспитан|компьютер|программир|техник|образован", "nonfic")]
G_MAP = [(re.compile(r, re.I), g) for r, g in G_MAP]
G_ = ["classic", "modern", "detective", "fantasy", "scifi", "kids", "nonfic"]
norm = lambda s: re.sub(r"[^0-9a-zа-я]", "", str(s or "").lower().replace("ё", "е"))


def get(path, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(API + path, headers=H), timeout=40) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            print("  !", path, e, flush=True)
            time.sleep(4 * (k + 1))
    return None


def leaves():
    tree = (get("genres?limit=500") or {}).get("payload", {}).get("data", [])
    out = []

    def walk(nodes, path):
        for n in nodes or []:
            p = path + [n.get("name", "")]
            if n.get("subgenres"):
                walk(n["subgenres"], p)
            else:
                out.append((n["id"], " / ".join(p), n))
    walk(tree, [])
    seen, L = set(), []
    for gid, path, n in out:
        if gid in seen or SKIP_G.search(path):
            continue
        seen.add(gid)
        L.append((gid, path, n))
    return sorted(L, key=lambda x: x[0])


def nora_genre(path):
    for rx, g in G_MAP:
        if rx.search(path):
            return g
    if re.search(r"любов|роман", path, re.I):
        return "modern"
    return "modern"


def crawl(part, parts):
    L = [x for i, x in enumerate(leaves()) if i % parts == part]
    if L:
        print("пример жанра:", json.dumps({k: v for k, v in L[0][2].items() if k != "subgenres"}, ensure_ascii=False)[:600], flush=True)
    books, stat = {}, []
    for gi, (gid, path, n) in enumerate(L):
        if time.time() - START > 5.0 * 3600:
            print("время вышло на жанре", gi, "из", len(L), flush=True); break
        g, got, off, total = nora_genre(path), 0, 0, None
        while True:
            d = get(f"genres/{gid}/arts?limit=50&offset={off}&o=popular&art_types=text_book")
            pl = (d or {}).get("payload") or {}
            if total is None:
                pg = pl.get("pagination") or {}
                total = pg.get("total") or pg.get("count") or n.get("arts_count") or n.get("count")
            data = pl.get("data") or []
            if not data:
                break
            for x in data:
                if x.get("art_type") not in (0, None) or x.get("is_draft") or not x.get("title") or not x.get("id"):
                    continue
                au = next((p.get("full_name") for p in x.get("persons") or [] if p.get("role") == "author"), "")
                if not au:
                    continue
                rt = x.get("rating") or {}
                nv = rt.get("rated_total_count") or 0
                y = int(str(x.get("date_written_at") or x.get("available_from") or "0")[:4] or 0)
                books[x["id"]] = [x["id"], x["title"].strip(), au.strip(), y, G_.index(g), round((rt.get("rated_avg") or 0) * 10) if nv >= 5 else 0, nv,
                                  1 if (x.get("is_adult_content") or (x.get("min_age") or 0) >= 18) else 0, round((x.get("symbols_count") or 0) / 2000) or 0]
                got += 1
            off += 50
            if len(data) < 50:
                break
            time.sleep(0.25)
        stat.append([gid, path, got, total])
        if gi % 20 == 0:
            print(f"  {gi}/{len(L)} {path}: {got} (у ЛитРес: {total}), всего книг: {len(books)}", flush=True)
    os.makedirs(os.path.join(ROOT, "books", "lr"), exist_ok=True)
    json.dump({"b": list(books.values()), "stat": stat}, open(os.path.join(ROOT, "books", "lr", f"part-{part}.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("часть", part, "книг:", len(books), "жанров:", len(stat), flush=True)


def surname(a):
    w = [x for x in re.split(r"\s+", str(a or "").strip()) if x]
    return w[-1] if w else ""


def merge():
    import glob
    B, stat = {}, []
    for f in sorted(glob.glob(os.path.join(ROOT, "books", "lr", "part-*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        for r in d["b"]:
            B.setdefault(r[0], r)
        stat += d.get("stat") or []
    # запрещённые книги и авторы - тот же список, что в приложении (tools/ban.py)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from ban import is_ban
    rows = [r for r in B.values() if not is_ban(r[1], r[2]) and not re.search(r"комплект из|\(комплект", r[1], re.I)]
    rows.sort(key=lambda r: (-r[6], r[0]))
    # кусочки по первым буквам названия и фамилии; большие - по трём буквам
    def keys_for(r):
        t, s = norm(r[1]), norm(surname(r[2]))
        return [("t", t), ("a", s)]
    buckets = {}
    for r in rows:
        for ns, w in keys_for(r):
            if len(w) < 2:
                continue
            buckets.setdefault((ns, w[:2]), []).append((w, r))
    out = {}
    for (ns, k2), L in buckets.items():
        if len(L) <= 2500:
            out[f"{ns}_{k2}"] = [r for _, r in L]
        else:
            for w, r in L:
                out.setdefault(f"{ns}_{w[:3] if len(w) >= 3 else w}", []).append(r)
    D = os.path.join(ROOT, "books", "lrall")
    os.makedirs(D, exist_ok=True)
    for f in glob.glob(os.path.join(D, "*.json")):
        os.remove(f)
    for k, L in out.items():
        json.dump(L, open(os.path.join(D, k + ".json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    tot = sum(int(s[3] or 0) for s in stat if str(s[3] or "").isdigit() or isinstance(s[3], int))
    json.dump({"built": time.strftime("%Y-%m-%d"), "n": len(rows), "litres_total": tot, "keys": {k: len(v) for k, v in sorted(out.items())},
               "genres": len(stat), "short": [s for s in stat if s[3] and isinstance(s[3], int) and s[2] < 0.8 * s[3]][:200]},
              open(os.path.join(D, "index.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("книг:", len(rows), "кусочков:", len(out), "у ЛитРес в жанрах всего:", tot, "МБ:",
          round(sum(os.path.getsize(os.path.join(D, k + ".json")) for k in out) / 1e6, 1))


if __name__ == "__main__":
    if sys.argv[1] == "crawl":
        crawl(int(sys.argv[2]), int(sys.argv[3]))
    else:
        merge()
