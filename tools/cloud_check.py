#!/usr/bin/env python3
"""Проверка облака Норы из GitHub Actions (бот nora-bot, секрет BOT_FB_PASS): проходят ли записи, которые делает приложение.
Сейчас: может ли бот читать заявки других (для уведомлений в Telegram) - только коды ответа, без данных. Запуск вручную: workflow cloud_check."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from bot_stats import http, BOTMAIL, FS, ROOT  # noqa: E402

def main():
    pw = os.environ.get("BOT_FB_PASS", "").strip()
    app = open(os.path.join(ROOT, "app.html"), encoding="utf-8").read()
    key = re.search(r'apiKey:"([^"]+)"', app).group(1)
    j, c = http("https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=" + key, {"email": BOTMAIL, "password": pw, "returnSecureToken": True})
    if c != 200:
        print("вход не удался", c, j); return
    H = {"Authorization": "Bearer " + j["idToken"]}; uid = j["localId"]
    q = lambda w: {"structuredQuery": {"from": [{"collectionId": "requests"}], **({"where": w} if w else {}), "limit": 3}}
    r, c = http(FS[:-len("documents/")] + "documents:runQuery", q(None), H)
    print("чтение всех заявок:", c, "" if c == 200 else str(r)[:200], "найдено:", sum(1 for x in r if x.get("document")) if c == 200 and isinstance(r, list) else "")
    w = {"fieldFilter": {"field": {"fieldPath": "s"}, "op": "EQUAL", "value": {"stringValue": "p"}}}
    r, c = http(FS[:-len("documents/")] + "documents:runQuery", q(w), H)
    print("чтение заявок s=p:", c, "" if c == 200 else str(r)[:200])
    r, c = http(FS + "requests?pageSize=3", None, H)
    print("список заявок:", c, "" if c == 200 else str(r)[:200])

main()
