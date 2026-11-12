import json,urllib.request
H={"User-Agent":"Mozilla/5.0 (nora probe)","Accept":"application/json"}
def get(u):
  try:
    with urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=40) as r: return r.status,json.loads(r.read())
  except Exception as e: return "ERR",str(e)[:200]
B="https://api.litres.ru/foundation/api/"
for q in ["arts/facets?limit=3&genres=5090&o=popular","arts/facets?limit=3&genre_id=5090&o=popular","genres/5090/arts?limit=3&o=popular","arts?limit=3&genres=5090&o=popular","search?q=%D0%B4%D1%80%D0%B0%D0%BA%D0%BE%D0%BD&types=text_book&limit=3",
          "arts/facets?limit=3&genres=5090&o=popular&art_types=text_book&only_drafts=true"]:
  s,j=get(B+q)
  if s==200:
    d=(j.get("payload") or {}).get("data") or []
    if isinstance(d,dict): d=d.get("arts") or d.get("items") or list(d.values())[:3]
    print("==",q,s,[ (x.get("title"),[p.get("full_name") for p in x.get("persons",[])][:1],x.get("is_draft")) for x in d[:3] if isinstance(x,dict)])
  else: print("==",q,s,j)
s,j=get(B+"arts/74710831/genres"); print("genres of art",s,json.dumps(j,ensure_ascii=False)[:600])
s,j=get(B+"arts/74710831/annotation"); print("annot",s,json.dumps(j,ensure_ascii=False)[:400])
