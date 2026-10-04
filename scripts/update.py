import json,re,urllib.request,datetime
URL="https://www.pref.okinawa.jp/iryokenko/shippeikansensho/1005861/1006484.html"
req=urllib.request.Request(URL,headers={"User-Agent":"Mozilla/5.0 OkinawaHealthRadar/1.1"})
html=urllib.request.urlopen(req,timeout=30).read().decode("utf-8","ignore")
text=re.sub(r"<[^>]+>"," ",html); text=re.sub(r"\s+"," ",text)
with open("data.json",encoding="utf-8") as f: d=json.load(f)
m=re.search(r"週報\s*2026年第(\d+)週（(2026年\d+月\d+日)[^～]*～(2026年\d+月\d+日)",text)
if m:
 d["week"]=int(m.group(1)); d["period"]=m.group(2)+"–"+m.group(3)
areas={"okinawa":"県全体","north":"北部保健所管内","central":"中部保健所管内","naha":"那覇市保健所管内","south":"南部保健所管内","miyako":"宮古保健所管内","yaeyama":"八重山保健所管内"}
for key,label in areas.items():
 p=re.search(re.escape(label)+r".{0,160}?インフルエンザ（([0-9.]+)人/定点）",text)
 if p:d["flu"][key]=float(p.group(1))
d["alerts"]["influenza"]="warning" if d["flu"]["okinawa"]>=30 else ("caution" if d["flu"]["okinawa"]>=10 else "low")
d["alerts"]["gastro"]="warning" if re.search(r"県全体.{0,180}?感染性胃腸炎",text) else "monitor"
d["alerts"]["hfmd"]="warning" if re.search(r"県全体.{0,180}?手足口病",text) else "monitor"
d["lastChecked"]=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST")
with open("data.json","w",encoding="utf-8") as f:json.dump(d,f,ensure_ascii=False,indent=2)
