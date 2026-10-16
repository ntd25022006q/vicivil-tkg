"""Hybrid law retrieval v1: BM25 (lexical, exact numbers/terms) + dense, RRF fusion.
Mirrors ADGR's lesson (dense-only fails) with the cheapest correct fix.
Usage: import hybrid_search; or run law_eval2.py
"""
import json, math, re, unicodedata
from collections import Counter


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

    def score(self, q):
        qt = toks(q)
        out = []
        for i, t in enumerate(self.docs):
            c = Counter(t)
            s = 0.0
            for w in qt:
                if w not in self.idf or w not in c:
                    continue
                f = c[w]
                s += self.idf[w] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.lens[i] / self.avg))
            out.append(s)
        return out


def rrf(rank_lists, k=60):
    fused = {}
    for ranks in rank_lists:
        for r, idx in enumerate(ranks):
            fused[idx] = fused.get(idx, 0) + 1.0 / (k + r + 1)
    return sorted(fused, key=fused.get, reverse=True)
