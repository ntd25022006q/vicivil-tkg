#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inter-annotator agreement for the ViCivil-TKG annotation sheet.
Usage: python3 compute_iaa.py review_sheet_60.csv
Reads rater_A / rater_B / rater_C columns (DUNG | SAI | MOTPHAN),
prints Cohen's kappa per pair and Fleiss kappa over all raters,
lists disputed rows, and writes iaa_kappa.json."""
import csv, json, sys, itertools

VALID = {"DUNG", "SAI", "MOTPHAN"}


def cohen_kappa(a, b):
    n = len(a)
    cats = sorted(set(a) | set(b))
    idx = {c: i for i, c in enumerate(cats)}
    M = [[0] * len(cats) for _ in cats]
    for x, y in zip(a, b):
        M[idx[x]][idx[y]] += 1
    po = sum(M[i][i] for i in range(len(cats))) / n
    pe = sum((sum(M[i]) / n) * (sum(row[i] for row in M) / n) for i in range(len(cats)))
    return (po - pe) / (1 - pe) if pe < 1 else 1.0, po


def fleiss_kappa(ratings):
    """ratings: list of rows, each a list of category labels (may contain None)."""
    cats = sorted({c for row in ratings for c in row if c})
    idx = {c: i for i, c in enumerate(cats)}
    complete = [row for row in ratings if all(c for c in row)]
    if len({len(row) for row in complete}) != 1:
        complete = [row for row in complete]
    n_r = len(complete[0]) if complete else 0
    N = len(complete)
    if N == 0 or n_r < 2:
        return None
    n_ij = [[row.count(c) for c in cats] for row in complete]
    P_i = [(sum(m * m for m in row) - n_r) / (n_r * (n_r - 1)) for row in n_ij]
    P_bar = sum(P_i) / N
    p_j = [sum(row[i] for row in n_ij) / (N * n_r) for i in range(len(cats))]
    P_e = sum(p * p for p in p_j)
    return (P_bar - P_e) / (1 - P_e) if P_e < 1 else 1.0


def main(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    raters = {}
    for col in ("rater_A", "rater_B", "rater_C"):
        vals = [(r["qid"], (r[col] or "").strip().upper()) for r in rows]
        bad = [v for _, v in vals if v and v not in VALID]
        if bad:
            print(f"INVALID labels in {col}: {set(bad)}"); sys.exit(1)
        filled = [(q, v) for q, v in vals if v]
        if filled:
            raters[col] = dict(filled)
    print(f"rows={len(rows)} raters={list(raters)} "
          f"({', '.join(str(len(v)) + ' filled' for v in raters.values())})")
    if len(raters) < 2:
        print("Need >= 2 filled raters."); sys.exit(2)

    out = {"file": path, "n_rows": len(rows), "raters": {k: len(v) for k, v in raters.items()}}
    for a, b in itertools.combinations(raters, 2):
        common = sorted(set(raters[a]) & set(raters[b]))
        k, po = cohen_kappa([raters[a][q] for q in common], [raters[b][q] for q in common])
        print(f"Cohen kappa {a} vs {b}: kappa={k:.3f}  (po={po:.3f}, n={len(common)})")
        out[f"kappa_{a}_vs_{b}"] = {"kappa": round(k, 4), "po": round(po, 4), "n": len(common)}

    fk = fleiss_kappa([[raters[c].get(r["qid"]) for c in raters] for r in rows])
    if fk is not None:
        print(f"Fleiss kappa (all raters, complete rows): {fk:.3f}")
        out["fleiss_kappa"] = round(fk, 4)
    print("TARGET kappa >= 0.75:", "MET" if (fk or 0) >= 0.75 or any(
        v["kappa"] >= 0.75 for v in out.values() if isinstance(v, dict) and "kappa" in v) else "NOT MET")

    disputes = []
    for r in rows:
        vals = {raters[c][r["qid"]] for c in raters if r["qid"] in raters[c]}
        if len(vals) > 1:
            disputes.append({"qid": r["qid"], "votes": {c: raters[c][r["qid"]]
                            for c in raters if r["qid"] in raters[c]}})
    print(f"disputed rows: {len(disputes)}")
    for d in disputes[:15]:
        print("  ", d)
    out["n_disputed"] = len(disputes)
    out["disputed"] = disputes
    json.dump(out, open("iaa_kappa.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("wrote iaa_kappa.json")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "review_sheet_60.csv")
