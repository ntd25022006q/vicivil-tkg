#!/usr/bin/env python3
"""Regenerate the full-tree SHA256SUMS manifest (CI check twin of
agent_workspace/regen_sums.py).

Usage: python tools/law_manifest_full.py <tree_root> <out_file>
Walks the whole tree (skipping the manifest itself, its provenance/ sibling
and the output file), writes "<sha256>  ./<rel>" lines sorted by path --
byte-identical to the release gate's regen_sums.py output.
"""
import hashlib
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

root, out = sys.argv[1], sys.argv[2]
skip = {os.path.abspath(out), os.path.abspath(os.path.join(root, "SHA256SUMS")),
        os.path.abspath(os.path.join(root, "provenance", "SHA256SUMS"))}
# v1.2.0: provenance/repro_check/ holds ephemeral re-derivation outputs that
# tools/reproduce.sh regenerates at check time - they are intentionally not
# part of the frozen manifest.
skip_dirs = {os.path.abspath(os.path.join(root, "provenance", "repro_check"))}
lines = []
for dirpath, _dirs, files in os.walk(root):
    if os.path.abspath(dirpath) in skip_dirs:
        continue
    # skip VCS/cache dirs (same convention as tools/law_sweep.py): a git
    # checkout carries .git/ and may carry __pycache__/.cache - none of them
    # are release files, and the server-side regen_sums.py tree has no .git
    _dirs[:] = [d for d in _dirs if d not in (".git", ".cache", "__pycache__")]
    for f in files:
        if f.endswith(".pyc"):
            continue
        p = os.path.join(dirpath, f)
        if os.path.abspath(p) in skip:
            continue
        rel = "./" + os.path.relpath(p, root)
        h = hashlib.sha256()
        with open(p, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        lines.append(f"{h.hexdigest()}  {rel}")
lines.sort(key=lambda x: x.split("  ", 1)[1])
io.open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print(f"full-tree manifest: {len(lines)} entries")
