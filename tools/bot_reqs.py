#!/usr/bin/env python3
"""Бот сразу пишет о заявке в друзья и о приглашении в книжный клуб.

Вызывается из дежурства бота (bot_relay.py) примерно раз в минуту: tick(state, save).
Кому: тем, у кого в Норе включены напоминания в Telegram (запись notify/<uid> с полем tg).
Что: заявки requests/* не старше двух суток (статус "p", а по ссылке-приглашению - уже "a"):
  • k пустой - «Имя хочет добавить тебя в друзья»;
  • k = "cl:<id клуба>" - «Имя зовёт тебя в книжный клуб «Название»»;
  • другой k (пришли по ссылке-приглашению) - «Имя в Норе по твоему приглашению - теперь вы друзья».
Отправленное помнится в state["rq"] (id заявки + время), чтобы не писать дважды.
Бот входит в Firebase как nora-bot (секрет BOT_FB_PASS). Если облако не даёт читать заявки - молча пропускает.
DRY=1 - только показать тексты."""
import html, json, os, re, time, urllib.request

ROOT = os.path.join(os.path.dirname(__file__), "..")
TOKEN = os.environ.get("BOT_TOKEN", "").strip()
PW = os.environ.get("BOT_FB_PASS", "").strip()
DRY = os.environ.get("DRY") == "1"
BOTMAIL = "nora-bot@login.moya-nora.github.io"
DB = "https://firestore.googleapis.com/v1/projects/nora-ed429/databases/(default)/documents"
APP = "https://nora-books.ru/app.html"
FRESH = 2 * 86400 * 1000

_s = {"tok": None, "tok_t": 0, "people": {}, "people_t": 0, "last": 0, "off": False, "clubs": {}}


def http(url, data=None, headers=None):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None,
                                 headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r), 200
    except urllib.error.HTTPError as e:
        return {"error": e.read()[:200].decode("utf-8", "replace")}, e.code
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}, 0


def _auth():
    if _s["tok"] and time.time() - _s["tok_t"] < 45 * 60:
        return {"Authorization": "Bearer " + _s["tok"]}
    app = open(os.path.join(ROOT, "app.html"), encoding="utf-8").read()
    key = re.search(r'apiKey:"([^"]+)"', app).group(1)
    j, c = http("https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=" + key,
                {"email": BOTMAIL, "password": PW, "returnSecureToken": True})
    if c != 200:
        print("заявки: вход бота не удался", c)
        return None
    _s["tok"], _s["tok_t"] = j["idToken"], time.time()
    return {"Authorization": "Bearer " + _s["tok"]}


def _people(H):
    """uid → chat id в Telegram (у кого включены напоминания). Обновляется раз в 10 минут."""
    if time.time() - _s["people_t"] < 600:
        return _s["people"]
    out, page = {}, ""
    while True:
        j, c = http(DB + "/notify?pageSize=300" + ("&pageToken=" + page if page else ""), headers=H)
        if c != 200:
            return _s["people"]
        for doc in j.get("documents") or []:
            try:
                v = json.loads(doc["fields"]["d"]["stringValue"])
                if v.get("tg"):
                    out[doc["name"].rsplit("/", 1)[1]] = str(v["tg"])
            except Exception:  # noqa: BLE001
                pass
        page = j.get("nextPageToken") or ""
        if not page:
            break
    _s["people"], _s["people_t"] = out, time.time()
    return out


def _club_name(cid, H):
    if cid not in _s["clubs"]:
        j, c = http(DB + "/clubs/" + cid, headers=H)
        _s["clubs"][cid] = (j.get("fields") or {}).get("n", {}).get("stringValue", "") if c == 200 else ""
    return _s["clubs"][cid]


def text_for(q, club=""):
    """Текст и кнопка. q["k"]: пусто - заявка в друзья, "cl:<id>" - клуб, иное - пришли по ссылке-приглашению."""
    who = (q.get("n") or "").strip()[:40] or "Кто-то"
    k = q.get("k") or ""
    if k.startswith("cl:"):
        return f"📚 {who} зовёт тебя в книжный клуб" + (f" «{club}»" if club else "") + ".", "Открыть клуб"
    if k:   # пришли по ссылке-приглашению: приложение само добавит в друзья
        return f"🎉 {who} в Норе по твоему приглашению - теперь вы друзья.", "Открыть Нору"
    return f"👋 {who} хочет добавить тебя в друзья в Норе.", "Открыть Нору"


def tick(state, save=None, force=False):
    """Один проход. Возвращает число отправленных."""
    if _s["off"] or not PW or (not TOKEN and not DRY):
        return 0
    if not force and time.time() - _s["last"] < 60:
        return 0
    _s["last"] = time.time()
    H = _auth()
    if not H:
        return 0
    q = {"structuredQuery": {"from": [{"collectionId": "requests"}],
                             "where": {"fieldFilter": {"field": {"fieldPath": "s"}, "op": "IN",
                                                       "value": {"arrayValue": {"values": [{"stringValue": "p"}, {"stringValue": "a"}]}}}},
                             "limit": 500}}
    L, c = http(DB + ":runQuery", q, H)
    if c == 403:
        print("заявки: облако не даёт боту читать requests - уведомления выключены до правки правил")
        _s["off"] = True
        return 0
    if c != 200 or not isinstance(L, list):
        return 0
    people, now, n = _people(H), int(time.time() * 1000), 0
    sent = state.setdefault("rq", [])
    for x in L:
        d = x.get("document")
        if not d:
            continue
        f = d.get("fields") or {}
        g = lambda k: (f.get(k) or {}).get("stringValue", "")
        r = {"id": d["name"].rsplit("/", 1)[1], "s": g("s"), "f": g("f"), "t": g("t"), "n": g("n"), "k": g("k"),
             "ts": int((f.get("ts") or {}).get("integerValue") or 0)}
        mark = r["id"] + ":" + str(r["ts"]) + r["s"]
        # принятые заявки интересны только с меткой ссылки-приглашения (k не пустой и не клуб)
        if r["s"] == "a" and (not r["k"] or r["k"].startswith("cl:")):
            continue
        if r["s"] == "p" and r["k"] and not r["k"].startswith("cl:"):
            continue
        if mark in sent or now - r["ts"] > FRESH or r["f"] == r["t"] or r["t"] not in people:
            continue
        cid = r["k"][3:] if r["k"].startswith("cl:") else ""
        txt, btn = text_for(r, _club_name(cid, H) if re.fullmatch(r"[a-z0-9]{12,24}", cid or "-") else "")
        if not txt:
            continue
        chat = people[r["t"]]
        print("заявка →", chat, txt)
        if not DRY:
            body = {"chat_id": int(chat), "text": html.unescape(txt),
                    "reply_markup": {"inline_keyboard": [[{"text": btn, "web_app": {"url": APP}}]]}}
            req = urllib.request.Request(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            try:
                urllib.request.urlopen(req, timeout=30).read()
                n += 1
            except urllib.error.HTTPError as e:
                print("заявка не ушла:", e.code)
                if e.code not in (400, 403):
                    continue
        sent.append(mark)
        time.sleep(0.1)
    if len(sent) > 600:
        del sent[:-600]
    if n and save:
        save()
    return n


if __name__ == "__main__":
    st = {}
    print("отправлено:", tick(st, force=True))
