"""BLDS1995 split: whole-Dieu -> Muc sub-chunks from official text + vdb surgery.
Backup -> replace 836 parents with ~1814 official Muc chunks -> remap CIV012 ->
embed new -> vdb row surgery -> verify. Log: runs/law95split.log
"""
import base64, io, json, re, shutil, sys, time, urllib.request
import numpy as np
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
D = f"{W}/law_data"
OFF_URL = "https://thuvienphapluat.vn/van-ban/Quyen-dan-su/Bo-luat-Dan-su-1995-44-L-CTN-39391.aspx"
shutil.copy(f"{R}/civil_chunks.jsonl", f"{R}/civil_chunks_v11.jsonl")
print("backup v1.1 done", flush=True)
off = open("/tmp/off_blds1995.txt", encoding="utf-8").read()
arts = re.split(r"(?=Điều \d+\.)", off)
print("segments:", len(arts), flush=True)
new95 = []
for a in arts[1:]:
    m0 = re.match(r"Điều\s+(\d+)\.\s*([^\n]{0,120})", a)
    if not m0:
        continue
    N, title = m0.group(1), m0.group(2).strip()
    parts = re.split(r"(?m)^(\d+)-\s", a)
    items = []
    if len(parts) > 1:
        for i in range(1, len(parts), 2):
            items.append((parts[i], (parts[i + 1] if i + 1 < len(parts) else "").strip()))
    head = parts[0] if len(parts) > 1 else a
    head = re.sub(r"^Điều\s+\d+\.\s*[^\n]*\n?", "", head).strip()
    if len(items) >= 1 and len(head) > 50:
        items = [("0", head)] + items
    if not items:
        body = re.sub(r"^Điều\s+\d+\.\s*[^\n]*\n?", "", a).strip()
        items = [("0", body)]
    if len(items) == 1 and items[0][0] == "0":
        cid = f"BLDS1995|Dieu{N}"
        content = f"Điều {N}. {title}\n{items[0][1]}"
        new95.append({"chunk_id": cid, "law_id": "BLDS1995", "dieu": N, "khoan": "",
                      "diem": "", "muc": "", "tieu_de": title, "content": content,
                      "chars": str(len(content)), "source_url": OFF_URL,
                      "source_type": "official", "fetched": "2026-10-17"})
    else:
        for k, txt in items:
            if k == "0":
                cid = f"BLDS1995|Dieu{N}|Muc0"
                content = f"Điều {N}. {title}\n{txt}"
            else:
                cid = f"BLDS1995|Dieu{N}|Muc{k}"
                content = f"Điều {N}. {title}\n{k}. {txt}"
            new95.append({"chunk_id": cid, "law_id": "BLDS1995", "dieu": N, "khoan": "",
                          "diem": "", "muc": k, "tieu_de": title, "content": content,
                          "chars": str(len(content)), "source_url": OFF_URL,
                          "source_type": "official", "fetched": "2026-10-17"})
print("new95 chunks:", len(new95), flush=True)
rows = [json.loads(L) for L in open(f"{R}/civil_chunks_v11.jsonl", encoding="utf-8")]
rows = [r for r in rows if r["law_id"] != "BLDS1995"] + new95
with open(f"{R}/civil_chunks.jsonl", "w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print("chunks total:", len(rows), flush=True)
txt = {r["chunk_id"]: r["content"] for r in new95}


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
            print("embed retry", str(e)[:60], flush=True)
            time.sleep(15)
    raise RuntimeError("embed failed")


ids = list(txt)
vecs = []
B = 16
for s in range(0, len(ids), B):
    v = embed_batch([txt[i] for i in ids[s:s + B]])
    v = v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-9)
    vecs.append(v)
    if (s // B) % 20 == 0:
        print(f"embedded {s + len(v)}/{len(ids)}", flush=True)
V = np.vstack(vecs)
vdb = json.load(open(f"{D}/vdb_chunks.json", encoding="utf-8"))
mat = np.frombuffer(base64.b64decode(vdb["matrix"]), dtype=np.float32).reshape(-1, 768).copy()
keep = [i for i, c in enumerate(vdb["data"]) if not c["__id__"].startswith("BLDS1995")]
print("dropped parent rows:", len(vdb["data"]) - len(keep), flush=True)
mat2 = np.vstack([mat[keep], V])
data2 = [vdb["data"][i] for i in keep] + [
    {"__id__": cid, "content": txt[cid], "url": "BLDS1995"} for cid in ids]
vdb["data"] = data2
vdb["matrix"] = base64.b64encode(np.ascontiguousarray(mat2, dtype=np.float32).tobytes()).decode()
json.dump(vdb, open(f"{D}/vdb_chunks.json", "w", encoding="utf-8"), ensure_ascii=False)
kv = json.load(open(f"{D}/kv_store_text_chunks.json", encoding="utf-8"))
kv = {k: v for k, v in kv.items() if not k.startswith("BLDS1995")}
for r in new95:
    kv[r["chunk_id"]] = {"law_id": "BLDS1995", "content": r["content"]}
json.dump(kv, open(f"{D}/kv_store_text_chunks.json", "w", encoding="utf-8"), ensure_ascii=False)
print("vdb rows now:", mat2.shape, flush=True)


def judge(q, c):
    SYS = ("Ban doc CAU HOI va DOAN LUAT. DOAN nay co tra loi TRON VEN cau hoi khong? "
           "Chi tra loi: CO / KHONG.")
    body = {"model": "qwen3:14b", "stream": False,
            "messages": [{"role": "system", "content": SYS},
                         {"role": "user", "content": f"CAU HOI: {q}\nDOAN LUAT:\n{c[:1200]}"}]}
    for _ in range(2):
        try:
            req = urllib.request.Request("http://127.0.0.1:11434/api/chat",
                                         data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=600) as r:
                t = (json.load(r)["message"]["content"] or "").strip().upper().replace(" ", "")
            return "CO" if "CO" in t and "KHONG" not in t else "KHONG"
        except Exception:
            time.sleep(10)
    return "ERROR"


for fn in ["law_bench_200c.json", "law_bench_v1.json"]:
    qs = json.load(open(f"{R}/{fn}", encoding="utf-8"))
    for o in qs:
        if o["qid"] == "CIV012":
            cands = [r["chunk_id"] for r in new95 if r["dieu"] == "679"]
            print("CIV012 Q:", o["question"], flush=True)
            for cid in cands:
                v = judge(o["question"], txt[cid])
                print(cid, "->", v, flush=True)
                if v == "CO":
                    o["gold_ids"] = [cid]
                    o["regolded_from"] = "BLDS1995|Dieu679"
                    o["gold_tier"] = "regolded"
                    break
    json.dump(qs, open(f"{R}/{fn}", "w", encoding="utf-8"), ensure_ascii=False)
print("SPLIT95 DONE", flush=True)
