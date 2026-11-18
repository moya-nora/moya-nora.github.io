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


def main():
    pw = os.environ.get("BOT_FB_PASS", "").strip()
    if not pw:
        print("нет секрета BOT_FB_PASS - пропускаю"); return
    owner = json.load(open(os.path.join(ROOT, "tools", "bot_state.json"), encoding="utf-8")).get("owner")
    app = open(os.path.join(ROOT, "app.html"), encoding="utf-8").read()
    key = re.search(r'apiKey:"([^"]+)"', app).group(1)
    j, c = http("https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=" + key,
                {"email": BOTMAIL, "password": pw, "returnSecureToken": True})
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

    text = (f"📊 Нора за вчера\n"
            f"Новых аккаунтов: {out['regY']} (за 7 дней: {out['reg7']})\n"
            f"Заходили за сутки: {out['a1']}, за неделю: {out['a7']}\n"
            f"Всего аккаунтов: {out['accounts']}, устройств с полками: {out['devices']}\n"
            f"Книг на полках: прочитано {read_n}, хотят прочитать {want_n}")
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
