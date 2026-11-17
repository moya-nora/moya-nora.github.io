#!/usr/bin/env python3
"""Ручной каталог приложения (CAT, ~2300 книг с описаниями) живёт отдельным файлом books/cat.json, а не внутри app-dev.html.
Так браузер кэширует его отдельно и приложение быстрее запускается (3 МБ внутри страницы -> ~1,9 МБ).

Как менять ручной каталог: править books/cat.json, затем запустить python3 tools/make_cat.py -
он соберёт books/cat.<хэш>.js и пропишет новое имя в app-dev.html (старые файлы не удаляет: на них может ссылаться app.html до выпуска).
Первый запуск (если CAT ещё внутри app-dev.html) сам вынимает его в books/cat.json."""
import hashlib, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEV = os.path.join(ROOT, "app-dev.html")
SRC = os.path.join(ROOT, "books", "cat.json")


def cut_inline(s):
    i = s.find("const CAT=[")
    if i < 0:
        return s, None
    j = i + len("const CAT=")
    depth, k, instr, esc = 0, j, False, False
    while True:
        c = s[k]
        if instr:
            if esc: esc = False
            elif c == "\\": esc = True
            elif c == '"': instr = False
        else:
            if c == '"': instr = True
            elif c == "[": depth += 1
            elif c == "]":
                depth -= 1
                if depth == 0: break
        k += 1
    data = json.loads(s[j:k + 1])
    return s[:i] + 'const CAT=window.NORA_CAT||[]' + s[k + 1:], data


def main():
    s = open(DEV, encoding="utf-8").read()
    s, data = cut_inline(s)
    if data is not None:
        json.dump(data, open(SRC, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        print("CAT вынут из app-dev.html:", len(data), "книг")
    data = json.load(open(SRC, encoding="utf-8"))
    body = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    lit = body.replace("\\", "\\\\").replace("'", "\\'").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    js = "window.NORA_CAT=JSON.parse('" + lit + "');\n"
    h = hashlib.sha256(js.encode()).hexdigest()[:10]
    name = f"books/cat.{h}.js"
    open(os.path.join(ROOT, name), "w", encoding="utf-8").write(js)
    tag = f'<script src="{name}"></script>'
    if re.search(r'<script src="books/cat\.[0-9a-f]+\.js"></script>', s):
        s = re.sub(r'<script src="books/cat\.[0-9a-f]+\.js"></script>', tag, s)
    else:
        a = '<script>/* Скрипт Telegram нужен'
        assert a in s
        s = s.replace(a, tag + "\n" + a, 1)
    open(DEV, "w", encoding="utf-8").write(s)
    print("готово:", name, round(len(js.encode()) / 1024), "КБ; app-dev.html", round(len(s.encode()) / 1024), "КБ")


if __name__ == "__main__":
    main()
