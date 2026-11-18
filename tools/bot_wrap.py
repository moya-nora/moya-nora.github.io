#!/usr/bin/env python3
"""Итоги года: рассылка подписчикам бота (notify/*).
1 декабря - «итоги готовы», 26 декабря - напоминание тем, кто ещё не открыл (в облачной полке нет zal.wrseen = текущий год).
Кнопка открывает приложение сразу на итогах (#wrap). DRY=1 - только показать, FORCE=dec1|dec26 - запустить вне даты."""
import datetime as dt, json, os, re, urllib.request, urllib.error

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
            b = r.read()
            return (json.loads(b) if b else {}), 200
    except urllib.error.HTTPError as e:
        return {"error": e.read()[:300].decode("utf-8", "replace")}, e.code
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}, 0


def main():
    now = dt.datetime.now(MSK)
    mode = os.environ.get("FORCE") or ("dec1" if (now.month, now.day) == (12, 1) else "dec26" if (now.month, now.day) == (12, 26) else "")
    if not mode:
        print("сегодня рассылки нет"); return
    Y = str(now.year)
    pw = os.environ.get("BOT_FB_PASS", "").strip()
    app = open(os.path.join(ROOT, "app.html"), encoding="utf-8").read()
    key = re.search(r'apiKey:"([^"]+)"', app).group(1)
    j, c = http("https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=" + key, {"email": BOTMAIL, "password": pw, "returnSecureToken": True})
    if c != 200:
        print("вход бота не удался:", c); return
    H = {"Authorization": "Bearer " + j["idToken"]}
    subs, page = [], ""
    while True:
        j, c = http(FS + "notify?pageSize=300" + ("&pageToken=" + page if page else ""), headers=H)
        if c != 200:
            print("notify недоступны:", c); return
        for d in j.get("documents") or []:
            try:
                v = json.loads(d["fields"]["d"]["stringValue"]); v["uid"] = d["name"].rsplit("/", 1)[1]
                if v.get("tg"):
                    subs.append(v)
            except Exception:  # noqa: BLE001
                pass
        page = j.get("nextPageToken") or ""
        if not page:
            break

    def seen(uid):
        u, c = http(FS + "users/" + uid, headers=H)
        k = (((u.get("fields") or {}).get("k") or {}).get("stringValue")) if c == 200 else None
        if not k:
            return False
        v, c = http(FS + "vaults/" + k, headers=H)
        try:
            d = json.loads(v["fields"]["d"]["stringValue"])
            return str(json.loads(d.get("zal.wrseen", {}).get("v") or '""')) == Y
        except Exception:  # noqa: BLE001
            return False

    if mode == "dec1":
        text = f"✨ Твои книжные итоги {Y} готовы!\nСколько книг, книга года, самый читающий месяц и твой читательский тип - в красивых картинках для сторис."
    else:
        text = f"Ты ещё не смотришь свои итоги {Y}? 📚\nТам твоя книга года, страницы и читательский тип. До 31 января их можно открыть и выложить в сторис."
    btn = {"inline_keyboard": [[{"text": "Открыть итоги", "web_app": {"url": "https://nora-books.ru/app.html?app=1#wrap"}}]]}
    sent = 0
    for v in subs:
        if mode == "dec26" and seen(v["uid"]):
            continue
        if DRY or not TOKEN:
            sent += 1; continue
        _, c = http(f"https://api.telegram.org/bot{TOKEN}/sendMessage", {"chat_id": v["tg"], "text": text, "reply_markup": btn})
        sent += c == 200
    print(mode, "подписчиков:", len(subs), "отправлено:", sent)


if __name__ == "__main__":
    main()
