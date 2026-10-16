# tools/ — one-off and development utilities (not part of the pipeline)

These scripts were used once during construction or for probing. They are kept
for transparency; the reproducible pipeline lives in `../src/`.

| Script | Purpose |
|---|---|
| `rrpull.py` | One-time download of Qwen3-Reranker-0.6B weights into HF cache |
| `rtfget.py` | Probe: fetch an old Công báo `.rtf` (led to the VNI dual-font diagnosis) |
| `lawsmoke.py` | Dev smoke test: hybrid vs graph mode on 2 questions |
| `law_extract_pilot.py` | First extraction pilot (superseded by `src/law_kg_extract.py`) |
| `lawq_time_demo.py` | Standalone point-in-time query demo (see `src/law_temporal.py`) |
