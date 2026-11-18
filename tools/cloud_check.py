#!/usr/bin/env python3
"""Проверка облака Норы из GitHub Actions (бот nora-bot, секрет BOT_FB_PASS): проходят ли записи, которые делает приложение.
Сейчас: приглашение в клуб через requests (s="c") - пишет заявку самому себе и сразу удаляет. Запуск вручную: workflow cloud_check."""
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
    for s in ["p"]:
        doc = f"requests/{uid}_{uid}"
        fields = {"f": {"stringValue": uid}, "t": {"stringValue": uid}, "n": {"stringValue": "проверка"}, "s": {"stringValue": s}, "ts": {"integerValue": "1"}, "k": {"stringValue": "cl:check"}}
        r, c = http(FS + doc, {"fields": fields}, H, "PATCH")
        print(f"запись заявки s={s}:", c, "" if c == 200 else str(r)[:300])
        r2, c2 = http(FS + doc, None, H, "DELETE"); print("  удаление:", c2)

main()
