#!/usr/bin/env python3
"""Поддержка через бота @Wonderbookworld_bot без своего сервера.

Каждые 10 минут GitHub Actions забирает новые сообщения бота (getUpdates):
  • человек пишет боту → бот отвечает «Спасибо, передали» и пересылает вопрос владелице;
  • владелица отвечает на пересланное сообщение (свайп → «Ответить») → ответ уходит человеку от имени бота;
  • /start от обычного человека → приветствие и кнопка «Открыть Нору».
Владелица — тот, кто пишет боту /start с ником из OWNER_USERNAME (по умолчанию из настроек ниже).
Её chat id хранится в tools/bot_state.json. Нужен секрет репозитория BOT_TOKEN."""
import json, os, re, sys, time, urllib.request

TOKEN = os.environ.get("BOT_TOKEN", "").strip()
OWNER = os.environ.get("OWNER_USERNAME", "").strip().lstrip("@").lower() or "stanislava_kurdina"
STATE = os.path.join(os.path.dirname(__file__), "bot_state.json")
APP = "https://nora-books.ru/app.html"
if not TOKEN:
    print("нет секрета BOT_TOKEN — пропускаю")
    sys.exit(0)


def api(method, **params):
    req = urllib.request.Request(f"https://api.telegram.org/bot{TOKEN}/{method}", data=json.dumps(params).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=70) as r:
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
acked = set()


def save():
    json.dump(state, open(STATE, "w", encoding="utf-8"), ensure_ascii=False)
    print("состояние бота сохранено", flush=True)


def sub(chat, fr, on=True):
    """Читатель, которому можно раз в неделю прислать «Шуршуня советует»: написал боту, нажал /start или разрешил сообщения из Норы."""
    S = state.setdefault("subs", {})
    k = str(chat)
    old = S.get(k)
    S[k] = {"n": fr.get("first_name") or "", "on": 1 if on else 0, "t": int(time.time()), "w": (old or {}).get("w", 0)}
    if not old or old.get("on") != S[k]["on"]:
        save()


HOSTED = os.path.join(os.path.dirname(__file__), "..", "books", "hosted.json")


_HC = {"t": 0, "d": None}


