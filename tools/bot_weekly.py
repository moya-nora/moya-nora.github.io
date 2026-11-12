#!/usr/bin/env python3
"""Раз в неделю: «Шуршуня советует» — каждому подписчику бота одна книга с обложкой и кнопкой «Открыть в Норе».

Подписчики — tools/bot_state.json → subs (их собирает bot_relay.py: /start, сообщения, разрешение из Норы).
Что уже отправлено — tools/bot_weekly.json {chat: {"s": [ключи книг], "off": 1 если бот заблокирован}}.
DRY=1 — только показать, кому что ушло бы. Нужен секрет BOT_TOKEN."""
import html, json, os, random, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.join(os.path.dirname(__file__), "..")
TOKEN = os.environ.get("BOT_TOKEN", "").strip()
DRY = os.environ.get("DRY") == "1"
APP = "https://moya-nora.github.io/app.html"
SENT = os.path.join(ROOT, "tools", "bot_weekly.json")
if not TOKEN and not DRY:
    print("нет секрета BOT_TOKEN — пропускаю"); sys.exit(0)


def norm(s):
    return re.sub(r"[^0-9a-zа-я]+", "", str(s or "").lower().replace("ё", "е"))


def api(method, **p):
    req = urllib.request.Request(f"https://api.telegram.org/bot{TOKEN}/{method}", data=json.dumps(p).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r).get("result"), 200
    except urllib.error.HTTPError as e:
        print(method, e.code, e.read()[:200].decode("utf-8", "replace"))
        return None, e.code


app = open(os.path.join(ROOT, "app.html"), encoding="utf-8").read()
i = app.index("const CAT=") + len("const CAT=")
CAT, _ = json.JSONDecoder().raw_decode(app[i:])
cov = json.load(open(os.path.join(ROOT, "books", "covers.json"), encoding="utf-8"))
ck = lambda b: norm(b["t"]) + "|" + norm(str(b.get("a") or "").split(" ")[-1])
POOL = [b for b in CAT if (b.get("q") or 0) >= 3 and b.get("ann") and cov.get(ck(b)) and b.get("g") != "kids"]
print("книг для советов:", len(POOL))
subs = (json.load(open(os.path.join(ROOT, "tools", "bot_state.json"), encoding="utf-8")).get("subs") or {})
try:
    sent = json.load(open(SENT, encoding="utf-8"))
except FileNotFoundError:
    sent = {}
week = time.strftime("%G-%V")
INTRO = ["Шуршуня нашла для тебя книгу на эту неделю", "Новая находка Шуршуни", "Что почитать на неделе? Шуршуня советует", "Шуршуня принесла книгу"]
n = 0
ONLY = os.environ.get("ONLY", "").strip()
for chat, s in subs.items():
    if ONLY and chat != ONLY:
        continue
    if not s.get("on"):
        continue
    me = sent.setdefault(chat, {"s": []})
    if me.get("off") or me.get("wk") == week:
        continue
    rnd = random.Random(chat + week)
    left = [b for b in POOL if ck(b) not in me["s"]] or POOL
    b = rnd.choice(left)
    ann = b["ann"] if len(b["ann"]) <= 320 else b["ann"][:320].rsplit(" ", 1)[0] + "…"
    cap = f"{rnd.choice(INTRO)} 📚\n\n<b>{html.escape(b['t'])}</b>\n{html.escape(b.get('a') or '')}\n\n{html.escape(ann)}"
    kb = {"inline_keyboard": [[{"text": "Открыть в Норе", "web_app": {"url": APP + "?bk=" + urllib.parse.quote(b["t"] + "|" + (b.get("a") or ""))}}]]}
    print(chat, s.get("n"), "→", b["t"])
    if DRY:
        continue
    r, code = api("sendPhoto", chat_id=int(chat), photo=cov[ck(b)], caption=cap, parse_mode="HTML", reply_markup=kb)
    if not r and code not in (403,):
        r, code = api("sendMessage", chat_id=int(chat), text=cap, parse_mode="HTML", reply_markup=kb)
    if code == 403:
        me["off"] = 1
        continue
    if r:
        me["wk"] = week; me["s"] = (me["s"] + [ck(b)])[-60:]; n += 1
    time.sleep(0.2)
json.dump(sent, open(SENT, "w", encoding="utf-8"), ensure_ascii=False)
print("отправлено:", n)
