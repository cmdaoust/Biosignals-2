
import os
import glob
import numpy as np
import scipy.io as sio
import pandas as pd
import bioread
import sys as _sys, os as _os
# config.py lives at the repo root (two folders up from this script)
_sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..')))
from config import RAW_PHYSIOLOGY_DIR

# ── CONFIG ────────────────────────────────────────────────────────────────────

RAW_PHYSIOLOGY_DIR = str(RAW_PHYSIOLOGY_DIR)

physio_file = os.path.join(RAW_PHYSIOLOGY_DIR, '001_physiology.mat')

mat = sio.loadmat(physio_file, squeeze_me=True)

for k, v in mat.items():
    if not k.startswith('_'):
        shape = v.shape if hasattr(v, 'shape') else 'n/a'
        dtype = v.dtype if hasattr(v, 'dtype') else type(v).__name__
        print(f"{k:30s}  shape={shape}  dtype={dtype}")