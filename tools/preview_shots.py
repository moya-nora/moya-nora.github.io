import asyncio,sys,json

import os
os.makedirs("out",exist_ok=True)
async def idt(route):
  await route.fulfill(status=200,content_type="application/json",body=json.dumps({"localId":"u1","idToken":"t","refreshToken":"r","email":"anya@mail.ru","expiresIn":"3600"}))
async def fs(route):
  r=route.request
  if r.method=="GET": await route.fulfill(status=404,body="{}")
  else: await route.fulfill(status=200,content_type="application/json",body="{}")
from playwright.async_api import async_playwright
O="out/"
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(args=["--no-sandbox"])
    ctx=await b.new_context(viewport={"width":390,"height":844},device_scale_factor=3,is_mobile=True,has_touch=True)
    await ctx.route('**/identitytoolkit.googleapis.com/**',idt);await ctx.route('**/firestore.googleapis.com/**',fs)
    await ctx.route('**/securetoken.googleapis.com/**',lambda r:r.fulfill(status=200,content_type="application/json",body=json.dumps({"id_token":"t","refresh_token":"r","user_id":"u1","expires_in":"3600"})))
    await ctx.add_init_script("localStorage.setItem('zal.coach','1');localStorage.setItem('zal.coachsx','1');localStorage.setItem('zal.sync.hs',JSON.stringify({never:1}));['col','fr','sum','feed'].forEach(k=>localStorage.setItem('zal.tour.'+k,'1'))")
    pg=await ctx.new_page();errs=[];pg.on("pageerror",lambda e:errs.append(str(e)[:200]));js=lambda c:pg.evaluate(c); w=lambda ms=1500:pg.wait_for_timeout(ms)
    clean="document.querySelectorAll('.toast,#toast,.tip,.tour,#whT').forEach(t=>t.remove())"
    await pg.goto("http://localhost:8766/app.html?app=1");await w(4000)
    await pg.screenshot(path=O+"0_splash.png") if False else None
    await js("document.getElementById('introGo').click()");await w(1500)
    for step in range(2):
      for i in [0,2,3,6,8,10,13,15][: (8 if step==0 else 3)]:
        await js(f"document.querySelectorAll('#onbGrid .op')[{i}].click()");await w(500)
        await js("document.querySelector('#rmSt [data-st=\"5\"]').click()");await w(450)
      await js("document.getElementById('onbNext').click()");await w(1500)
    await pg.fill("#auN","Аня");await pg.fill("#auE","anya@mail.ru");await pg.fill("#auP","secret123");await js("document.getElementById('auGo').click()");await w(3000)
    await js(clean);await w(6000);await js(clean)
    await pg.screenshot(path=O+"1_home.png")
    await js("document.querySelector('.dock [data-s=feed]').click()");await w(5000);await js(clean);await pg.screenshot(path=O+"2_feed.png")
    await js("document.querySelector('.dock [data-s=col]').click()");await w(1500)
    await js("document.getElementById('srchB').click()");await w(1200)
    await js("document.querySelectorAll('#fwrap button')[0].click()");await w(400)
    await js("document.querySelector('[data-fshow]').click()");await w(5000);await js(clean);await pg.screenshot(path=O+"3_search.png")
    await js("document.querySelector('#fres .fr').click()");await w(5000);await js(clean);await pg.screenshot(path=O+"4_book.png")
    await js("location.reload()");await w(5000)
    await js("document.querySelector('.dock [data-s=sum]').click()");await w(5000);await js(clean);await pg.screenshot(path=O+"5_stats.png")
    print(errs);await b.close()
asyncio.run(main())
