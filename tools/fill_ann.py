#!/usr/bin/env python3
"""Описания для книг сайта, у которых их нет.

tools/build_seo.py пишет books/ann_want.json - книги со страницами, но без описания: [[название, автор, ключ], ...].
Здесь для каждой ищем книгу на ЛитРес и берём аннотацию; результат - books/ann_extra.json {ключ: "описание" или ""}.
Пустая строка = искали и не нашли: такую книгу сборка сайта убирает (страница без описания бесполезна).
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_lcovers as L  # noqa: E402  поиск книги на ЛитРес по названию и автору

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P_WANT, P_OUT = os.path.join(ROOT, "books", "ann_want.json"), os.path.join(ROOT, "books", "ann_extra.json")


def get(path):
    import urllib.request
    for i in range(3):
        try:
            rq = urllib.request.Request("https://api.litres.ru/foundation/api/" + path, headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(rq, timeout=25) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            print("  повтор:", path, str(e)[:60])
            time.sleep(3 * (i + 1))
    return None


def clean(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = re.sub(r"НЕЗАКОННОЕ ПОТРЕБЛЕНИЕ НАРКОТИЧЕСКИХ СРЕДСТВ[^.]*?ОТВЕТСТВЕННОСТЬ\.?\s*", "", s, flags=re.I)
    return re.sub(r"\s+", " ", s).strip()


def main():
    want = json.load(open(P_WANT, encoding="utf-8")) if os.path.exists(P_WANT) else []
    out = json.load(open(P_OUT, encoding="utf-8")) if os.path.exists(P_OUT) else {}
    lcov = json.load(open(os.path.join(ROOT, "books", "lcovers.json"), encoding="utf-8"))
    n_ok = 0
    for t, a, k in want:
        if out.get(k):
            continue
        i = lcov.get(k) or L.find(t, a) or 0
        ann = ""
        if i:
            x = ((get(f"arts/{i}") or {}).get("payload") or {}).get("data") or {}
            ann = clean(x.get("html_annotation") or x.get("annotation") or "")
            if len(ann) < 60:
                ann = ""
        out[k] = ann
        n_ok += bool(ann)
        print(("ok  " if ann else "нет ") + t + " - " + a)
        time.sleep(0.3)
    json.dump(out, open(P_OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0, sort_keys=True)
    print("искали:", len(want), "нашли сейчас:", n_ok, "без описания:", sum(1 for v in out.values() if not v))


if __name__ == "__main__":
    main()
