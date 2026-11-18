import sys,asyncio
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
  b=p.chromium.launch(executable_path="/usr/bin/google-chrome");pg=b.new_page(viewport={"width":1080,"height":1920})
  for f in sys.argv[1:]:
    svg=open(f,encoding='utf8').read()
    pg.set_content(f'<html><body style="margin:0">{svg}</body></html>');pg.wait_for_timeout(200)
    pg.screenshot(path=f.replace('.svg','.png'),omit_background=True)
  b.close()
