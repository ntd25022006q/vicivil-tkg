"""Build docs/graph/explorer.html : two-view professional explorer.

View 1 "Mạng kế thừa"  : AntV G6 5.1 (open-source, MIT) — the standard
                          academic interactive-graph library; preset layout,
                          pan/zoom, tap-to-focus neighborhood, tip overlay.
View 2 "Phổ thời gian" : Vega-Lite 5 through vega-embed — declarative
                          (spec-based) validity-window Gantt; the same spec is
                          shipped as docs/graph/law_timeline.vl.json.
Open interchange       : docs/graph/law_graph.gexf (Gephi/Gephi-Lite).
All user-facing text in Vietnamese with proper diacritics."""
import io
import json
import os
import sys
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
REL = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(REL, "docs", "graph")
os.makedirs(OUT, exist_ok=True)

G = json.load(open(os.path.join(REL, "provenance", "temporal_graph.json"), encoding="utf-8"))
CE = json.load(open(os.path.join(REL, "provenance", "cite_edges.json"), encoding="utf-8"))
laws, edges = G["laws"], G["succession"]

nchunks = Counter()
with open(os.path.join(REL, "data", "civil_chunks.jsonl"), encoding="utf-8") as f:
    for line in f:
        nchunks[json.loads(line)["law_id"]] += 1
intra = Counter()
for e in CE:
    intra[e["src_law"]] += e["n"]

CAT = {
    "BLDS1995": ("Dòng BLDS", "#f4a23a"), "BLDS2005": ("Dòng BLDS", "#f4a23a"),
    "BLDS2015": ("Dòng BLDS", "#f4a23a"),
    "HNGD2000": ("Gia đình", "#d05d9c"), "HNGD2014": ("Gia đình", "#d05d9c"),
    "HNGDVBHN2025": ("Gia đình", "#d05d9c"),
    "HOTICH2014": ("Hộ tịch", "#8e6fc7"), "HOTICH2026": ("Hộ tịch", "#8e6fc7"),
    "TNBTCNN2017": ("Bồi thường nhà nước", "#4c9fbe"),
    "luat-so-15-2026-qh16-470450": ("Bồi thường nhà nước", "#4c9fbe"),
    "van-ban-hop-nhat-so-21-vbhn-vpqh-468974": ("Tố tụng dân sự", "#57a773"),
    "thong-tu-lien-tich-so-07-2026-ttlt-vksndtc-tandtc-469106": ("Tố tụng dân sự", "#57a773"),
    "THADS2008": ("Thi hành án dân sự", "#b05636"), "THADSVBHN": ("Thi hành án dân sự", "#b05636"),
    "nghi-dinh-so-152-2026-nd-cp-469524": ("Thi hành án dân sự", "#b05636"),
    "HOAGIAI2026": ("Khác", "#7f8c8d"), "NCN2010": ("Khác", "#7f8c8d"),
}
NAME = {
    "BLDS1995": "Bộ luật Dân sự 1995",
    "BLDS2005": "Bộ luật Dân sự 2005",
    "BLDS2015": "Bộ luật Dân sự 2015",
    "HNGD2000": "Luật HN&GĐ 2000",
    "HNGD2014": "Luật HN&GĐ 2014",
    "HNGDVBHN2025": "Luật HN&GĐ (VBHN 2025)",
    "HOTICH2014": "Luật Hộ tịch 2014",
    "HOTICH2026": "Luật Hộ tịch (VBHN 2026)",
    "TNBTCNN2017": "Luật TNBT-NN 2017",
    "luat-so-15-2026-qh16-470450": "Luật 15/2026 (sửa TNBT-NN)",
    "van-ban-hop-nhat-so-21-vbhn-vpqh-468974": "BLTTHDS (VBHN 21/2025)",
    "thong-tu-lien-tich-so-07-2026-ttlt-vksndtc-tandtc-469106": "TT liên tịch 07/2026",
    "THADS2008": "Luật THADS 2008",
    "THADSVBHN": "Luật THADS (VBHN 2025)",
    "nghi-dinh-so-152-2026-nd-cp-469524": "NĐ 152/2026 (thi hành THADS)",
    "HOAGIAI2026": "Luật Hòa giải tại cơ sở 2026",
    "NCN2010": "Luật Nuôi con nuôi 2010",
}
STATUS = {
    "con_hieu_luc": "đang có hiệu lực",
    "het_hieu_luc": "đã hết hiệu lực",
    "needs_review": "cần kiểm tra lại",
}
NOTE = {
    "BLDS 2005 thay the BLDS 1995": "BLDS 2005 thay thế BLDS 1995",
    "BLDS 2015 thay the BLDS 2005": "BLDS 2015 thay thế BLDS 2005",
    "HN&GĐ 2014 thay the HN&GĐ 2000": "HN&GĐ 2014 thay thế HN&GĐ 2000",
    "VBHN 2025 hop nhat HN&GĐ 2014 + sua doi (thieu Dieu 132-133 ban goc)":
        "VBHN 2025 hợp nhất HN&GĐ 2014 và các sửa đổi (thiếu Điều 132-133 bản gốc)",
    "verified from VBHN preamble (2025-06-24)": "kiểm chứng từ tiền văn (preamble) VBHN (24-06-2025)",
}
RELVIE = {
    "REPLACES": "thay thế", "CONSOLIDATES": "hợp nhất", "AMENDS": "sửa đổi",
}
LANES = ["Dòng BLDS", "Gia đình", "Hộ tịch", "Bồi thường nhà nước",
         "Tố tụng dân sự", "Thi hành án dân sự", "Khác"]

TODAY_Y = 2026
TODAY_D = 291  # ~Oct 18


def ms(iso):
    return (int(iso[:4]) if iso else 2010) - 1996


host_of = {}
for e in edges:
    if e["src"].startswith("EXT-"):
        host_of.setdefault(e["src"], e["tgt"])
import math as _math

FALLBACK_LANE = LANES[-1]


def lane_cat(lid, ext):
    if ext and host_of.get(lid):
        cat = CAT.get(host_of[lid])
    else:
        cat = CAT.get(lid)
    if cat is None:
        return FALLBACK_LANE, "#9aa0a6"
    return cat[0], cat[1]


lane_of = {}
for L in laws:
    lid = L["law_id"]
    c, _ = lane_cat(lid, lid.startswith("EXT-"))
    if c not in LANES:
        c = FALLBACK_LANE
    lane_of[lid] = c


def node_rad(L):
    lid = L["law_id"]
    ch = 0 if lid.startswith("EXT-") else nchunks.get(lid, 0)
    if not ch:
        return 5.0
    return min(46.0, 12.0 + _math.sqrt(ch) * 0.72) / 2.0


def short_name(L):
    import re as _re
    lid = L["law_id"]
    so = L.get("so_hieu") or ""
    if lid.startswith("EXT-"):
        num = so.replace("Luật số", "").replace("Luật so", "").strip()
        m = _re.match(r"(\d{1,4}/\d{4})", num)
        if not m:
            m2 = _re.search(r"(\d{1,4})-(\d{4})", lid)
            m = _re.match(r"(\d{1,4}/\d{4})", m2.group(1) + "/" + m2.group(2)) if m2 else None
        if m:
            base = m.group(1)
            return ("VBHN " + base) if "vbhn" in (so + lid).lower() else base
    return NAME.get(lid) or L["ten"] or lid


