#!/usr/bin/env python3
"""Статистика Норы для владелицы - раз в день.

Бот входит в Firebase как nora-bot (секрет BOT_FB_PASS) и читает только списки: users (аккаунты, дата регистрации),
vaults (облачные полки всех устройств, в том числе без входа - из Telegram), profiles, notify. Наружу уходят только
сводные цифры, без имён и почт: они пишутся в stats/<ключ> (ключ - хэш от пароля бота, его знает только бот),
а владелице в бот приходит короткая сводка и ссылка на экран статистики в приложении (#st=<ключ>).
История по дням копится в том же документе (90 дней). DRY=1 - только показать, ничего не писать и не отправлять."""
import datetime as dt, hashlib, json, os, re, urllib.request, urllib.error
from collections import Counter

ROOT = os.path.join(os.path.dirname(__file__), "..")
TOKEN = os.environ.get("BOT_TOKEN", "").strip()
DRY = os.environ.get("DRY") == "1"
FS = "https://firestore.googleapis.com/v1/projects/nora-ed429/databases/(default)/documents/"
BOTMAIL = "nora-bot@login.moya-nora.github.io"
MSK = dt.timezone(dt.timedelta(hours=3))


def http(url, data=None, headers=None, method=None):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None,
                                 headers={"Content-Type": "application/json", **(headers or {})}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read()
            return (json.loads(body) if body else {}), 200
    except urllib.error.HTTPError as e:
        return {"error": e.read()[:300].decode("utf-8", "replace")}, e.code
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}, 0


def listall(coll, H, mask=None):
    out, page = [], ""
    while True:
        q = FS + coll + "?pageSize=300" + ("&pageToken=" + page if page else "") + "".join("&mask.fieldPaths=" + m for m in (mask or []))
        j, c = http(q, headers=H)
        if c != 200:
            print(coll, "недоступны:", c, str(j)[:200]); return None
        out += j.get("documents") or []
        page = j.get("nextPageToken") or ""
        if not page or len(out) > 50000:
            return out


