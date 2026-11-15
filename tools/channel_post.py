"""Посты в канал @nora_bookworld от имени бота.

python3 tools/channel_post.py tools/channel/intro.html   - один пост из файла
python3 tools/channel_post.py --next                      - следующий пост из очереди tools/channel/queue.json
  (что уже вышло - tools/channel/sent.json; книга -> фото обложки и кнопка «Открыть в Норе» прямо на её карточку)"""
import json, os, sys, urllib.request, urllib.error
TOKEN = os.environ["BOT_TOKEN"]; CH = os.environ.get("CHANNEL", "@nora_bookworld")
HERE = os.path.dirname(os.path.abspath(__file__))
BOT = "https://t.me/Wonderbookworld_bot"


def api(method, data):
    req = urllib.request.Request(f"https://api.telegram.org/bot{TOKEN}/{method}", json.dumps(data).encode(), {"Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=30))
    except urllib.error.HTTPError as e:
        print("error", e.code, e.read().decode()); sys.exit(1)


def post(text, photo=None, btn=None, url=None):
    kb = {"inline_keyboard": [[{"text": btn or "Подобрать книгу под мой вкус", "url": url or BOT + "?startapp=channel"}]]}
    if photo:  # обложку скачиваем сами и отправляем файлом: по ссылке Telegram её не забирает
        img = urllib.request.urlopen(urllib.request.Request(photo, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read()
        bnd = "----nora" + str(len(img))
        parts = []
        for k_, v_ in (("chat_id", CH), ("caption", text), ("parse_mode", "HTML"), ("reply_markup", json.dumps(kb, ensure_ascii=False))):
            parts.append(f'--{bnd}\r\nContent-Disposition: form-data; name="{k_}"\r\n\r\n{v_}\r\n'.encode())
        parts.append(f'--{bnd}\r\nContent-Disposition: form-data; name="photo"; filename="cover.jpg"\r\nContent-Type: image/jpeg\r\n\r\n'.encode() + img + f"\r\n--{bnd}--\r\n".encode())
        req = urllib.request.Request(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", b"".join(parts), {"Content-Type": f"multipart/form-data; boundary={bnd}"})
        try:
            r = json.load(urllib.request.urlopen(req, timeout=60))
        except urllib.error.HTTPError as e:
            print("error", e.code, e.read().decode()); sys.exit(1)
    else:
        r = api("sendMessage", {"chat_id": CH, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True, "reply_markup": kb})
    print("ok", r["ok"], r["result"]["message_id"])


if sys.argv[1:] == ["--next"]:
    Q = json.load(open(os.path.join(HERE, "channel", "queue.json"), encoding="utf-8"))
    sp = os.path.join(HERE, "channel", "sent.json")
    sent = json.load(open(sp)) if os.path.exists(sp) else []
    i = len(sent)
    if i >= len(Q):
        print("очередь закончилась"); sys.exit(0)
    p = Q[i]
    if p.get("file"):
        post(open(os.path.join(HERE, "channel", p["file"]), encoding="utf-8").read().strip())
    elif p.get("book"):
        post(p["text"], p.get("photo"), "Открыть в Норе", f"{BOT}?startapp=b_{p['book']}")
    else:
        post(p["text"], p.get("photo"), p.get("btn"))
    sent.append(i); json.dump(sent, open(sp, "w"))
else:
    post(open(sys.argv[1], encoding="utf-8").read().strip())
