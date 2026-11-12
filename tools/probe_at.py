import json,urllib.request,urllib.parse
H={"Authorization":"Bearer guest","User-Agent":"Mozilla/5.0 (nora probe)","Accept":"application/json"}
def get(u):
  try:
    with urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=40) as r: return r.status,r.read()[:3000].decode("utf-8","replace")
  except Exception as e: return "ERR",str(e)[:300]
for u in ["https://api.author.today/v1/catalog/search?page=1&ps=5&sorting=popular",
          "https://api.author.today/v1/catalog/search?page=1&ps=5&sorting=popular&genre=romantic-fantasy",
          "https://api.author.today/v1/catalog/genres",
          "https://litnet.com/api/v1/books?page=1",
          "https://api.litres.ru/foundation/api/arts/facets?limit=5"]:
  s,b=get(u);print("==",u,s);print(b[:2500]);print()
