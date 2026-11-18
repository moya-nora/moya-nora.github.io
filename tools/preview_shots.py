# Рендер картинок предпросмотра для Telegram (запускается в GitHub Actions, где есть доступ к обложкам)
import asyncio,json,os,urllib.parse,time,subprocess,glob
from playwright.async_api import async_playwright
os.makedirs("out",exist_ok=True);O="out/"
ONLY=[x for x in os.environ.get("ONLY","").split(",") if x]
async def idt(route):
  await route.fulfill(status=200,content_type="application/json",body=json.dumps({"localId":"u1","idToken":"t","refreshToken":"r","email":"anya@mail.ru","expiresIn":"3600"}))
async def fs(route):
  if route.request.method=="GET": await route.fulfill(status=404,body="{}")
  else: await route.fulfill(status=200,content_type="application/json",body="{}")
SLIDES=[
 ("1_home","Все полки в одном месте","Все твои книги —<br><em>в одной Норе</em>","Бумажные, из Литрес, Яндекс Книг, LiveLib и других сервисов. Оценки, отзывы и заметки рядом.","#7A2E4A","#C98A3A"),
 ("2_feed","Лента","Что почитать —<br><em>подскажет Шуршуня</em>","Подбирает книги под твой вкус и не предлагает уже прочитанное. С каждой оценкой подборка точнее.","#4A2A7A","#D08A5A"),
 ("3_where","Без долгих поисков","Где прочитать —<br><em>сразу</em>","Нора покажет, где купить или прочитать нужную книгу.","#22406E","#C98A3A"),
 ("4_search","Поиск","Найдётся книга<br><em>на любой вечер</em>","Классика, дарк роман, новинки — фильтры по жанру, настроению и тропам.","#6E2A3C","#B0607A"),
 ("6_diary","Читательский дневник","Запиши,<br><em>как тебе книга</em>","Оценка, настроение, отзыв и цитаты к каждой прочитанной книге.","#5A2A4E","#C98A3A"),
 ("7_club","Книжный клуб","Одна книга<br><em>на весь клуб</em>","Общий срок, вопросы для разговора и полка прочитанного.","#2A3E5E","#D0A060"),
 ("5_stats","Статистика","Твой год<br><em>в книгах</em>","Страницы, любимые авторы и итоги года — красиво, хоть в сторис.","#3C2A6E","#C9708A"),
]
DEMO={"rec":["Королевство шипов и роз|Маас","Там, где раки поют|Оуэнс","Тень ветра|Сафон","Семь мужей Эвелин Хьюго|Рид","До самого рая|Янагихара","Незримая жизнь Адди Ларю|Шваб","Шестёрка воронов|Бардуго"],
 "feed":["Семь мужей Эвелин Хьюго|Рид","Шестёрка воронов|Бардуго","Незримая жизнь Адди Ларю|Шваб","Семь мужей Эвелин Хьюго|Рид","Гипотеза любви|Хейзелвуд","Из крови и пепла|Арментроут","Жестокий принц|Блэк","Ночной цирк|Моргенштерн"]}
import time as _t
D=[("Четвёртое крыло","Ребекка Яррос","fantasy","США",10,"Залетела за два вечера. Виолетта и драконы - это любовь, жду продолжения.",["напряжённая","романтичная"],{"p":"залпом","h":"герои","e":"открытый"},"2026-11-14","Драконы не выбирают слабых."),
   ("Гордость и предубеждение","Джейн Остин","classic","Великобритания",10,"Перечитываю третий раз и всё равно смеюсь над миссис Беннет.",["ироничная","уютная"],{"p":"спокойно","h":"герои","e":"идеальный"},"2026-11-02","Я могла бы простить его гордость, если бы он не уязвил мою."),
   ("Ночной цирк","Эрин Моргенштерн","fantasy","США",8,"Самая красивая атмосфера за год. Хочу в этот цирк.",["атмосферная","загадочная"],{"p":"медленно","h":"атмосфера","e":"ожидаемый"},"2026-10-21",""),
   ("Джейн Эйр","Шарлотта Бронте","classic","Великобритания",10,"Джейн сильнее всех вокруг. Ночной Торнфилд - мурашки.",["мрачная","трогательная"],{"p":"залпом","h":"всё вместе","e":"идеальный"},"2026-10-05","Я не птица, и никакие сети не удержат меня.")]
