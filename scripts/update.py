"""Update only when the weekly header AND current influenza figures are parsed.
Missing data is unknown; never relabel previous-week numbers as new observations.
"""
import json, re, urllib.request, datetime, os
URL="https://www.pref.okinawa.jp/iryokenko/shippeikansensho/1005861/1006484.html"
AREAS={"okinawa":"県全体","north":"北部保健所管内","central":"中部保健所管内","naha":"那覇市保健所管内","south":"南部保健所管内","miyako":"宮古保健所管内","yaeyama":"八重山保健所管内"}
def parse(html):
    plain=re.sub(r"<[^>]+>"," ",html)
    plain=re.sub(r"\s+"," ",plain)
    m=re.search(r"週報\s*(20\d{2})年第\s*(\d+)週[（(]\s*(20\d{2}年\d+月\d+日).*?[～〜–－-]\s*((?:20\d{2}年)?\d+月\d+日)",plain)
    if not m: raise ValueError("Weekly header not found; preserved previous data")
    year,week=int(m[1]),int(m[2]);datetime.date.fromisocalendar(year,week,1)
    flu={}
    for key,label in AREAS.items():
        p=re.search(re.escape(label)+r"(?:(?!保健所管内|県全体).){0,180}?インフルエンザ[（(]\s*([0-9.]+)人/定点",plain)
        flu[key]=float(p[1]) if p else None
    if flu["okinawa"] is None: raise ValueError("Current prefecture influenza value not found; preserved previous data")
    return year,week,m[3]+"–"+m[4],flu

def main():
    req=urllib.request.Request(URL,headers={"User-Agent":"OkinawaHealthRadar/1.3"})
    html=urllib.request.urlopen(req,timeout=40).read().decode("utf-8")
    year,week,period,flu=parse(html)
    with open("data.json",encoding="utf-8") as f: d=json.load(f)
    old_year=d.get("year") or int(str(d["period"])[:4])
    old_week=int(d.get("week") or 0)
    if (year,week)<(old_year,old_week):
        raise ValueError("Official source returned an older week; preserved current data")
    now_jst=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    changed_observation=(year,week)!=(old_year,old_week) or flu!=d.get("flu")
    history=[{**p,"year":p.get("year",old_year)} for p in d.get("history",[])]
    history=[p for p in history if (p["year"],p["week"])!=(year,week)]
    history.append({"year":year,"week":week,"label":f"W{week}","value":flu["okinawa"]})
    history.sort(key=lambda p:(p["year"],p["week"]))
    d.update(year=year,week=week,period=period,flu=flu,history=history[-26:],lastChecked=now_jst.isoformat(timespec="minutes"))
    if changed_observation or not d.get("sourceUpdated"):
        d["sourceUpdated"]=now_jst.date().isoformat()
    d["alerts"]={"influenza":"warning" if flu["okinawa"]>=30 else "caution" if flu["okinawa"]>=10 else "low"}
    with open("data.json.tmp","w",encoding="utf-8") as f:json.dump(d,f,ensure_ascii=False,indent=2)
    os.replace("data.json.tmp","data.json")
if __name__=="__main__":main()
