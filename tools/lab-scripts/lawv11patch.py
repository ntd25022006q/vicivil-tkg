"""Patch v1.1: re-embed 1203 cleaned chunks into vdb_chunks.json (rows+contents).
Background job with checkpoints. Output: runs/vdb_patch.log
"""
import base64, io, json, sys, time, urllib.request
import numpy as np
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
D = f"{W}/law_data"
chunks = [json.loads(L) for L in open(f"{R}/civil_chunks.jsonl", encoding="utf-8")]
txt = {r["chunk_id"]: r["content"] for r in chunks if r.get("cleaned_v11")}
print("to patch:", len(txt), flush=True)
vdb = json.load(open(f"{D}/vdb_chunks.json", encoding="utf-8"))
mat = np.frombuffer(base64.b64decode(vdb["matrix"]), dtype=np.float32).reshape(-1, 768).copy()
pos = {c["__id__"]: i for i, c in enumerate(vdb["data"])}
assert len(pos) == mat.shape[0], (len(pos), mat.shape)
print("matrix rows:", mat.shape, flush=True)


def embed_batch(texts):
    body = {"model": "embeddinggemma:300m", "input": texts}
    for _ in range(3):
        try:
            req = urllib.request.Request("http://127.0.0.1:11434/api/embed",
                                         data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=600) as r:
                return np.asarray(json.load(r)["embeddings"], dtype=np.float32)
        except Exception as e:
            print("embed retry", str(e)[:80], flush=True)
            time.sleep(15)
    raise RuntimeError("embed failed")


ids = [i for i in txt if i in pos]
print("matched:", len(ids), flush=True)
B = 16
for s in range(0, len(ids), B):
    batch = ids[s:s + B]
    vecs = embed_batch([txt[i] for i in batch])
    for cid, v in zip(batch, vecs):
        mat[pos[cid]] = v / (np.linalg.norm(v) + 1e-9)
        vdb["data"][pos[cid]]["content"] = txt[cid]
    if (s // B) % 10 == 0:
        print(f"patched {s + len(batch)}/{len(ids)}", flush=True)
vdb["matrix"] = base64.b64encode(np.ascontiguousarray(mat, dtype=np.float32).tobytes()).decode()
json.dump(vdb, open(f"{D}/vdb_chunks.json", "w", encoding="utf-8"), ensure_ascii=False)
kv = json.load(open(f"{D}/kv_store_text_chunks.json", encoding="utf-8"))
n = 0
for cid, t in txt.items():
    if cid in kv:
        kv[cid]["content"] = t
        n += 1
json.dump(kv, open(f"{D}/kv_store_text_chunks.json", "w", encoding="utf-8"), ensure_ascii=False)
print(f"PATCH DONE rows={len(ids)} kv={n}", flush=True)