M=[{"id":"u%d"%i,"t":t,"a":a,"g":g,"c":c,"r":r,"f":[],"n":n,"dm":dm,"dp":dp,"dd":dd,"rd":dd[:7]} for i,(t,a,g,c,r,n,dm,dp,dd,q) in enumerate(D)]
Q=[{"text":q,"book":"u%d"%i,"bt":D[i][0],"ts":1795000000000-i} for i,(*_,q) in enumerate(D) if q]
CLUB={"book":{"k":"","t":"Мастер и Маргарита","a":"Михаил Булгаков"},"parts":4,"per":7,"start":int(_t.time()*1000)-3*864e5,"meet":None,"chat":"","shelf":[],"cr":0}
async def fsc(route):
  r=route.request;u=r.url
  if r.method=='GET' and '/clubs/t1' in u:
    tail=u.split('/clubs/t1')[1].split('?')[0]
    if tail=='':
      await route.fulfill(status=200,content_type='application/json',body=json.dumps({"name":"x/clubs/t1","fields":{"n":{"stringValue":"Ночные читатели"},"o":{"stringValue":"u1"},"d":{"stringValue":json.dumps(CLUB,ensure_ascii=False)}}}));return
    if tail.startswith('/m'):
      docs=[{"name":"x/clubs/t1/m/f%d"%i,"fields":{"n":{"stringValue":n},"d":{"stringValue":json.dumps({"p":{"0":1} if i<3 else {},"v":[],"rs":{},"r":{},"h":[]})},"u":{"integerValue":str(int(_t.time()*1000))}}} for i,n in enumerate(["katya_reads","lisa.books","marina","sonya_night","vera"])]
      await route.fulfill(status=200,content_type='application/json',body=json.dumps({"documents":docs}));return
    await route.fulfill(status=200,content_type='application/json',body='{"documents":[]}');return
  await fs(route)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(args=["--no-sandbox"])
    ctx=await b.new_context(viewport={"width":390,"height":844},device_scale_factor=3,is_mobile=True,has_touch=True)
    await ctx.route('**/identitytoolkit.googleapis.com/**',idt);await ctx.route('**/firestore.googleapis.com/**',fs)
    await ctx.route('**/securetoken.googleapis.com/**',lambda r:r.fulfill(status=200,content_type="application/json",body=json.dumps({"id_token":"t","refresh_token":"r","user_id":"u1","expires_in":"3600"})))
    await ctx.add_init_script("localStorage.setItem('zal.coach','1');localStorage.setItem('zal.coachsx','1');localStorage.setItem('zal.sync.hs',JSON.stringify({never:1}));['col','fr','sum','feed'].forEach(k=>localStorage.setItem('zal.tour.'+k,'1'));localStorage.setItem('zal.demo','"+json.dumps(DEMO,ensure_ascii=False).replace("'","")+"')")
    pg=await ctx.new_page();errs=[];pg.on("pageerror",lambda e:errs.append(str(e)[:200]));js=lambda c:pg.evaluate(c); w=lambda ms=1500:pg.wait_for_timeout(ms)
    clean="document.querySelectorAll('.toast,#toast,.tip,.tour').forEach(t=>t.remove())"
    shot=lambda n:pg.screenshot(path=O+n+".png")
    if not ONLY:
      await pg.goto("http://localhost:8766/app.html?app=1");await w(4000)
      await js("const g=document.getElementById('introGo');g&&g.click()");await w(1500)
      for step,idx in enumerate([[6,8,12,13,16,19],[5,6,7]]):
        for i in idx:
          await js(f"const o=document.querySelectorAll('#onbGrid .op')[{i}];o&&o.click()");await w(500)
          await js("const r=document.querySelector('#rmSt [data-st=\"5\"]');r&&r.offsetParent&&r.click()");await w(450)
        await js("document.getElementById('onbNext').click()");await w(1500)
      await js("const a=document.querySelector('[data-acct]');a&&!document.getElementById('auth').classList.contains('on')&&a.click()");await w(800)
      for sel,v in (("#auE","anya@mail.ru"),("#auP","secret123")):
        try: await pg.fill(sel,v,timeout=3000)
        except Exception: pass
      await js("const g=document.getElementById('auGo');g&&g.click()");await w(3000)
      await js(clean);await w(6000);await js(clean);await shot("1_home")
      await js("document.querySelector('.dock [data-s=feed]').click()");await w(5000);await js(clean);await shot("2_feed")
      await js("document.querySelector('.dock [data-s=col]').click()");await w(1500)
      await js("document.querySelectorAll('#flow .cv')[4].click()");await w(5000)
      await js("document.querySelector('.bkc-where').click()");await w(800)
      await js("const o=document.querySelector('[data-wh=on]');o&&o.click()");await w(4000);await js(clean);await shot("3_where")
      await js("document.querySelector('#vsheet .sh-bg').click()");await w(800)
      await js("const c=document.querySelector('[data-bkc=close]');c&&c.click()");await w(800)
      await js("document.querySelector('.dock [data-s=col]').click()");await w(1500)
      await js("document.getElementById('srchB').click()");await w(1200)
      await js("([...document.querySelectorAll('#fwrap button')].find(b=>/^Классика$/.test(b.textContent.trim()))||document.querySelector('#fwrap button')).click()");await w(400)
      await js("document.querySelector('[data-fshow]').click()");await w(5000);await js(clean);await shot("4_search")
      await js("location.reload()");await w(5000)
      await js("document.querySelector('.dock [data-s=sum]').click()");await w(5000);await js(clean);await shot("5_stats")
    # дневник и клуб: отдельный вход с готовыми записями дневника и демо-клубом
    dc=await b.new_context(viewport={"width":390,"height":844},device_scale_factor=3,is_mobile=True,has_touch=True)
    await dc.route('**/identitytoolkit.googleapis.com/**',idt);await dc.route('**/firestore.googleapis.com/**',fsc)
    init="localStorage.setItem('zal.onb','1');localStorage.setItem('zal.coach','1');localStorage.setItem('zal.coachsx','1');localStorage.setItem('zal.sync.hs',JSON.stringify({never:1}));['col','fr','sum','feed','club','acc'].forEach(k=>localStorage.setItem('zal.tour.'+k,'1'));"
    init+="localStorage.setItem('zal.mine',%s);localStorage.setItem('zal.quotes',%s);localStorage.setItem('zal.club',JSON.stringify('t1'));"%(json.dumps(json.dumps(M,ensure_ascii=False),ensure_ascii=False),json.dumps(json.dumps(Q,ensure_ascii=False),ensure_ascii=False))
    await dc.add_init_script(init)
    pg=await dc.new_page();pg.on("pageerror",lambda e:errs.append(str(e)[:200]));js=lambda c:pg.evaluate(c)
    clean2="document.querySelectorAll('.toast,#toast,.tip,.tour,.coach').forEach(t=>t.remove());document.getElementById('auth')&&document.getElementById('auth').classList.remove('on')"
    await pg.goto("http://localhost:8766/app.html?app=1");await pg.wait_for_timeout(4000)
    await js("const a=document.querySelector('[data-acct]');a&&a.click()");await pg.wait_for_timeout(800)
    if await js("document.getElementById('auth').classList.contains('on')"):
      if not await js("/Создай|Сохрани/.test(document.querySelector('#auth h1').textContent)"): await js("document.getElementById('auSw')&&document.getElementById('auSw').click()");await pg.wait_for_timeout(300)
      await pg.fill('#auE','anya@mail.ru');await pg.fill('#auP','secret12');await js("document.getElementById('auGo').click()");await pg.wait_for_timeout(3000)
    await js(clean2)
    await js("document.querySelector('.dock [data-s=sum]').click()");await pg.wait_for_timeout(2500)
    await js("const d=document.querySelector('[data-f=diary]');d&&d.click()");await pg.wait_for_timeout(5000);await js(clean2)
    await pg.screenshot(path=O+"6_diary.png")
    await js("document.querySelector('.dock [data-s=club]').click()");await pg.wait_for_timeout(6000);await js(clean2)
    await pg.screenshot(path=O+"7_club.png")
    await dc.close()
    print(errs)
    fp=await b.new_page(viewport={"width":1080,"height":1920})
    for i,(img,k,h,pp,a,bb) in enumerate(SLIDES):
      if ONLY and img not in ONLY: continue
      q={"k":k,"h":h,"p":pp,"img":"../out/"+img+".png","a":a,"b":bb}
      await fp.goto("http://localhost:8766/tools/frame.html?i="+str(i)+"#"+urllib.parse.quote(json.dumps(q)));await fp.wait_for_timeout(1500)
      await fp.screenshot(path=O+f"nora_preview_{i+1}.png")
    if ONLY: await b.close();return
    # видео ленты: как листаются книги (кадры через CDP screencast в полном разрешении)
    import base64
    vc=await b.new_context(viewport={"width":390,"height":844},device_scale_factor=3,is_mobile=True,has_touch=True)
    await vc.route('**/identitytoolkit.googleapis.com/**',idt);await vc.route('**/firestore.googleapis.com/**',fs)
    await vc.add_init_script("localStorage.setItem('zal.onb','1');localStorage.setItem('zal.coach','1');localStorage.setItem('zal.sync.hs',JSON.stringify({never:1}));['col','fr','sum','feed'].forEach(k=>localStorage.setItem('zal.tour.'+k,'1'));localStorage.setItem('zal.demo','"+json.dumps(DEMO,ensure_ascii=False)+"')")
    vp=await vc.new_page();js2=vp.evaluate
    await vp.goto("http://localhost:8766/app.html?app=1");await vp.wait_for_timeout(6000)
    await js2("document.getElementById('auth').classList.remove('on');document.querySelectorAll('.toast,#toast,.tip,.tour').forEach(t=>t.remove())")
    await js2("document.querySelector('.dock [data-s=feed]').click()");await vp.wait_for_timeout(4000)
    os.makedirs("out/fr",exist_ok=True);frames=[];cdp=await vc.new_cdp_session(vp)
    def onf(ev):
      n=len(frames);open(f"out/fr/{n:05d}.jpg","wb").write(base64.b64decode(ev["data"]));frames.append(ev["metadata"]["timestamp"])
      asyncio.ensure_future(cdp.send("Page.screencastFrameAck",{"sessionId":ev["sessionId"]}))
    cdp.on("Page.screencastFrame",onf)
    await cdp.send("Page.startScreencast",{"format":"jpeg","quality":92,"maxWidth":1170,"maxHeight":2532,"everyNthFrame":1})
    for k in ["want","skip","want","want","skip"]:
      await vp.wait_for_timeout(2000)
      await js2(f"[...document.querySelectorAll('#feed .slide')].find(s=>Math.abs(s.getBoundingClientRect().top)<200).querySelector('[data-{k}]').click()")
      await vp.wait_for_timeout(250);await js2("document.querySelectorAll('.toast,#toast,#whT').forEach(t=>t.style.display='none')")
    await vp.wait_for_timeout(2200);await cdp.send("Page.stopScreencast");await vp.wait_for_timeout(500)
    await vc.close()
    with open("out/fr/list.txt","w") as f:
      for n in range(len(frames)):
        d=(frames[n+1]-frames[n]) if n+1<len(frames) else 0.04
        f.write(f"file '{n:05d}.jpg'\nduration {max(d,0.001):.4f}\n")
      f.write(f"file '{len(frames)-1:05d}.jpg'\n")
    subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i","out/fr/list.txt","-vf","scale=1170:2532,fps=30","-c:v","libx264","-crf","16","-pix_fmt","yuv420p","out/feed_raw.mp4"],check=True)
    raw="out/feed_raw.mp4";ts=0;dur=frames[-1]-frames[0]+0.5
    from PIL import Image,ImageDraw
    Image.new("RGB",(1170,2532),"black").save("out/black.png")
    m=Image.new("L",(590,1277),0);ImageDraw.Draw(m).rounded_rectangle((0,0,589,1276),radius=66,fill=255);m.save("out/mask.png")
    i=[x[0] for x in SLIDES].index("2_feed");img,k,h,pp,a,bb=SLIDES[i]
    q={"k":k,"h":h,"p":pp,"img":"../out/black.png","a":a,"b":bb}
    await fp.goto("http://localhost:8766/tools/frame.html?v=1#"+urllib.parse.quote(json.dumps(q)));await fp.wait_for_timeout(1500)
    await fp.screenshot(path="out/frame_feed.png")
    subprocess.run(["ffmpeg","-y","-loop","1","-i","out/frame_feed.png","-ss",f"{ts:.2f}","-t",f"{dur:.2f}","-i",raw,"-i","out/mask.png","-filter_complex",
      "[1:v]scale=590:1277,format=rgba[v];[2:v]format=gray[m];[v][m]alphamerge[vm];[0:v][vm]overlay=245:575:shortest=1,format=yuv420p[o]",
      "-map","[o]","-r","30","-c:v","libx264","-preset","slow","-crf","20","-movflags","+faststart","out/nora_preview_feed.mp4"],check=True)
    await b.close()
asyncio.run(main())
