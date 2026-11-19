"""Правка уже вышедших постов канала @nora_bookworld по списку tools/channel/edits.json.

Формат: [{"msg": номер сообщения в канале, "file": "intro.html"} или {"msg": ..., "text": "..."}]. Сделанные правки пишутся в
tools/channel/edits_done.json, второй раз не выполняются. Запускается сам при изменении edits.json (.github/workflows/channel_edit.yml).
Правит только текстовые посты бота; под постом остаётся кнопка «Подобрать книгу под мой вкус»."""
import json, os, sys, urllib.request, urllib.error
TOKEN = os.environ["BOT_TOKEN"]; CH = os.environ.get("CHANNEL", "@nora_bookworld")
HERE = os.path.dirname(os.path.abspath(__file__))
BOT = "https://t.me/Wonderbookworld_bot"
E = json.load(open(os.path.join(HERE, "channel", "edits.json"), encoding="utf-8"))
dp = os.path.join(HERE, "channel", "edits_done.json")
done = json.load(open(dp)) if os.path.exists(dp) else []
for e in E:
    key = f"{e['msg']}:{e.get('file') or e.get('text', '')[:40]}"
    if key in done:
        continue
    text = open(os.path.join(HERE, "channel", e["file"]), encoding="utf-8").read().strip() if e.get("file") else e["text"]
    kb = {"inline_keyboard": [[{"text": e.get("btn", "Подобрать книгу под мой вкус"), "url": BOT + "?startapp=channel"}]]}
    d = {"chat_id": CH, "message_id": int(e["msg"]), "text": text, "parse_mode": "HTML", "disable_web_page_preview": True, "reply_markup": kb}
    req = urllib.request.Request(f"https://api.telegram.org/bot{TOKEN}/editMessageText", json.dumps(d).encode(), {"Content-Type": "application/json"})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=30)); print("ok", e["msg"], r.get("ok"))
        done.append(key)
    except urllib.error.HTTPError as x:
        print("не вышло", e["msg"], x.code, x.read().decode()[:300])
json.dump(done, open(dp, "w"))
