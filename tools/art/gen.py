#!/usr/bin/env python3
"""Пробные рисунки для итогов года через совместимый с OpenAI сервис картинок.
Секреты: IMAGE_API_KEY, IMAGE_BASE_URL (адрес вида https://.../v1). Модель - IMAGE_MODEL (по умолчанию gpt-image-2).
SCENES=main,book - какие сцены, N - вариантов на сцену. Картинки кладутся в art_out/ (их забирает workflow)."""
import base64, json, os, sys, urllib.request, urllib.error

KEY = os.environ.get("IMAGE_API_KEY", "").strip()
BASE = (os.environ.get("IMAGE_BASE_URL", "").strip() or "https://dindindon.ru/v1").rstrip("/")
MODEL = os.environ.get("IMAGE_MODEL", "gpt-image-2").strip() or "gpt-image-2"
N = int(os.environ.get("N", "2") or 2)
P = json.load(open(os.path.join(os.path.dirname(__file__), "prompts.json"), encoding="utf-8"))
want = [s for s in (os.environ.get("SCENES") or ",".join(P["scenes"])).split(",") if s in P["scenes"]]
os.makedirs("art_out", exist_ok=True)
if not KEY or not BASE:
    print("нет IMAGE_API_KEY или IMAGE_BASE_URL"); sys.exit(1)
if not BASE.endswith("/v1"):
    BASE += "/v1"


def call(prompt, size="1024x1536"):
    body = json.dumps({"model": MODEL, "prompt": prompt, "size": size, "n": 1, "quality": "high"}).encode()
    req = urllib.request.Request(BASE + "/images/generations", data=body, headers={"Content-Type": "application/json", "Authorization": "Bearer " + KEY})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read()), 200
    except urllib.error.HTTPError as e:
        return {"error": e.read()[:400].decode("utf-8", "replace")}, e.code
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}, 0


try:  # какие модели картинок есть у сервиса
    rq = urllib.request.Request(BASE + "/models", headers={"Authorization": "Bearer " + KEY})
    ms = [m.get("id", "") for m in json.loads(urllib.request.urlopen(rq, timeout=60).read()).get("data", [])]
    print("модели с картинками:", [m for m in ms if "image" in m.lower() or "dall" in m.lower()] or "не видно", "| всего моделей:", len(ms))
except Exception as e:  # noqa: BLE001
    print("список моделей недоступен:", str(e)[:150])
ok = 0
for s in want:
    for i in range(N):
        sc = P["scenes"][s]
        wide = isinstance(sc, dict)
        j, c = call((sc["p"] if wide else sc) + "\n\n" + (sc.get("style") or P["style"] if wide else P["style"]), sc.get("size", "1536x1024") if wide else "1024x1536")
        if c != 200:
            print(s, i, "ошибка", c, str(j)[:300]); continue
        d = (j.get("data") or [{}])[0]
        if d.get("b64_json"):
            raw = base64.b64decode(d["b64_json"])
        elif d.get("url"):
            raw = urllib.request.urlopen(d["url"], timeout=120).read()
        else:
            print(s, i, "пустой ответ", str(j)[:200]); continue
        open(f"art_out/{s}_{i+1}.png", "wb").write(raw); ok += 1
        print(s, i, "готово", len(raw) // 1024, "КБ")
print("всего картинок:", ok)
