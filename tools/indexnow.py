#!/usr/bin/env python3
"""Сообщаем Яндексу и Bing (IndexNow) обо всех страницах из sitemap.xml — новые страницы попадают в поиск быстрее."""
import json, re, urllib.request
KEY = "3a7b86a6bed641162ee1f6002802523a"
urls = re.findall(r"<loc>([^<]+)</loc>", open("sitemap.xml", encoding="utf-8").read())
for host in ("https://yandex.com/indexnow", "https://api.indexnow.org/indexnow"):
    for i in range(0, len(urls), 9000):
        body = json.dumps({"host": "moya-nora.github.io", "key": KEY, "keyLocation": f"https://moya-nora.github.io/{KEY}.txt", "urlList": urls[i:i + 9000]}).encode()
        req = urllib.request.Request(host, data=body, headers={"Content-Type": "application/json; charset=utf-8"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                print(host, r.status, len(urls[i:i + 9000]))
        except Exception as e:  # noqa: BLE001
            print(host, "ошибка:", e)
