"""Civil KG index builder: chunks + extraction + temporal -> 8-file ADGR-style index.
Entity key = normalized name (cross-law merge; node validity = union of chunk dates).
Deterministic refs become DAN_CHIEU chunk->chunk edges. Embeddings via ollama.
Output: law_data/ (8 files) + runs/law_index_stats.json
"""
import json, os, re, time, base64, hashlib, unicodedata, urllib.request
import numpy as np

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
OUT = f"{W}/law_data"
os.makedirs(OUT, exist_ok=True)
SEP = "<|#|>"


def nfc(s):
    return unicodedata.normalize("NFC", s or "")


def nkey(s):
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s).strip().lower())


def h(pre, s):
    return pre + hashlib.md5(s.encode("utf-8")).hexdigest()


G = json.load(open(f"{R}/temporal_graph.json", encoding="utf-8"))
LAWMAP = {L["law_id"]: L for L in G["laws"]}
chunks = [json.loads(L) for L in open(f"{R}/civil_chunks.jsonl", encoding="utf-8")]
ext = json.load(open(f"{R}/civil_extract.json", encoding="utf-8"))
cmap = {c["chunk_id"]: c for c in chunks}

ent_name, ent_desc, ent_type, ent_ch, ent_law = {}, {}, {}, {}, {}
rel_rows = []
n_bad = 0
for cid, row in ext.items():
    c = cmap.get(cid)
    if not c:
        continue
    law = c["law_id"]
    for line in row.get("ents", []):
        p = line.split(SEP)
        if len(p) != 4 or not p[1].strip():
            n_bad += 1
            continue
        nm, ty, ds = nfc(p[1]).strip(), p[2].strip(), nfc(p[3]).strip()
        key = nkey(nm)
        if not key:
            n_bad += 1
            continue
        if key not in ent_name:
            ent_name[key] = nm[:120]
            ent_desc[key] = []
            ent_type[key] = ty
            ent_ch[key] = set()
            ent_law[key] = set()
        if ds and len(ent_desc[key]) < 6:
            ent_desc[key].append(ds)
        ent_ch[key].add(cid)
        ent_law[key].add(law)
    for line in row.get("rels", []):
        p = line.split(SEP)
        if len(p) != 5 or not p[1].strip() or not p[2].strip():
            n_bad += 1
            continue
        ks, kt = nkey(p[1]), nkey(p[2])
        if not ks or not kt or ks == kt:
            n_bad += 1
            continue
        if ks not in ent_name or kt not in ent_name:
            n_bad += 1
            continue
        rel_rows.append({"s": ks, "t": kt, "kw": nfc(p[3]).strip() or "lien quan",
                         "ds": nfc(p[4]).strip(), "ch": cid, "law": law})
    for ref in row.get("refs", []):
        rel_rows.append({"s": "__CHUNK__" + cid, "t": "__CHUNK__" + ref,
                         "kw": "dan chieu", "ds": "dan chieu den " + ref,
                         "ch": cid, "law": law})

ent_keys = sorted(ent_name)
print(f"entities={len(ent_keys)} rels={len(rel_rows)} bad={n_bad}", flush=True)

_cache_p = f"{R}/law_emb_cache.npy"
_txt_p = f"{R}/law_emb_texts.json"
if os.path.exists(_cache_p) and os.path.exists(_txt_p):
    cache_txt = json.load(open(_txt_p, encoding="utf-8"))
    import numpy as _np
    cache_m = _np.load(_cache_p)
    print("emb cache:", cache_m.shape, flush=True)
else:
    cache_txt, cache_m = [], np.zeros((0, 768), dtype=np.float32)


