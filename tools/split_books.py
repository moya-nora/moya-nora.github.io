#!/usr/bin/env python3
"""Делит большой каталог books/books.json на две части для приложения, чтобы оно не подвисало при запуске:
  books/books.core.json - известные книги (статей в Википедиях >= CORE_SL или есть статья в рувики): грузится сразу;
  books/books.rest.json - остальные (малоизвестные рассказы, стихи и т.п.): грузится, только когда человек начинает искать.
Формат обоих файлов - как у books.json (meta, c, g, tg, aw, a, b); списки авторов у каждой части свои.
books.json остаётся как есть (из него собирается сайт). Запуск: python3 tools/split_books.py (books.yml - после сборки)."""
import json, os

ROOT = os.path.join(os.path.dirname(__file__), "..", "books")
CORE_SL = int(os.environ.get("CORE_SL", "3"))


def part(d, rows, kind):
    amap, a = {}, []
    out = []
    for r in rows:
        ai = r[2]
        if ai not in amap:
            amap[ai] = len(a)
            a.append(d["a"][ai] if 0 <= ai < len(d["a"]) else ["", -1])
        r = list(r)
        r[2] = amap[ai]
        out.append(r)
    meta = dict(d.get("meta") or {}, part=kind, books=len(out))
    return {"meta": meta, "c": d["c"], "g": d["g"], "tg": d["tg"], "aw": d["aw"], "a": a, "b": out}


def main():
    d = json.load(open(os.path.join(ROOT, "books.json"), encoding="utf-8"))
    core, rest = [], []
    for r in d["b"]:
        sl = r[7] or 0
        rw = r[11] if len(r) > 11 else 0
        (core if sl >= CORE_SL or rw else rest).append(r)
    for name, rows, kind in (("books.core.json", core, "core"), ("books.rest.json", rest, "rest")):
        p = part(d, rows, kind)
        with open(os.path.join(ROOT, name), "w", encoding="utf-8") as f:
            json.dump(p, f, ensure_ascii=False, separators=(",", ":"))
        print(name, len(rows), "книг,", round(os.path.getsize(os.path.join(ROOT, name)) / 1e6, 1), "МБ")


if __name__ == "__main__":
    main()
