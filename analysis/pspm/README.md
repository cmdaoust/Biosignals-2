# PsPM SCR Analysis Pipeline

## Overview

This pipeline analyses skin conductance responses (SCR) using PsPM (Psychophysiological Modelling). It runs spontaneous fluctuation (SF) models across four methods (AUC, SCL, MP, DCM) and exports per-epoch statistics for analysis in R.

---

## Prerequisites

### MATLAB toolboxes required

The following toolboxes must be installed in MATLAB. On a local machine check via **Home → Add-Ons → Manage Add-Ons**. On the HPC cluster, load the appropriate module.

| Toolbox | Why needed |
|---|---|
| **Statistics and Machine Learning Toolbox** | Required by PsPM's `pspm_scr_pp.m` (missing epoch detection). Without it you will get: `Undefined function 'range' for input arguments of type 'double'` |

> **Note:** This pipeline has been confirmed to run correctly on the HPC cluster. Running locally may fail if the Statistics Toolbox is not installed.

### PsPM

Initialise PsPM before running any script by calling `pspm` in the MATLAB command window, or set `RUN_PSPM_INIT = true` in `run_all_pspm.m`.

### Python

`02_create_pspm_onsets_psychopy.py` must be run before the MATLAB scripts to generate the epoch onset files. Requires Python with `scipy` and `numpy`.

### Config

Copy `config_template.m` (repo root) to `config.m` and fill in `SERVER_ROOT` (path to the data folder on your machine/cluster) and `PSPM_PATH`. `config.m` is gitignored and never committed.

---

## Data preparation — IMPORTANT

### Export physiology data as MATLAB .mat from AcqKnowledge

The pipeline uses PsPM's `acqmat` import type, which reads files exported directly from AcqKnowledge as MATLAB files. **Do not use the raw `.acq` files directly** — PsPM's `acq_python` import reads uncalibrated voltage values rather than the calibrated µS values that AcqKnowledge displays, producing incorrect results.

**Steps to export:**
1. Open the `.acq` file in AcqKnowledge
2. File → Save As → MATLAB (`.mat`)
3. Name the file `{participant_id}_physiology.mat` (e.g. `001_physiology.mat`)
4. Save to the `raw_physiology/` folder on the server

The EDA channel must be on **channel 2** (as recorded). If your channel layout differs, update `chan_nr_spec` in `x03_preprocess_scr.m`.

---

## Run order

```
02_create_pspm_onsets_psychopy.py   ← Python: generates epoch .mat and labels .csv
x03_preprocess_scr.m                ← MATLAB: import + missing epoch detection
x04_run_sf.m                        ← MATLAB: fit SF models (AUC, SCL, MP, DCM)
x05_sf_export_stats.m               ← MATLAB: export per-epoch statistics to TSV
03_analyse_sf.Rmd                   ← R: LMM analysis of SF output by condition
```

To run all MATLAB steps in sequence, use `run_all_pspm.m`. Set the `SKIP_X03 / SKIP_X04 / SKIP_X05` flags at the top to control which steps re-run.

---

## Known issues and patches

### DCM rmfield error in pspm_sf_dcm.m

PsPM's DCM code errors when the display window option is absent. Patch line ~165 of `pspm_sf_dcm.m`:

```matlab
% Before (original):
for i = 1:length(output)
    output(i).options = rmfield(output(i).options, 'hf');
end

% After (patched):
for i = 1:length(output)
    if isfield(output(i).options, 'hf')
        output(i).options = rmfield(output(i).options, 'hf');
    end
end
```

### Transfer function (acq_python import — do not use)

If importing `.acq` files directly via `acq_python`, PsPM reads raw voltage (≈ −0.008 to +0.003 V) rather than calibrated µS (≈ 11–17 µS for this hardware). The `acqmat` import of AcqKnowledge-exported `.mat` files avoids this entirely. See `../NOTES_TO_FOLLOW_UP.md` for details and outstanding questions for the PsPM developers.

---

## Output files

| Location | Contents |
|---|---|
| `{SERVER_ROOT}/pspm/preprocessed/` | Imported PsPM `.mat` files |
| `{SERVER_ROOT}/pspm/missing epoch/` | Missing epoch files (one per participant) |
| `{SERVER_ROOT}/event_onsets/blocks/` | Epoch onset `.mat` files and condition label `.csv` files |
| `{SERVER_ROOT}/pspm/models/` | SF model `.mat` files (one per participant per method) |
| `{SERVER_ROOT}/pspm/outputs/` | Exported statistics `.txt` files (TSV) |
