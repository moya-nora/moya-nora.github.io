#!/usr/bin/env python3
"""Выпуск: тестовая версия (app-dev.html) -> настоящая (app.html).

Правило проекта: все правки приложения делаются в app-dev.html (nora-books.ru/app-dev.html?app=1 - с меткой «тестовая версия»).
Владелица проверяет, говорит «выпусти» - любой чат запускает этот скрипт:
  1) проверяет, что app.html никто не правил напрямую после прошлого выпуска (иначе эти правки потерялись бы);
  2) прогоняет автотест на app-dev.html;
  3) копирует app-dev.html в app.html и запоминает выпуск в tools/release.json.
Дальше - обычный git commit и push. Запуск: python3 tools/release.py   (--check - только проверить, ничего не копировать)
"""
import datetime, hashlib, json, os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP, DEV, REL = (os.path.join(ROOT, x) for x in ("app.html", "app-dev.html", "tools/release.json"))


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    only_check = "--check" in sys.argv
    rel = json.load(open(REL, encoding="utf-8")) if os.path.exists(REL) else {}
    if rel.get("app_sha") and sha(APP) != rel["app_sha"]:
        print("СТОП: app.html меняли напрямую после прошлого выпуска.")
        print("Перенеси эти правки в app-dev.html (git log -p -- app.html), потом выпускай. Иначе они пропадут.")
        sys.exit(2)
    if sha(APP) == sha(DEV):
        print("Тестовая и настоящая версии одинаковые - выпускать нечего."); return
    print("Автотест тестовой версии…")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "smoke_test.py")], env={**os.environ, "APP": "app-dev.html"})
    if r.returncode != 0:
        print("СТОП: автотест не прошёл - выпуск отменён."); sys.exit(1)
    if only_check:
        print("Проверка пройдена, можно выпускать."); return
    shutil.copyfile(DEV, APP)
    rel = {"app_sha": sha(APP), "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
    json.dump(rel, open(REL, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("Готово: app-dev.html выпущен в app.html. Теперь git add app.html tools/release.json, commit, push.")


if __name__ == "__main__":
    main()
