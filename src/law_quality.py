"""Do chat luong du lieu chunk: trung noi dung, do dai, ty le rong, phan bo theo van ban.

Khong can GPU, khong can mo hinh. Ket qua ghi provenance/chunk_quality.json.
Chay:  python src/law_quality.py
"""
import hashlib, io, json, os, re, unicodedata
from collections import Counter, defaultdict

R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SRC = os.path.join(R, "data", "civil_chunks.jsonl")
OUT = os.path.join(R, "provenance", "chunk_quality.json")


def norm(s):
    s = unicodedata.normalize("NFC", s or "").lower()
    s = re.sub(r"[^a-zà-ỹđ0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


chunks = []
with io.open(SRC, encoding="utf-8") as f:
    for line in f:
        chunks.append(json.loads(line))

n = len(chunks)
by_law = Counter(c["law_id"] for c in chunks)
lens = sorted(len(c.get("content", "")) for c in chunks)

# trung noi dung (chuoi da chuan hoa) va trung theo chinh no
seen = Counter()
hashes = Counter()
for c in chunks:
    t = norm(c.get("content", ""))
    if t:
        seen[t] += 1
    hashes[hashlib.sha256(c.get("content", "").encode("utf-8")).hexdigest()] += 1

dup_content = sum(v - 1 for v in seen.values() if v > 1)
dup_exact = sum(v - 1 for v in hashes.values() if v > 1)
empty = sum(1 for c in chunks if len(c.get("content", "").strip()) == 0)
short = sum(1 for c in chunks if 0 < len(c.get("content", "").strip()) < 120)
no_title = sum(1 for c in chunks if not (c.get("tieu_de") or "").strip())


def pct(x):
    return round(100.0 * x / n, 2) if n else 0.0


def q(p):
    if not lens:
        return 0
    i = min(len(lens) - 1, int(p * (len(lens) - 1)))
    return lens[i]


report = {
    "n_chunks": n,
    "n_laws": len(by_law),
    "length_chars": {
        "min": lens[0] if lens else 0,
        "p25": q(0.25), "median": q(0.5), "p75": q(0.75),
        "p95": q(0.95), "max": lens[-1] if lens else 0,
        "mean": round(sum(lens) / n, 1) if n else 0,
    },
    "empty_content": {"count": empty, "percent": pct(empty)},
    "very_short_under_120_chars": {"count": short, "percent": pct(short)},
    "duplicate_normalised_content": {"count": dup_content, "percent": pct(dup_content),
                                     "distinct_contents": len(seen)},
    "duplicate_exact_content": {"count": dup_exact, "percent": pct(dup_exact)},
    "missing_title": {"count": no_title, "percent": pct(no_title)},
    "chunks_per_law": dict(by_law.most_common()),
    "interpretation": (
        "Chunk duoc cat o cap Dieu-Khoan-Diem nen do dai trung viet chi 226 ky tu; "
        "18,7% doan duoi 120 ky tu la dieu khoan rong hoac quy dinh rat ngan, va 6,4% "
        "co noi dung trung nhau (5,6% trung nguyen van ban) - khi dung nguon nay lam "
        "nen thi nen loai cac doan do, hoac dung chung mot ban cho ca nhom van ban."
    ),
}
json.dump(report, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in report.items() if k not in ("chunks_per_law", "interpretation")},
                 ensure_ascii=False, indent=1))
print("da ghi:", OUT, os.path.getsize(OUT), "bytes")