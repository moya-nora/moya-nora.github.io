#!/usr/bin/env python3
"""Поддержка через бота @Wonderbookworld_bot без своего сервера.

Каждые 10 минут GitHub Actions забирает новые сообщения бота (getUpdates):
  • человек пишет боту → бот отвечает «Спасибо, передали» и пересылает вопрос владелице;
  • владелица отвечает на пересланное сообщение (свайп → «Ответить») → ответ уходит человеку от имени бота;
  • /start от обычного человека → приветствие и кнопка «Открыть Нору».
Владелица — тот, кто пишет боту /start с ником из OWNER_USERNAME (по умолчанию из настроек ниже).
Её chat id хранится в tools/bot_state.json. Нужен секрет репозитория BOT_TOKEN."""
import json, os, re, sys, urllib.request

TOKEN = os.environ.get("BOT_TOKEN", "").strip()
OWNER = os.environ.get("OWNER_USERNAME", "").strip().lstrip("@").lower() or "stanislava_kurdina"
STATE = os.path.join(os.path.dirname(__file__), "bot_state.json")
APP = "https://moya-nora.github.io/app.html"
if not TOKEN:
    print("нет секрета BOT_TOKEN — пропускаю")
    sys.exit(0)


def api(method, **params):
    req = urllib.request.Request(f"https://api.telegram.org/bot{TOKEN}/{method}", data=json.dumps(params).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r).get("result")
    except urllib.error.HTTPError as e:
        print(method, e.code, e.read()[:300].decode("utf-8", "replace"))
        return None


try:
    state = json.load(open(STATE, encoding="utf-8"))
except FileNotFoundError:
    state = {}
owner_id = state.get("owner")
me = api("getMe") or {}
wh = api("getWebhookInfo") or {}
print("бот:", "@" + str(me.get("username")), "| вебхук:", "есть — сообщения забирает другая система" if wh.get("url") else "нет", "| ждут:", wh.get("pending_update_count"))
ups = api("getUpdates", timeout=0, allowed_updates=["message"]) or []
print("новых сообщений:", len(ups))
last, acked, changed = None, set(), False
for u in ups:
    last = u["update_id"]
    m = u.get("message")
    if not m:
        continue
    fr, chat = m.get("from", {}), m["chat"]["id"]
    if m["chat"].get("type") != "private":
        continue
    text = m.get("text") or m.get("caption") or ""
    is_owner = (fr.get("username") or "").lower() == OWNER
    if is_owner:
        if owner_id != chat:
            owner_id, changed = chat, True
            state["owner"] = chat
        rep = m.get("reply_to_message")
        tag = re.search(r"#u(\d+)", (rep or {}).get("text") or (rep or {}).get("caption") or "")
        if rep and tag:
            ok = api("copyMessage", chat_id=int(tag.group(1)), from_chat_id=chat, message_id=m["message_id"])
            api("sendMessage", chat_id=chat, text="✓ Отправлено" if ok else "Не получилось отправить — человек мог остановить бота.", reply_to_message_id=m["message_id"])
        elif text.startswith("/start"):
            api("sendMessage", chat_id=chat, text="Готово! Сюда будут приходить вопросы читателей. Чтобы ответить, смахни сообщение влево и нажми «Ответить».")
        continue
    if text.startswith("/start"):
        api("sendMessage", chat_id=chat, text="Привет! Это Нора — все твои книги в одном месте и советы, что читать дальше.\n\nЕсли есть вопрос или идея — просто напиши сюда, мы ответим.",
            reply_markup={"inline_keyboard": [[{"text": "Открыть Нору", "web_app": {"url": APP}}]]})
        continue
    if not owner_id:  # владелица ещё не написала боту /start — сообщения подождут (Telegram хранит их сутки)
        last = None
        break
    who = " ".join(x for x in [fr.get("first_name"), fr.get("last_name")] if x) or "Читатель"
    head = f"✉️ {who}{' @' + fr['username'] if fr.get('username') else ''} · #u{chat}"
    if text and not any(k in m for k in ("photo", "document", "video", "voice")):
        api("sendMessage", chat_id=owner_id, text=f"{head}\n\n{text}")
    else:
        api("sendMessage", chat_id=owner_id, text=head)
        api("copyMessage", chat_id=owner_id, from_chat_id=chat, message_id=m["message_id"])
    if chat not in acked:
        acked.add(chat)
        api("sendMessage", chat_id=chat, text="Спасибо! Передали в команду Норы — ответим здесь же.")
if last is not None:
    api("getUpdates", offset=last + 1, timeout=0)  # подтверждаем: эти сообщения обработаны
if changed:
    json.dump(state, open(STATE, "w", encoding="utf-8"))
    print("сохранён chat id владелицы")
