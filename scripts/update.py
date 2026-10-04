import json,re,urllib.request,datetime,os,tempfile
from urllib.parse import urljoin
from openpyxl import load_workbook

URL="https://www.pref.okinawa.jp/iryokenko/shippeikansensho/1005861/1006484.html"
UA={"User-Agent":"Mozilla/5.0 OkinawaHealthRadar/1.2"}

def get(url):
    return urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=40).read()

raw=get(URL); html=raw.decode("utf-8","ignore")
plain=re.sub(r"<[^>]+>"," ",html); plain=re.sub(r"\s+"," ",plain)
with open("data.json",encoding="utf-8") as f:d=json.load(f)

m=re.search(r"週報\s*2026年第(\d+)週（(2026年\d+月\d+日)[^～]*～(2026年\d+月\d+日)",plain)
if m:
    d["week"]=int(m.group(1)); d["period"]=m.group(2)+"–"+m.group(3)

# Alert table: robust source for influenza regions.
areas={"okinawa":"県全体","north":"北部保健所管内","central":"中部保健所管内","naha":"那覇市保健所管内","south":"南部保健所管内","miyako":"宮古保健所管内","yaeyama":"八重山保健所管内"}
for key,label in areas.items():
    p=re.search(re.escape(label)+r".{0,180}?インフルエンザ[（(]([0-9.]+)人/定点",plain)
    if p:d.setdefault("flu",{})[key]=float(p.group(1))

# Find the newest official Excel linked under the 19-disease weekly section.
links=re.findall(r'href=["\']([^"\']+\.xlsx?(?:\?[^"\']*)?)["\']',html,re.I)
excel_url=None
for x in reversed(links):
    if "month" not in x.lower():
        excel_url=urljoin(URL,x); break

aliases={
 "gastro":["感染性胃腸炎"],
 "hfmd":["手足口病"],
}
def nums(v):
    if isinstance(v,(int,float)): return float(v)
    if isinstance(v,str):
        try:return float(v.replace(",","").strip())
        except:return None

# Workbook layouts change. Search disease-labelled rows and choose the latest-week
# numeric value on a row/sheet containing Okinawa/県全体 context.
if excel_url:
    path=os.path.join(tempfile.gettempdir(),"okinawa_weekly.xlsx")
    open(path,"wb").write(get(excel_url))
    wb=load_workbook(path,data_only=True,read_only=True)
    for key,names in aliases.items():
        candidates=[]
        for ws in wb.worksheets:
            rows=list(ws.iter_rows(values_only=True))
            for ri,row in enumerate(rows):
                joined=" ".join(str(x) for x in row if x is not None)
                if any(n in joined for n in names):
                    for rr in rows[ri:ri+5]:
                        vals=[nums(x) for x in rr]
                        vals=[x for x in vals if x is not None]
                        if vals:candidates.append(vals[-1])
        # conservative sanity limits; never publish obviously wrong counts/week labels
        lim=100
        good=[x for x in candidates if 0<=x<=lim]
        if good:d.setdefault(key,{})["okinawa"]=good[-1]

# COVID value: parse the official influenza/COVID page text when exposed as text.
cm=re.search(r"COVID-19.{0,500}?(?:定点当たり|定点あたり).{0,80}?([0-9]+\.[0-9]+)",plain,re.I)
if cm:d.setdefault("covid",{})["okinawa"]=float(cm.group(1))

d.setdefault("thresholds",{}).update({"influenza":{"caution":10,"warning":30},"gastro":{"warning":20,"end":12},"hfmd":{"warning":5,"end":2}})
f=d.get("flu",{}).get("okinawa")
d.setdefault("alerts",{})["influenza"]="warning" if f is not None and f>=30 else ("caution" if f is not None and f>=10 else "low")
for key,thr in [("gastro",20),("hfmd",5)]:
    v=d.get(key,{}).get("okinawa")
    d["alerts"][key]="warning" if v is not None and v>=thr else ("low" if v is not None else "pending")
d["alerts"]["covid"]="data" if d.get("covid",{}).get("okinawa") is not None else "pending"
d["lastChecked"]=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M JST")
d["sourceExcel"]=excel_url
with open("data.json","w",encoding="utf-8") as f:json.dump(d,f,ensure_ascii=False,indent=2)
