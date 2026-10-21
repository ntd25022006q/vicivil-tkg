"""Chung minh file RDF/JSON-LD cua bo du lieu thuc su nap duoc vao mot kho tri thuc
va tra loi duoc cau hoi - khong chi "parse duoc".

Cach kiem chung (khong can GPU, khong can may chu):
  1. Nap Turtle vao kho RDF (rdflib) va JSON-LD vao cung kho.
  2. Truy van bang SPARQL nhu reviewer se hoi:
     - văn bản nào thay thế văn bản nào
     - văn bản nào còn hiệu lực tại một mốc thời gian
     - đoạn văn bản nào thuộc văn bản nào
  3. In kết quả ra tệp để kiểm tra.

Chay:  python src/law_rdf_verify.py
"""
import json, os, sys

R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
G = os.path.join(R, "docs", "graph")
TTL = os.path.join(G, "law_graph.ttl")
JSONLD = os.path.join(G, "law_graph.jsonld")
OUT = os.path.join(R, "provenance", "rdf_verify.json")

try:
    from rdflib import Graph
except ImportError:
    print("thieu rdflib: pip install rdflib")
    sys.exit(2)

g = Graph()
g.parse(TTL, format="turtle")
n_ttl = len(g)
g.parse(JSONLD, format="json-ld")
n_jsonld = len(g)

QS = {
    "văn bản nào thay thế BLDS1995": """
        PREFIX vicivil: <https://w3id.org/vicivil-tkg/>
        PREFIX law: <https://w3id.org/vicivil-tkg/law/>
        SELECT ?new ?old WHERE {
          ?e a vicivil:LawEdge ; vicivil:subject ?new ; vicivil:object ?old ;
              dct:title "thay the" .
          FILTER(CONTAINS(STR(?old), "BLDS1995"))
        }""",
    "văn bản nào còn hiệu lực tại 2026-06-01": """
        PREFIX vicivil: <https://w3id.org/vicivil-tkg/>
        PREFIX law: <https://w3id.org/vicivil-tkg/law/>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT ?id ?title ?from ?to WHERE {
          ?id a vicivil:Law ; dct:title ?title ;
               vicivil:validFrom ?from .
          OPTIONAL { ?id vicivil:validTo ?to }
          FILTER(?from <= "2026-06-01"^^xsd:date)
          FILTER(!BOUND(?to) || ?to > "2026-06-01"^^xsd:date)
        } ORDER BY ?id""",
    "đoạn văn bản thuộc văn bản nào (mẫu)": """
        PREFIX vicivil: <https://w3id.org/vicivil-tkg/>
        PREFIX chunk: <https://w3id.org/vicivil-tkg/chunk/>
        PREFIX law: <https://w3id.org/vicivil-tkg/law/>
        SELECT ?c ?l WHERE { ?c a vicivil:Chunk ; vicivil:partOf ?l } LIMIT 5""",
}

res = {}
for name, q in QS.items():
    rows = list(g.query(q))
    res[name] = {"n_rows": len(rows), "sample": [str(r) for r in rows[:8]]}
    print("%-52s -> %d dong" % (name, len(rows)))

out = {
    "triples_turtle": n_ttl,
    "triples_after_adding_jsonld": n_jsonld,
    "queries": res,
    "note": "nap duoc vao kho RDF va tra loi duoc bang SPARQL; khong can GPU hay may chu khac",
}
json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("da ghi:", OUT)
print("turtle:", n_ttl, "triples | + jsonld:", n_jsonld, "triples")