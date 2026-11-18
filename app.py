
import math
from datetime import datetime
import requests, folium, pandas as pd, plotly.express as px, streamlit as st
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation

st.set_page_config(page_title="CAREWAY", page_icon="💙", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700;800&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif}
.stApp{background:#090E18;color:#F0F5FA}
[data-testid="stSidebar"]{background:#0D1726;border-right:1px solid #26384D}
[data-testid="stSidebar"] *{color:#F0F5FA}
.main .block-container{max-width:1500px;padding-top:1.4rem}
h1,h2,h3,h4,p,label{color:#F0F5FA}
[data-testid="stCaptionContainer"] p{color:#9AABC0!important}
.hero{background:radial-gradient(circle at 85% 10%,#19b8ff33,transparent 32%),linear-gradient(120deg,#14243A,#101B2B);border:1px solid #26384D;border-radius:22px;padding:25px 30px;margin-bottom:22px}
.kicker{color:#A3F56B;font-size:11px;font-weight:800;letter-spacing:.16em}
.hero h1{font-size:32px;margin:8px 0;color:#F0F5FA}.hero p{color:#AAB9CA}
div.stButton>button{background:#19B8FF;color:#07121D!important;border:0;border-radius:11px;font-weight:800}
div.stButton>button p{color:#07121D!important}
[data-testid="stMetric"]{background:#142238;border:1px solid #26384D;border-radius:14px;padding:12px}
[data-testid="stMetric"] label,[data-testid="stMetricValue"]{color:#F0F5FA!important}
iframe{border-radius:15px}hr{border-color:#26384D}
</style>""", unsafe_allow_html=True)

HEAD={"User-Agent":"CAREWAY-StudentProject/1.0"}
OVERPASS=["https://overpass-api.de/api/interpreter","https://overpass.kumi.systems/api/interpreter"]

def distance(a,b):
    p1,p2=math.radians(a[0]),math.radians(b[0]); dp=math.radians(b[0]-a[0]); dl=math.radians(b[1]-a[1])
    h=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 6371.0088*2*math.asin(math.sqrt(h))

def geocode(q):
    r=requests.get("https://nominatim.openstreetmap.org/search",params={"q":q,"format":"jsonv2","limit":1,"countrycodes":"bg"},headers=HEAD,timeout=20)
    r.raise_for_status(); data=r.json()
    return (float(data[0]["lat"]),float(data[0]["lon"]),data[0]["display_name"]) if data else None

def pharmacies_near(lat,lon,meters):
    query='[out:json][timeout:35];(node["amenity"="pharmacy"](around:%d,%s,%s);way["amenity"="pharmacy"](around:%d,%s,%s);relation["amenity"="pharmacy"](around:%d,%s,%s););out center tags;'%(meters,lat,lon,meters,lat,lon,meters,lat,lon)
    err=None
    for endpoint in OVERPASS:
        try:
            r=requests.post(endpoint,data={"data":query},headers=HEAD,timeout=45); r.raise_for_status()
            found=[]
            for e in r.json().get("elements",[]):
                t=e.get("tags",{}); c=e.get("center",{})
                la=e.get("lat",c.get("lat")); lo=e.get("lon",c.get("lon"))
                if la is None or lo is None: continue
                addr=[t.get("addr:street"),t.get("addr:housenumber"),t.get("addr:city") or t.get("addr:place")]
                found.append({"id":str(e["type"])+"_"+str(e["id"]),"name":t.get("name") or t.get("brand") or "Аптека без име",
                  "lat":float(la),"lon":float(lo),"address":", ".join(str(x) for x in addr if x) or "Няма адрес в OSM",
                  "phone":t.get("phone") or t.get("contact:phone") or "Няма телефон в OSM",
                  "hours":t.get("opening_hours") or "Няма работно време в OSM","wheelchair":t.get("wheelchair","unknown")})
            unique={(p["name"].lower(),round(p["lat"],5),round(p["lon"],5)):p for p in found}
            return list(unique.values())
        except Exception as ex: err=ex
    raise RuntimeError(err)

def road_route(a,b):
    url="https://router.project-osrm.org/route/v1/driving/%s,%s;%s,%s"%(a[1],a[0],b[1],b[0])
    r=requests.get(url,params={"overview":"full","geometries":"geojson"},headers=HEAD,timeout=25); r.raise_for_status()
    data=r.json()
    if data.get("code")!="Ok": return None
    rt=data["routes"][0]
    return {"km":rt["distance"]/1000,"min":rt["duration"]/60,"line":[(y,x) for x,y in rt["geometry"]["coordinates"]]}

def map_view(center,origin=None,items=None,dest=None,route=None):
    m=folium.Map(location=center,zoom_start=14,tiles="OpenStreetMap",control_scale=True)
    if origin:
        folium.Marker(origin,tooltip="Начална точка",icon=folium.Icon(color="blue",icon="user",prefix="fa")).add_to(m)
        folium.Circle(origin,radius=60,color="#19B8FF",fill=True,fill_opacity=.08).add_to(m)
    for p in items or []:
        folium.Marker((p["lat"],p["lon"]),tooltip=p["name"],popup="<b>%s</b><br>%s<br>%s<br>%s"%(p["name"],p["address"],p["phone"],p["hours"]),icon=folium.Icon(color="green",icon="plus",prefix="fa")).add_to(m)
    if dest: folium.Marker(dest,tooltip="Избрана дестинация",icon=folium.Icon(color="red",icon="flag",prefix="fa")).add_to(m)
    if route:
        folium.PolyLine(route["line"],color="#19B8FF",weight=5).add_to(m); m.fit_bounds(route["line"])
    elif origin and items: m.fit_bounds([origin]+[(p["lat"],p["lon"]) for p in items[:30]])
    return m

for k,v in {"origin":None,"origin_label":"","pharmacies":[],"module":"Dashboard","selected":None,"route":None,"last_search":"—"}.items():
    if k not in st.session_state: st.session_state[k]=v

fleet=pd.DataFrame([
 {"Оператор":"CAREWAY Demo Mobility","Тип":"Достъпен ван","Район":"Пловдив и област","Места":3,"Рампа":"Да","Количка":"Да","Статус":"Симулация"},
 {"Оператор":"CAREWAY Community Ride","Тип":"Социален транспорт","Район":"Асеновград, Пловдив","Места":4,"Рампа":"Не","Количка":"Не","Статус":"Симулация"},
 {"Оператор":"CAREWAY Assisted Car","Тип":"Автомобил с помощник","Район":"Пловдив, Родопи","Места":2,"Рампа":"Не","Количка":"Сгъваема","Статус":"Симулация"},
 {"Оператор":"CAREWAY Rural Connect","Тип":"Междуселищен транспорт","Район":"Пазарджик и област","Места":6,"Рампа":"По заявка","Количка":"По заявка","Статус":"Симулация"},
])

with st.sidebar:
    st.markdown("## 💙 CAREWAY"); st.caption("SMART HEALTHCARE ACCESS"); st.divider()
    for name in ["Dashboard","PharmaNearby","SafeRide","Smart Route","Accessibility Center","Data Analytics","Data Monitor"]:
        if st.button(name,use_container_width=True,key="nav_"+name):
            st.session_state.module=name; st.rerun()
    st.divider(); st.markdown("### 📍 Местоположение")
    gps=streamlit_geolocation()
    if isinstance(gps,dict) and gps.get("latitude") is not None and gps.get("longitude") is not None:
        st.session_state.origin=(float(gps["latitude"]),float(gps["longitude"])); st.session_state.origin_label="GPS устройство"
        st.success("GPS позицията е получена")
        if gps.get("accuracy") is not None: st.caption("Отчетена точност ±%.0f m"%float(gps["accuracy"]))
        st.caption("%.6f, %.6f"%st.session_state.origin)
    else: st.info("Разреши Location в браузъра или въведи населено място.")
    place=st.text_input("Населено място","Пловдив, България")
    if st.button("Задай местоположение",use_container_width=True):
        try:
            g=geocode(place)
            if g: st.session_state.origin=(g[0],g[1]); st.session_state.origin_label=g[2]; st.success("Местоположението е зададено")
            else: st.error("Не е намерено населено място.")
        except Exception as e: st.error("Геокодирането е неуспешно: "+str(e))

st.markdown('<div class="hero"><div class="kicker">SMART MOBILITY · HEALTHCARE ACCESS · BULGARIA</div><h1>CAREWAY</h1><p>Открий аптека. Намери достъпен транспорт. Планирай придвижването си.</p></div>',unsafe_allow_html=True)
mod=st.session_state.module; origin=st.session_state.origin; ps=st.session_state.pharmacies

if mod=="Dashboard":
    st.markdown("### Общ преглед")
    a,b,c,d=st.columns(4); a.metric("Аптеки в текущото търсене",len(ps)); b.metric("Транспортни записа",len(fleet)); c.metric("Модули",7); d.metric("Последно търсене",st.session_state.last_search)
    l,r=st.columns(2)
    with l:
        st.markdown("#### PharmaNearby"); st.write("Откриване на аптеки по GPS или населено място.")
        if st.button("Отвори PharmaNearby"): st.session_state.module="PharmaNearby"; st.rerun()
    with r:
        st.markdown("#### Smart Route"); st.write("Маршрут до избрана аптека.")
        if st.button("Отвори Smart Route"): st.session_state.module="Smart Route"; st.rerun()
    if origin: st.success("Начална точка: "+st.session_state.origin_label)
    else: st.warning("Задай GPS позиция или населено място от менюто.")

elif mod=="PharmaNearby":
    st.markdown("### 💊 PharmaNearby"); st.write("Търси аптеки, отбелязани в OpenStreetMap.")
    radius=st.select_slider("Радиус на търсене",options=[2,3,5,10,15,25],value=10,format_func=lambda x:f"{x} km")
    if st.button("🔎 Потърси аптеки",type="primary"):
        if not origin: st.warning("Първо задай местоположение.")
        else:
            with st.spinner("Търсене в OpenStreetMap…"):
                try:
                    found=pharmacies_near(origin[0],origin[1],radius*1000)
                    for p in found: p["distance_km"]=distance(origin,(p["lat"],p["lon"]))
                    found.sort(key=lambda p:p["distance_km"])
                    st.session_state.pharmacies=found; st.session_state.last_search=datetime.now().strftime("%d.%m.%Y %H:%M")
                    st.session_state.selected=None; st.session_state.route=None; st.rerun()
                except Exception as e: st.error("Грешка при търсенето: "+str(e))
    if ps:
        l,r=st.columns([1.3,1])
        with l: st_folium(map_view(origin,origin,ps),height=530,width=None,key="pharmacy_map")
        with r:
            st.markdown("#### Намерени аптеки: %d"%len(ps))
            for p in ps:
                with st.container(border=True):
                    st.markdown("**💊 "+p["name"]+"**"); st.caption("%.2f km · %s"%(p["distance_km"],p["address"]))
                    st.caption("☎ %s · 🕒 %s"%(p["phone"],p["hours"]))
                    if st.button("Избери аптека",key="choose_"+p["id"]):
                        st.session_state.selected=p["id"]; st.session_state.module="Smart Route"; st.rerun()
        st.caption("Източник: OpenStreetMap contributors. Данните може да са непълни или неактуални; потвърди работното време и телефона.")
    else: st.info("Задай местоположение и натисни „Потърси аптеки“.")

elif mod=="SafeRide":
    st.markdown("### 🚐 SafeRide"); st.warning("Демонстрационен каталог. Това не са реални оператори и не може да се прави резервация.")
    only=st.toggle("Само варианти за инвалидна количка")
    view=fleet[fleet["Количка"].isin(["Да","По заявка"])] if only else fleet
    st.dataframe(view,use_container_width=True,hide_index=True)
    st.caption("За реална услуга използвай проверени общински, социални или лицензирани оператори.")

elif mod=="Smart Route":
    st.markdown("### 🧭 Smart Route")
    if not origin: st.warning("Задай начална точка.")
    elif not ps: st.info("Първо потърси аптеки в PharmaNearby.")
    else:
        labels=[f'{p["name"]} · {p["distance_km"]:.2f} km · {p["address"]}' for p in ps]
        lookup=dict(zip(labels,ps)); idx=next((i for i,p in enumerate(ps) if p["id"]==st.session_state.selected),0)
        label=st.selectbox("Избери дестинация",labels,index=idx); target=lookup[label]
        if st.button("Изчисли маршрут",type="primary"):
            try:
                with st.spinner("Изчисляване по пътната мрежа…"): st.session_state.route=road_route(origin,(target["lat"],target["lon"]))
                st.session_state.selected=target["id"]
            except Exception as e: st.error("Маршрутната услуга е недостъпна: "+str(e))
        rt=st.session_state.route
        if rt:
            x,y,z=st.columns(3); x.metric("Разстояние по пътя","%.1f km"%rt["km"]); y.metric("Ориентировъчно време","%.0f min"%rt["min"]); z.metric("Дестинация",target["name"])
            st_folium(map_view(origin,origin,[target],(target["lat"],target["lon"]),rt),height=540,width=None,key="route_map")
            st.caption("OSRM demo service. Времето е ориентировъчно и не гарантира отчитане на актуален трафик.")
        else: st_folium(map_view(origin,origin,ps),height=470,width=None,key="route_preview")

elif mod=="Accessibility Center":
    st.markdown("### ♿ Accessibility Center")
    st.info("Липсващ OSM етикет не означава, че обектът е недостъпен.")
    if ps: st.dataframe(pd.DataFrame([{"Аптека":p["name"],"Адрес":p["address"],"Wheelchair":p["wheelchair"]} for p in ps]),use_container_width=True,hide_index=True)
    else: st.info("Зареди аптеки от PharmaNearby.")
    st.markdown("#### Транспортни характеристики"); st.dataframe(fleet[["Тип","Район","Рампа","Количка"]],use_container_width=True,hide_index=True)

elif mod=="Data Analytics":
    st.markdown("### 📊 Data Analytics")
    if ps:
        df=pd.DataFrame(ps); a,b,c=st.columns(3); a.metric("Аптеки",len(df)); b.metric("Средно разстояние","%.2f km"%df.distance_km.mean()); c.metric("Най-близка","%.2f km"%df.distance_km.min())
        fig=px.histogram(df,x="distance_km",nbins=10,title="Разстояния до намерените аптеки")
        fig.update_layout(paper_bgcolor="#111C2D",plot_bgcolor="#111C2D",font_color="#F0F5FA")
        st.plotly_chart(fig,use_container_width=True); st.caption("Статистиката е само за текущото търсене, не за цяла България.")
    else: st.info("Потърси аптеки в PharmaNearby за генериране на анализ.")

elif mod=="Data Monitor":
    st.markdown("### 🛡️ Data Monitor")
    if ps:
        df=pd.DataFrame(ps); a,b,c,d=st.columns(4)
        a.metric("Без адрес",int((df.address=="Няма адрес в OSM").sum())); b.metric("Без телефон",int((df.phone=="Няма телефон в OSM").sum()))
        c.metric("Без работно време",int((df.hours=="Няма работно време в OSM").sum())); d.metric("Дублирани",int(df.duplicated(["name","lat","lon"]).sum()))
        st.dataframe(df,use_container_width=True,hide_index=True)
        st.download_button("Експорт CSV",df.to_csv(index=False).encode("utf-8-sig"),"careway_pharmacies.csv","text/csv")
    else: st.info("Няма записи за проверка. Зареди аптеки в PharmaNearby.")
    st.markdown("#### Източници и ограничения")
    st.write("Аптеки: OpenStreetMap / Overpass · Геокодиране: Nominatim · Маршрути: OSRM · Транспорт: симулиран каталог.")
    st.caption("Публичните услуги имат ограничения за заявки и наличност. За реално внедряване са нужни официални проверени данни.")

st.divider()
st.markdown("<center><small style='color:#71849A'>CAREWAY · EDUCATIONAL PROTOTYPE · OpenStreetMap contributors · Transport catalogue simulated</small></center>",unsafe_allow_html=True)
