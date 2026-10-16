"""Law ADGR-fixed retrieval: temporal filter -> LLM keywords -> hybrid anchors
(BM25 + dense over entities, overlap bonus) -> 1-hop edge expansion (incl.
DAN_CHIEU ref edges) with query-relevance filter -> RRF fusion. NO rerank
override (ADGR's measured defect). Usage: law_adgr_eval.py
"""
import json, math, re, unicodedata, urllib.request
from collections import Counter
import numpy as np

W = "/home/devlab1/law_workspace"
R = f"{W}/runs"
D = f"{W}/law_data"
VLLM = "http://127.0.0.1:8000/v1/chat/completions"
MODEL = "/home/devlab1/adgr_workspace/models/qwen25-awq"


def toks(s):
    s = unicodedata.normalize("NFC", s or "").lower()
    return re.findall(r"[a-zà-ỹđ0-9]+", s)


class BM25:
    def __init__(self, docs, k1=1.2, b=0.75):
        self.docs = [toks(d) for d in docs]
        self.N = len(self.docs)
        df = Counter()
        self.lens = []
        for t in self.docs:
            self.lens.append(len(t))
            for w in set(t):
                df[w] += 1
        self.idf = {w: math.log(1 + (self.N - f + 0.5) / (f + 0.5)) for w, f in df.items()}
        self.avg = sum(self.lens) / max(1, self.N)
        self.k1, self.b = k1, b

    def scores(self, q):
        qt = toks(q)
        out = np.zeros(self.N)
        for i, t in enumerate(self.docs):
            c = Counter(t)
            s = 0.0
            for w in qt:
                if w not in self.idf or w not in c:
                    continue
                f = c[w]
                s += self.idf[w] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.lens[i] / self.avg))
            out[i] = s
        return out


def rrf(lists, k=60):
    f = {}
    for L in lists:
        for r, i in enumerate(L):
            f[i] = f.get(i, 0) + 1.0 / (k + r + 1)
    return sorted(f, key=f.get, reverse=True)


