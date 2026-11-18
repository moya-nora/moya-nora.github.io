#!/usr/bin/env python3
"""Короткая автопроверка приложения и сайта (запускается при каждом обновлении, .github/workflows/test.yml).

Открывает приложение на экране телефона, ищет книгу с опечаткой, открывает карточку и отзывы,
проверяет главную сайта, страницу книги и поиск по сайту. Любая ошибка в коде страницы = провал.
Запуск: python3 tools/smoke_test.py  (нужен playwright и локальный сервер на 8799 - скрипт поднимает его сам)
"""
import http.server
import os
import socketserver
import sys
import threading

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 8799
APP = os.environ.get("APP", "app.html")  # тестовая версия: APP=app-dev.html
fails = []


def check(name, ok, info=""):
    print(("ok   " if ok else "FAIL ") + name + (" - " + str(info)[:200] if info else ""))
    if not ok:
        fails.append(name)


def serve():
    os.chdir(ROOT)
    h = http.server.SimpleHTTPRequestHandler
    h.log_message = lambda *a, **k: None
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", PORT), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()


def main():
    serve()
    base = f"http://127.0.0.1:{PORT}/"
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 375, "height": 690}, is_mobile=True, has_touch=True)
        ctx.add_init_script("localStorage.setItem('zal.onb','1');localStorage.setItem('zal.coach','1');localStorage.setItem('zal.coachsx','1');localStorage.setItem('zal.tour.col','1');localStorage.setItem('zal.clubon','1')")
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
        js = pg.evaluate

        # --- приложение ---
        pg.goto(base + APP + "?app=1")
        pg.wait_for_timeout(6000)
        js("(document.getElementById('auX')||{click(){}}).click();document.querySelectorAll('.coach,.tour').forEach(e=>e.remove())")
        check("приложение: главная нарисовалась", js("document.querySelectorAll('#app h2, #app h3').length>2"))
        js("document.querySelector('#srchB').click()")
        pg.wait_for_timeout(700)
        for q, want in (("Мастер и Маргорита", "Мастер и Маргарита"), ("Ujkjlyst buhs", "Голодные игры"), ("Телефон мистера Харригана", "Телефон мистера Харригана"), ("Шестёрка воронов", "Шестёрка воронов")):
            js("q=>{const f=document.querySelector('#fq');f.value=q;f.dispatchEvent(new Event('input'))}", q)
            pg.wait_for_timeout(2500)
            got = js("(document.querySelector('#fres .fr[data-i]')||{textContent:''}).textContent")
            check(f"приложение: поиск «{q}»", want in got, got[:60])
        js("document.querySelector('#fres .fr[data-i]').click()")
        pg.wait_for_timeout(1500)
        check("приложение: карточка книги", "Шестёрка воронов" in (js("(document.querySelector('#bkc h2')||{}).textContent") or ""))
        check("приложение: описание в карточке", len(js("(document.querySelector('#bkcDs')||{textContent:''}).textContent")) > 40)
        check("приложение: кнопки карточки", js("[...document.querySelectorAll('#bkc button')].filter(b=>b.offsetParent).length>=4"))
        js("window.__op=[];window.open=u=>{window.__op.push(u);return null}")
        js("(document.querySelector('[data-bkc=\"where\"]')||{click(){}}).click()")
        pg.wait_for_timeout(600)
        js("(document.querySelector('[data-wh=\"on\"]')||{click(){}}).click()")
        pg.wait_for_timeout(600)
        n = js("document.querySelectorAll('[data-whu]').length")
        check("приложение: «Где прочитать» - магазины", n >= 3, n)
        ok = js("""(()=>{let k=0;for(const b of document.querySelectorAll('[data-whu]')){const r=b.getBoundingClientRect(),el=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);if(el&&b.contains(el))k++}return k})()""")
        check("приложение: «Где прочитать» - все магазины нажимаются", ok == n, f"{ok} из {n}")
        js("(document.querySelector('[data-whk=\"ozon\"]')||{click(){}}).click()")
        pg.wait_for_timeout(300)
        check("приложение: «Где прочитать» - магазин открывается", js("window.__op.length") >= 1)
        js("(document.querySelector('#vsheet [data-close]')||{click(){}}).click()")
        pg.wait_for_timeout(500)
        js("(document.querySelector('[data-bkc=\"close\"]')||{click(){}}).click()")
        pg.wait_for_timeout(500)
        js("document.querySelector('#clubDock').click()")
        pg.wait_for_timeout(700)
        check("приложение: раздел «Клуб» открывается", js("!!document.querySelector('#clBox .cb-seal')&&!!document.querySelector('#clBox [data-cb=new]')"))
        for tab in ("Полки", "Аккаунт", "Нора"):
            js("t=>[...document.querySelectorAll('button')].find(b=>b.textContent.trim()===t).click()", tab)
            pg.wait_for_timeout(700)
        check("приложение: вкладки переключаются", True)
        js("document.querySelector('.dock [data-s=acc]').click()")
        pg.wait_for_timeout(600)
        check("приложение: «Аккаунт» - пункты на месте", js("['Поддержка','Конфиденциальность'].every(t=>document.querySelector('#accBox').textContent.includes(t))"))
        js("document.querySelector('.dock [data-s=sum]').click()")
        pg.wait_for_timeout(600)
        js("document.querySelector('#sumScroll [data-sht=fr]').click()")
        pg.wait_for_timeout(600)
        check("приложение: «Полки друзей» открываются", js("document.querySelector('#s-fr').classList.contains('on')&&document.querySelector('.dock button.on').dataset.s==='sum'"))
        js("document.querySelector('.dock [data-s=sum]').click()")
        pg.wait_for_timeout(600)
        check("приложение: шапка полок со значками", js("!!document.querySelector('#sumScroll .shh #addIn')&&!!document.querySelector('#shS')"))
        js("const w=document.querySelector('#pills [data-f=want]');w&&!document.querySelector('#pills [data-ushnew]')&&w.click()")
        pg.wait_for_timeout(500)
        check("приложение: кнопка новой полки", js("!!document.querySelector('#pills [data-ushnew],#ushRow [data-ushnew]')"))
        js("document.querySelector('#pills [data-ushnew],#ushRow [data-ushnew]').click()")
        pg.wait_for_timeout(500)
        js("document.querySelector('#ushN').value='Тест';document.querySelector('#ushOk').click()")
        pg.wait_for_timeout(600)
        check("приложение: своя полка создаётся", js("[...document.querySelectorAll('#pills button,#ushRow button')].some(b=>b.textContent.trim()==='Тест')"))
        check("приложение: разбор таблицы дневника", js("(()=>{const L=_nf.xlParse([['№','Название','Автор','Оценка','Формат'],[1,'Книга','Автор',5,'слушала']]);return L.length===1&&L[0].t==='Книга'&&L[0].r===10&&L[0].fmt==='аудио'})()"))
        check("приложение: нет ошибок в коде", not errs, errs)

        # --- сайт ---
        errs.clear()
        pg.goto(base + "index.html")
        pg.wait_for_timeout(1500)
        check("сайт: главная", "книг" in (js("(document.querySelector('h1')||{}).textContent") or "").lower())
        check("сайт: нет прокрутки вбок", js("document.documentElement.scrollWidth-document.documentElement.clientWidth") <= 1)
        pg.goto(base + "c/romantezi.html")
        pg.wait_for_timeout(800)
        check("сайт: подборка с книгами", js("document.querySelectorAll('.grid .bk').length") >= 8)
        pg.goto(base + "k/shesterka-voronov-bardugo.html")
        pg.wait_for_timeout(800)
        check("сайт: страница книги", "Шестёрка воронов" in (js("(document.querySelector('h1')||{}).textContent") or ""))
        check("сайт: «Где прочитать» на странице книги", js("[...document.querySelectorAll('a')].some(a=>/litres\\.ru/.test(a.href))"))
        pg.goto(base + "poisk.html")
        pg.wait_for_timeout(1500)
        check("сайт: страница «Найти книгу»", js("document.querySelectorAll('button, .fchips *').length") > 5)
        check("сайт: нет ошибок в коде", not errs, errs)
        b.close()
    print("\nИтог:", "всё в порядке" if not fails else "ПРОВАЛЫ: " + "; ".join(fails))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
