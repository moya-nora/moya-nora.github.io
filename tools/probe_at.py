import json,urllib.request
H={"User-Agent":"Mozilla/5.0 (nora probe)","Accept":"application/json"}
def get(u):
  try:
    with urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=40) as r: return r.status,json.loads(r.read())
  except Exception as e: return "ERR",str(e)[:300]
s,j=get("https://api.litres.ru/foundation/api/genres?limit=200")
print("genres",s, json.dumps(j,ensure_ascii=False)[:6000] if s==200 else j)
s,j=get("https://api.litres.ru/foundation/api/arts/facets?limit=3&o=popular&genre=5077")
print("facet genre",s,json.dumps(j,ensure_ascii=False)[:800] if s==200 else j)
s,j=get("https://api.litres.ru/foundation/api/arts/74710831")
print("art",s,json.dumps(j,ensure_ascii=False)[:3000] if s==200 else j)
