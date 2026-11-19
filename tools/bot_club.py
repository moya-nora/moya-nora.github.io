#!/usr/bin/env python3
"""Напоминания книжного клуба в боте - раз в день, утром.

Кому: тем, кто состоит в клубе и включил в Норе напоминания в Telegram (запись notify/<uid> с полем club, читает только бот).
Запуск раз в час. Обычные сообщения - только днём (с 9 до 22 по времени участника), не больше одного в день:
  • клуб начал новую книгу; • до срока 2 дня; • срок сегодня (только тем, кто ещё не отметил);
  • встреча назначена / отменена; • встреча завтра; • встреча сегодня.
И в любое время - «встреча через час» (кто не ответил «Не смогу»).
Встречи могут повторяться: d.mrep = 7, 14 или 30 (раз в месяц), пропущенные - d.mskip.
Бот входит в Firebase так же, как bot_weekly.py (секрет BOT_FB_PASS). Что уже отправлено - tools/bot_club.json.
DRY=1 - только показать тексты. Нужен секрет BOT_TOKEN."""
import html, json, os, re, sys, time, urllib.request

ROOT = os.path.join(os.path.dirname(__file__), "..")
TOKEN = os.environ.get("BOT_TOKEN", "").strip()
DRY = os.environ.get("DRY") == "1"
APP = "https://nora-books.ru/app.html?club=1"
SENT = os.path.join(ROOT, "tools", "bot_club.json")
FS = "https://firestore.googleapis.com/v1/projects/nora-ed429/databases/(default)/documents/"
BOTMAIL = "nora-bot@login.moya-nora.github.io"
MON = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]
DAY = 86400000


def local(ts, tz):
    return time.gmtime(ts / 1000 + tz * 60)


