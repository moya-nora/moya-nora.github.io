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
