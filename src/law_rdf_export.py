"""Xuat do thi tri thuc ra dinh dang RDF/JSON-LD (W3C).

Khong can GPU, khong can mang nghien cuu: doc truc tiep tu cac tep da
cong bo trong kho va ghi ra:
  docs/graph/law_graph.ttl      -- Turtle, nap duoc boi rdflib / rapper
  docs/graph/law_graph.jsonld   -- JSON-LD, nap duoc boi neo4j / blazegraph

Cau truc:
  :Law        -- văn bản luật        (node)
  :Chunk      -- đoạn văn bản        (node)
  :LawEdge    -- quan hệ giữa luật   (node, mang nhãn quan hệ)
  :ChunkEdge  -- quan hệ dẫn chiếu   (node, mang nhãn quan hệ)
  :inForce    -- quan hệ luật -> chunk (đoạn thuộc văn bản)
  :validFrom / :validTo            -- khoảng hiệu lực
"""
import io, json, os, datetime

R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(R, "docs", "graph")
GEN = "2026-10-28"  # release date; fixed so CI regeneration is byte-identical

# ---------------------------------------------------------------- input
tg = json.load(io.open(os.path.join(R, "provenance", "temporal_graph.json"), encoding="utf-8"))
laws = tg["laws"]
edges = tg["succession"]

# tên luật có dấu lấy từ payload của trang xem (đã đúng dấu)
built = io.open(os.path.join(R, "docs", "graph", "explorer.html"), encoding="utf-8").read()
i = built.find('{"nodes"')
payload = json.loads(built[i:].split("\n", 1)[0].rsplit(";", 1)[0].split("const D=", 1)[-1])
DISPLAY = {n["id"]: n["name"] for n in payload["nodes"] if n.get("cat")}
SYMBOL = {n["id"]: (n.get("sym") or "") for n in payload["nodes"] if n.get("cat")}

# chunk theo luật
chunk_of = {}
chunk_titles = {}
with io.open(os.path.join(R, "data", "civil_chunks.jsonl"), encoding="utf-8") as f:
    for line in f:
        c = json.loads(line)
        chunk_of.setdefault(c["law_id"], []).append(c["chunk_id"])
        chunk_titles[c["chunk_id"]] = c.get("tieu_de", "")

REL_LABEL = {"REPLACES": "thay the", "AMENDS": "sua doi", "CONSOLIDATES": "hop nhat"}
REL_SAMEAS = {"REPLACES": "vicivil:replaces", "AMENDS": "vicivil:amends",
              "CONSOLIDATES": "vicivil:consolidates"}

def esc(s):
    return (str(s).replace("\\", "\\\\").replace('"', '\\"')
            .replace("\n", " ").replace("\r", " ").replace("\t", " "))

def slug(s):
    keep = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
    return "".join(c if c in keep else "_" for c in str(s))

# ---------------------------------------------------------------- turtle
L = []
L.append("# ViCivil-TKG - do thi tri thuc theo dinh dang RDF (Turtle)")
L.append("# Sinh tu cac tep da cong bo trong kho; khong can GPU.")
L.append("@prefix vicivil: <https://w3id.org/vicivil-tkg/> .")
L.append("@prefix law:    <https://w3id.org/vicivil-tkg/law/> .")
L.append("@prefix chunk:  <https://w3id.org/vicivil-tkg/chunk/> .")
L.append("@prefix dct:    <http://purl.org/dc/terms/> .")
L.append("@prefix xsd:    <http://www.w3.org/2001/XMLSchema#> .")
L.append("@prefix rdfs:   <http://www.w3.org/2000/01/rdf-schema#> .")
L.append("@prefix rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .")
L.append("")
L.append("vicivil:dataset a vicivil:Dataset ;")
L.append('    dct:title "Khung tri thuc thoi gian cua luat dan su Viet Nam" ;')
L.append('    dct:created "%s" ;' % GEN)
L.append('    dct:license <https://creativecommons.org/licenses/by/4.0/> .')
L.append("")

for lw in laws:
    lid = lw["law_id"]
    name = DISPLAY.get(lid, lw.get("ten", lid))
    sym = SYMBOL.get(lid, lw.get("so_hieu", ""))
    L.append("law:%s a vicivil:Law ;" % slug(lid))
    L.append('    dct:identifier "%s" ;' % esc(lid))
    L.append('    dct:title "%s" ;' % esc(name))
    if sym:
        L.append('    vicivil:soHieu "%s" ;' % esc(sym))
    if lw.get("valid_from"):
        L.append('    vicivil:validFrom "%s"^^xsd:date ;' % lw["valid_from"])
    if lw.get("valid_to"):
        L.append('    vicivil:validTo "%s"^^xsd:date ;' % lw["valid_to"])
    L.append('    vicivil:status "%s" ;' % esc(lw.get("status", "")))
    L.append('    vicivil:chunkCount %d ;' % len(chunk_of.get(lid, [])))
    succ = ["law:%s" % slug(e["tgt"]) for e in edges if e["src"] == lid]
    if succ:
        L.append('    vicivil:successorOf %s ;' % ", ".join(succ))
    cids = chunk_of.get(lid, [])
    if cids:
        L.append('    vicivil:containsChunk %s ;' % ", ".join("chunk:%s" % slug(c) for c in cids))
    L.append("    vicivil:nodeType \"law\" .")
    L.append("")

