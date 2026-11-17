#!/usr/bin/env python3
"""Сводка ошибок приложения - раз в день владелице в бот.

Приложение при ошибке у человека пишет запись в errs/ (без личных данных: текст ошибки, место в коде, iOS/Android/ПК, Telegram или браузер).
Бот входит в Firebase как nora-bot (секрет BOT_FB_PASS), читает errs, группирует одинаковые ошибки, присылает сводку и удаляет прочитанное.
Если ошибок не было - ничего не пишет. DRY=1 - только показать текст."""
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
    if c != 200:
        print("вход бота не удался:", c, str(j)[:200]); return
    H = {"Authorization": "Bearer " + j["idToken"]}
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


if __name__ == "__main__":
    main()