def hosted():
    """Свежий список клубов с ведущими прямо с GitHub (бот дежурит часами, файл в его копии мог устареть); запасной - локальный."""
    if _HC["d"] is not None and time.time() - _HC["t"] < 60:
        return _HC["d"]
    try:
        with urllib.request.urlopen("https://raw.githubusercontent.com/moya-nora/moya-nora.github.io/main/books/hosted.json?t=%d" % time.time(), timeout=15) as r:
            d = json.load(r)
    except Exception:  # noqa: BLE001
        try:
            d = json.load(open(HOSTED, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            d = {"clubs": []}
    _HC.update(t=time.time(), d=d)
    return d


def hc_find(cid):
    return next((c for c in hosted().get("clubs", []) if c.get("id") == cid), None)


def hc_left(c):
    return max(0, int(c.get("seats") or 0) - int(c.get("taken") or 0))


def pre_checkout(q):
    """Telegram спрашивает перед списанием звёзд: подтверждаем, если клуб есть и места остались (ответ нужен за 10 секунд)."""
    pl = q.get("invoice_payload", "")
    c = hc_find(pl.split(":")[1]) if pl.startswith("hc:") else None
    if c and hc_left(c):
        api("answerPreCheckoutQuery", pre_checkout_query_id=q["id"], ok=True)
    else:
        api("answerPreCheckoutQuery", pre_checkout_query_id=q["id"], ok=False, error_message="Места в клубе закончились - деньги не списаны.")


def paid(m, fr, chat):
    """Оплата прошла: приглашение человеку, сообщение владелице, +1 занятое место в books/hosted.json."""
    sp = m["successful_payment"]
    cid = sp.get("invoice_payload", "hc::").split(":")[1]
    _HC["t"] = 0
    data = hosted()
    c = next((x for x in data.get("clubs", []) if x.get("id") == cid), None)
    if c:
        c["taken"] = int(c.get("taken") or 0) + 1
        json.dump(data, open(HOSTED, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    title = f"«{c.get('t')}» с {c.get('host', {}).get('n', '')}" if c else cid
    btn = []
    if c and c.get("join"):
        btn.append([{"text": "Открыть клуб в Норе", "url": c["join"]}])
    if c and c.get("chat"):
        btn.append([{"text": "Войти в чат клуба", "url": c["chat"]}])
    api("sendMessage", chat_id=chat, text=f"Оплата прошла - ты в клубе {title}. " + ("Ниже вход в клуб и чат." if btn else "Приглашение пришлём сюда же в ближайшее время."),
        **({"reply_markup": {"inline_keyboard": btn}} if btn else {}))
    who = " ".join(x for x in [fr.get("first_name"), fr.get("last_name")] if x) or "Читатель"
    if owner_id:
        api("sendMessage", chat_id=owner_id, text=f"💫 Оплата: {who}{' @' + fr['username'] if fr.get('username') else ''} · #u{chat}\nКлуб {title} - {sp.get('total_amount')} ⭐\n"
            f"Вернуть деньги: /refund {chat} {sp.get('telegram_payment_charge_id')}")


def handle(m):
    """Одно сообщение. Возвращает False, если его пока нельзя обработать (владелица ещё не известна)."""
    global owner_id
    fr, chat = m.get("from", {}), m["chat"]["id"]
    if m["chat"].get("type") != "private":
        return True
    text = m.get("text") or m.get("caption") or ""
    if "successful_payment" in m:
        paid(m, fr, chat)
        return True
    if "write_access_allowed" in m:
        sub(chat, fr)
        return True
    if text.startswith("/stop") or text.lower().strip() in ("стоп", "отписаться"):
        sub(chat, fr, False)
        api("sendMessage", chat_id=chat, text="Хорошо, больше не буду присылать советы. Чтобы вернуть - напиши /start.")
        return True
    if (fr.get("username") or "").lower() == OWNER:
        sub(chat, fr)
        if owner_id != chat:
            owner_id = state["owner"] = chat
            save()
        rep = m.get("reply_to_message")
        tag = re.search(r"#u(\d+)", (rep or {}).get("text") or (rep or {}).get("caption") or "")
        if rep and tag:
            ok = api("copyMessage", chat_id=int(tag.group(1)), from_chat_id=chat, message_id=m["message_id"])
            api("sendMessage", chat_id=chat, text="✓ Отправлено" if ok else "Не получилось отправить - человек мог остановить бота.", reply_to_message_id=m["message_id"])
        elif text.startswith("/refund"):
            pr = text.split()
            ok = len(pr) == 3 and api("refundStarPayment", user_id=int(pr[1]), telegram_payment_charge_id=pr[2])
            api("sendMessage", chat_id=chat, text="✓ Звёзды возвращены" if ok else "Не получилось вернуть - проверь команду: /refund <id> <charge_id>")
        elif text.startswith("/start"):
            api("sendMessage", chat_id=chat, text="Готово! Сюда будут приходить вопросы читателей. Чтобы ответить, смахни сообщение влево и нажми «Ответить».")
        return True
    sub(chat, fr)
    hc = re.match(r"/start hc_([a-z0-9-]{2,40})", text)
    if hc:  # вступление в клуб с ведущим: счёт в звёздах Telegram, после оплаты - приглашение (paid)
        c = hc_find(hc.group(1))
        if not c:
            api("sendMessage", chat_id=chat, text="Этот клуб уже не набирает участников. Загляни в Нору - там есть другие.")
            return True
        if not hc_left(c):
            api("sendMessage", chat_id=chat, text=f"В клубе «{c.get('t')}» места закончились. Напиши сюда - сообщим, если освободится.")
            return True
        stars = int(c.get("stars") or 0)
        if stars <= 0:  # звёзды не назначены - заявка владелице, как раньше
            who = " ".join(x for x in [fr.get("first_name"), fr.get("last_name")] if x) or "Читатель"
            if owner_id:
                api("sendMessage", chat_id=owner_id, text=f"🎟 Заявка в клуб «{c.get('t')}»\n{who}{' @' + fr['username'] if fr.get('username') else ''} · #u{chat}\n\nОтветь на это сообщение - ссылкой на оплату и приглашением.")
            api("sendMessage", chat_id=chat, text=f"Записали тебя в клуб «{c.get('t')}». Скоро пришлём сюда ссылку на оплату и приглашение.")
            return True
        h = c.get("host", {})
        ok = api("sendInvoice", chat_id=chat, title=f"Клуб «{c.get('t')}»"[:32],
                 description=f"Книжный клуб с {h.get('n', 'ведущим')} в Норе: заметки к каждой части, эфиры и чат клуба. Старт {c.get('start', '')}."[:255],
                 payload=f"hc:{c['id']}", currency="XTR", prices=[{"label": "Участие в клубе", "amount": stars}])
        if not ok:
            api("sendMessage", chat_id=chat, text="Не получилось выставить счёт - напиши сюда, поможем.")
        return True
    if text.startswith("/start"):
        api("sendMessage", chat_id=chat, text="Привет! Это Нора: подберу книги под твой вкус и подскажу, что читать дальше.\n\nРаз в неделю Шуршуня будет присылать сюда одну книгу для тебя (отписаться - /stop).\n\nЕсли есть вопрос или идея - просто напиши сюда, мы ответим.",
            reply_markup={"inline_keyboard": [[{"text": "Открыть Нору", "web_app": {"url": APP}}]]})
        return True
    if not owner_id:
        return False
    who = " ".join(x for x in [fr.get("first_name"), fr.get("last_name")] if x) or "Читатель"
    head = f"✉️ {who}{' @' + fr['username'] if fr.get('username') else ''} · #u{chat}"
    if text and not any(k in m for k in ("photo", "document", "video", "voice")):
        api("sendMessage", chat_id=owner_id, text=f"{head}\n\n{text}")
    else:
        api("sendMessage", chat_id=owner_id, text=head)
        api("copyMessage", chat_id=owner_id, from_chat_id=chat, message_id=m["message_id"])
    if chat not in acked:
        acked.add(chat)
        api("sendMessage", chat_id=chat, text="Спасибо! Передали в команду Норы - ответим здесь же.")
    return True


# LOOP=секунды: дежурим всё это время с долгим ожиданием — ответы почти мгновенные; иначе один проход
end = time.time() + int(os.environ.get("LOOP") or 0)
offset, n = None, 0
while True:
    wait = 50 if time.time() < end - 60 else 0
    ups = api("getUpdates", offset=offset, timeout=wait, allowed_updates=["message", "pre_checkout_query"]) or []
    stop = False
    for u in ups:
        if u.get("pre_checkout_query"):
            pre_checkout(u["pre_checkout_query"])
        if u.get("message") and not handle(u["message"]):
            stop = True
            break
        offset, n = u["update_id"] + 1, n + 1
    if stop or time.time() >= end - 60:
        break
if offset:
    api("getUpdates", offset=offset, timeout=0)  # подтверждаем обработанные
print("обработано сообщений:", n)
