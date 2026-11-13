#!/usr/bin/env python3
"""ИИ-обложки для книг ручного каталога.

Берём книги ручного каталога (сначала самые известные). Рисуем обложку только если на Фантлабе нет русского издания с картинкой свежее 2015 года. Просим нейросеть (Pollinations, бесплатно) нарисовать
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
LIMIT = int(os.environ.get("AI_LIMIT", "0"))  # для пробного запуска: сколько обложек нарисовать
VER = 2  # версия 2: у каждой книги своя картинка по сюжету, своё настроение и свои цвета, без лиц
NOFACE = "no faces, no portraits, no close-up people, people only as tiny distant figures or seen from behind, no text, no letters, no typography, no watermark"

# цвета — от настроения книги (теги каталога), первое совпадение главное
PALETTES = [
    (("смешное", "юмор", "сатира"), "bright sunny yellows, tangerine orange and sky blue, cheerful high-key light"),
    (("уют", "тёплое"), "warm honey, cream, soft terracotta and sage green, cosy golden lamplight"),
    (("романтичное", "любовь"), "blush pink, coral, peach and soft gold, tender warm light"),
    (("светлое", "вдохновляющее"), "fresh mint, pale turquoise, lemon and white, airy morning light"),
    (("хоррор", "жутковатое", "готика"), "ink black, bone white and blood crimson, eerie moonlight"),
    (("мрачное", "война"), "charcoal, rust, ash grey and smoky ochre, harsh dim light"),
    (("напряжённое", "триллер", "детектив"), "deep navy, signal red and stark white, high contrast noir light"),
    (("грустное", "медленное"), "muted slate blue, dove grey and faded lilac, quiet overcast light"),
    (("мистика", "магический реализм", "атмосферное"), "teal, violet and misty silver, dreamy haze"),
    (("космос", "научная фантастика", "искусственный интеллект"), "electric cyan, magenta and deep space indigo, glowing light"),
    (("море",), "ocean turquoise, sea foam and sand beige, salty bright air"),
    (("природа и животные", "деревня"), "leaf green, wheat gold and earth brown, natural daylight"),
    (("исторический роман", "история", "викторианская эпоха"), "sepia, ochre, oxblood and parchment, candlelit"),
    (("интеллектуальное", "философский роман"), "ultramarine, cream and a single vermilion accent, calm light"),
]
# манера рисунка — от жанра
STYLES = {
    "kids": "whimsical storybook gouache illustration, playful shapes",
    "fantasy": "rich painterly fantasy illustration, detailed environment",
    "scifi": "retro-futurist sci-fi poster illustration, bold geometric forms",
    "detective": "graphic noir illustration, strong shadows and shapes",
    "classic": "classic oil painting, visible brushstrokes, museum quality",
    "modern": "contemporary editorial illustration, textured flat colors",
    "nonfic": "minimal conceptual illustration, one strong symbolic object, lots of empty space",
}


def look(b):
    tg = set(b.get("tags") or [])
    pal = next((p for ks, p in PALETTES if tg & set(ks)), "harmonious colors chosen to match the story")
    sty = STYLES.get(b.get("g"), STYLES["modern"])
    if "сказка" in tg or "юмор" in tg:
        sty = "whimsical hand-drawn gouache illustration" if b.get("g") != "kids" else sty
    return pal, sty


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


def scene(b, desc, pal):
    tags = ", ".join(t for t in (b.get("tags") or []) if not t.startswith("троп:"))
    q = ("Write one English sentence (max 45 words) describing a single striking visual scene for an illustrated "
         f"book cover of «{b['t']}» by {b.get('a') or ''}. Summary: {desc or b.get('ann') or 'unknown'}. Mood: {tags}. "
         "Pick a place, an object, weather or a symbol that is specific to THIS story, so the cover could not belong to any other book. "
         f"Use these colors: {pal}. People may appear only as tiny distant figures or seen from behind, never faces. "
         "Describe only what is seen. No text, no title, no quotes.")
    t = get("https://text.pollinations.ai/" + urllib.parse.quote(q) + "?model=openai", raw=True, timeout=90)
    t = (t or b"").decode("utf-8", "ignore").strip().replace("\n", " ")
    return t[:420] if 20 < len(t) < 650 else f"a symbolic scene from the book {b['t']}"


FACE = None


def has_face(path):
    """Нашла ли проверка лицо заметного размера: такие картинки выбрасываем."""
    global FACE
    try:
        import cv2
    except ImportError:
        return False
    if FACE is None:
        FACE = [cv2.CascadeClassifier(cv2.data.haarcascades + f) for f in ("haarcascade_frontalface_default.xml", "haarcascade_profileface.xml")]
    im = cv2.imread(path)
    if im is None:
        return False
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    m = int(min(g.shape[:2]) * 0.07)
    return any(len(c.detectMultiScale(g, 1.1, 6, minSize=(m, m))) for c in FACE)


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
            # книги до 2005 года — всегда своя обложка (их издания на Фантлабе часто старые или некрасивые);
            # у новых книг — только если на Фантлабе нет русского издания с картинкой свежее 2015 года
            st.setdefault("v", {})
            if st["m"].get(k) and st["v"].get(k) == VER:
                continue
            if LIMIT and made >= LIMIT:
                break
            old = False  # рисуем только тем книгам, у которых нет свежего (с 2015) русского издания с обложкой — и классике тоже
            if not old and k in st["m"] and st["t"].get(k, "") >= time.strftime("%Y", time.gmtime(time.time() - 365 * 86400)):
                continue
            done += 1
            fl = fantlab(b)
            if not old and fl and fl[0] >= FRESH:
                st["m"][k] = "";st["t"][k] = ym
                continue
            desc = fl[1] if fl else ""
            pal, sty = look(b)
            prompt = scene(b, desc, pal) + f", {sty}, color palette: {pal}, " + NOFACE
            seed0 = int(hashlib.md5(k.encode()).hexdigest()[:6], 16)
            raw = os.path.join(DIR, "_raw.jpg")
            img = None
            for tr in range(6):  # до трёх попыток с разным зерном, если нашлось лицо
                url = "https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt) + f"?width=768&height=1152&nologo=true&model=flux&seed={seed0 + tr}"
                img = get(url, tries=1, raw=True, timeout=180)
                if not img or len(img) < 20000:
                    img = None
                    time.sleep(60)
                    continue
                open(raw, "wb").write(img)
                if has_face(raw):
                    print("  лицо на картинке, перерисовываю:", b["t"], flush=True)
                    img = None
                    time.sleep(20)
                    continue
                break
            if not img:
                print("  нет подходящей картинки:", b["t"], flush=True)
                continue
            fn = hashlib.md5(k.encode()).hexdigest()[:11] + "v.webp"
            oldf = st["m"].get(k)
            q = {"img": "../img/ai/_raw.jpg?" + fn, "t": b["t"], "a": b.get("a") or ""}
            await pg.goto("http://localhost:8766/tools/ai_cover.html?" + fn + "#" + urllib.parse.quote(json.dumps(q)))
            await pg.wait_for_timeout(1200)
            png = os.path.join(DIR, "_c.png")
            await pg.screenshot(path=png)
            from PIL import Image
            Image.open(png).convert("RGB").resize((480, 720), Image.LANCZOS).save(os.path.join(DIR, fn), "WEBP", quality=82)
            if oldf and oldf != fn:
                try:
                    os.remove(os.path.join(DIR, oldf))
                except FileNotFoundError:
                    pass
            st["m"][k] = fn;st["t"][k] = ym;st["v"][k] = VER;made += 1
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