# quan hệ giữa các luật
for e in edges:
    rid = slug(e["src"] + "-" + e["tgt"] + "-" + e.get("relation", "REL"))
    L.append("law:%s a vicivil:LawEdge ;" % rid)
    L.append('    dct:title "%s" ;' % esc(REL_LABEL.get(e.get("relation"), e.get("relation", ""))))
    L.append("    vicivil:subject law:%s ;" % slug(e["src"]))
    L.append("    vicivil:object law:%s ;" % slug(e["tgt"]))
    if e.get("at"):
        L.append('    vicivil:date "%s"^^xsd:date ;' % e["at"])
    if e.get("note"):
        L.append('    rdfs:comment "%s" ;' % esc(e["note"]))
    L.append("    rdf:type %s ." % REL_SAMEAS.get(e.get("relation"), "vicivil:relatedTo"))
    L.append("")

# node chunk: để đồ thị RDF có đủ đoạn văn bản, không chỉ luật
for lid, cids in chunk_of.items():
    for cid in cids:
        L.append("chunk:%s a vicivil:Chunk ;" % slug(cid))
        L.append('    dct:identifier "%s" ;' % esc(cid))
        t = chunk_titles.get(cid, "")
        if t:
            L.append('    dct:title "%s" ;' % esc(t))
        L.append("    vicivil:partOf law:%s ." % slug(lid))
        L.append("")

io.open(os.path.join(OUT, "law_graph.ttl"), "w", encoding="utf-8", newline="\n").write("\n".join(L))

# ---------------------------------------------------------------- json-ld
def jnode(lw):
    lid = lw["law_id"]
    d = {
        "@id": "law:%s" % slug(lid),
        "@type": "vicivil:Law",
        "dct:identifier": lid,
        "dct:title": DISPLAY.get(lid, lw.get("ten", lid)),
        "vicivil:status": lw.get("status", ""),
        "vicivil:chunkCount": len(chunk_of.get(lid, [])),
        "vicivil:validFrom": lw.get("valid_from"),
        "vicivil:validTo": lw.get("valid_to"),
        "vicivil:soHieu": SYMBOL.get(lid, lw.get("so_hieu", "")),
        "vicivil:successorOf": ["law:%s" % slug(e["tgt"]) for e in edges if e["src"] == lid],
        "vicivil:containsChunk": ["chunk:%s" % slug(c) for c in chunk_of.get(lid, [])],
    }
    return {k: v for k, v in d.items() if v not in (None, "", [])}

doc = {
    "@context": {
        "vicivil": "https://w3id.org/vicivil-tkg/",
        "law": "https://w3id.org/vicivil-tkg/law/",
        "chunk": "https://w3id.org/vicivil-tkg/chunk/",
        "dct": "http://purl.org/dc/terms/",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "dct:identifier": {"@id": "dct:identifier", "@type": "xsd:string"},
        "dct:title": {"@id": "dct:title", "@type": "xsd:string"},
        "dct:created": {"@id": "dct:created", "@type": "xsd:date"},
        "dct:license": {"@id": "dct:license", "@type": "@id"},
        "vicivil:validFrom": {"@id": "vicivil:validFrom", "@type": "xsd:date"},
        "vicivil:validTo": {"@id": "vicivil:validTo", "@type": "xsd:date"},
        "vicivil:soHieu": {"@id": "vicivil:soHieu", "@type": "xsd:string"},
        "vicivil:status": {"@id": "vicivil:status", "@type": "xsd:string"},
        "vicivil:chunkCount": {"@id": "vicivil:chunkCount", "@type": "xsd:integer"},
        "vicivil:successorOf": {"@id": "vicivil:successorOf", "@type": "@id"},
        "vicivil:containsChunk": {"@id": "vicivil:containsChunk", "@type": "@id"},
        "vicivil:subject": {"@id": "vicivil:subject", "@type": "@id"},
        "vicivil:object": {"@id": "vicivil:object", "@type": "@id"},
        "vicivil:date": {"@id": "vicivil:date", "@type": "xsd:date"},
        "vicivil:chunk": {"@id": "vicivil:chunk", "@type": "@id"},
        "rdfs:comment": {"@id": "rdfs:comment", "@type": "xsd:string"},
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    },
    "@id": "vicivil:dataset",
    "@type": "vicivil:Dataset",
    "dct:title": "Khung tri thuc thoi gian cua luat dan su Viet Nam",
    "dct:created": GEN,
    "dct:license": "https://creativecommons.org/licenses/by/4.0/",
    "vicivil:graph": [jnode(lw) for lw in laws],
    "vicivil:relation": [
        {
            "@id": "law:%s" % slug(e["src"] + "-" + e["tgt"] + "-" + e.get("relation", "REL")),
            "@type": "vicivil:LawEdge",
            "dct:title": REL_LABEL.get(e.get("relation"), e.get("relation", "")),
            "vicivil:subject": "law:%s" % slug(e["src"]),
            "vicivil:object": "law:%s" % slug(e["tgt"]),
            "vicivil:date": e.get("at"),
            "rdfs:comment": e.get("note", ""),
        } for e in edges
    ],
}
io.open(os.path.join(OUT, "law_graph.jsonld"), "w", encoding="utf-8", newline="\n").write(
    json.dumps(doc, ensure_ascii=False, indent=1))

print("TTL   :", os.path.getsize(os.path.join(OUT, "law_graph.ttl")), "bytes |",
      len(laws), "luat |", len(edges), "quan he")
print("JSON-LD:", os.path.getsize(os.path.join(OUT, "law_graph.jsonld")), "bytes")
print("so chunk lien kiet:", sum(len(v) for v in chunk_of.values()))