def embed_all(texts, tag):
    global cache_txt, cache_m
    todo = [t for t in texts if t not in set(cache_txt)]
    if todo:
        for i in range(0, len(todo), 64):
            batch = todo[i:i + 64]
            for _ in range(3):
                try:
                    req = urllib.request.Request(
                        "http://127.0.0.1:11434/api/embed",
                        data=json.dumps({"model": "embeddinggemma:300m",
                                         "input": batch}).encode(),
                        headers={"Content-Type": "application/json"})
                    with urllib.request.urlopen(req, timeout=600) as r:
                        v = np.asarray(json.load(r)["embeddings"], dtype=np.float32)
                    v = v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-9)
                    cache_txt.extend(batch)
                    cache_m = np.vstack([cache_m, v]) if len(cache_m) else v
                    np.save(_cache_p, cache_m)
                    json.dump(cache_txt, open(_txt_p, "w", encoding="utf-8"),
                              ensure_ascii=False)
                    break
                except Exception:
                    time.sleep(5)
            if (i // 64) % 50 == 0:
                print(f"  {tag} {i}/{len(todo)}", flush=True)
    pos = {t: i for i, t in enumerate(cache_txt)}
    return np.asarray([cache_m[pos[t]] for t in texts], dtype=np.float32)


names = [ent_name[k] for k in ent_keys]
ent_content = [f"{ent_name[k]}\n{ent_type[k]}\n" + " ".join(ent_desc[k])[:1200]
               for k in ent_keys]
rel_content, rel_data, rel_ch = [], [], {}
for i, r in enumerate(rel_rows):
    sn = r["s"] if not r["s"].startswith("__CHUNK__") else r["s"][9:]
    tn = r["t"] if not r["t"].startswith("__CHUNK__") else r["t"][9:]
    body = f"{r['kw']}\t{ent_name.get(r['s'], sn)}\n{ent_name.get(r['t'], tn)}\n{r['ds']}"[:1200]
    rel_content.append(body)
    rk = f"rel-{i}"
    rel_data.append({"__id__": h("rel-", rk + sn + tn),
                     "src_id": ent_name.get(r["s"], sn),
                     "tgt_id": ent_name.get(r["t"], tn), "content": body,
                     "source_id": r["ch"], "law_id": r["law"]})
    rel_ch.setdefault(rk, set()).add(r["ch"])
chunk_content = [c["content"][:3000] for c in chunks]

print("embed...", flush=True)
N = embed_all(names, "names")
E = embed_all(ent_content, "ents")
R_ = embed_all(rel_content, "rels")
C = embed_all(chunk_content, "chunks")
print("matrices", N.shape, E.shape, R_.shape, C.shape, flush=True)


def pack(mat, data):
    return {"embedding_dim": 768, "data": data,
            "matrix": base64.b64encode(np.ascontiguousarray(mat, dtype=np.float32).tobytes()).decode()}


cid = [c["chunk_id"] for c in chunks]
ent_data = [{"__id__": h("ent-", k), "entity_name": ent_name[k],
             "content": ent_content[i], "chunk_ids": sorted(ent_ch[k]),
             "law_ids": sorted(ent_law[k])} for i, k in enumerate(ent_keys)]
json.dump(pack(E, ent_data), open(f"{OUT}/vdb_entities.json", "w"), ensure_ascii=False)
json.dump(pack(R_, rel_data), open(f"{OUT}/vdb_relationships.json", "w"), ensure_ascii=False)
json.dump(pack(C, [{"__id__": c["chunk_id"], "content": chunk_content[i],
                   "url": c["law_id"]} for i, c in enumerate(chunks)]),
          open(f"{OUT}/vdb_chunks.json", "w"), ensure_ascii=False)
json.dump(names, open(f"{OUT}/name_list.json", "w"), ensure_ascii=False)
np.save(f"{OUT}/name_matrix_normed.npy", N)
json.dump({ent_name[k]: {"chunk_ids": sorted(ent_ch[k])} for k in ent_keys},
          open(f"{OUT}/kv_store_entity_chunks.json", "w"), ensure_ascii=False)
json.dump({rel_data[i]["__id__"]: {"chunk_ids": sorted(rel_ch[f"rel-{i}"])}
           for i in range(len(rel_data))},
          open(f"{OUT}/kv_store_relation_chunks.json", "w"), ensure_ascii=False)
json.dump({c["chunk_id"]: {"law_id": c["law_id"], "content": chunk_content[i]}
           for i, c in enumerate(chunks)},
          open(f"{OUT}/kv_store_text_chunks.json", "w"), ensure_ascii=False)
json.dump({"n_ent": len(ent_data), "n_rel": len(rel_data), "n_chunk": len(chunks)},
          open(f"{R}/law_index_stats.json", "w"), indent=2)
print("INDEX OK", len(ent_data), len(rel_data), len(chunks), flush=True)
