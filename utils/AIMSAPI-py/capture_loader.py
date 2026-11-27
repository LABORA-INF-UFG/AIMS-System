"""Load a modular AIMS capture folder.

Format (written by the ROS capture node):
  meta.json            format_version, status ("recording"|"complete"), request, start_ns,
                       end_ns, timezone, sources {name: {topic, type, files, rows, error}}
  csi/part-NNNN.npz    per-frame arrays [N] (host_ns, pktid, rssi, ...; open set), csi complex64
                       [N, L], subcarrierindex int16 [L]; L may differ between parts
  <source>.csv         header row first; first column host_ns (ns since epoch); others numeric,
                       0/1 bools, or strings

Example:
    cap = load_capture("captures/2026-01-01_run1")
    cap["meta"]["status"]
    cap["csi"]["csi"].shape          # (N_total, L)
    cap["breath_estimate"]["host_ns"]  # int64 array, one key per CSV file stem

Return value: {"meta": dict, "csi": {key: array}, "<csv stem>": {column: array}}.
"csi" is absent if there is no csi/ folder. Per-frame keys are concatenated over parts. "csi" is a
single array if L is equal in all parts, otherwise a list with one array per part.
"subcarrierindex" is a single array if identical in all parts, otherwise a list per part. CSV columns: host_ns int64; others float64 if all values numeric, else str.
"""
import csv
import json
import warnings
from pathlib import Path

import numpy as np

def _column(name, values):
    if name == "host_ns":
        return np.array(values, dtype=np.int64)
    try:
        return np.array(values, dtype=np.float64)
    except ValueError:
        return np.array(values, dtype=str)


def _read_csv(path):
    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    header, data = rows[0], rows[1:]
    return {h: _column(h, [r[i] for r in data]) for i, h in enumerate(header)}


def load_capture(path):
    path = Path(path)
    meta = json.loads((path / "meta.json").read_text())
    if meta.get("status") != "complete":
        warnings.warn(f"capture status is {meta.get('status')!r}, not 'complete'")
    out = {"meta": meta}

    parts = sorted((path / "csi").glob("part-*.npz"))
    if (path / "csi").is_dir():
        loaded = []
        for p in parts:
            with np.load(p, allow_pickle=False) as z:
                loaded.append({k: z[k] for k in z.files})
        csi = {}
        for k in dict.fromkeys(k for d in loaded for k in d):
            arrs = [d[k] for d in loaded if k in d]
            if k == "subcarrierindex":  # one per part, not per frame
                same = all(np.array_equal(a, arrs[0]) for a in arrs)
                csi[k] = arrs[0] if same else arrs
                continue
            same_l = len({a.shape[1:] for a in arrs}) == 1
            csi[k] = arrs if k == "csi" and not same_l else np.concatenate(arrs)
        out["csi"] = csi

    for f in sorted(path.glob("*.csv")):
        out[f.stem] = _read_csv(f)
    return out
