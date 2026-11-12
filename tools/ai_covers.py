#!/usr/bin/env python3
"""ИИ-обложки для книг со старыми обложками.

Берём книги ручного каталога (сначала самые известные). Если у книги на Фантлабе нет русского
издания с картинкой свежее 2015 года — просим нейросеть (Pollinations, бесплатно) нарисовать
иллюстрацию по описанию, а название и автора накладываем шрифтом Норы (tools/ai_cover.html).
Результат: img/ai/<ключ>.webp и books/ai_covers.json {"m": {ключ: "файл" | ""}, "t": {ключ: "ГГГГ-ММ"}}.
Работает, пока не кончится время (AI_MINUTES), и продолжает со следующего запуска."""
import asyncio, hashlib, json, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(ROOT, "books", "ai_covers.json")
DIR = os.path.join(ROOT, "img", "ai")
MAX_MIN = int(os.environ.get("AI_MINUTES", "300"))
FRESH = 2015
T0 = time.time()
UA = {"User-Agent": "nora-ai-covers/1.0 (moya-nora.github.io)"}
STYLE = "contemporary illustrated book cover art, painterly, rich cinematic colors, elegant composition, no text, no letters, no typography, no watermark"


def norm(s):
    return re.sub(r"[^a-zа-я0-9]", "", str(s or "").lower().replace("ё", "е"))


def ikey(b):  # тот же ключ, что ikey() в приложении
    return norm(b["t"]) + "|" + norm(b.get("a") or "")


def get(url, tries=3, raw=False, timeout=40):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                d = r.read()
                return d if raw else json.loads(d.decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            if k == tries - 1:
                print("  !", url[:90], e, flush=True)
                return None
            time.sleep(20 * (k + 1))


def fantlab(b):
    """(год самого свежего русского издания с картинкой, описание) или None, если не нашли."""
    sur = norm(str(b.get("a") or "").split(" ")[-1])
    L = get("https://api.fantlab.ru/search-works?q=" + urllib.parse.quote(b["t"]) + "&page=1&onlymatches=1") or []
    w = next((w for w in L if not sur or sur in norm(w.get("autor_rusname")) or sur in norm(w.get("autor_name"))), None)
    if not w:
        return None
    j = get(f"https://api.fantlab.ru/work/{w['work_id']}/extended") or {}
    eds = [e for bl in (j.get("editions_blocks") or {}).values() for e in (bl.get("list") or [])]
    ys = [int(e.get("year") or 0) for e in eds if (e.get("pic_num") or 0) > 0 and (not e.get("lang_code") or e.get("lang_code") == "ru")]
    desc = re.sub(r"\[[^\]]*\]", "", j.get("work_description") or "").strip()
    return (max(ys) if ys else 0), desc[:900]


def scene(b, desc):
    q = ("Write one English sentence (max 40 words) describing a single striking visual scene for an illustrated "
         f"book cover of the novel «{b['t']}» by {b.get('a') or ''}. Base it on this summary: {desc or 'unknown'}. "
         "Describe only what is seen: characters, setting, light, mood. No text, no title, no quotes.")
    t = get("https://text.pollinations.ai/" + urllib.parse.quote(q) + "?model=openai", raw=True, timeout=90)
    t = (t or b"").decode("utf-8", "ignore").strip().replace("\n", " ")
    return t[:400] if 20 < len(t) < 600 else f"atmospheric scene from the book {b['t']}"


async def main():
    from playwright.async_api import async_playwright
    app = open(os.path.join(ROOT, "app.html"), encoding="utf-8").read()
    i = app.index("const CAT=") + len("const CAT=")
    CAT, _ = json.JSONDecoder().raw_decode(app[i:])
    CAT.sort(key=lambda b: -(b.get("q") or 0))
    try:
        st = json.load(open(OUT, encoding="utf-8"))
    except FileNotFoundError:
        st = {"m": {}, "t": {}}
    os.makedirs(DIR, exist_ok=True)
    ym = time.strftime("%Y-%m")
    done = made = 0
    async with async_playwright() as p:
        br = await p.chromium.launch(args=["--no-sandbox"])
        pg = await br.new_page(viewport={"width": 600, "height": 900})
        for b in CAT:
            if (time.time() - T0) / 60 > MAX_MIN:
                break
            k = ikey(b)
            if k in st["m"] and (st["m"][k] or st["t"].get(k, "") >= time.strftime("%Y", time.gmtime(time.time() - 365 * 86400))):
                continue
            done += 1
            fl = fantlab(b)
            if fl and fl[0] >= FRESH:
                st["m"][k] = "";st["t"][k] = ym
                continue
            desc = fl[1] if fl else ""
            prompt = scene(b, desc) + ", " + STYLE
            seed = int(hashlib.md5(k.encode()).hexdigest()[:6], 16)
            url = "https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt) + f"?width=768&height=1152&nologo=true&model=flux&seed={seed}"
            img = None
            for tr in range(4):
                img = get(url, tries=1, raw=True, timeout=180)
                if img and len(img) > 20000:
                    break
                img = None
                time.sleep(60)
            if not img:
                print("  нет картинки:", b["t"], flush=True)
                continue
            raw = os.path.join(DIR, "_raw.jpg")
            open(raw, "wb").write(img)
            fn = hashlib.md5(k.encode()).hexdigest()[:12] + ".webp"
            q = {"img": "../img/ai/_raw.jpg?" + fn, "t": b["t"], "a": b.get("a") or ""}
            await pg.goto("http://localhost:8766/tools/ai_cover.html?" + fn + "#" + urllib.parse.quote(json.dumps(q)))
            await pg.wait_for_timeout(1200)
            png = os.path.join(DIR, "_c.png")
            await pg.screenshot(path=png)
            from PIL import Image
            Image.open(png).convert("RGB").resize((480, 720), Image.LANCZOS).save(os.path.join(DIR, fn), "WEBP", quality=82)
            st["m"][k] = fn;st["t"][k] = ym;made += 1
            print(f"{made}. {b['t']} — {prompt[:80]}", flush=True)
            json.dump(st, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
            time.sleep(35)
        await br.close()
    for f in ("_raw.jpg", "_c.png"):
        try:
            os.remove(os.path.join(DIR, f))
        except FileNotFoundError:
            pass
    json.dump(st, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"проверено {done}, нарисовано {made}, всего обложек {sum(1 for v in st['m'].values() if v)}")

asyncio.run(main())
