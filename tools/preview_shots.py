# Рендер картинок предпросмотра для Telegram (запускается в GitHub Actions, где есть доступ к обложкам)
import asyncio,json,os,urllib.parse
from playwright.async_api import async_playwright
os.makedirs("out",exist_ok=True);O="out/"
async def idt(route):
  await route.fulfill(status=200,content_type="application/json",body=json.dumps({"localId":"u1","idToken":"t","refreshToken":"r","email":"anya@mail.ru","expiresIn":"3600"}))
async def fs(route):
  if route.request.method=="GET": await route.fulfill(status=404,body="{}")
  else: await route.fulfill(status=200,content_type="application/json",body="{}")
SLIDES=[
 ("1_home","Твой книжный советник","Что почитать —<br><em>подскажет Шуршуня</em>","Подбирает книги под твой вкус и никогда не предлагает то, что ты уже прочитала.","#7A2E4A","#C98A3A"),
 ("2_feed","Лента","Листай книги,<br><em>как сторис</em>","✓ — на полку, ✕ — не моё. С каждой оценкой советы всё точнее.","#4A2A7A","#D08A5A"),
 ("3_where","Без поисков по сайтам","Где прочитать —<br><em>сразу</em>","Литрес, Яндекс Книги, бумажная — Нора покажет, где есть книга.","#22406E","#C98A3A"),
 ("4_search","Поиск","Ромэнтези, дарк роман,<br><em>новинки</em>","Фильтры по жанру и настроению — найдётся книга на любой вечер.","#6E2A3C","#B0607A"),
 ("5_book","Все полки в одном месте","Все твои книги —<br><em>в одной Норе</em>","Бумажные, из Литрес, Яндекс Книг и LiveLib. Оценки, отзывы и заметки рядом.","#5A3A22","#C98A3A"),
 ("6_stats","Статистика","Твой год<br><em>в книгах</em>","Страницы, любимые авторы и итоги года — красиво, хоть в сторис.","#3C2A6E","#C9708A"),
]
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(args=["--no-sandbox"])
    ctx=await b.new_context(viewport={"width":390,"height":844},device_scale_factor=3,is_mobile=True,has_touch=True)
    await ctx.route('**/identitytoolkit.googleapis.com/**',idt);await ctx.route('**/firestore.googleapis.com/**',fs)
    await ctx.route('**/securetoken.googleapis.com/**',lambda r:r.fulfill(status=200,content_type="application/json",body=json.dumps({"id_token":"t","refresh_token":"r","user_id":"u1","expires_in":"3600"})))
    await ctx.add_init_script("localStorage.setItem('zal.coach','1');localStorage.setItem('zal.coachsx','1');localStorage.setItem('zal.sync.hs',JSON.stringify({never:1}));['col','fr','sum','feed'].forEach(k=>localStorage.setItem('zal.tour.'+k,'1'));localStorage.setItem('zal.fgen',JSON.stringify({gen:['romantasy']}))")
    pg=await ctx.new_page();errs=[];pg.on("pageerror",lambda e:errs.append(str(e)[:200]));js=lambda c:pg.evaluate(c); w=lambda ms=1500:pg.wait_for_timeout(ms)
    clean="document.querySelectorAll('.toast,#toast,.tip,.tour').forEach(t=>t.remove())"
    shot=lambda n:pg.screenshot(path=O+n+".png")
    await pg.goto("http://localhost:8766/app.html?app=1");await w(4000)
    await js("document.getElementById('introGo').click()");await w(1500)
    for step,idx in enumerate([[2,8,13,14,18,21],[0,1,2]]):
      for i in idx:
        await js(f"document.querySelectorAll('#onbGrid .op')[{i}].click()");await w(500)
        await js("document.querySelector('#rmSt [data-st=\"5\"]').click()");await w(450)
      await js("document.getElementById('onbNext').click()");await w(1500)
    await pg.fill("#auN","Аня");await pg.fill("#auE","anya@mail.ru");await pg.fill("#auP","secret123");await js("document.getElementById('auGo').click()");await w(3000)
    await js(clean);await w(6000);await js(clean);await shot("1_home")
    await js("document.querySelector('.dock [data-s=feed]').click()");await w(5000);await js(clean);await shot("2_feed")
    await js("document.querySelector('.slide [data-want]').click()");await w(1500)
    await js("const t=document.getElementById('whT');t&&t.click()");await w(4000);await js(clean);await shot("3_where")
    await js("document.querySelector('#vsheet .sh-bg').click()");await w(800)
    await js("document.querySelector('.dock [data-s=col]').click()");await w(1500)
    await js("document.getElementById('srchB').click()");await w(1200)
    await js("([...document.querySelectorAll('#fwrap button')].find(b=>/Ромэнтези/.test(b.textContent))||document.querySelector('#fwrap button')).click()");await w(400)
    await js("document.querySelector('[data-fshow]').click()");await w(5000);await js(clean);await shot("4_search")
    await js("document.querySelectorAll('#fres .fr')[1].click()");await w(5000);await js(clean);await shot("5_book")
    await js("location.reload()");await w(5000)
    await js("document.querySelector('.dock [data-s=sum]').click()");await w(5000);await js(clean);await shot("6_stats")
    print(errs)
    fp=await b.new_page(viewport={"width":1080,"height":1920})
    for i,(img,k,h,pp,a,bb) in enumerate(SLIDES):
      q={"k":k,"h":h,"p":pp,"img":"../out/"+img+".png","a":a,"b":bb}
      await fp.goto("http://localhost:8766/tools/frame.html?i="+str(i)+"#"+urllib.parse.quote(json.dumps(q)));await fp.wait_for_timeout(1500)
      await fp.screenshot(path=O+f"nora_preview_{i+1}.png")
    await b.close()
asyncio.run(main())
