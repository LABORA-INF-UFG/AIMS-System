import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent))
from capture_loader import load_capture  # noqa: E402


def _part(path, n, L, start):
    np.savez(
        path,
        host_ns=np.arange(start, start + n, dtype=np.int64),
        pktid=np.arange(n, dtype=np.uint64),
        rssi=np.full(n, -40, dtype=np.int16),
        csi=np.ones((n, L), dtype=np.complex64),
        subcarrierindex=np.arange(L, dtype=np.int16),
    )


def _make(tmp_path, L0, L1, status="complete"):
    (tmp_path / "meta.json").write_text(json.dumps({"format_version": 1, "status": status}))
    (tmp_path / "csi").mkdir()
    _part(tmp_path / "csi" / "part-0000.npz", 3, L0, 0)
    _part(tmp_path / "csi" / "part-0001.npz", 2, L1, 3)
    (tmp_path / "breath_estimate.csv").write_text("host_ns,bpm\n10,12.5\n20,13\n")
    (tmp_path / "person_present.csv").write_text("host_ns,present\n")
    (tmp_path / "ui_breath_annotation.csv").write_text("host_ns,label,vals\n5,in,1 2 3\n6,out,4 5\n")
    return tmp_path


def test_same_l(tmp_path):
    cap = load_capture(_make(tmp_path, 4, 4))
    assert cap["meta"]["status"] == "complete"
    c = cap["csi"]
    assert c["csi"].shape == (5, 4) and c["csi"].dtype == np.complex64
    assert c["subcarrierindex"].shape == (4,)
    assert c["host_ns"].tolist() == [0, 1, 2, 3, 4] and c["host_ns"].dtype == np.int64
    assert c["rssi"].shape == (5,)

    b = cap["breath_estimate"]
    assert b["host_ns"].dtype == np.int64 and b["host_ns"].tolist() == [10, 20]
    assert b["bpm"].dtype == np.float64 and b["bpm"].tolist() == [12.5, 13.0]

    p = cap["person_present"]
    assert p["host_ns"].shape == (0,) and p["present"].shape == (0,)

    a = cap["ui_breath_annotation"]
    assert a["label"].tolist() == ["in", "out"] and a["vals"].tolist() == ["1 2 3", "4 5"]


def test_different_l(tmp_path):
    c = load_capture(_make(tmp_path, 4, 6))["csi"]
    assert [a.shape for a in c["csi"]] == [(3, 4), (2, 6)]
    assert [a.shape for a in c["subcarrierindex"]] == [(4,), (6,)]
    assert c["rssi"].shape == (5,)


def test_warns_and_no_csi(tmp_path):
    (tmp_path / "meta.json").write_text(json.dumps({"status": "recording"}))
    with pytest.warns(UserWarning):
        cap = load_capture(tmp_path)
    assert "csi" not in cap
