#!/usr/bin/env python3
"""Generate a fully self-contained, offline waffle_map.html from waffle_houses.csv.

No runtime dependencies: location data and a (filtered, simplified) US-states
GeoJSON are embedded directly, and the map + bar chart are drawn in pure SVG.
"""
import csv, json

CSV_PATH = "waffle_houses.csv"
# Low-resolution US-states outlines, vendored locally so the build is fully
# reproducible offline. Originally from the public-domain PublicaMundi
# MappingAPI dataset (us-states.json).
GEOJSON_PATH = "us-states.geojson"
OUT_PATH = "waffle_map.html"

# Territories/non-continental states to drop so the map frames the lower 48.
DROP = {"Alaska", "Hawaii", "Puerto Rico"}

# ---- 1. Locations -----------------------------------------------------------
locs = []
with open(CSV_PATH, newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        locs.append([
            r["Store Code"],
            r["Business Name"],
            r["Address"],
            r["City"],
            r["State"],
            r["Postal Code"],
            round(float(r["Latitude"]), 4),
            round(float(r["Longitude"]), 4),
            r["Phone Number"],
            r["Formatted Business Hours"].strip(),
            r["Operated By"].strip(),
            1 if r["Store Code"] == "WH_Museum" else 0,
        ])
FIELDS = ["code", "name", "addr", "city", "state", "zip",
          "lat", "lon", "phone", "hours", "op", "museum"]

# ---- 1b. Huddle Houses (optional second chain) ------------------------------
# A small, manually sourced sample (real addresses from huddlehouse.com store
# pages; coordinates are approximate town-level placements). Loaded if present.
import os
HUDDLE_PATH = "huddle_houses.csv"
huddle = []
if os.path.exists(HUDDLE_PATH):
    with open(HUDDLE_PATH, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            huddle.append([
                r["Business Name"],
                r["Address"],
                r["City"],
                r["State"],
                r["Postal Code"],
                round(float(r["Latitude"]), 4),
                round(float(r["Longitude"]), 4),
            ])
HUDDLE_FIELDS = ["name", "addr", "city", "state", "zip", "lat", "lon"]
huddle_json = json.dumps(huddle, separators=(",", ":"))
huddle_fields_json = json.dumps(HUDDLE_FIELDS)
print(f"huddle houses: {len(huddle)}")

# ---- 2. State outlines (filter + round to ~2 decimals) ----------------------
def round_geom(geom, nd=2):
    t = geom["type"]
    def rr(ring):
        return [[round(x, nd), round(y, nd)] for x, y in ring]
    if t == "Polygon":
        return {"type": t, "coordinates": [rr(ring) for ring in geom["coordinates"]]}
    else:  # MultiPolygon
        return {"type": t,
                "coordinates": [[rr(ring) for ring in poly] for poly in geom["coordinates"]]}

raw = json.load(open(GEOJSON_PATH))
states = []
for feat in raw["features"]:
    name = feat["properties"]["name"]
    if name in DROP:
        continue
    states.append({"name": name, "geometry": round_geom(feat["geometry"])})

locs_json = json.dumps(locs, separators=(",", ":"))
states_json = json.dumps(states, separators=(",", ":"))
fields_json = json.dumps(FIELDS)

print(f"locations: {len(locs)}  states drawn: {len(states)}")
print(f"locs bytes: {len(locs_json)}  states bytes: {len(states_json)}")

# ---- 3. Assemble HTML -------------------------------------------------------
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Waffle House Locations — Map &amp; Count by State</title>
<style>
  :root { --wh-yellow:#FFD200; --ink:#1a1a1a; --muted:#6b6b6b; --line:#e3e3e3; }
  * { box-sizing: border-box; }
  body {
    margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: var(--ink); background: #faf9f6;
  }
  header { background: var(--ink); color: #fff; padding: 18px 24px; }
  header h1 { margin: 0; font-size: 20px; }
  header h1 .y { color: var(--wh-yellow); }
  header .stats { margin-top: 6px; font-size: 13px; color: #cfcfcf; }
  header .stats b { color: #fff; }
  .wrap { display: grid; grid-template-columns: 1.55fr 1fr; gap: 16px; padding: 16px 24px; align-items: start; }
  @media (max-width: 900px){ .wrap { grid-template-columns: 1fr; } }
  .card { background:#fff; border:1px solid var(--line); border-radius:10px; padding:14px; }
  .card h2 { margin:0 0 4px; font-size:14px; letter-spacing:.02em; text-transform:uppercase; color:var(--muted); }
  .card .sub { font-size:12px; color:var(--muted); margin-bottom:10px; }
  #mapwrap { position: relative; }
  svg { width:100%; height:auto; display:block; touch-action:none; }
  .state { fill:#eceae3; stroke:#fff; stroke-width:0.6; }
  .dot { fill: var(--wh-yellow); stroke:#7a5b00; stroke-width:0.4; cursor:pointer; }
  .dot:hover { fill:#ff8a00; }
  .museum { fill:#e4002b; stroke:#fff; stroke-width:1; cursor:pointer; }
  .huddle { fill:#1f78d1; stroke:#0a2f57; stroke-width:0.5; cursor:pointer; }
  .huddle:hover { fill:#0a4fa0; }
  .hint { font-size:11px; color:var(--muted); margin-top:8px; }
  .bar { fill: var(--wh-yellow); cursor:pointer; }
  .bar:hover { fill:#ff8a00; }
  .bar.sel { fill:#e4002b; }
  .blabel { font-size:11px; fill:var(--ink); }
  .bcount { font-size:11px; fill:var(--muted); }
  /* tooltip */
  #tip {
    position: fixed; pointer-events:none; z-index:10; max-width:260px;
    background:#fff; border:1px solid var(--ink); border-radius:8px; padding:8px 10px;
    box-shadow:0 6px 18px rgba(0,0,0,.18); font-size:12px; line-height:1.35; display:none;
  }
  #tip .t-name { font-weight:700; margin-bottom:3px; }
  #tip .t-mu { color:#e4002b; font-weight:700; }
  #tip .t-row { color:#333; }
  #tip .t-op { color:var(--muted); margin-top:4px; font-style:italic; }
  footer { padding: 8px 24px 28px; font-size:12px; color:var(--muted); }
  footer code { background:#efece4; padding:1px 4px; border-radius:3px; }
  .reset { font-size:11px; color:#2a5db0; cursor:pointer; user-select:none; }
</style>
</head>
<body>
<header>
  <h1><span class="y">●</span> Waffle House Locations <span style="color:#bbb;font-weight:400">— map &amp; count by state</span></h1>
  <div class="stats" id="stats"></div>
</header>

<div class="wrap">
  <div class="card" id="mapcard">
    <h2>Map of every location</h2>
    <div class="sub">Scroll to zoom · drag to pan · hover a dot for details. <span class="reset" id="reset">Reset view</span></div>
    <div id="mapwrap"><svg id="map" viewBox="0 0 960 600" preserveAspectRatio="xMidYMid meet"></svg></div>
    <div class="hint" id="legend"></div>
  </div>

  <div class="card">
    <h2>Count by state</h2>
    <div class="sub">Sorted high → low. Click a bar to zoom the map to that state.</div>
    <svg id="chart" preserveAspectRatio="xMinYMin meet"></svg>
  </div>
</div>

<div id="tip"></div>

<footer id="methods"></footer>

<script>
const FIELDS = __FIELDS__;
const LOCS = __LOCS__;
const STATES = __STATES__;
const HUDDLE_FIELDS = __HUDDLE_FIELDS__;
const HUDDLE = __HUDDLE__;
// Build index map for field positions
const F = {}; FIELDS.forEach((n,i)=>F[n]=i);
const H = {}; HUDDLE_FIELDS.forEach((n,i)=>H[n]=i);

// ---------- projection (continental US) ----------
// Compute lon/lat bounds from state outlines, project with a simple
// equirectangular + cos(midLat) correction, fit into the SVG box.
let minLon=Infinity,maxLon=-Infinity,minLat=Infinity,maxLat=-Infinity;
function scanRing(ring){ for(const [x,y] of ring){ if(x<minLon)minLon=x; if(x>maxLon)maxLon=x; if(y<minLat)minLat=y; if(y>maxLat)maxLat=y; } }
for(const s of STATES){ const g=s.geometry;
  if(g.type==="Polygon"){ for(const r of g.coordinates) scanRing(r); }
  else { for(const poly of g.coordinates) for(const r of poly) scanRing(r); } }

const MAPW=960, MAPH=600, PAD=12;
const midLat=(minLat+maxLat)/2, kx=Math.cos(midLat*Math.PI/180);
const lonSpan=(maxLon-minLon)*kx, latSpan=(maxLat-minLat);
const scale=Math.min((MAPW-2*PAD)/lonSpan,(MAPH-2*PAD)/latSpan);
const drawW=lonSpan*scale, drawH=latSpan*scale;
const offX=(MAPW-drawW)/2, offY=(MAPH-drawH)/2;
function proj(lon,lat){
  const x=offX+((lon-minLon)*kx)*scale;
  const y=offY+((maxLat-lat))*scale;   // invert lat
  return [x,y];
}

// ---------- draw map ----------
const SVGNS="http://www.w3.org/2000/svg";
const map=document.getElementById("map");
function el(tag,attrs){ const e=document.createElementNS(SVGNS,tag); for(const k in attrs) e.setAttribute(k,attrs[k]); return e; }

function ringToPath(ring){
  let d="";
  for(let i=0;i<ring.length;i++){ const [x,y]=proj(ring[i][0],ring[i][1]); d+=(i?"L":"M")+x.toFixed(1)+" "+y.toFixed(1); }
  return d+"Z";
}
const gStates=el("g",{}); map.appendChild(gStates);
for(const s of STATES){
  const g=s.geometry; let d="";
  if(g.type==="Polygon"){ for(const r of g.coordinates) d+=ringToPath(r); }
  else { for(const poly of g.coordinates) for(const r of poly) d+=ringToPath(r); }
  const p=el("path",{d:d,class:"state"}); p.setAttribute("data-name",s.name); gStates.appendChild(p);
}

// dots
const gDots=el("g",{}); map.appendChild(gDots);
const tip=document.getElementById("tip");
function showTip(ev,L){
  const museum = L[F.museum]===1;
  tip.innerHTML =
    (museum?'<div class="t-mu">🏛 WAFFLE HOUSE MUSEUM (not an operating restaurant)</div>':'') +
    '<div class="t-name">'+esc(L[F.name])+'</div>'+
    '<div class="t-row">'+esc(L[F.addr])+'</div>'+
    '<div class="t-row">'+esc(L[F.city])+', '+esc(L[F.state])+' '+esc(L[F.zip])+'</div>'+
    '<div class="t-row">'+esc(L[F.phone]||'—')+'</div>'+
    '<div class="t-row">'+esc(L[F.hours]||'—')+'</div>'+
    '<div class="t-op">'+esc(L[F.op]||'operator unknown')+'</div>';
  tip.style.display="block";
  positionTip(ev);
}
function positionTip(ev){
  const pad=14; let x=ev.clientX+pad, y=ev.clientY+pad;
  const r=tip.getBoundingClientRect();
  if(x+r.width>window.innerWidth) x=ev.clientX-r.width-pad;
  if(y+r.height>window.innerHeight) y=ev.clientY-r.height-pad;
  tip.style.left=x+"px"; tip.style.top=y+"px";
}
function showHuddleTip(ev,L){
  tip.innerHTML =
    '<div class="t-name" style="color:#0a4fa0">'+esc(L[H.name])+'</div>'+
    '<div class="t-row">'+esc(L[H.addr])+'</div>'+
    '<div class="t-row">'+esc(L[H.city])+', '+esc(L[H.state])+' '+esc(L[H.zip])+'</div>'+
    '<div class="t-op">Huddle House · location approximate (town-level)</div>';
  tip.style.display="block"; positionTip(ev);
}
function esc(s){ return String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])); }

for(const L of LOCS){
  const [x,y]=proj(L[F.lon],L[F.lat]);
  const museum=L[F.museum]===1;
  const c=el(museum?"rect":"circle", museum
    ? {x:(x-4).toFixed(1),y:(y-4).toFixed(1),width:8,height:8,transform:`rotate(45 ${x.toFixed(1)} ${y.toFixed(1)})`,class:"museum"}
    : {cx:x.toFixed(1),cy:y.toFixed(1),r:2.1,class:"dot"});
  c.addEventListener("mouseenter",ev=>showTip(ev,L));
  c.addEventListener("mousemove",positionTip);
  c.addEventListener("mouseleave",()=>tip.style.display="none");
  gDots.appendChild(c);
}

// Huddle House layer (drawn on top, distinct blue squares)
const gHuddle=el("g",{}); map.appendChild(gHuddle);
for(const L of HUDDLE){
  const [x,y]=proj(L[H.lon],L[H.lat]);
  const c=el("rect",{x:(x-3).toFixed(1),y:(y-3).toFixed(1),width:6,height:6,class:"huddle"});
  c.addEventListener("mouseenter",ev=>showHuddleTip(ev,L));
  c.addEventListener("mousemove",positionTip);
  c.addEventListener("mouseleave",()=>tip.style.display="none");
  gHuddle.appendChild(c);
}

// ---------- pan / zoom via viewBox ----------
let vb={x:0,y:0,w:MAPW,h:MAPH};
function applyVB(){ map.setAttribute("viewBox",`${vb.x} ${vb.y} ${vb.w} ${vb.h}`); }
function zoomTo(box,padFrac=0.15){
  // box in lon/lat -> project corners
  const [x1,y1]=proj(box.minLon,box.maxLat), [x2,y2]=proj(box.maxLon,box.minLat);
  let w=Math.max(x2-x1,20), h=Math.max(y2-y1,20);
  const px=w*padFrac, py=h*padFrac; w+=2*px; h+=2*py;
  // keep aspect of viewport
  const ar=MAPW/MAPH; if(w/h>ar) h=w/ar; else w=h*ar;
  vb={x:x1-px-(w-(x2-x1+2*px))/2, y:y1-py-(h-(y2-y1+2*py))/2, w, h}; applyVB();
}
map.addEventListener("wheel",ev=>{
  ev.preventDefault();
  const pt=clientToSvg(ev); const f=ev.deltaY<0?0.85:1.18;
  const nw=Math.min(Math.max(vb.w*f,40),MAPW*3), nh=nw*(vb.h/vb.w);
  vb.x=pt.x-(pt.x-vb.x)*(nw/vb.w); vb.y=pt.y-(pt.y-vb.y)*(nh/vb.h); vb.w=nw; vb.h=nh; applyVB();
},{passive:false});
let drag=null;
map.addEventListener("pointerdown",ev=>{ drag={x:ev.clientX,y:ev.clientY,vx:vb.x,vy:vb.y}; map.setPointerCapture(ev.pointerId); });
map.addEventListener("pointermove",ev=>{ if(!drag)return; const s=vb.w/map.clientWidth;
  vb.x=drag.vx-(ev.clientX-drag.x)*s; vb.y=drag.vy-(ev.clientY-drag.y)*s; applyVB(); });
map.addEventListener("pointerup",ev=>{ drag=null; });
function clientToSvg(ev){ const r=map.getBoundingClientRect();
  return {x:vb.x+(ev.clientX-r.left)/r.width*vb.w, y:vb.y+(ev.clientY-r.top)/r.height*vb.h}; }
document.getElementById("reset").addEventListener("click",()=>{ vb={x:0,y:0,w:MAPW,h:MAPH}; applyVB(); clearSel(); });

// ---------- bar chart: count by state ----------
const counts={};
for(const L of LOCS){ const s=L[F.state]; counts[s]=(counts[s]||0)+1; }
const order=Object.keys(counts).sort((a,b)=>counts[b]-counts[a]);
const nStates=order.length, total=LOCS.length;

const chart=document.getElementById("chart");
const rowH=20, gap=4, left=34, right=44, padT=8, maxCount=Math.max(...Object.values(counts));
const chartW=380, barMax=chartW-left-right;
const chartH=padT*2+nStates*(rowH+gap);
chart.setAttribute("viewBox",`0 0 ${chartW} ${chartH}`);
chart.style.maxWidth=chartW+"px";
let bars={};
order.forEach((st,i)=>{
  const y=padT+i*(rowH+gap);
  const w=Math.max(2,barMax*counts[st]/maxCount);
  chart.appendChild(el("text",{x:left-6,y:y+rowH*0.72,"text-anchor":"end",class:"blabel"})).textContent=st;
  const bar=el("rect",{x:left,y:y,width:w,height:rowH,rx:2,class:"bar"});
  bar.setAttribute("data-state",st);
  bar.addEventListener("click",()=>selectState(st));
  chart.appendChild(bar); bars[st]=bar;
  chart.appendChild(el("text",{x:left+w+5,y:y+rowH*0.72,class:"bcount"})).textContent=counts[st];
});

function stateBox(st){
  let b={minLon:Infinity,maxLon:-Infinity,minLat:Infinity,maxLat:-Infinity};
  for(const L of LOCS){ if(L[F.state]!==st) continue;
    b.minLon=Math.min(b.minLon,L[F.lon]); b.maxLon=Math.max(b.maxLon,L[F.lon]);
    b.minLat=Math.min(b.minLat,L[F.lat]); b.maxLat=Math.max(b.maxLat,L[F.lat]); }
  return b;
}
function clearSel(){ for(const k in bars) bars[k].classList.remove("sel"); }
function selectState(st){ clearSel(); bars[st].classList.add("sel"); zoomTo(stateBox(st)); }

// ---------- header stats + legend + methods ----------
const topState=order[0];
document.getElementById("stats").innerHTML =
  `<b>${total.toLocaleString()}</b> Waffle Houses · <b>${nStates}</b> states · most: <b>${topState}</b> (${counts[topState]}, ${(100*counts[topState]/total).toFixed(1)}%)`+
  (HUDDLE.length?` &nbsp;|&nbsp; <b>${HUDDLE.length}</b> Huddle Houses (sample)`:``);
document.getElementById("legend").innerHTML =
  `<span style="color:#7a5b00">●</span> Waffle House &nbsp;·&nbsp; <span style="color:#e4002b">◆</span> Waffle House Museum`+
  (HUDDLE.length?` &nbsp;·&nbsp; <span style="color:#1f78d1">■</span> Huddle House (${HUDDLE.length}-location sample, approx.)`:``);
document.getElementById("methods").innerHTML =
  `Source: <code>waffle_houses.csv</code> (${total.toLocaleString()} records incl. the museum). `+
  `Map drawn offline from embedded US-state outlines; no internet or tiles required. `+
  `Counts are by the <code>State</code> field. Note from data QA: website URLs contain a `+
  `<code>///</code> artifact and 229 rows hold two phone numbers — neither affects these counts.`+
  (HUDDLE.length?` &nbsp;Huddle Houses: a hand-picked sample of ${HUDDLE.length} real locations `+
    `(addresses from huddlehouse.com store pages via <code>huddle_houses.csv</code>); `+
    `their dots are placed at <b>approximate town-level coordinates</b>, not surveyed building points.`:``);
</script>
</body>
</html>
"""

HTML = (HTML
        .replace("__FIELDS__", fields_json)
        .replace("__LOCS__", locs_json)
        .replace("__STATES__", states_json)
        .replace("__HUDDLE_FIELDS__", huddle_fields_json)
        .replace("__HUDDLE__", huddle_json))

with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write(HTML)
print(f"wrote {OUT_PATH}: {len(HTML)} bytes")