def ts(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def val(f, k):
    v = (f.get(k) or {})
    return next(iter(v.values()), None) if v else None


def arr(d, k):
    try:
        x = (d.get(k) or {}).get("v")
        x = json.loads(x) if isinstance(x, str) else x
        return x if isinstance(x, list) else []
    except Exception:  # noqa: BLE001
        return []


# журнал действий (ev/): что люди делают в приложении. Анонимно - только случайный номер устройства.
EVL = {"open": "открыл Нору", "search": "открыл поиск", "q": "искал", "book": "карточка книги", "book_fr": "карточка книги друга",
       "want": "в «Хочу прочитать»", "read": "отметил прочитанной", "diary": "запись в дневнике", "reviews": "открыл отзывы",
       "where": "«Где прочитать»", "where_go": "ушёл в магазин", "luck": "подарок Шуршуни", "invite": "пригласил в клуб",
       "ask_friend": "спросил друга", "club_where": "«Где взять книгу» в клубе", "hc_join": "клуб с ведущим: вступить",
       "hs_web": "клуб с ведущим на сайте", "signup_done": "зарегистрировался", "wrap": "итоги года", "wrap_share": "поделился итогами"}
SHOP = {"ya": "Яндекс Книги", "litres": "ЛитРес", "ozon": "Ozon", "chitai": "Читай-город", "bukvoed": "Буквоед", "gbooks": "Google Книги"}
SCR = {"col": "главная", "club": "Клуб", "sum": "Полки", "acc": "Аккаунт", "feed": "Лента", "fr": "Полки друзей"}


def evlabel(c, x=""):
    if c == "scr":
        return SCR.get(x, x)
    if c.startswith("wrap_share"):
        c = "wrap_share"
    lb = EVL.get(c, c)
    if c == "where_go":
        x = SHOP.get(x, x)
    if c in ("q", "book", "book_fr"):
        return f"{lb} «{x}»" if x else lb
    return f"{lb}: {x}" if x else lb


def evstats(H, now, today, day):
    """Собирает ev/ в сводку: действия за 7 дней, поиск, книги, сеансы по дням и последние визиты. Старше 30 дней - удаляет."""
    docs = listall("ev", H)
    if docs is None:
        return None
    S, old = {}, []
    for d in docs:
        f = d.get("fields", {})
        t = ts(d.get("createTime"))
        if t and t < now - dt.timedelta(days=30):
            old.append(d["name"])
            continue
        if val(f, "v") or val(f, "o"):  # тестовая версия и сама владелица не считаются
            continue
        k = val(f, "k") or d["name"]
        try:
            e = json.loads(val(f, "e") or "[]")
        except Exception:  # noqa: BLE001
            e = []
        x = S.setdefault(k, {"d": val(f, "d") or "", "w": val(f, "w") or "", "p": val(f, "p") or "", "n": bool(val(f, "n")),
                             "s": int(val(f, "s") or 0), "e": []})
        x["e"] += [z for z in e if isinstance(z, list) and len(z) >= 2]
    for nm in old[:400]:
        http("https://firestore.googleapis.com/v1/" + nm, headers=H, method="DELETE")
    ses = sorted(S.values(), key=lambda z: z["s"])
    for z in ses:
        z["e"].sort(key=lambda q: q[0])
        z["day"] = day(dt.datetime.fromtimestamp(z["s"] / 1000, MSK)) if z["s"] else today
    days30 = [(today - dt.timedelta(days=i)) for i in range(29, -1, -1)]
    lim7 = today - dt.timedelta(days=6)
    w7 = [z for z in ses if z["day"] >= lim7]
    acts, who, qs, bk, shop, scr, where, devdays = Counter(), {}, Counter(), Counter(), Counter(), Counter(), Counter(), {}
    for z in w7:
        devdays.setdefault(z["d"], set()).add(z["day"])
        where[z["w"] + ", " + z["p"]] += 1
        seen = set()
        for q in z["e"]:
            c, x = q[1], (q[2] if len(q) > 2 else "")
            if c == "scr":
                if x not in seen:
                    scr[SCR.get(x, x)] += 1
                seen.add(x)
                continue
            if c == "open":
                continue
            cc = "wrap_share" if c.startswith("wrap_share") else c
            acts[cc] += 1
            who.setdefault(cc, set()).add(z["d"])
            if c == "q":
                qs[x.lower()] += 1
            elif c in ("book", "book_fr"):
                bk[x] += 1
            elif c == "where_go":
                shop[SHOP.get(x, x)] += 1
    per = Counter(z["day"] for z in ses)
    ppl = {}
    for z in ses:
        ppl.setdefault(z["day"], set()).add(z["d"])
    newd = Counter(z["day"] for z in ses if z["n"])
    stories = []
    for z in reversed(ses[-30:]):
        st = dt.datetime.fromtimestamp(z["s"] / 1000, MSK) if z["s"] else now
        steps = [evlabel(q[1], q[2] if len(q) > 2 else "") for q in z["e"] if q[1] != "open"]
        dur = z["e"][-1][0] if z["e"] else 0
        stories.append({"t": st.strftime("%d.%m %H:%M"), "w": z["w"], "p": z["p"], "n": z["n"], "m": max(1, round(dur / 60)) if dur else 0,
                        "s": steps[:40], "more": max(0, len(steps) - 40), "id": z["d"][-4:]})
    return {"ses": [[d.isoformat(), per.get(d, 0), len(ppl.get(d, ())), newd.get(d, 0)] for d in days30],
            "ses7": len(w7), "ppl7": len(devdays), "back7": sum(1 for v in devdays.values() if len(v) >= 2),
            "acts": [[EVL.get(c, c), n, len(who[c])] for c, n in acts.most_common()],
            "scr": scr.most_common(), "q": qs.most_common(15), "bk": bk.most_common(10), "shop": shop.most_common(),
            "where": where.most_common(), "stories": stories}


def main():
    pw = os.environ.get("BOT_FB_PASS", "").strip()
    if not pw:
        print("нет секрета BOT_FB_PASS - пропускаю"); return
    owner = json.load(open(os.path.join(ROOT, "tools", "bot_state.json"), encoding="utf-8")).get("owner")
    app = open(os.path.join(ROOT, "app.html"), encoding="utf-8").read()
    key = re.search(r'apiKey:"([^"]+)"', app).group(1)
    j, c = http("https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=" + key,
                {"email": BOTMAIL, "password": pw, "returnSecureToken": True})
    if c != 200 and ("EMAIL_NOT_FOUND" in str(j) or "INVALID_LOGIN_CREDENTIALS" in str(j)):  # аккаунта бота ещё нет - создаём
        j, c = http("https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=" + key, {"email": BOTMAIL, "password": pw, "returnSecureToken": True})
    if c != 200:
        print("вход бота не удался:", c, str(j)[:200]); return
    H = {"Authorization": "Bearer " + j["idToken"]}
    SK = hashlib.sha256(("nora-stats:" + pw).encode()).hexdigest()

    now = dt.datetime.now(MSK)
    today = now.date()
    day = lambda t: t.astimezone(MSK).date()  # noqa: E731
    users = listall("users", H) or []
    vaults = listall("vaults", H) or []
    notify = listall("notify", H, ["u"]) or []
    try:
        EVS = evstats(H, now, today, day)
    except Exception as e:  # noqa: BLE001
        print("журнал действий не посчитан:", e); EVS = None

    reg = Counter(day(ts(u["createTime"])) for u in users if u.get("createTime"))
    vnew = Counter(day(ts(v["createTime"])) for v in vaults if v.get("createTime"))
    last, read_n, want_n, books, bweek = [], 0, 0, Counter(), Counter()
    for v in vaults:
        f = v.get("fields", {})
        u = val(f, "u")
        lt = dt.datetime.fromtimestamp(int(u) / 1000, MSK) if u else ts(v.get("updateTime"))
        last.append(lt)
        try:
            d = json.loads(val(f, "d") or "{}")
        except Exception:  # noqa: BLE001
            d = {}
        mine, want = arr(d, "zal.mine"), arr(d, "zal.want.v2")
        read_n += len(mine)
        want_n += len(want)
        for b in mine + want:
            if isinstance(b, dict) and b.get("t"):
                books[(str(b.get("t"))[:60], str(b.get("a") or "")[:40])] += 1

    def active(days):
        lim = now - dt.timedelta(days=days)
        return sum(1 for t in last if t and t >= lim)

    def since(cnt, days):
        return sum(v for k, v in cnt.items() if k > today - dt.timedelta(days=days))

    y = today - dt.timedelta(days=1)
    snap = {"date": today.isoformat(), "accounts": len(users), "devices": len(vaults), "a1": active(1), "a7": active(7),
            "a30": active(30), "read": read_n, "want": want_n}

    old, c = http(FS + "stats/" + SK, headers=H)
    hist = []
    if c == 200:
        try:
            hist = json.loads(val(old.get("fields", {}), "d") or "{}").get("hist", [])
        except Exception:  # noqa: BLE001
            hist = []
    hist = [h for h in hist if h.get("date") != snap["date"]][-89:] + [snap]

    days30 = [(today - dt.timedelta(days=i)) for i in range(29, -1, -1)]
    out = {"t": int(now.timestamp() * 1000), "accounts": len(users), "devices": len(vaults), "notify": len(notify),
           "reg1": reg.get(today, 0), "regY": reg.get(y, 0), "reg7": since(reg, 7), "reg30": since(reg, 30),
           "dev7": since(vnew, 7), "a1": snap["a1"], "a7": snap["a7"], "a30": snap["a30"], "read": read_n, "want": want_n,
           "regs": [[d.isoformat(), reg.get(d, 0)] for d in days30], "devs": [[d.isoformat(), vnew.get(d, 0)] for d in days30],
           "top": [[t, a, n] for (t, a), n in books.most_common(10)], "hist": hist}
    if EVS:
        out["ev"] = EVS

    text = (f"📊 Нора за вчера\n"
            f"Новых аккаунтов: {out['regY']} (за 7 дней: {out['reg7']})\n"
            f"Заходили за сутки: {out['a1']}, за неделю: {out['a7']}\n"
            f"Всего аккаунтов: {out['accounts']}, устройств с полками: {out['devices']}\n"
            f"Книг на полках: прочитано {read_n}, хотят прочитать {want_n}")
    if EVS:
        yd = next((z for z in EVS["ses"] if z[0] == y.isoformat()), None)
        top3 = ", ".join(f"{a} {n}" for a, n, _ in EVS["acts"][:3])
        text += (f"\nВизитов вчера: {yd[1] if yd else 0}, людей: {yd[2] if yd else 0}"
                 f"\nЗа неделю {EVS['ppl7']} человек, вернулись снова {EVS['back7']}" + (f"\nЧаще всего: {top3}" if top3 else ""))
    print(text)
    print("top:", out["top"][:5])
    if DRY:
        return
    body = {"fields": {"d": {"stringValue": json.dumps(out, ensure_ascii=False)}, "u": {"integerValue": str(out["t"])}}}
    _, c = http(FS + "stats/" + SK, body, headers=H, method="PATCH")
    print("записано:", c)
    page = "app.html" if "data-stats" in app else "app-dev.html"
    link = f"https://nora-books.ru/{page}?app=1#st={SK}"
    if TOKEN and owner:
        http(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
             {"chat_id": owner, "text": text + "\n\nЭкран статистики (ссылка только для тебя, никому не пересылай):\n" + link,
              "disable_web_page_preview": True})


if __name__ == "__main__":
    main()
