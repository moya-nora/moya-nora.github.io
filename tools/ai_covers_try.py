# Проба ИИ-обложек: картинка от Pollinations (FLUX) + название и автор шрифтом Норы
import json,os,time,urllib.parse,urllib.request,asyncio
from playwright.async_api import async_playwright
os.makedirs("out/ai",exist_ok=True)
STYLE="contemporary illustrated book cover art, painterly, rich cinematic colors, elegant composition, no text, no letters, no typography"
B=[("Гробницы Атуана","Урсула Ле Гуин","a young priestess in a black hooded robe holding a lantern inside vast dark underground labyrinth tombs, ancient stone columns, faint golden light"),
 ("Техану","Урсула Ле Гуин","an old woman and a scarred little girl on a windswept cliff above the sea at dusk, a huge dragon silhouette in the glowing sky"),
 ("Око Мира","Роберт Джордан","three young men fleeing a burning village at night, a mysterious cloaked woman on a white horse, dark wolves and fog, epic fantasy"),
 ("Через соловьиный этаж","Лиан Хирн","feudal Japan, a young assassin boy in black leaping across a moonlit wooden castle floor, nightingales, cherry blossoms, ink and gold"),
 ("Мельница на Флоссе","Джордж Элиот","a girl with dark hair by a river with an old watermill, Victorian English countryside, golden autumn light, flood clouds gathering"),
 ("Ярмарка тщеславия","Уильям Теккерей","a clever young woman in a regency era ball gown at a glittering masquerade fair, chandeliers, masks, satirical elegance"),
 ("Большие надежды","Чарльз Диккенс","a boy on misty marshes at dawn, an abandoned mansion with a stopped clock and a faded wedding cake, cobwebs, Victorian gothic"),
 ("Джуд Незаметный","Томас Харди","a lonely stonemason walking towards distant spires of a university city at sunset, English countryside, melancholy"),
 ("Воскресение","Лев Толстой","a young woman in a grey prison dress in a snowy Siberian landscape, a convoy of prisoners, a nobleman following, Russian winter, hope"),
 ("Дэвид Копперфилд","Чарльз Диккенс","a small boy with a bundle walking along a long road to the white cliffs of Dover, Victorian England, warm hopeful light"),
 ("Джейн Эйр","Шарлотта Бронте","a young governess in a dark dress on moorland before a gothic manor with one lit window at night, fire in the attic, romantic gothic"),
 ("Сто лет одиночества","Габриэль Гарсиа Маркес","a magical Colombian village of Macondo, yellow butterflies, an old house overgrown with tropical plants, magical realism"),
]
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(args=["--no-sandbox"]);pg=await b.new_page(viewport={"width":600,"height":900})
    for i,(t,a,pr) in enumerate(B):
      f=f"out/ai/raw{i}.jpg"
      url="https://image.pollinations.ai/prompt/"+urllib.parse.quote(pr+", "+STYLE)+"?width=768&height=1152&nologo=true&model=flux&seed=7"
      for k in range(4):
        try:
          with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"nora/1.0"}),timeout=180) as r: open(f,"wb").write(r.read())
          if os.path.getsize(f)>20000: break
        except Exception as e: print(t,e); time.sleep(10)
      print(t,os.path.getsize(f) if os.path.exists(f) else 0,flush=True)
      q={"img":f"../out/ai/raw{i}.jpg","t":t,"a":a}
      await pg.goto(f"http://localhost:8766/tools/ai_cover.html?i={i}#"+urllib.parse.quote(json.dumps(q)));await pg.wait_for_timeout(1200)
      await pg.screenshot(path=f"out/ai/cover{i}.png")
    await b.close()
asyncio.run(main())
