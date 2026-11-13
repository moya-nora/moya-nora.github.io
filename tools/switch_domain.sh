#!/bin/bash
# Переводит сайт на nora-books.ru (запускается из domain.yml, когда публичный DNS начинает отвечать)
set -e
echo "nora-books.ru" > CNAME
sed -i 's#SITE = "https://moya-nora.github.io"#SITE = "https://nora-books.ru"#' tools/build_seo.py
sed -i 's#"host": "moya-nora.github.io"#"host": "nora-books.ru"#; s#https://moya-nora.github.io/{KEY}#https://nora-books.ru/{KEY}#' tools/indexnow.py
sed -i 's#APP = "https://moya-nora.github.io/app.html"#APP = "https://nora-books.ru/app.html"#' tools/bot_relay.py tools/bot_weekly.py
sed -i 's#https://moya-nora.github.io/sitemap.xml#https://nora-books.ru/sitemap.xml#' robots.txt
python3 - <<'PY'
import re
s=open('app.html').read()
s=re.sub(r'https://moya-nora\.github\.io(?!\S*@)',"https://nora-books.ru",s)
open('app.html','w').write(s)
PY
rm -rf p
python3 -u tools/build_seo.py