def day_no(ts, tz):
    return int((ts / 1000 + tz * 60) // 86400)


def dm(ts, tz):
    t = local(ts, tz)
    return f"{t.tm_mday} {MON[t.tm_mon - 1]}"


def hm(ts, tz):
    t = local(ts, tz)
    return f"{t.tm_hour:02d}:{t.tm_min:02d}"


def next_ts(ts, rep, skip, now):
    """Ближайшая встреча с учётом повтора; встреча «живёт» 3 часа от начала."""
    t, i = ts, 0
    while (t < now - 3 * 3600 * 1000 or t in skip) and i < 400:
        if not rep:
            return 0
        if rep == 30:
            g = time.gmtime(t / 1000); y, mo = g.tm_year + (g.tm_mon // 12), g.tm_mon % 12 + 1
            import calendar
            day = min(g.tm_mday, calendar.monthrange(y, mo)[1])
            t = int(calendar.timegm((y, mo, day, g.tm_hour, g.tm_min, 0)) * 1000)
        else:
            t += rep * DAY
        i += 1
    return t


def club_msgs(name, d, members, uid, now):
    """Список (ключ, текст) для одного участника. d - данные клуба, members - {uid: данные участника}."""
    out = []
    me = members.get(uid) or {}
    tz = me.get("tz", d.get("tz", 180))   # время - по часовому поясу участника
    today = day_no(now, tz)
    hour = local(now, tz).tm_hour
    b = d.get("book")
    if b and d.get("start"):
        parts = max(1, d.get("parts") or 4); per = d.get("per") or 7
        done = min(parts, (me.get("p") or {}).get(b["k"], 0))
        due = lambda i: d["start"] + per * DAY * i
        ttl = f"«{b['t']}»" + (f" - {b['a']}" if b.get("a") else "")
        if now - d["start"] < 36 * 3600 * 1000:
            out.append((f"st:{b['k']}", f"📖 Клуб «{name}» начал новую книгу: {ttl}.\n"
                        + (f"Срок - до {dm(due(1), tz)}." if parts == 1 else f"Читаем по частям, их {parts}. Первая - до {dm(due(1), tz)}.")))
        if done < parts:
            nxt = due(done + 1); left = day_no(nxt, tz) - today
            what = f"по книге «{b['t']}»" if parts == 1 else f"по части {done + 1} из {parts} книги «{b['t']}»"
            if left == 2:
                out.append((f"d2:{b['k']}:{done + 1}", f"⏳ Клуб «{name}»: до срока {what} осталось 2 дня - до {dm(nxt, tz)}."))
            elif left == 0:
                out.append((f"d0:{b['k']}:{done + 1}", f"🔔 Клуб «{name}»: сегодня срок {what}.\n"
                            + ("Если книга дочитана - отметь это в клубе и поставь оценку." if parts == 1 else "Если часть дочитана - отметь её в клубе, и откроются вопросы для обсуждения.")))
    # варианты времени предлагают участники; встреча - назначенная ведущим или время, которое подошло всем
    opts = {t for t in (d.get("mopts") or []) if t > now}
    for mu, x in members.items():   # время предлагает любой участник
        opts |= {t for t in (x.get("mo") or []) if t > now}
    votes = lambda t: sum(1 for x in members.values() if t in (x.get("mv") or []))
    mx = d.get("mcx") or 0
    if mx > now and not (d.get("meet") or {}).get("ts"):
        out.append((f"mx:{mx}", f"❌ Встреча клуба «{name}» {dm(mx, tz)} в {hm(mx, tz)} отменена. Новое время появится в клубе."))
    m = d.get("meet")
    if m and m.get("ts"):
        t = next_ts(m["ts"], d.get("mrep") or 0, d.get("mskip") or [], now)
        m = {**m, "ts": t} if t else None
    if not (m and m.get("ts", 0) > now - 3 * 3600 * 1000):
        full = sorted(t for t in opts if len(members) >= 2 and votes(t) >= len(members))
        m = {"ts": full[0]} if full else None
    if m:
        left = day_no(m["ts"], tz) - today
        go = sum(1 for x in members.values() if (x.get("rs") or {}).get(str(m["ts"])) == 1)
        mine = (me.get("rs") or {}).get(str(m["ts"]))
        about = f" Обсуждаем «{b['t']}»." if b else ""
        loc = d.get("mloc") or {}
        mins = (m["ts"] - now) / 60000
        if 0 < mins <= 75 and mine != 0:
            out.append((f"h1:{m['ts']}", f"⏰ Скоро встреча клуба «{name}» - в {hm(m['ts'], tz)}." + (f"\nСсылка: {loc['v']}" if loc.get("v") and loc.get("t") != "off" else f"\nМесто: {loc['v']}" if loc.get("v") else "")))
        if left == 1:
            out.append((f"m1:{m['ts']}", f"📅 Завтра в {hm(m['ts'], tz)} встреча клуба «{name}».{about}" + ("" if mine in (0, 1) else "\nОтметь, придёшь ли ты.")))
        elif left == 0:
            out.append((f"m0:{m['ts']}", f"📅 Сегодня клуб «{name}» собирается в {hm(m['ts'], tz)}.{about}" + (f"\nПридут: {go}." if go else "")))
        elif left > 1 and d.get("meet"):
            rep = {7: " Встречаемся каждую неделю.", 14: " Встречаемся раз в две недели.", 30: " Встречаемся раз в месяц."}.get(d.get("mrep") or 0, "")
            where = (" Онлайн." if loc.get("t") != "off" else f" Место: {loc.get('v')}.") if loc.get("v") else ""
            out.append((f"ms:{m['ts']}", f"📅 Встреча клуба «{name}» назначена: {dm(m['ts'], tz)}, {hm(m['ts'], tz)}.{about}{where}{rep}" + ("" if mine in (0, 1) else "\nОтметь в клубе, придёшь ли ты.")))
        elif left > 1 and not d.get("meet"):
            out.append((f"ma:{m['ts']}", f"✅ Клуб «{name}» выбрал время встречи: {dm(m['ts'], tz)}, {hm(m['ts'], tz)} - оно подошло всем."))
    elif opts and not [t for t in (me.get("mv") or []) if t in opts]:
        L = sorted(opts, key=lambda t: (-votes(t), t))
        out.append((f"mv:{min(opts)}", f"🗳 Клуб «{name}» выбирает время встречи. Отметь, когда тебе удобно:\n" + "\n".join(f"• {dm(t, tz)}, {hm(t, tz)}" for t in L)))
    if not 9 <= hour < 22:   # ночью и рано утром - только «через час»
        out = [x for x in out if x[0].startswith("h1:")]
    return out


def http(url, data=None, headers=None):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None, headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.load(r), 200
    except urllib.error.HTTPError as e:
        return {"error": e.read()[:300].decode("utf-8", "replace")}, e.code
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}, 0


def main():
    if not TOKEN and not DRY:
        print("нет секрета BOT_TOKEN - пропускаю"); return
    pw = os.environ.get("BOT_FB_PASS", "").strip()
    if not pw:
        print("нет секрета BOT_FB_PASS - пропускаю"); return
    app = open(os.path.join(ROOT, "app.html"), encoding="utf-8").read()
    key = re.search(r'apiKey:"([^"]+)"', app).group(1)
    j, c = http("https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=" + key, {"email": BOTMAIL, "password": pw, "returnSecureToken": True})
    if c != 200:
        print("вход бота не удался:", c, str(j)[:200]); return
    H = {"Authorization": "Bearer " + j["idToken"]}
    people, page = [], ""
    while True:
        j, c = http(FS + "notify?pageSize=300" + ("&pageToken=" + page if page else ""), headers=H)
        if c != 200:
            print("список недоступен:", c, str(j)[:200]); return
        for doc in j.get("documents") or []:
            try:
                v = json.loads(doc["fields"]["d"]["stringValue"])
                if v.get("club") and v.get("tg"):
                    people.append((str(v["tg"]), doc["name"].rsplit("/", 1)[1], v["club"]))
            except Exception:  # noqa: BLE001
                pass
        page = j.get("nextPageToken") or ""
        if not page:
            break
    print("в клубах с напоминаниями:", len(people))
    try:
        sent = json.load(open(SENT, encoding="utf-8"))
    except FileNotFoundError:
        sent = {}
    clubs, now, n = {}, int(time.time() * 1000), 0
    for chat, uid, cid in people:
        if not re.fullmatch(r"[a-z0-9]{12,24}", cid):
            continue
        if cid not in clubs:
            cj, c1 = http(FS + "clubs/" + cid, headers=H)
            mj, c2 = http(FS + "clubs/" + cid + "/m?pageSize=300", headers=H)
            if c1 != 200 or c2 != 200:
                clubs[cid] = None; continue
            try:
                mem = {m["name"].rsplit("/", 1)[1]: json.loads(m["fields"]["d"]["stringValue"]) for m in mj.get("documents") or []}
                cd = json.loads(cj["fields"]["d"]["stringValue"]); cd["_o"] = cj["fields"]["o"]["stringValue"]
                clubs[cid] = (cj["fields"]["n"]["stringValue"], cd, mem)
            except Exception:  # noqa: BLE001
                clubs[cid] = None
        if not clubs[cid] or uid not in clubs[cid][2]:
            continue
        me = sent.setdefault(chat, [])
        items = [(k, t) for k, t in club_msgs(*clubs[cid], uid, now) if cid + ":" + k not in me]
        if not items:
            continue
        txt = "\n\n".join(html.escape(t) for _, t in items)
        print(chat, "→", txt.replace("\n", " | "))
        if DRY:
            continue
        req = urllib.request.Request(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data=json.dumps({"chat_id": int(chat), "text": txt, "reply_markup": {"inline_keyboard": [[{"text": "Открыть клуб", "web_app": {"url": APP}}]]}}).encode(), headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=60).read()
            sent[chat] = (me + [cid + ":" + k for k, _ in items])[-80:]; n += 1
        except urllib.error.HTTPError as e:
            print("не ушло:", e.code)
            if e.code != 403:
                continue
            sent[chat] = (me + [cid + ":" + k for k, _ in items])[-80:]
        time.sleep(0.2)
    json.dump(sent, open(SENT, "w", encoding="utf-8"), ensure_ascii=False)
    print("отправлено:", n)


if __name__ == "__main__":
    main()
