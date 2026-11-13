"""Публикует пост в канал @nora_bookworld от имени бота. Текст — HTML-файл из tools/channel/."""
import json, os, sys, urllib.request
TOKEN = os.environ["BOT_TOKEN"]; CH = os.environ.get("CHANNEL", "@nora_bookworld")
text = open(sys.argv[1], encoding="utf-8").read().strip()
kb = {"inline_keyboard": [[{"text": "Подобрать книгу под мой вкус", "url": "https://t.me/Wonderbookworld_bot?start=channel"}]]}
body = json.dumps({"chat_id": CH, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True, "reply_markup": kb}).encode()
req = urllib.request.Request(f"https://api.telegram.org/bot{TOKEN}/sendMessage", body, {"Content-Type": "application/json"})
try:
    r = json.load(urllib.request.urlopen(req, timeout=30)); print("ok", r["ok"], r["result"]["message_id"])
except urllib.error.HTTPError as e:
    print("error", e.code, e.read().decode()); sys.exit(1)
