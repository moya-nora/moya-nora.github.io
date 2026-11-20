#!/usr/bin/env python3
"""Новые книги серий, за которыми следят читатели («Сообщить, когда выйдет новая книга» в карточке книги).

Вызывается из дежурства бота (bot_relay.py): tick(state, save), проверка раз в 3 часа.
Кому: записи notify/<uid> с полем fs (серии Фантлаба). Telegram (поле tg) - сообщение от бота,
без Telegram (поле wp) - веб-пуш в браузер.
Что проверяем на Фантлабе у каждой серии (прямые части: романы, повести, сборники):
  • у части появилось русское издание - «вышла на русском»;
  • издательство объявило русское издание (план) - «скоро на русском»;
  • часть вышла в оригинале или в серии объявлена новая книга.
Снимок серии у каждого читателя - state["sr"][uid][серия]; в первый раз только запоминаем.
Прочитанное (поле read) не присылаем. DRY=1 - только показать тексты."""
import html, json, os, time, urllib.parse, urllib.request

import bot_reqs

TOKEN = os.environ.get("BOT_TOKEN", "").strip()
DRY = os.environ.get("DRY") == "1"
APP = "https://nora-books.ru/app.html"
EVERY = 3 * 3600
SERT = {"роман", "повесть", "сборник", "роман-эпопея", "антология"}
_s = {"last": 0}


def norm(s):
    import re
    return re.sub(r"[^0-9a-zа-я]+", "", str(s or "").lower().replace("ё", "е"))


def fl(path):
    req = urllib.request.Request("https://api.fantlab.ru" + path, headers={"User-Agent": "nora-bot/1.0 (nora-books.ru)"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)


def ru_status(wid, cache):
    """(есть русское издание, объявлено русское издание) для произведения."""
    if wid in cache:
        return cache[wid]
    ru = plan = 0
    try:
        j = fl(f"/work/{wid}/extended")
        for b in (j.get("editions_blocks") or {}).values():
            for e in b.get("list") or []:
                if e.get("lang_code") not in (None, "", "ru"):
                    continue
                if e.get("plandate"):
                    plan = 1
                else:
                    ru = 1
    except Exception as e:  # noqa: BLE001
        print("серии: издания", wid, "недоступны:", str(e)[:80])
        return None
    time.sleep(0.3)
    cache[wid] = (ru, plan)
    return cache[wid]


def parts(cid, cache):
    """Прямые части серии: [(id, название, вышла, объявлена)]."""
    if cid in cache:
        return cache[cid]
    try:
        j = fl(f"/work/{int(cid)}/extended")
    except Exception as e:  # noqa: BLE001
        print("серии:", cid, "недоступна:", str(e)[:80])
        cache[cid] = None
        return None
    L = []
    for w in j.get("children") or []:
        t = w.get("work_name") or w.get("work_name_orig") or ""
        if int(w.get("deep") or 0) == 1 and str(w.get("work_type") or "").lower() in SERT and t:
            L.append((int(w["work_id"]), t, int(w.get("work_published") or 0), int(w.get("work_preparing") or 0)))
    time.sleep(0.3)
    cache[cid] = (L, ((j.get("authors") or [{}])[0] or {}).get("name") or "")
    return cache[cid]


def events(old, L, author, name, read, rucache):
    """Сравнить снимок с текущим. Возвращает (новые события, новый снимок)."""
    out, snap = [], {}
    for wid, t, pub, prep in L:
        was = (old or {}).get(str(wid))
        ru, plan = (was[2], was[3]) if was and len(was) >= 4 else (0, 0)
        if pub and not ru:   # русское издание проверяем, пока его нет; при ошибке оставляем прежнее
            st = ru_status(wid, rucache)
            if st:
                ru, plan = st
        snap[str(wid)] = [pub, prep, ru, plan]
        if old is None or norm(t) in read:
            continue
        bk = t + "|" + author
        if ru and not (was and len(was) >= 3 and was[2]):
            out.append((f"📚 Вышла на русском новая книга серии «{name}»: «{t}»", bk))
        elif plan and not ru and not (was and len(was) >= 4 and was[3]):
            out.append((f"📚 Скоро на русском: издательство объявило «{t}» из серии «{name}»", bk))
        elif was is None and (pub or prep):
            out.append((f"🔔 В серии «{name}» " + (f"вышла новая книга «{t}» - пока на языке оригинала" if pub else f"объявлена новая книга «{t}»"), bk))
        elif was and not was[0] and pub:
            out.append((f"🔔 Вышла новая книга серии «{name}»: «{t}» - пока на языке оригинала", bk))
    return out, snap


def send(who, txt, bk):
    if DRY:
        print("серии →", who.get("tg") or "веб-пуш", txt)
        return True
    if who.get("tg") and TOKEN:
        data = {"chat_id": int(who["tg"]), "text": html.escape(txt), "parse_mode": "HTML",
                "reply_markup": {"inline_keyboard": [[{"text": "Открыть в Норе", "web_app": {"url": APP + "?bk=" + urllib.parse.quote(bk)}}]]}}
        j, c = bot_reqs.http(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data)
        return c == 200
    if isinstance(who.get("wp"), dict) and who["wp"].get("endpoint"):
        return bot_reqs.push(who["wp"], txt)
    return False


def people(H):
    """uid → запись notify (только у кого есть серии)."""
    out, page = {}, ""
    while True:
        j, c = bot_reqs.http(bot_reqs.DB + "/notify?pageSize=300" + ("&pageToken=" + page if page else ""), headers=H)
        if c != 200:
            print("серии: список уведомлений недоступен", c)
            return out
        for doc in j.get("documents") or []:
            try:
                v = json.loads(doc["fields"]["d"]["stringValue"])
                if v.get("fs") and (v.get("tg") or (isinstance(v.get("wp"), dict) and v["wp"].get("endpoint"))):
                    out[doc["name"].rsplit("/", 1)[1]] = v
            except Exception:  # noqa: BLE001
                pass
        page = j.get("nextPageToken") or ""
        if not page:
            return out


def tick(state, save=None, force=False):
    if not force and time.time() - _s["last"] < EVERY:
        return 0
    _s["last"] = time.time()
    if not bot_reqs.PW:
        return 0
    H = bot_reqs._auth()
    if not H:
        return 0
    P = people(H)
    sr = state.setdefault("sr", {})
    cyc, rucache, n = {}, {}, 0
    for uid, v in P.items():
        mine = sr.setdefault(uid, {})
        read = set(v.get("read") or [])
        keep = {}
        for f in (v.get("fs") or [])[:30]:
            cid = str(f.get("id"))
            got = parts(cid, cyc)
            if not got:
                if cid in mine:
                    keep[cid] = mine[cid]
                continue
            L, author = got
            ev, snap = events(mine.get(cid), L, author, f.get("n") or "серии", read, rucache)
            keep[cid] = snap
            for txt, bk in ev[:3]:
                if send(v, txt, bk):
                    n += 1
        sr[uid] = keep
    for uid in [u for u in sr if u not in P]:
        del sr[uid]
    if save:
        save()
    print("серии: проверено читателей", len(P), "| отправлено", n)
    return n
