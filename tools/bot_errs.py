#!/usr/bin/env python3
"""Сводка ошибок приложения - раз в день владелице в бот.

Приложение при ошибке у человека пишет запись в errs/ (без личных данных: текст ошибки, место в коде, iOS/Android/ПК, Telegram или браузер).
Бот входит в Firebase как nora-bot (секрет BOT_FB_PASS), читает errs, группирует одинаковые ошибки, присылает сводку и удаляет прочитанное.
Если ошибок не было - ничего не пишет. DRY=1 - только показать текст.
MODE=collab - вместо ошибок переслать новые заявки «Сотрудничество» (collab/), запускается каждый час вместе с ботом поддержки."""
import json, os, re, urllib.request, urllib.error

ROOT = os.path.join(os.path.dirname(__file__), "..")
TOKEN = os.environ.get("BOT_TOKEN", "").strip()
DRY = os.environ.get("DRY") == "1"
FS = "https://firestore.googleapis.com/v1/projects/nora-ed429/databases/(default)/documents/"
BOTMAIL = "nora-bot@login.moya-nora.github.io"


def http(url, data=None, headers=None, method=None):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None,
                                 headers={"Content-Type": "application/json", **(headers or {})}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            body = r.read()
            return (json.loads(body) if body else {}), 200
    except urllib.error.HTTPError as e:
        return {"error": e.read()[:300].decode("utf-8", "replace")}, e.code
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}, 0


def main():
    pw = os.environ.get("BOT_FB_PASS", "").strip()
    if not pw:
        print("нет секрета BOT_FB_PASS - пропускаю"); return
    owner = json.load(open(os.path.join(ROOT, "tools", "bot_state.json"), encoding="utf-8")).get("owner")
    app = open(os.path.join(ROOT, "app.html"), encoding="utf-8").read()
    key = re.search(r'apiKey:"([^"]+)"', app).group(1)
    j, c = http("https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=" + key,
                {"email": BOTMAIL, "password": pw, "returnSecureToken": True})
    if c != 200 and "EMAIL_NOT_FOUND" in str(j) or c != 200 and "INVALID_LOGIN_CREDENTIALS" in str(j):  # аккаунта бота ещё нет - создаём
        j, c = http("https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=" + key, {"email": BOTMAIL, "password": pw, "returnSecureToken": True})
    if c != 200:
        print("вход бота не удался:", c, str(j)[:200]); return
    H = {"Authorization": "Bearer " + j["idToken"]}
    if os.environ.get("MODE") == "collab":
        return collab(H, owner)
    docs, page = [], ""
    while True:
        j, c = http(FS + "errs?pageSize=300" + ("&pageToken=" + page if page else ""), headers=H)
        if c != 200:
            print("errs недоступны:", c, str(j)[:300]); return
        docs += j.get("documents") or []
        page = j.get("nextPageToken") or ""
        if not page or len(docs) > 3000:
            break
    print("записей об ошибках:", len(docs))
    if not docs:
        return
    groups = {}
    for d in docs:
        f = {k: list(v.values())[0] for k, v in d.get("fields", {}).items()}
        k = (f.get("m", ""), f.get("s", ""), str(f.get("l", "")))
        g = groups.setdefault(k, {"n": 0, "u": set()})
        g["n"] += 1
        g["u"].add(f.get("u", ""))
    top = sorted(groups.items(), key=lambda x: -x[1]["n"])[:8]
    lines = [f"Нора: ошибки в приложении за сутки - {len(docs)} (разных: {len(groups)})."]
    for (m, s, l), g in top:
        where = f" ({s}:{l})" if s else ""
        lines.append(f"• {g['n']}× {m[:160]}{where} - {', '.join(sorted(x for x in g['u'] if x))}")
    lines.append("Перешли это в чат проекта - разберём.")
    text = "\n".join(lines)
    print(text)
    save_list(groups, docs)
    if DRY or not TOKEN or not owner:
        return
    j, c = http(f"https://api.telegram.org/bot{TOKEN}/sendMessage", {"chat_id": owner, "text": text, "disable_web_page_preview": True})
    if c != 200:
        print("не отправилось:", c, str(j)[:200]); return
    gone = 0
    for d in docs:
        _, c = http("https://firestore.googleapis.com/v1/" + d["name"], headers=H, method="DELETE")
        gone += c == 200
    print("удалено:", gone)


def save_list(groups, docs):
    """полный список ошибок - в tools/errs_last.json (последние 14 дней), чтобы разбирать их по коду, а не по сводке"""
    fl = lambda d: {k: list(v.values())[0] for k, v in d.get("fields", {}).items()}
    full = []
    for (m, s, l), g in sorted(groups.items(), key=lambda x: -x[1]["n"]):
        ex = next((fl(d) for d in docs if (fl(d).get("m", ""), fl(d).get("s", ""), str(fl(d).get("l", ""))) == (m, s, l)), {})
        full.append({"n": g["n"], "m": m, "s": s, "l": l, "where": sorted(x for x in g["u"] if x), "sample": ex})
    if DRY:
        print(json.dumps(full, ensure_ascii=False, indent=1)[:20000]); return
    path = os.path.join(ROOT, "tools", "errs_last.json")
    try:
        old = json.load(open(path, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        old = []
    import time
    json.dump(([{"day": time.strftime("%Y-%m-%d"), "errors": full}] + old)[:14], open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def collab(H, owner):
    j, c = http(FS + "collab?pageSize=100", headers=H)
    if c != 200:
        print("collab недоступны:", c, str(j)[:300]); return
    docs = j.get("documents") or []
    print("заявок на сотрудничество:", len(docs))
    for d in docs:
        f = {k: list(v.values())[0] for k, v in d.get("fields", {}).items()}
        text = (f"🤝 Заявка «Сотрудничество» (клуб с платным входом)\nКто: {f.get('w', '')}\nБлог: {f.get('l', '')}\n"
                f"Первая книга: {f.get('b', '') or '-'}\nЦена: {f.get('p', '') or '-'} ₽")
        print(text)
        if DRY or not TOKEN or not owner:
            continue
        _, c = http(f"https://api.telegram.org/bot{TOKEN}/sendMessage", {"chat_id": owner, "text": text, "disable_web_page_preview": True})
        if c == 200:
            http("https://firestore.googleapis.com/v1/" + d["name"], headers=H, method="DELETE")


if __name__ == "__main__":
    main()