def lab_w(name):
    return min(len(name) * 5.7, 96.0)


PXP, PYP, X0P, Y0P = 36.0, 64.0, 150.0, 40.0
DXS = (0, -9, 9, -17, 17, -25, 25, -34, 34, -43, 43, -55, 55,
       -64, 64, -76, 76, -89, 89, -97, 97, -112, 112, -118, 118)
DYS = (0, -15, 15, -30, 30, -45, 45, -60, 60, -75, 75, -90, 90)
_LATTICE = sorted(((dxx, dy) for dy in DYS for dxx in DXS),
                  key=lambda t: (1.35 * abs(t[0])) ** 2 + t[1] ** 2)
_YLO, _YHI = Y0P + 10, Y0P + (len(LANES) - 1) * PYP + 34


def _fits(xp, yp, hw, vh, placed):
    for ox, oy, ohw, ovh in placed:
        if abs(xp - ox) < hw + ohw + 6 and abs(yp - oy) < vh + ovh + 6:
            return False
    return True


_placed = []
_ylane = {}
_xjit = {}
YBAND = 94
for L in sorted(laws, key=lambda Z: (ms(Z.get("valid_from")), lane_of[Z["law_id"]])):
    lid = L["law_id"]
    li = LANES.index(lane_of[lid])
    base = Y0P + li * PYP
    xp0 = X0P + ms(L.get("valid_from")) * PXP
    rad = node_rad(L)
    nm = short_name(L)
    hw = max(rad, lab_w(nm) / 2.0)
    _lines = max(1, -(-int(lab_w(nm)) // 90))
    vh = rad + 15.0 * _lines + (4.0 if rad > 15 else 0.0)
    chosen = None
    for dx, dy in _LATTICE:
        xp, yp = xp0 + dx, base + dy
        if yp < max(_YLO, base - YBAND) or yp > min(_YHI, base + YBAND):
            continue
        if _fits(xp, yp, hw, vh, _placed):
            chosen = (xp, yp, dx)
            break
    if chosen is None:
        best_pen = None
        for dx, dy in _LATTICE:
            xp, yp = xp0 + dx, base + dy
            if yp < max(_YLO, base - YBAND) or yp > min(_YHI, base + YBAND):
                continue
            pen = sum(max(0.0, min(1.0, (hw + ohw + 6 - abs(xp - ox)) / (hw + ohw + 6))) *
                      max(0.0, min(1.0, (vh + ovh + 6 - abs(yp - oy)) / (vh + ovh + 6)))
                      for ox, oy, ohw, ovh in _placed
                      if abs(xp - ox) < hw + ohw + 6 and abs(yp - oy) < vh + ovh + 6)
            if best_pen is None or pen < best_pen[0] - 1e-9:
                best_pen = (pen, xp, yp, dx)
        chosen = (best_pen[1], best_pen[2], best_pen[3]) if best_pen else (xp0, base, 0)
    xp, yp, dx = chosen
    _placed.append((xp, yp, hw, vh))
    _xjit[lid] = dx
    _ylane[lid] = round((yp - Y0P) / PYP, 3)

lane_lab_y = [float(i) for i in range(len(LANES))]
_maxypx = max(_placed, key=lambda Z: Z[1])[1]
TICK_LK = round((_maxypx - Y0P) / PYP + 1.0, 2)

nodes = []
for L in laws:
    lid = L["law_id"]
    ext = lid.startswith("EXT-")
    cat, color = lane_cat(lid, ext)
    nodes.append({
        "id": lid, "name": short_name(L),
        "full": NAME.get(lid) or L.get("ten") or lid,
        "sym": L.get("so_hieu") or lid.replace("-", " "),
        "from": L.get("valid_from") or "2010-01-01", "to": L.get("valid_to") or "",
        "status": STATUS.get(L.get("status") or "", L.get("status") or "chưa rõ"),
        "cat": cat, "color": color, "chunks": 0 if ext else nchunks.get(lid, 0),
        "cites": intra.get(lid, 0),
        "x": ms(L.get("valid_from")), "y": _ylane[lid], "dx": _xjit[lid],
        "ext": ext,
    })

edge_items = []
for e in edges:
    s = next(n for n in nodes if n["id"] == e["src"])
    t = next(n for n in nodes if n["id"] == e["tgt"])
    note = NOTE.get(e.get("note") or "", e.get("note") or "")
    edge_items.append({
        "src": e["src"], "tgt": e["tgt"], "rel": e.get("relation") or "AMENDS",
        "relvie": RELVIE.get(e.get("relation") or "AMENDS", e.get("relation")),
        "at": e.get("at") or "2000-01-01", "sname": s["name"], "tname": t["name"],
        "note": note,
    })

laws_count = sum(1 for n in nodes if not n["ext"])
ext_count = len(nodes) - laws_count
chunks_total = sum(nchunks.values())

# ---- Vega-Lite spec (declarative validity-window Gantt) ----
import datetime as _dt
rownum = {n["id"]: i for i, n in enumerate(sorted(nodes, key=lambda n: n["y"]))}
_name_seq = sorted(nodes, key=lambda n: n["y"])
_cnt = Counter(n["name"] for n in _name_seq)
_done = Counter()
vlnm = {}
for n in _name_seq:
    nmv = n["name"]
    if _cnt[nmv] > 1:
        _done[nmv] += 1
        nmv = nmv + " ‹" + (n["sym"] or n["id"]) + "›"
    vlnm[n["id"]] = nmv
VDOM = [vlnm[n["id"]] for n in _name_seq]
TODAY_ISO = (_dt.date(TODAY_Y, 1, 1) + _dt.timedelta(days=TODAY_D - 1)).isoformat()
XDOM = ["1995-01-01", "2027-02-01"]
cat_hex = {}
for L in laws:
    c, h = lane_cat(L["law_id"], L["law_id"].startswith("EXT-"))
    if c not in cat_hex:
        cat_hex[c] = h
_cats = [c for c in LANES if c in cat_hex] + [c for c in sorted(cat_hex) if c not in LANES]
_CATCOLOR = {"field": "cat", "type": "nominal",
             "scale": {"domain": _cats, "range": [cat_hex[c] for c in _cats]}}
bars = [{
    "id": n["id"], "name": vlnm[n["id"]], "cat": n["cat"], "color": n["color"],
    "status": n["status"], "sym": n["sym"],
    "s": n["from"], "e": (n["to"] + "T00:00:00") if n["to"] else "2026-12-31",
    "row": rownum[n["id"]], "chunks": n["chunks"], "cites": n["cites"],
} for n in nodes]
links = [{
    "relvie": e["relvie"], "rel": e["rel"], "at": e["at"],
    "name": vlnm[e["src"]], "name2": vlnm[e["tgt"]],
} for e in edge_items]
VLSPEC = {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "description": "ViCivil-TKG — phổ thời gian hiệu lực của 17 văn bản luật dân sự (1996-2026) và 21 cạnh kế thừa",
    "width": 820, "height": 470,
    "background": "#0a0d12",
    "config": {"font": "Be Vietnam Pro", "axis": {"labelColor": "#8b96a3", "titleColor": "#5d6874",
                "gridColor": "rgba(230,238,247,.05)", "domainColor": "#232c37"},
               "legend": {"labelColor": "#c3ccd5", "titleColor": "#8b96a3"},
               "tooltip": {"theme": "dark"}},
    "layer": [
        {"mark": {"type": "bar", "opacity": 0.92, "cornerRadius": 3, "height": 11},
         "encoding": {
             "x": {"field": "s", "type": "temporal", "scale": {"domain": XDOM},
                   "axis": {"title": "Năm hiệu lực", "format": "%Y", "grid": True,
                            "tickMinStep": {"interval": "year", "step": 5}}},
             "x2": {"field": "e"},
             "y": {"field": "name", "type": "nominal", "scale": {"domain": VDOM},
                   "axis": {"title": None, "labelFontSize": 9.5, "labelLimit": 210,
                            "grid": True, "tick": False, "domain": False}},
             "color": dict(_CATCOLOR, legend={"title": "Nhóm văn bản"})}},
        {"mark": {"type": "rule", "opacity": 0.9},
         "data": {"name": "links"},
         "encoding": {
             "x": {"field": "at", "type": "temporal", "scale": {"domain": XDOM}},
             "x2": {"field": "at"},
             "y": {"field": "name", "type": "nominal", "scale": {"domain": VDOM}},
             "y2": {"field": "name2"},
             "color": {"value": "#d9a441"},
             "size": {"value": 2.4},
             "opacity": {"value": 0.95}}},
        {"mark": {"type": "rule", "strokeDash": [4, 3], "opacity": 0.95},
         "encoding": {
             "x": {"value": TODAY_ISO, "type": "temporal", "scale": {"domain": XDOM}},
             "x2": {"value": TODAY_ISO},
             "y": {"value": VDOM[0], "type": "nominal", "scale": {"domain": VDOM}},
             "y2": {"value": VDOM[-1]},
             "color": {"value": "#6fd3e0"},
             "size": {"value": 1.6}}},
        {"mark": {"type": "point", "opacity": 1, "size": 60, "filled": True},
         "encoding": {
             "x": {"field": "s", "type": "temporal", "scale": {"domain": XDOM}},
             "y": {"field": "name", "type": "nominal", "scale": {"domain": VDOM}},
             "color": dict(_CATCOLOR, legend=None)}}
    ],
    "data": {"values": bars},
    "datasets": {"links": links},
}

PAYLOAD = json.dumps({
    "nodes": nodes, "edges": edge_items, "lanes": LANES, "relvie": RELVIE,
    "yearMin": min(n["x"] for n in nodes) + 1996, "yearMax": max(n["x"] for n in nodes) + 1996,
    "vl": VLSPEC,
    "stats": {"laws": laws_count, "edges": len(edge_items),
              "chunks": chunks_total, "gold": 281, "ext": ext_count},
}, ensure_ascii=False)

# ---- chi muc dieu/khoan: nen de tra cuu cap dieu (dung cho nhom "chu de bi sua doi")
# docs/graph/law_articles.json: {law_id: {key: {n, chars, in, out, ids}}}
ARTS_FULL = {}
_ap = os.path.join(OUT, "law_articles.json")
if os.path.exists(_ap):
    ARTS_FULL = json.load(open(_ap, encoding="utf-8"))
# ban compact nhung vao trang xem: [key, so doan, so lan duoc tro toi, so lan tro den]
ARTS = {}
for _law, _d in ARTS_FULL.items():
    _rows = [[k, v["n"], v["out"], v["in"]] for k, v in _d.items()]
    _rows.sort(key=lambda r: (-r[2], -r[3], r[0]))
    ARTS[_law] = _rows
ARTS_JSON = json.dumps(ARTS, ensure_ascii=False, separators=(",", ":"))

json.dump({"spec": VLSPEC}, open(os.path.join(OUT, "law_timeline.vl.json"), "w",
                                 encoding="utf-8"), ensure_ascii=False, indent=1)

_LIBDIR = os.path.join(REL, "docs", "graph")
LIBG6 = io.open(os.path.join(_LIBDIR, "g6.min.js"), encoding="utf-8").read()
LIBVEGA = io.open(os.path.join(_LIBDIR, "vega.min.js"), encoding="utf-8").read()
LIBVL = io.open(os.path.join(_LIBDIR, "vega-lite.min.js"), encoding="utf-8").read()
LIBEMBED = io.open(os.path.join(_LIBDIR, "vega-embed.min.js"), encoding="utf-8").read()

INIT_CNT = sum(1 for n in nodes if not n["ext"] and int(n["from"][:4]) <= 2026
              and (True if not n["to"] else int(n["to"][:4]) > 2026))

HTML = r"""<!DOCTYPE html>
<html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet" media="print" onload="this.media='all'">
<noscript><link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet"></noscript>
<title>ViCivil-TKG — Dòng thời gian luật dân sự Việt Nam</title>
<script>
/* Khong them bat ky UI chan doan nao vao trang. Loi chi duoc ghi ra
   console (chu thuan cua trinh duyet) va congsiu cho bo kiem tra
   tu dong chay tren nhieu trinh duyet truoc khi phat hanh. */
window.__errs=[];
window.onerror=function(m,f,l,c){
  window.__errs.push(String(m)+' @'+l+':'+c);console.error('[viewer]',m,l+':'+c);return false};
window.addEventListener('unhandledrejection',function(e){
  var r=e&&e.reason;var t=(r&&(r.message||String(r))||'promise rejection');
  window.__errs.push(t);console.error('[viewer]',t)});
</script>
<script>/* AntV G6 5.1.1 - MIT - vendored verbatim */__LIBG6__</script>
<script>/* Vega 5.30.0 - MIT - vendored verbatim */__LIBVEGA__</script>
<script>/* Vega-Lite 5.21.0 - MIT - vendored verbatim */__LIBVEGALITE__</script>
<script>/* vega-embed 6.26.0 - MIT - vendored verbatim */__LIBEMBED__</script>
<style>
:root{--bg:#0a0d12;--plate:#0e1218;--line:#1c232e;--line2:#232c37;
  --txt:#e6eaf0;--mut:#8b96a3;--mut2:#5d6874;--acc:#d9a441;--gold:#d9a441;--blue:#62778c;--green:#6fae7f;--cyan:#6fd3e0;
  --mono:'IBM Plex Mono',ui-monospace,monospace}
*{box-sizing:border-box}
html,body{margin:0}
body{font-family:'Be Vietnam Pro',system-ui,'Segoe UI',Roboto,sans-serif;color:var(--txt);
  background:var(--bg);font-kerning:normal;text-rendering:optimizeLegibility}
a{color:var(--txt);text-decoration:none;border-bottom:1px solid var(--line2)}a:hover{border-bottom-color:var(--mut)}
header{position:sticky;top:0;z-index:20;background:var(--bg);border-bottom:1px solid var(--line)}
.hrow{max-width:1440px;margin:0 auto;padding:13px 22px 11px;display:flex;gap:16px;align-items:baseline;flex-wrap:wrap}
.brand{display:flex;align-items:baseline;gap:10px}
.brand .mark{color:var(--acc);display:inline-flex;transform:translateY(2px)}
.brand h1{font-size:15.5px;margin:0;font-weight:700;letter-spacing:.3px}
.specl{color:var(--mut);font-size:12px;font-weight:500;display:flex;gap:0;flex-wrap:wrap}
.specl b{color:var(--txt);font-weight:600;font-variant-numeric:tabular-nums}
.specl .sep{color:var(--mut2);margin:0 9px}
.top-links{margin-left:auto;display:flex;gap:14px;align-items:baseline;font-size:12px}
.top-links .ver{color:var(--mut2);font:500 11px var(--mono)}
#cy .g6-minimap svg{filter:invert(.92) hue-rotate(180deg) saturate(.85)}
#cy .g6-minimap{background:rgba(14,18,24,.94)!important;border:1px solid #242d38;border-radius:8px;overflow:hidden}
#cy .g6-minimap svg{display:block}
#bar{max-width:1440px;margin:0 auto;padding:10px 22px;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
button{background:transparent;color:var(--txt);border:1px solid var(--line2);padding:7px 13px;
  border-radius:7px;cursor:pointer;font-size:12.5px;font-family:inherit;font-weight:500;
  transition:.15s}
button:hover{border-color:var(--mut2);background:rgba(255,255,255,.03)}
button.primary{border-color:rgba(217,164,65,.5);color:var(--acc);font-weight:600}
button.primary:hover{background:rgba(217,164,65,.08);border-color:var(--acc)}
button.tab{border:0;border-bottom:2px solid transparent;border-radius:0;color:var(--mut);
  padding:9px 2px 8px;font-weight:500;letter-spacing:.3px}
button.tab.active{color:var(--txt);border-bottom-color:var(--acc)}
button:focus-visible,input:focus-visible{outline:2px solid var(--acc);outline-offset:2px}
.playwrap{display:flex;align-items:center;gap:7px}
select{background:transparent;color:var(--mut);border:1px solid var(--line2);border-radius:7px;
  padding:6px 8px;font-size:11.5px;font-family:inherit;cursor:pointer}
#yearbig{font:600 14.5px var(--mono);color:var(--acc);border:1px solid rgba(217,164,65,.4);
  background:rgba(217,164,65,.06);border-radius:6px;padding:6px 10px;min-width:56px;text-align:center;
  letter-spacing:.5px}
.readout{font-size:12px;color:var(--mut)}
.readout b{color:var(--txt);font-variant-numeric:tabular-nums}
input[type=range]{width:min(360px,36vw);accent-color:var(--acc);cursor:pointer}
.searchwrap{position:relative;margin-left:auto}
#search{background:transparent;border:1px solid var(--line2);color:var(--txt);padding:7px 10px 7px 30px;
  border-radius:7px;font-size:12.5px;width:225px;font-family:inherit}
#search::placeholder{color:var(--mut2)}
.searchwrap svg{position:absolute;left:9px;top:9px;color:var(--mut2)}
datalist{color-scheme:dark}
#lanebar{max-width:1440px;margin:0 auto;padding:0 22px 9px;display:flex;gap:0 16px;flex-wrap:wrap;
  align-items:center}
#lanebar .grp{width:1px;align-self:stretch;background:var(--line);margin:1px 0}
.lchip,.tg{display:inline-flex;align-items:center;gap:7px;font-size:11.5px;color:var(--mut);
  cursor:pointer;user-select:none;transition:.15s;background:none;border:0;padding:6px 2px;
  font-family:inherit}
.lchip:hover,.tg:hover{color:var(--txt)}
.lchip i{width:8px;height:8px;border-radius:2px;display:inline-block;transition:.15s}
.lchip.off i{background:var(--line2)!important;transform:scale(.85)}
.lchip.off,.tg.off{color:var(--mut2);text-decoration:line-through;text-decoration-color:var(--mut2);text-decoration-thickness:1px}
.tg .sym{font:600 11px var(--mono);letter-spacing:-.5px}
.tg.on .sym{color:var(--mut)}
.tg.on[data-k=rep] .sym{color:var(--gold)}.tg.on[data-k=amd] .sym{color:#7d9cb8}
#tabbar{max-width:1440px;margin:0 auto;padding:8px 14px 0;display:flex;gap:18px;
  border-bottom:1px solid var(--line)}
main{position:relative;display:flex}
#viewwrap{flex:1 1 auto;position:relative;height:78vh;min-height:560px;min-width:0}
#cy{position:absolute;inset:0}
#tl{position:absolute;inset:0;background:#0a0d12;z-index:5;display:none;align-items:center;justify-content:center}
#tl .vega-bind{color:#93a0ac}
#drawer{width:0;flex:0 0 auto;transition:width .22s ease;overflow:hidden;background:rgba(17,22,28,.94);
  border-left:1px solid var(--line);position:relative}
#drawer.open{width:352px;overflow-y:auto}
#drawer .inner{width:352px;padding:18px 18px 26px}
#dclose{position:absolute;top:10px;right:10px;background:transparent;border:0;color:#93a0ad;font-size:18px}
.dname{font-size:15.5px;font-weight:700;line-height:1.35;margin:2px 40px 10px 0}
.dlane{display:inline-flex;align-items:center;gap:6px;font-size:11px;color:#c7d0d9;
  border:1px solid var(--line2);border-radius:99px;padding:4px 10px;margin-bottom:12px}
.dlane i{width:8px;height:8px;border-radius:2px;display:inline-block}
.drow{display:flex;justify-content:space-between;gap:10px;font-size:12.5px;padding:7px 0;border-bottom:1px solid #1d2530}
.drow span:first-child{color:var(--mut)}
.drow span:last-child{text-align:right;font-variant-numeric:tabular-nums}
.dnote{font-size:12px;color:#9aa6b2;margin-top:12px;line-height:1.5}
.dsec{margin-top:16px;font-size:11px;text-transform:uppercase;letter-spacing:1.1px;color:#6e7a86;font-weight:600}
.relrow{display:flex;align-items:center;gap:9px;font-size:12px;padding:7px 8px;border-radius:8px;
  cursor:pointer;border:1px solid transparent}
.relrow:hover{background:#1a212a;border-color:#2b3541}
.relrow .rdot{width:7px;height:7px;border-radius:99px;flex:none}
.relrow .rlab{flex:1;line-height:1.35}
 .relrow .rdate{color:#7d8894;font:500 10.5px var(--mono)}
 .artq{width:100%;background:#0d1218;border:1px solid var(--line2);border-radius:8px;color:var(--txt);
   padding:7px 9px;font:12px var(--sans);margin-bottom:8px}
 .artq:focus{outline:none;border-color:#3a4a5c}
 .arthead{font:500 10.5px var(--mono);color:var(--mut2);margin:6px 0 4px}
 .artrow{display:flex;align-items:baseline;gap:8px;font-size:12px;padding:5px 6px;border-radius:6px}
 .artrow:hover{background:#1a212a}
 .artrow .aname{flex:1;color:#c7d2de}
 .artrow .acnt{color:var(--mut2);font:500 10.5px var(--mono);white-space:nowrap}
 .artrow .acit{color:#8fd18f;font:500 10.5px var(--mono);white-space:nowrap}
.reltag{font-size:10px;padding:2px 7px;border-radius:5px;font-weight:600}
.reltag.REPLACES{background:rgba(217,164,65,.14);color:var(--gold)}
.reltag.AMENDS{background:rgba(125,156,184,.12);color:#a3bed8}
.reltag.CONSOLIDATES{background:rgba(111,174,127,.12);color:var(--green)}
footer{border-top:1px solid var(--line);color:var(--mut2);font-size:11.5px;font-weight:500}
footer .frow{max-width:1440px;margin:0 auto;padding:9px 22px;display:flex;gap:16px;flex-wrap:wrap;align-items:baseline}
.tip{position:fixed;pointer-events:none;background:#10151c;border:1px solid var(--line2);
  border-radius:9px;padding:11px 13px;font-size:12.5px;max-width:360px;
  box-shadow:0 10px 30px rgba(0,0,0,.55);opacity:0;transition:opacity .13s;z-index:30;line-height:1.45}
.tip b{color:#fff}.tip .sub{color:var(--mut);display:block;margin-top:3px;font-size:11.5px}
.tip .live{color:var(--green);font-weight:600}
.tip .dead{color:#8d99a5}
.tip .edgehead{font-weight:700;color:var(--gold)}
@media (max-width:1120px){#drawer.open{position:fixed;right:0;top:0;bottom:0;width:min(352px,92vw);z-index:40}}
</style></head><body>
<header>
  <div class="hrow">
    <div class="brand">
      <span class="mark" aria-hidden="true"><svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><line x1="3" y1="12" x2="21" y2="12"/><circle cx="7" cy="12" r="2.4" fill="currentColor" stroke="none"/><circle cx="13" cy="12" r="2"/><circle cx="18.4" cy="12" r="1.6" fill="currentColor" stroke="none"/></svg></span>
      <h1>ViCivil-TKG</h1>
      <span class="specl" style="margin-left:2px">khung tri thức thời gian của luật dân sự Việt Nam</span>
    </div>
    <span class="specl">
      <b id="st-laws">17</b> văn bản luật<span class="sep">·</span>
      <b id="st-edges">21</b> cạnh kế thừa<span class="sep">·</span>
      <b id="st-chunks">11.267</b> chunk<span class="sep">·</span>
      <b id="st-gold">281</b> câu hỏi gold
    </span>
    <div class="top-links">
      <span class="ver">v1.0.0</span>
      <a href="https://github.com/ntd25022006q/vicivil-tkg" target="_blank">GitHub</a>
      <a href="law_graph.gexf" download>GEXF cho Gephi</a>
    </div>
  </div>
</header>
<div id="bar">
  <span id="yearbig">2026</span>
  <input id="slider" type="range" min="1996" max="2026" value="2026" step="1" aria-label="Chọn thời điểm">
  <span class="playwrap">
    <button class="primary" id="play">Chạy dòng thời gian</button>
    <select id="speed" title="Tốc độ chạy"><option value="650">1×</option><option value="330">2×</option></select>
  </span>
  <span class="readout">Đang hiệu lực: <b id="ncur">__NCUR__</b> văn bản</span>
  <span class="searchwrap">
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6"><circle cx="11" cy="11" r="7"/><line x1="20" y1="20" x2="16.2" y2="16.2"/></svg>
    <input id="search" list="laws" placeholder="Tìm một luật → Enter" autocomplete="off">
    <datalist id="laws"></datalist>
  </span>
  <button id="shot" title="Tải ảnh PNG của đồ thị">Xuất PNG</button>
</div>
<div id="lanebar"></div>
<div id="tabbar">
  <button class="tab active" id="tab-cy">Mạng kế thừa</button>
  <button class="tab" id="tab-vl">Phổ thời gian</button>
</div>
<main>
  <div id="viewwrap">
    <div id="cy"></div>
    <div id="tl"></div>
  </div>
  <aside id="drawer" aria-label="Chi tiết văn bản"><div class="inner" id="dbody"></div></aside>
</main>
<footer><div class="frow">
  <span>Thẻ dữ liệu v1.0.0</span><span>·</span>
  <span>Nguồn công báo chính thức</span><span>·</span>
  <span><a href="law_graph.gexf" download>GEXF 1.3 cho Gephi</a></span><span>·</span>
  <span><a href="law_timeline.vl.json" download>spec Vega-Lite</a></span>
</div></footer>
<div class="tip" id="tip"></div>
<script>
const D=__DATA__;
const ARTS=__ARTS__;
const byId={};D.nodes.forEach(n=>byId[n.id]=n);
const adj={};D.edges.forEach(e=>{(adj[e.src]=adj[e.src]||[]).push(e.tgt);(adj[e.tgt]=adj[e.tgt]||[]).push(e.src)});
const state={cur:2026,focus:null,ext:true,rep:true,amd:true,timer:null,speed:650,lane:{}};
D.lanes.forEach(function(c){state.lane[c]=true});
const TIP=document.getElementById('tip');
function dt(iso){return iso?iso.split('-').reverse().join('/'):''}
function nodeSize(n){return n.chunks?Math.min(46,12+Math.sqrt(n.chunks)*0.72):10}
// ---- G6 view (AntV G6 5) ----
const G6API=window.G6;
const PX=40,PY=62,X0=190,Y0=70;
D.nodes.forEach(function(n){n.yx=X0+n.x*PX+(n.dx||0)*PX/36;});
const GX0=X0-12,GX1=X0+Math.max.apply(null,D.nodes.map(function(n){return n.x;}))*PX+230;
const LANEY=__LANEY__;
const GH=(Math.max.apply(null,LANEY)+1.18)*PY;
const CY=Y0+GH/2-6,CH=GH;
const YEARS=[];for(var gy=__TXTFIRST__;gy<=__TXTLAST__;gy+=5)YEARS.push(gy);
const chromeNodes=[];
function cpush(id,x,y,w,h,fill,label,opt){opt=opt||{};
  chromeNodes.push({id:id,type:'rect',data:{kind:'chrome'},style:Object.assign({
    x:x,y:y,size:[w,h],fill:fill,
    label:true,labelText:label||'',labelFill:'#5d6874',labelFontSize:10,
    labelFontWeight:400,labelFontFamily:'"IBM Plex Mono",monospace',
    labelPlacement:opt.lp||'center',labelOffsetY:opt.oy||0,
    labelBackground:false,fillOpacity:opt.fo===undefined?1:opt.fo,
    strokeOpacity:0,lineWidth:0},opt.s)});}
for(var gi=0;gi<YEARS.length;gi++){
  var gx=X0+(YEARS[gi]-1996)*PX;
  if(Math.abs(YEARS[gi]-1996-__TODAYX__)<1.2)continue;
  cpush('grid'+YEARS[gi],gx,CY,1,CH,'rgba(230,238,247,.12)');
  cpush('gcap'+YEARS[gi],gx,Y0+4,4,12,'rgba(230,238,247,.35)');
}
cpush('todayline',X0+__TODAYX__*PX,CY,1,CH,'rgba(111,211,224,.25)');
cpush('tcap',X0+__TODAYX__*PX,Y0+6,5,16,'rgba(111,211,224,.55)');
YEARS.forEach(function(y){
  if(Math.abs((y-1996)-__TODAYX__)<1.2)return;
  cpush('tick'+y,X0+(y-1996)*PX,Y0+GH+24,2,2,'transparent',String(y));
});
cpush('ticktoday',X0+__TODAYX__*PX,Y0+GH+24,2,2,'transparent','Hôm nay',
  {s:{labelFill:'#6fd3e0',labelFontWeight:600}});
D.lanes.forEach(function(cat,li){
  var ly=Y0+__LANEY__[li]*PY;
  cpush('stem'+li,GX0+(GX1-GX0)/2,ly,GX1-GX0,1.4,'rgba(230,238,247,.05)');
  cpush('lab'+li,64,ly-2,2,2,'transparent',cat,{lp:'right',s:{labelFontSize:9.5,labelFill:'#68737f'}});
});
D.nodes.forEach(function(n){
  n.fromY=+n.from.slice(0,4);n.deadY=n.to?+n.to.slice(0,4):9999;
});
function bornN(n){return n.fromY||9999}
function active(n,cur){return bornN(n)<=cur&&deadNo(n)>cur}
function deadNo(n){return n.deadY===undefined?9999:n.deadY}
var GCOLOR={};D.lanes.forEach(function(c){});
D.nodes.forEach(function(n){
  var fam='cat' in n?n.cat:null;
});
var nodesG6=D.nodes.map(function(n){
  var sz=n.ext?13:Math.min(46,12+Math.sqrt(n.chunks||0)*0.9);
  return {id:n.id,data:n,style:{x:n.yx,y:Y0+n.y*PY,size:sz,fill:n.color,
    stroke:'rgba(230,238,247,.35)',lineWidth:n.ext?0.6:1,
    label:true,labelText:n.name,labelPlacement:'bottom',labelFill:'#e6eaf0',
    labelFontSize:10,labelOffsetY:6,
    labelFontFamily:'"Be Vietnam Pro",sans-serif',labelFontWeight:500,
    labelBackground:true,labelBackgroundFill:'rgba(10,13,18,.9)',
    labelBackgroundRadius:6,labelBackgroundPadding:[3,5],
    labelBackgroundStroke:'rgba(230,238,247,.14)',labelBackgroundLineWidth:1,
    labelMaxWidth:96,labelMaxLines:2,labelWordWrap:true}};
});
var edgesG6=D.edges.map(function(e,i){
  var rep=e.rel==='REPLACES';
  return {id:'e'+i,source:e.src,target:e.tgt,data:e,
    type:rep?'line':'quadratic',
    style:{curveOffset:rep?0:-26,stroke:rep?'#d9a441':'#62778c',
      lineWidth:rep?2.4:1.3,lineDash:rep?null:[5,4],strokeOpacity:0.85,
      startArrow:true,startArrowSize:rep?10:8,
      startArrowFill:rep?'#d9a441':'#62778c'}};
});
function g6data(){
  return {nodes:chromeNodes.concat(nodesG6.map(function(n){var d=n.data;return {id:n.id,data:{kind:'law',
    full:d.full,name:d.name,sym:d.sym,ext:d.ext,fy:d.fromY,dy:d.deadY,ch:d.chunks,ci:d.cites,f:d.from,t:d.to,cat:d.cat,color:d.color},
    style:n.style}})),edges:edgesG6};
}
var G6G=null;var G6READY=false;
try{G6G=new G6API.Graph({container:document.getElementById('cy'),
  data:g6data(),theme:'dark',background:'#0a0d12',autoFit:'view',
  padding:[30,60,90,150],
  autoResize:false,
  behaviors:['drag-canvas','zoom-canvas',
    {type:'hover-activate',degree:1,direction:'both',state:'active',
      inactiveState:'inactive',
      enable:function(e){return !!byId[eidOf(e)]}}],
  node:{state:{ghost:{fillOpacity:0.05,strokeOpacity:0.08,labelOpacity:0.06,
      labelBackgroundOpacity:0.03},
    dimmed:{fillOpacity:0.26,strokeOpacity:0.18,labelOpacity:0.45,
      labelBackgroundOpacity:0.2},
    dead:{fillOpacity:0.3}}},
  edge:{state:{ghost:{strokeOpacity:0.06,labelOpacity:0.05},
    dimmed:{strokeOpacity:0.12}}},
  plugins:[
    {type:'grid-line',follow:true,size:40,stroke:'rgba(230,238,247,.04)'},
    {type:'minimap',size:[170,110],position:'right-bottom',
      key:'minimap1'},
    {type:'tooltip',position:'top',getContent:function(e,items){
      var d=items[0].data;
      if(d.kind==='chrome')return '';
      return d.fy!==undefined?fmtTipLaw(d):fmtTipEdge(d);
    },style:{'.tooltip':{background:'#0e1218',color:'#e6eaf0',
      border:'1px solid #242d38','border-radius':'8px',
      'font-family':'"Be Vietnam Pro",sans-serif','font-size':'12px',
      padding:'8px 12px','box-shadow':'0 10px 26px rgba(0,0,0,.5)',
      'pointer-events':'none'}}}
  ]});
G6READY=true;
}catch(e){window.__errs.push('G6-INIT: '+(e.message||String(e)))}
function fmtTipLaw(d){
  var act=d.fy<=state.cur&&d.dy>state.cur;
  var h='<b>'+d.full+'</b>';
  if(d.sym&&d.sym!==d.name)h+='<div class="sub">Số hiệu: '+d.sym+'</div>';
  h+='<div class="sub">Hiệu lực: '+d.f+' → '+d.t+'</div>';
  h+='<div class="sub">'+(act?'<span class="live">Đang hiệu lực tại '+state.cur+'</span>':'<span class="dead">Ngoài hiệu lực tại '+state.cur+'</span>')+'</div>';
  if(d.ch)h+='<div class="sub">'+d.ch+' chunk · '+d.ci+' dẫn chiếu nội bộ</div>';
  h+='<div class="sub" style="color:#7d8894">Nhấp để mở khung chi tiết</div>';
  return h;
}
function fmtTipEdge(d){
  return '<span class="edgehead">'+D.relvie[d.rel]+'</span><div class="sub">'+dt(d.at)+' · '+d.sname+' → '+d.tname+'</div><div class="sub">'+(d.note||'')+'</div>';
}
function eidOf(e){
  try{var t=e.target;
    if(t===undefined||t===null)return '';
    if(typeof t==='string')return t;
    if(typeof t.getId==='function')return t.getId();
    return t.id||'';}catch(_){return ''}
}
function renderCy(){applyTimeState()}
function applyTimeState(){
  if(!G6READY)return;
  if(!window.__renderDone){state.pending=true;return}
  var nx={},ex=[];
  D.nodes.forEach(function(n){
    var v=state.lane[n.cat]&&(!n.ext||state.ext)&&n.x<=state.cur-1996;
    var st=[];
    if(!v)st.push('ghost');
    else if(deadNo(n)<=state.cur)st.push('dimmed');
    nx[n.id]=st;});
  D.edges.forEach(function(e,i){
    var a=byId[e.src],b=byId[e.tgt];
    var kindOk=e.rel==='REPLACES'?state.rep:state.amd;
    var v=kindOk&&bornN(a)<=state.cur&&bornN(b)<=state.cur
      &&state.lane[a.cat]&&(!a.ext||state.ext)&&state.lane[b.cat]&&(!b.ext||state.ext)
      &&a.x<=state.cur-1996&&b.x<=state.cur-1996;
    if(!v)ex.push('e'+i);
    else if(+e.at.slice(0,4)>state.cur)ex.push('e'+i);});
  try{
    D.nodes.forEach(function(n){G6G.setElementState(n.id,nx[n.id])});
    edgesG6.forEach(function(ed,i){G6G.setElementState(ed.id,ex.indexOf(ed.id)>=0?['ghost']:[])});
  }catch(e){window.__errs.push('STATE: '+(e.message||String(e)))}
  var on=onList();document.getElementById('ncur').textContent=on.length;
}
function onList(){return D.nodes.filter(function(n){
  var v=state.lane[n.cat]&&(!n.ext||state.ext)&&n.x<=state.cur-1996;
  return v&&!n.ext&&bornN(n)<=state.cur&&deadNo(n)>state.cur
    &&(!state.focus||n.id===state.focus||(adj[state.focus]||[]).indexOf(n.id)>=0);});}
G6G.on('node:click',function(e){
  var id=eidOf(e);if(!byId[id])return;
  state.focus=id;document.getElementById('search').value=byId[id].name;
  openDrawer(byId[id]);});
G6G.on('edge:click',function(e){
  var id=eidOf(e);var ed=G6G.getEdgeData(id);var d=ed?ed.data:null;
  if(!d)return;state.focus=d.src;
  document.getElementById('search').value=byId[d.src].name;
  openDrawer(byId[d.src]);});
function g6fix(){if(!G6READY)return;try{
  var vw=document.getElementById('viewwrap');
  G6G.resize(vw.clientWidth,560);G6G.render();
}catch(e){}}
function openDrawer(n){
  const r=document.getElementById('drawer');r.classList.add('open');
  let h='<button id="dclose" title="Đóng">✕</button>';
  h+='<div class="dname">'+n.full+'</div>';
  h+='<div class="dlane"><i style="background:'+n.color+'"></i>'+n.cat+'</div>';
  h+='<div class="drow"><span>Số hiệu văn bản</span><span>'+(n.sym||'—')+'</span></div>';
  h+='<div class="drow"><span>Hiệu lực</span><span>'+dt(n.from)+' → '+(n.to?dt(n.to):'nay')+'</span></div>';
  h+='<div class="drow"><span>Trạng thái</span><span>'+n.status+'</span></div>';
  if(n.chunks)h+='<div class="drow"><span>Chunk · dẫn chiếu</span><span>'+n.chunks.toLocaleString('vi-VN')+' · '+n.cites+'</span></div>';
  const rels=D.edges.filter(e=>e.src===n.id||e.tgt===n.id);
  if(rels.length){h+='<div class="dsec">Liên hệ succession ('+rels.length+')</div>';
    rels.forEach(function(e){
      const other=e.src===n.id?e.tname:e.sname;
      const oid=e.src===n.id?e.tgt:e.src;
      const col=byId[oid]?byId[oid].color:'#7f8c8d';
      h+='<div class="relrow" data-go="'+oid+'"><span class="rdot" style="background:'+col+'"></span>'+
         '<span class="rlab"><span class="reltag '+e.rel+'">'+D.relvie[e.rel]+'</span> '+other+'</span>'+
         '<span class="rdate">'+dt(e.at)+'</span></div>';
    });}
  const arts=ARTS[n.id]||[];
  if(arts.length){
    h+='<div class="dsec">Điều khoản ('+arts.length+' đoạn)</div>';
    h+='<input id="artq" class="artq" placeholder="Tìm điều — ví dụ: 27" autocomplete="off">';
    h+='<div id="artlist" class="artlist"></div>';
  }
  h+='<div class="dnote">'+(n.ext?'Văn bản sửa đổi bên ngoài — không đóng góp chunk vào corpus, giữ để minh họa dòng sửa đổi.':'Dữ liệu mở chunk thuộc pháp điển ViCivil-TKG; dẫn chiếu nội bộ đếm từ provenance/cite_edges.json.')+'</div>';
  const b=document.getElementById('dbody');b.innerHTML=h;
  document.getElementById('dclose').onclick=function(){closeDrawer()};
  setTimeout(g6fix,260);
  if(arts.length){
    const list=document.getElementById('artlist'),q=document.getElementById('artq');
    const draw=function(){
      const s=(q.value||'').trim().toLowerCase();
      let rows=arts;
      if(s)rows=arts.filter(function(r){return r[0].toLowerCase().indexOf(s)>=0});
      const top=rows.slice(0,40);
      let out='<div class="arthead">'+rows.length+' kết quả'+(s?' cho “'+q.value+'”':'')+'</div>';
      top.forEach(function(r){
        out+='<div class="artrow"><span class="aname">'+r[0].replace(/^Dieu/,'Điều ').replace(/\|/g,' · ')+'</span>'+
             '<span class="acnt">'+r[1]+' đoạn</span>'+
             (r[2]?'<span class="acit">được trỏ '+r[2]+'</span>':'')+'</div>';
      });
      if(rows.length>40)out+='<div class="arthead">… và '+(rows.length-40)+' kết quả nữa</div>';
      list.innerHTML=out;
    };
    q.addEventListener('input',draw);
    draw();
  }
  b.querySelectorAll('.relrow').forEach(function(row){
    row.addEventListener('click',function(){const id=this.getAttribute('data-go');state.focus=id;
      document.getElementById('search').value=byId[id].name;openDrawer(byId[id]);renderCy();});
  });
}
function closeDrawer(){document.getElementById('drawer').classList.remove('open');
  state.focus=null;renderCy();setTimeout(g6fix,260)}
document.addEventListener('keydown',function(e){if(e.key==='Escape')closeDrawer()});
// ---- Controls ----
function stopPlay(){if(state.timer){clearInterval(state.timer);state.timer=null;
  document.getElementById('play').textContent='▶ Chạy dòng thời gian'}}
function setYear(y,fromSlider){stopPlay();
  state.cur=y;document.getElementById('yearbig').textContent=y;
  if(!fromSlider)document.getElementById('slider').value=y;renderCy()}
document.getElementById('slider').addEventListener('input',function(e){setYear(+e.target.value,true)});
document.getElementById('play').addEventListener('click',function(){
  if(state.timer){stopPlay();return}
  let y=D.yearMin-1;this.textContent='⏸ Tạm dừng';
  state.timer=setInterval(function(){y++;if(y>D.yearMax){stopPlay();return}setYear(y)},state.speed);
});
document.getElementById('speed').addEventListener('change',function(e){
  state.speed=+e.target.value;if(state.timer){stopPlay();
  document.getElementById('play').click()}});
const TGL={};
const EDGETIPS={ext:'Văn bản sửa đổi từ ngoài nhóm luật dân sự (không mang chunk)',
  rep:'Cạnh kế thừa REPLACES — luật mới thay luật cũ', amd:'Cạnh AMENDS — sửa đổi điều khoản cụ thể'};
const laneBar=document.getElementById('lanebar');
function mksep(){const s=document.createElement('span');s.className='grp';return s}
function mkedge(k,label,sym){
  const el0=document.createElement('span');el0.className='tg on';el0.setAttribute('data-k',k);
  el0.setAttribute('title',EDGETIPS[k]);
  el0.innerHTML='<span class="sym">'+sym+'</span>'+label;
  el0.addEventListener('click',function(){
    const k=this.getAttribute('data-k');TGL[k]=!TGL[k];this.classList.toggle('on',TGL[k]);
    this.classList.toggle('off',!TGL[k]);
    state.ext=TGL.ext;state.amd=TGL.amd;state.rep=TGL.rep;renderCy();
  });
  return el0;
}
D.lanes.forEach(function(cat){
  const dot=D.nodes.find(n=>n.cat===cat).color;
  const chip=document.createElement('span');
  chip.className='lchip on';chip.setAttribute('data-cat',cat);
  chip.innerHTML='<i style="background:'+dot+'"></i>'+cat;
  chip.title=cat+' — click để ẩn/hiện nhóm luật';
  chip.addEventListener('click',function(){
    state.lane[cat]=!state.lane[cat];
    this.classList.toggle('off',!state.lane[cat]);renderCy();
  });
  laneBar.appendChild(chip);
});
laneBar.appendChild(mksep());
TGL.ext=TGL.rep=TGL.amd=true;
laneBar.appendChild(mkedge('ext','Sửa đổi bên ngoài','◇'));
laneBar.appendChild(mkedge('rep','Kế thừa','━━'));
laneBar.appendChild(mkedge('amd','Sửa đổi','┄┄'));
const dl=document.getElementById('laws');
D.nodes.slice().sort((a,b)=>a.name.localeCompare(b.name,'vi')).forEach(function(n){
  const o=document.createElement('option');o.value=n.name;dl.appendChild(o)});
document.getElementById('search').addEventListener('change',function(e){
  const q=e.target.value.trim().toLowerCase();
  const n=D.nodes.find(x=>x.name.toLowerCase()===q)||D.nodes.find(x=>x.name.toLowerCase().indexOf(q)>=0);
  if(n){state.focus=n.id;openDrawer(n);renderCy();
    try{G6G.focusElement(n.id)}catch(e){}}
  else closeDrawer();
});
function g6PNG(cb){
  var pick=function(v){return (v&&v.dataURL)||v||''};
  try{var r=G6G.toDataURL({mode:'overall',type:'image/png'});
    if(r&&r.then){r.then(function(o){cb(pick(o))}).catch(function(){cb('')})}
    else cb(pick(r));
  }catch(e){try{var r2=G6G.toDataURL({mode:'overall',type:'image/png'});
    if(r2&&r2.then){r2.then(function(o){cb(pick(o))}).catch(function(){cb('')})}
    else cb(pick(r2));
  }catch(e2){cb('')}}
};
document.getElementById('shot').addEventListener('click',function(){
  g6PNG(function(url){
    if(!url)return;
    var a=document.createElement('a');
    a.download='vicivil-tkg-'+document.getElementById('yearbig').textContent+'.png';
    a.href=url;a.click();
  });
});
// ---- Tabs ----
const elCy=document.getElementById('cy'),elTl=document.getElementById('tl');
window.addEventListener('resize',function(){
  clearTimeout(window.__rsz);window.__rsz=setTimeout(g6fix,120);
});
document.getElementById('tab-cy').addEventListener('click',function(){
  elTl.style.display='none';
  this.classList.add('active');document.getElementById('tab-vl').classList.remove('active');
  setTimeout(g6fix,60);
});
document.getElementById('tab-vl').addEventListener('click',function(){
  elTl.style.display='flex';
  this.classList.add('active');document.getElementById('tab-cy').classList.remove('active');
  if(!elTl.dataset.done){
    vegaEmbed('#tl',D.vl,{actions:false,renderer:'canvas'});
    elTl.dataset.done='1';
  }
});
/* G6 5.x official async flow: graph.render() resolves once the first frame
   is drawn; every element-state update goes after that promise. Nothing
   custom, no timers, no extra UI. */
(function(){
  try{
    var p=G6G.render();
    if(p&&p.then){p.then(function(){
      window.__renderDone=true;
      if(state.pending){state.pending=false;renderCy()}
    },function(err){
      var t='graph.render(): '+((err&&(err.message||String(err)))||'unknown');
      window.__errs.push(t);console.error('[viewer]',t);
    })}
    else{window.__renderDone=true}
  }catch(e){
    var t='graph.render(): '+(e.message||String(e));
    window.__errs.push(t);console.error('[viewer]',t);
  }
})();
</script></body></html>"""

TXTFIRST = 1996 + 5 * max(0, (min(n["x"] for n in nodes) + 1995 - 1996) // 5 + 1)
TXTLAST = 1996 + 5 * ((max(n["x"] for n in nodes) + 1996 - 1996) // 5)
html = HTML.replace("__DATA__", PAYLOAD).replace("__ARTS__", ARTS_JSON).replace(
    "__TODAYX__", str(round(TODAY_Y - 1996 + TODAY_D / 365, 3))).replace(
    "__TICKLK__", str(TICK_LK)).replace("__LANEY__", json.dumps(lane_lab_y)).replace(
    "__TXTFIRST__", str(TXTFIRST)).replace("__TXTLAST__", str(TXTLAST)).replace(
    "__NCUR__", str(INIT_CNT)).replace(
    "__LIBG6__", LIBG6).replace("__LIBVEGA__", LIBVEGA).replace(
    "__LIBVEGALITE__", LIBVL).replace("__LIBEMBED__", LIBEMBED)
p = os.path.join(OUT, "explorer.html")
open(p, "w", encoding="utf-8").write(html)
bad = [s for s in ("__DATA__", "__ARTS__", "__TICKLK__", "__LANEY__", "__TXTFIRST__", "__TXTLAST__", "__TODAYX__", "__NCUR__", "__LIBG6__", "__LIBVEGA__", "__LIBVEGALITE__", "__LIBEMBED__") if s in html]
print("explorer.html:", os.path.getsize(p), "bytes | nodes", len(nodes), "| edges", len(edge_items),
      "| chunks", chunks_total, "| vl.json rows", len(rownum), "| placeholders left:", bad or "none")
