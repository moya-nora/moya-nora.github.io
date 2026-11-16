#!/usr/bin/env python3
"""Лёгкая копия каталога ЛитРес для приложения.

books/litres.json весит ~22 МБ, из них ~19 МБ - полные аннотации. Телефон скачивал и разбирал всё это при каждом открытии.
Здесь делаем:
  books/litres.lite.json - тот же формат, но аннотация обрезана до ~200 знаков (с «…» на конце),
                           а стандартный адрес обложки заменён на 1 (приложение восстановит его по номеру книги);
  books/ann/<k>.json     - полные аннотации обрезанных книг, 64 файла по номеру книги (k = номер % 64),
                           приложение подгружает один файл, когда человек открывает карточку.
Полный books/litres.json остаётся для сборки сайта (tools/build_seo.py).
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "books", "litres.json")
CUT, SHARDS = 200, 64


def main():
    d = json.load(open(SRC, encoding="utf-8"))
    shards = [dict() for _ in range(SHARDS)]
    out = []
    for r in d["b"]:
        r = list(r)
        w = str(r[0])
        num = int(w[1:]) if re.fullmatch(r"l\d+", w) else None
        if num is not None and r[13] == f"https://www.litres.ru/pub/c/cover/{num}.jpg":
            r[13] = 1
        an = r[14] or ""
        if num is not None and len(an) > CUT + 40:
            shards[num % SHARDS][w] = an
            short = an[:CUT].rsplit(" ", 1)[0].rstrip(" ,.;:-–—")
            r[14] = short + "…"
        out.append(r)
    lite = dict(d)
    lite["b"] = out
    json.dump(lite, open(os.path.join(ROOT, "books", "litres.lite.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    os.makedirs(os.path.join(ROOT, "books", "ann"), exist_ok=True)
    for k, sh in enumerate(shards):
        json.dump(sh, open(os.path.join(ROOT, "books", "ann", f"{k}.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("книг:", len(out), "обрезано аннотаций:", sum(len(s) for s in shards),
          "lite МБ:", round(os.path.getsize(os.path.join(ROOT, "books", "litres.lite.json")) / 1e6, 1))


if __name__ == "__main__":
    main()