class LawRetriever:
    def __init__(self):
        G = json.load(open(f"{R}/temporal_graph.json", encoding="utf-8"))
        self.lawmap = {L["law_id"]: L for L in G["laws"]}
        ch = json.load(open(f"{D}/vdb_chunks.json", encoding="utf-8"))
        self.chunks = ch["data"]
        self.cmat = np.frombuffer(__import__("base64").b64decode(ch["matrix"]),
                                  dtype=np.float32).reshape(-1, 768)
        self.bm_c = BM25([c["content"] for c in self.chunks])
        en = json.load(open(f"{D}/vdb_entities.json", encoding="utf-8"))
        self.ents = en["data"]
        self.emat = np.frombuffer(__import__("base64").b64decode(en["matrix"]),
                                  dtype=np.float32).reshape(-1, 768)
        self.bm_e = BM25([e["entity_name"] + " " + e["content"][:500] for e in self.ents])
        self.e2c = json.load(open(f"{D}/kv_store_entity_chunks.json", encoding="utf-8"))
        rl = json.load(open(f"{D}/vdb_relationships.json", encoding="utf-8"))
        self.rels = rl["data"]
        self.rmat = np.frombuffer(__import__("base64").b64decode(rl["matrix"]),
                                  dtype=np.float32).reshape(-1, 768)
        self.by_ent = {}
        for i, r in enumerate(self.rels):
            self.by_ent.setdefault(r["src_id"], []).append(i)
            self.by_ent.setdefault(r["tgt_id"], []).append(i)

    def embed(self, texts):
        req = urllib.request.Request(
            "http://127.0.0.1:11434/api/embed",
            data=json.dumps({"model": "embeddinggemma:300m", "input": texts}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as r:
            v = np.asarray(json.load(r)["embeddings"], dtype=np.float32)
        return v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-9)

    def keywords(self, q):
        try:
            body = {"model": MODEL, "messages": [
                {"role": "system", "content": "Trich 3-6 tu khoa ngan ve luat, moi tu 1 dong. Khong giai thich."},
                {"role": "user", "content": q}], "temperature": 0, "max_tokens": 120}
            req = urllib.request.Request(VLLM, data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                o = json.load(r)["choices"][0]["message"]["content"] or ""
            kws = [L.strip("-• ") for L in o.split("\n") if len(L.strip()) > 1][:6]
            return kws if kws else [q]
        except Exception:
            return [q]

    def expand(self, q):
        """Formal paraphrase for dense/BM25: colloquial -> legal style."""
        try:
            body = {"model": MODEL, "messages": [
                {"role": "system", "content": "Viet lai cau hoi duoi day theo van phong phap luat (dung thuat ngu Dieu/Khoan/quyen/nghia vu). Chi in 1 cau."},
                {"role": "user", "content": q}], "temperature": 0, "max_tokens": 120}
            req = urllib.request.Request(VLLM, data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                o = (json.load(r)["choices"][0]["message"]["content"] or "").strip().split("\n")[0]
            return o if len(o) >= 10 else q
        except Exception:
            return q

    def valid_idx(self, as_of):
        return [i for i, c in enumerate(self.chunks)
                if (lambda L: L["valid_from"] <= as_of and
                   (L["valid_to"] is None or as_of < L["valid_to"]))(self.lawmap[c["url"]])]

    def retrieve(self, q, as_of, topk=10, rerank=False):
        vix = self.valid_idx(as_of)
        vset = set(vix)
        kws = self.keywords(q)
        kq = " ".join(kws)
        qx = self.expand(q)
        qfull = q + " " + qx + " " + kq
        qv = self.embed([qfull])[0]
        kv = self.embed([kq])[0]
        # anchors: dense top10 over entities + BM25 top10, overlap bonus
        ds = (self.emat @ qv).tolist()
        od = sorted(range(len(self.ents)), key=lambda i: -ds[i])[:10]
        bs = self.bm_e.scores(kq).tolist()
        ob = sorted(range(len(self.ents)), key=lambda i: -bs[i])[:10]
        asc = {}
        for i in od:
            asc[i] = asc.get(i, 0) + ds[i]
        for i in ob:
            asc[i] = asc.get(i, 0) + (0.5 if i in od else 0.0) + min(bs[i] / 10.0, 1.0)
        anchors = sorted(asc, key=asc.get, reverse=True)[:15]
        # 1-hop edges, query-relevance filter (kw overlap + dense)
        cand = {}
        r2c = json.load(open(f"{D}/kv_store_relation_chunks.json", encoding="utf-8"))
        ktoks = set(toks(kq)) | set(toks(q))
        for a in anchors:
            nm = self.ents[a]["entity_name"]
            for ri in self.by_ent.get(nm, [])[:30]:
                r = self.rels[ri]
                if r.get("law_id") and not (lambda L: L["valid_from"] <= as_of and
                   (L["valid_to"] is None or as_of < L["valid_to"]))(self.lawmap.get(r["law_id"], {"valid_from": "1900", "valid_to": None})):
                    continue
                rel_txt = r["content"]
                overlap = len(set(toks(kq)) & set(toks(rel_txt))) / max(1, len(set(toks(kq))))
                if overlap < 0.15 and len(anchors) > 5:
                    continue
                for cid in r2c.get(r["__id__"], {}).get("chunk_ids", []):
                    cand[cid] = cand.get(cid, 0) + asc[a] * (0.5 + overlap)
        # 2-hop: neighbors-of-neighbors, stricter filter, half weight
        hop2 = {}
        for a in anchors[:8]:
            nm = self.ents[a]["entity_name"]
            for ri in self.by_ent.get(nm, [])[:20]:
                r = self.rels[ri]
                nb = r["tgt_id"] if r["src_id"] == nm else r["src_id"]
                for rj in self.by_ent.get(nb, [])[:20]:
                    r2 = self.rels[rj]
                    overlap2 = len(ktoks & set(toks(r2["content"]))) / max(1, len(ktoks))
                    if overlap2 < 0.2:
                        continue
                    for cid in r2c.get(r2["__id__"], {}).get("chunk_ids", [])[:4]:
                        hop2[cid] = hop2.get(cid, 0) + asc[a] * 0.25 * (0.5 + overlap2)
        # pools -> chunk indices
        id2i = {c["__id__"]: i for i, c in enumerate(self.chunks)}
        edge_idx = [id2i[c] for c in cand if c in id2i and id2i[c] in vset]
        anch_idx = []
        for a in anchors:
            for cid in self.e2c.get(self.ents[a]["entity_name"], {}).get("chunk_ids", [])[:8]:
                if cid in id2i and id2i[cid] in vset:
                    anch_idx.append(id2i[cid])
        dd = (self.cmat[vix] @ qv).tolist()
        order_d = sorted(range(len(vix)), key=lambda r: -dd[r])[:30]
        pool_d = [vix[r] for r in order_d]
        bd = self.bm_c.scores(qfull)
        bdv = [(bd[i], i) for i in vix]
        pool_b = [i for _, i in sorted(bdv, reverse=True)[:30]]
        # RRF fusion over the 5 pools (no rerank override: ADGR's defect fixed)
        scores = {}
        h2_idx = [id2i[c] for c in hop2 if c in id2i and id2i[c] in vset][:30]
        for rank, lst in enumerate([pool_d, pool_b, anch_idx[:30], edge_idx[:50], h2_idx]):
            for r, gi in enumerate(lst):
                scores[gi] = scores.get(gi, 0) + 1.0 / (60 + r + 1)
        # exact-match precision layer: legal answers hinge on exact numbers
        # ("20 tuoi") and verbatim phrases -> promote within top-20
        qnums = set(re.findall(r"\d+", qfull))
        qgrams = set()
        qt = toks(qfull)
        for i in range(len(qt) - 3):
            qgrams.add(" ".join(qt[i:i + 4]))
        top20 = sorted(scores, key=scores.get, reverse=True)[:20]
        boosted = {}
        for gi in top20:
            txt = self.chunks[gi]["content"]
            cn = set(re.findall(r"\d+", txt))
            ct = set(toks(txt))
            ph = sum(1 for g in qgrams if g in " ".join(ct))
            boosted[gi] = scores[gi] + 2.0 * len(qnums & cn) + 0.3 * min(ph, 5)
        final = sorted(boosted, key=boosted.get, reverse=True)[:topk]
        if rerank:
            try:
                from law_rerank import score_pairs
                docs = [self.chunks[i]["content"] for i in final]
                rs = score_pairs(q, docs)
                if rs and len(rs) == len(final):
                    order = sorted(range(len(final)),
                                   key=lambda r: (-(0.5 * (len(final) - r) / len(final) +
                                                    0.5 * (rs[r] - min(rs)) / (max(rs) - min(rs) + 1e-9))))
                    final = [final[r] for r in order]
            except Exception as e:
                print("rerank skipped:", repr(e)[:100], flush=True)
        ranked = final
        return [self.chunks[i]["__id__"] for i in ranked]
