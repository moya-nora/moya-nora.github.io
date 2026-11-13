#!/usr/bin/env python3
"""Раз в неделю каждому подписчику бота: новости о его книгах (если он включил их в Норе) или «Шуршуня советует».

Новости (только для тех, кто включил «Новости о моих книгах» — их список в Firestore notify/<uid>, читает только бот):
  • книга из избранного со скидкой или в подписке ЛитРес; • новинка любимого автора; • друг дочитал книгу из избранного.
Бот входит в Firebase как nora-bot@login.moya-nora.github.io с паролем из секрета BOT_FB_PASS (аккаунт создаётся сам при первом запуске).

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
YNOW = int(time.strftime("%Y"))
FBKEY = re.search(r'apiKey:"([^"]+)"', app).group(1)
FS = "https://firestore.googleapis.com/v1/projects/nora-ed429/databases/(default)/documents/"
BOTMAIL = "nora-bot@login.moya-nora.github.io"


def http(url, data=None, headers=None, method=None):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None, headers={"Content-Type": "application/json", **(headers or {})}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.load(r), 200
    except urllib.error.HTTPError as e:
        return {"error": e.read()[:300].decode("utf-8", "replace")}, e.code
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}, 0


def fb_login():
    pw = os.environ.get("BOT_FB_PASS", "").strip()
    if not pw:
        print("нет секрета BOT_FB_PASS — новости о книгах пропускаю"); return None
    idt = "https://identitytoolkit.googleapis.com/v1/accounts:"
    j, c = http(idt + "signInWithPassword?key=" + FBKEY, {"email": BOTMAIL, "password": pw, "returnSecureToken": True})
    if c != 200 and "EMAIL_NOT_FOUND" in str(j) or c != 200 and "INVALID_LOGIN" in str(j) and os.environ.get("CREATE") == "1":
        j, c = http(idt + "signUp?key=" + FBKEY, {"email": BOTMAIL, "password": pw, "returnSecureToken": True})
        print("создан аккаунт бота:", c, (j or {}).get("localId"))
    if c != 200:
        print("вход бота не удался:", c, str(j)[:200]); return None
    return j["idToken"]


def notify_docs(tok):
    out, page = {}, ""
    while True:
        j, c = http(FS + "notify?pageSize=300" + ("&pageToken=" + page if page else ""), headers={"Authorization": "Bearer " + tok})
        if c != 200:
            print("список новостей недоступен:", c, str(j)[:200]); break
        for d in j.get("documents") or []:
            try:
                v = json.loads(d["fields"]["d"]["stringValue"]); v["uid"] = d["name"].rsplit("/", 1)[1]; out[str(v.get("tg"))] = v
            except Exception:  # noqa: BLE001
                pass
        page = j.get("nextPageToken") or ""
        if not page:
            break
    return out


def catalog_rows(fn):
    try:
        d = json.load(open(os.path.join(ROOT, "books", fn), encoding="utf-8"))
    except FileNotFoundError:
        return []
    A = d.get("a") or []
    return [{"t": r[1], "a": (A[r[2]][0] if r[2] < len(A) else ""), "y": r[3] or 0} for r in d.get("b") or []]


FRESH = [b for b in catalog_rows("new.json") + catalog_rows("litres.json") if b["y"] >= YNOW - 1]


def litres_find(t, a):
    j, c = http("https://api.litres.ru/foundation/api/search?q=" + urllib.parse.quote(t + " " + a) + "&types=text_book&limit=5", headers={"User-Agent": "moya-nora-bot/1.0"})
    for x in ((j or {}).get("payload") or {}).get("data") or []:
        x = x.get("instance") or x
        if norm(x.get("title")) == norm(t):
            return x
    return None


def profile_ev(uid):
    j, c = http(FS + "profiles/" + uid + "?key=" + FBKEY)
    try:
        return json.loads(j["fields"]["d"]["stringValue"]).get("ev") or [], (j["fields"].get("n") or {}).get("stringValue", "")
    except Exception:  # noqa: BLE001
        return [], ""


def news_for(nd, me):
    """До 5 новостей человеку; me['a'] — что уже присылали."""
    sentk = set(me.get("a") or []); out = []
    want = {norm(w["t"]): w for w in nd.get("want") or []}
    have = set(want) | set(nd.get("read") or [])
    fav = {norm(x) for x in nd.get("fav") or []}
    for b in FRESH:
        k = "n:" + norm(b["t"])
        if norm(b["a"]) in fav and norm(b["t"]) not in have and k not in sentk:
            out.append((k, f"📖 Новая книга автора, которого ты любишь: «{b['t']}» - {b['a']}")); sentk.add(k)
            if len(out) >= 2: break
    for uid in (nd.get("fr") or [])[:40]:
        ev, name = profile_ev(uid)
        for e in ev:
            k = f"f:{uid}:{norm(e.get('t'))}"
            if e.get("k") == "read" and norm(e.get("t")) in want and time.time() - (e.get("ts") or 0) / 1000 < 9 * 86400 and k not in sentk:
                r = f" и поставила {round(e['r'] / 2)}★" if e.get("r") is not None else ""
                out.append((k, f"👋 {name or 'Друг'} дочитал(а) «{e['t']}» из твоего избранного{r}")); sentk.add(k)
    for w in list(want.values())[:25]:
        x = litres_find(w["t"], w.get("a") or "")
        if not x:
            continue
        pr = x.get("prices") or {}
        if x.get("is_available_with_subscription") or x.get("is_available_with_litres_subscription"):
            k = "s:" + norm(w["t"])
            if k not in sentk:
                out.append((k, f"✨ «{w['t']}» из твоего избранного есть в подписке ЛитРес")); sentk.add(k)
        elif (pr.get("discount_percent") or 0) >= 20:
            k = f"d:{norm(w['t'])}:{week}"
            if k not in sentk:
                out.append((k, f"🏷 «{w['t']}» сейчас со скидкой {pr['discount_percent']}% на ЛитРес - {int(pr.get('final_price') or 0)} ₽")); sentk.add(k)
        time.sleep(0.3)
        if len(out) >= 5:
            break
    return out[:5]


NEWS = {}
tok = fb_login()
if tok:
    NEWS = notify_docs(tok)
    print("включили новости:", len(NEWS))
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
    nd = NEWS.get(chat)
    if nd:
        items = news_for(nd, me)
        if items:
            txt = "Новости о твоих книгах 📚\n\n" + "\n\n".join(html.escape(t) for _, t in items)
            print(chat, s.get("n"), "→ новости:", len(items))
            if not DRY:
                r, code = api("sendMessage", chat_id=int(chat), text=txt, parse_mode="HTML", reply_markup={"inline_keyboard": [[{"text": "Открыть Нору", "web_app": {"url": APP}}]]})
                if code == 403:
                    me["off"] = 1; continue
                if r:
                    me["wk"] = week; me["a"] = ((me.get("a") or []) + [k for k, _ in items])[-300:]; n += 1
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
