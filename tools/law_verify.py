import hashlib
import io
import os
import sys
import tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from huggingface_hub import snapshot_download

_dest = sys.argv[1] if len(sys.argv) > 1 else \
    os.path.join(tempfile.gettempdir(), "vicivil_tkg_hubverify")
p = snapshot_download("datbazuka2502/vicivil-tkg", repo_type="dataset",
                      local_dir=_dest)
mf = {}
for line in open(os.path.join(p, "SHA256SUMS"), encoding="utf-8"):
    h, rel = line.strip().split("  ", 1)
    mf[rel] = h
hub_files = []
for dp, _, fns in os.walk(p):
    if os.path.basename(dp) == ".git":
        continue
    for fn in fns:
        hub_files.append(os.path.relpath(os.path.join(dp, fn), p).replace(os.sep, "/"))
hub_files = [f for f in hub_files if f != "SHA256SUMS"]
ok, bad, unl = 0, [], [f for f in hub_files if f not in mf]
for rel, h in sorted(mf.items()):
    f = os.path.join(p, rel.replace("/", os.sep))
    if not os.path.exists(f):
        bad.append(rel + " MISSING")
        continue
    d = hashlib.sha256(open(f, "rb").read()).hexdigest()
    if d == h:
        ok += 1
    else:
        bad.append(rel)
print("hub files:", len(hub_files), "| manifest entries:", len(mf))
print("match:", ok, "| bad:", bad or "-", "| unlisted:", unl or "-")
