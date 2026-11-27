# AIMSAPI

Helper functions and classes used in the AIMS project to handle data and support integration routines.

## Loading a capture

`capture_loader.py` reads a capture folder (`meta.json`, `csi/part-*.npz`, one CSV per other source) using only numpy and the standard library:

```python
from capture_loader import load_capture

cap = load_capture("captures/2026-01-01_run1")
cap["meta"]["status"]              # warns if not "complete"
cap["csi"]["csi"].shape            # (N, L); a list per part if L differs between parts
cap["breath_estimate"]["host_ns"]  # one key per CSV file stem, columns as numpy arrays
```

Test: `python -m pytest utils/AIMSAPI-py/test_capture_loader.py`
