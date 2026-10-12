# Biosignals2 — Project Data & Code Overview

This document is for collaborators. It covers where data lives, what each file/folder contains, and how the two storage locations relate to each other.

---

## Storage locations

| Location | Purpose |
|---|---|
| **Box** — `Project_Biosignals_study_2/3_Data/` | All raw and processed data (shared server) |
| **GitHub** — `Biosignals2/` | Analysis code, config, and pilot data copies |

Box is not included in the GitHub repo. Code references Box paths via `config.py` (see below).

---

## Box — Data server

Root: `C:\Users\carme\Box\Project_Biosignals_study_2\3_Data\`
(Update the root path for your machine in `config.py`.)

```
3_Data/
├── raw_physiology/              # BIOPAC .acq originals — ECG and EDA recordings, one per participant
│   └── exports/                 # AcqKnowledge exports: full physiology .mat, EDA-only .mat and .acq cuts
│                                #   Staging area — EDA .mat files are copied to ledalab/input/ when ready
├── raw_psychopy/                # PsychoPy output files (includes webcam biometrics .csv and clocksync .json)
├── raw_questionnaire/           # Raw questionnaire responses
├── clean_combined_data/
│   ├── psychopy/                # Cleaned/processed PsychoPy data
│   ├── questionnaires/          # Cleaned questionnaire data
│   └── psychopy_questionnaire/  # Merged psychopy + questionnaire dataset
├── ledalab/
│   ├── input/                   # EDA-only .mat files copied from raw_physiology/exports/ — stable input for Ledalab
│   ├── {id}_eda_era.txt         # Ledalab CDA ERA output per participant
│   └── {id}_eda_scrlist.txt     # Ledalab individual SCR event list per participant
├── pspm/                        # PsPM SCR pipeline output (pipeline abandoned — kept for reference)
│   ├── preprocessed/            # Imported PsPM .mat files
│   ├── missing epoch/           # Missing epoch .mat files
│   ├── models/                  # SF model .mat files (AUC, SCL, MP, DCM)
│   └── outputs/                 # Exported statistics .tsv files
├── event_onsets/
│   ├── blocks/                  # All block-level event onset files. Naming convention:
│   │                            #   {pid}_events_blocks_{source}_{software}.{ext}
│   │                            #   source   = biopac | psychopy
│   │                            #   software = pspm (archived) | ledalab | r
│   │                            #   e.g. 001_carmen_pilot_events_blocks_psychopy_ledalab.txt
│   │                            #        001_carmen_pilot_events_blocks_biopac_pspm.mat
│   │                            #        002_events_blocks_psychopy_r.csv  ← block boundaries for R/FaceReader
│   │                            #   Also contains nid_map_{source}_ledalab.txt (Ledalab condition legend)
│   │                            #   and PsPM epochs files (_epochs_conditions_*.mat, *_labels.csv)
│   └── stimulus_videos/         # Per-video timing files: {pid}_events_stimuli_{source}_pspm.mat
│                                #   (PsPM archived pipeline only — no video-level Ledalab analysis)
├── kubios/                      # Kubios HRV Scientific output (raw CSV/PDF/MAT) + tidy extracts
└── video/                       # FaceReader output and webcam recordings per participant
                                 #   (heart beat logs, expression logs, state logs, frame timestamps, .avi)
```

### Kubios files

Kubios HRV Scientific 4.3 was run on the BIOPAC ECG recordings. Output is one wide-format CSV per participant.

`002_carmen_pilot_physiology_hrv.csv` covers 5 experimental blocks (baseline, negative induction, negative recovery, positive induction, positive recovery). The file contains:
- Lines 1–60: Kubios analysis parameters and settings
- Lines 62–151: Summary HRV statistics per block (RMSSD, SDNN, mean HR, LF/HF power, etc.)
- Lines 207+: Per-beat RR interval data and spectral estimates (FFT and AR), one set of columns per block

Two tidy extracts are also saved in `kubios/`: `002_carmen_pilot_kubios_summary.csv` (one row per block) and `002_carmen_pilot_kubios_rr.csv` (per-beat RR intervals). These are what `03_hr_comparison_pilot.Rmd` reads directly.

---

## GitHub — Code repository

Root: `C:\Users\carme\OneDrive\Documents\GitHub\Biosignals2\`

```
Biosignals2/
├── config.py                    # Maps Box subdirectory paths — update SERVER_ROOT for your machine
├── config.R                     # Same paths for R scripts
├── config.m                     # Same paths for MATLAB scripts
├── config_template.R / .m       # Templates with placeholder paths (for new machines)
│
├── analysis/
│   ├── 01_data_cleaning.Rmd     # Concatenates raw PsychoPy CSVs across participants; extracts
│   │                            #   trial-level valence/arousal ratings, condition order, and
│   │                            #   metadata; outputs biosignals2_psychopy_clean.csv to
│   │                            #   Box/clean_combined_data/psychopy/. Run this first.
│   ├── 02_analysis.Rmd          # Reads biosignals2_psychopy_clean.csv; descriptive stats and
│   │                            #   condition effects on self-report ratings (valence, arousal);
│   │                            #   linear mixed models (condition + random intercept per pid).
│   │                            #   Pilot scaffold — interpret cautiously with small N.
│   ├── 03_hr_comparison_pilot.Rmd  # Participant 002 only. Compares HR and HRV across three
│   │                            #   simultaneous sources — ECG/Kubios (reference), FaceReader
│   │                            #   (facial video), and webcam rPPG (PsychoPy plugin) — across
│   │                            #   all five experimental blocks. See section below for detail.
│   ├── 04_analyse_ledalab_scr.Rmd  # Reads Ledalab CDA ERA output (era.txt) and individual SCR
│   │                            #   lists (scrlist.txt) from Box/ledalab/. Fits LMM per EDA
│   │                            #   measure (condition + random intercept per pid). Primary
│   │                            #   measure: CDA.SCR. Planned contrasts: pos vs neg induction,
│   │                            #   each induction vs baseline, each induction vs its recovery.
│   ├── NOTES_TO_FOLLOW_UP.md    # Open methodological questions
│   ├── kubios/
│   │   └── Kubios_Samples.csv   # Kubios sample/block label mapping
│   ├── ledalab/                 # EDA processing pipeline (active — see below)
│   │   ├── 01_create_ledalab_events_biopac.py   # Generate Ledalab epoch files from BIOPAC triggers
│   │   ├── 02_create_ledalab_events_psychopy.py # Generate Ledalab epoch files from PsychoPy data (preferred)
│   │   ├── 03_compare_ledalab_events.py         # Compare BIOPAC vs PsychoPy onset times to verify channel mapping
│   │   ├── run_ledalab_batch.m  # Run Ledalab CDA analysis in MATLAB (batch)
│   │   └── inspect_data.py      # Utility: inspect EDA data
│   ├── pspm/                    # PsPM SCR pipeline (archived — see note below)
│   │   ├── README.md            # PsPM pipeline documentation
│   │   ├── 01_create_pspm_onsets_biopac.py      # (archived) Generate PsPM onset files from BIOPAC
│   │   ├── 02_create_pspm_onsets_psychopy.py    # (archived) Generate PsPM onset files from PsychoPy
│   │   ├── 03_compare_pspm_onsets.py            # (archived) Compare BIOPAC vs PsychoPy onsets
│   │   └── archive/             # Archived PsPM MATLAB scripts (SF, DCM, AUC, SCL models)
│   └── video/                   # Scripts for extracting video event onsets
│
├── pilot_data/                  # Pilot data copies for offline troubleshooting — use this folder
│   │                            #   if you don't have Box access (e.g. working on a new machine
│   │                            #   before Box is set up). Normal analysis reads from Box directly.
│   │
│   │   # Note on pilot participants:
│   │   # 001 — EDA and PsychoPy data only. No FaceReader or webcam biometrics were collected.
│   │   # 002 — Full dataset: ECG (Kubios), FaceReader, webcam biometrics, PsychoPy, and EDA.
│   │
│   │   # --- Participant 001 ---
│   ├── 001_carmen_pilot_eda_era.txt                            # Ledalab CDA ERA output (event-related activation per epoch)
│   ├── 001_carmen_pilot_eda_scrlist.txt                        # Ledalab individual SCR event list (onset, amplitude)
│   ├── 001_carmen_pilot_epochs_conditions_psychopy.mat         # PsPM epoch onset file (generated from PsychoPy timing)
│   └── 001_carmen_pilot_epochs_conditions_psychopy_labels.csv  # Condition labels for the above
│   │
│   │   # --- Participant 002 ---
│   │   # --- ECG (Kubios) ---
│   ├── 002_carmen_pilot_physiology_hrv.csv        # Copy of raw Kubios output from Box/kubios/
│   ├── 002_carmen_pilot_kubios_summary.csv        # Tidy extract: one row per block, HRV summary stats
│   ├── 002_carmen_pilot_kubios_rr.csv             # Tidy extract: per-beat RR intervals (block, time_s, rr_s)
│   │
│   │   # --- FaceReader (video HR) ---
│   ├── 002_carmen_pilot_video_20260612_113452_heart beat log.txt   # IBI series from FaceReader
│   ├── 002_carmen_pilot_video_20260612_113452_detailed.txt         # Facial expression probabilities (1 fps)
│   ├── 002_carmen_pilot_20260612_113452_state.txt                  # Dominant expression over time
│   │
│   │   # --- Webcam Biometrics (rPPG) ---
│   ├── 002_carmen_pilot_Biosignals2_internalcamera_Psychopy_2026-06-12_10h55.04.705_biometrics.csv
│   │       # rPPG output: video_time (ms), hr_peak (bool), bpm_fft (reliable), bpm_peak (noisy)
│   ├── 002_carmen_pilot_Biosignals2_internalcamera_Psychopy_2026-06-12_10h55.04.705_clocksync.json
│   │       # Clock sync: mono_reset = 70385.396062 (used to align video time to experiment time)
│   ├── 002_carmen_pilot_frame_timestamps.csv      # Per-frame timestamps for the webcam recording
│   │
│   │   # --- Experiment timing ---
│   ├── 002_carmen_pilot_videorecording_blocks.csv # Block start/end times (nearest_frame_start/end_t)
│   └── 002_carmen_pilot_Biosignals2_internalcamera_Psychopy_2026-06-12_10h55.04.705.csv
│           # PsychoPy trial-level data
│
├── experiment/                  # PsychoPy experiment files (.psyexp, .py) and stimulus lists
└── manuscripts/                 # Preregistration and manuscript drafts
```

---

## EDA (skin conductance) analysis

EDA is analysed using **Ledalab** (MATLAB toolbox, continuous decomposition analysis / CDA method).

**Pipeline:**
1. `analysis/ledalab/01_create_ledalab_events_biopac.py` — reads BIOPAC .acq files directly and writes Ledalab event files (BIOPAC-derived timing). Channel names correctly reflect condition polarity (P=positive, N=negative); see script header for verified mapping.
2. `analysis/ledalab/02_create_ledalab_events_psychopy.py` — reads PsychoPy CSVs + BIOPAC (for clock alignment) and writes Ledalab event files (PsychoPy-derived timing; preferred source).
3. `analysis/ledalab/03_compare_ledalab_events.py` — compares BIOPAC vs PsychoPy onset times; use to verify the BIOPAC channel mapping is correct before running Ledalab.
4. `analysis/ledalab/run_ledalab_batch.m` — runs Ledalab CDA in MATLAB, exports results to Box/ledalab/
5. `analysis/04_analyse_ledalab_scr.Rmd` — statistical analysis of Ledalab output in R

Scripts 1–2 write to `event_onsets/blocks/` and are self-contained — no need to run the PsPM onset scripts first.

**Ledalab output files** (in Box `ledalab/`; participant 001 copies also in `pilot_data/`):
- `{pid}_eda_era.txt` — event-related EDA: one row per epoch, columns include nSCR, latency, amplitude sum, phasic max, tonic, ISCR (CDA and TTP decompositions)
- `{pid}_eda_scrlist.txt` — list of individual SCR events: onset (s) and amplitude (µS)

Both participants (001 and 002) have era and scrlist output in Box `ledalab/`.

**Note on PsPM:** A PsPM spontaneous fluctuation (SF) pipeline was also developed and tested (scripts in `analysis/pspm/`, full documentation in `analysis/pspm/README.md`). It was ultimately not used — the SF model results were not satisfactory (see `analysis/archive/03_analyse_sf.Rmd` for the evaluation). The scripts and documentation are retained for reference.

---

## `03_hr_comparison_pilot.Rmd` — Pilot HR/HRV comparison

This script compares heart rate and HRV across three sources for participant 002:

| Source | Signal | Key data file |
|---|---|---|
| **ECG (Kubios)** | Gold standard — BIOPAC ECG, Kubios HRV | `002_carmen_pilot_kubios_summary.csv` + `_rr.csv` |
| **FaceReader** | Facial video HR (Noldus FaceReader) | `..._heart beat log.txt` |
| **Webcam Biometrics** | rPPG from internal webcam (PsychoPy plugin) | `..._biometrics.csv` |

Metrics compared per block: mean HR, SDNN, RMSSD, LF/HF power.

**Notes:**
- FaceReader data is used as output with no additional filtering.
- Webcam biometrics IBI artifact rejection uses `bpm_fft` (FFT-based HR) as the reference, not the peak-detected median. This is because the rPPG peak detector fires ~30% too often, making the peak-based median unreliable.
- Time alignment for webcam data: `t_video_s = video_time / 1000 - mono_reset`.

---

## Experiment

The PsychoPy experiment files are in `experiment/`.

```
experiment/
├── Biosignals2_internalcamera_Psychopy.psyexp   # PsychoPy Builder file (source of truth)
├── Biosignals2_internalcamera_Psychopy_lastrun.py  # Auto-generated Python (last run)
├── biometrics_server.py      # Companion server for webcam rPPG biometrics plugin
├── negative_stim.csv         # Negative stimulus list
├── positive_stim.csv         # Positive stimulus list
└── rating_images.csv         # Images used in rating screens
```

**To run the experiment:**
1. Open `Biosignals2_internalcamera_Psychopy.psyexp` in PsychoPy Builder.
2. Set counterbalancing manually at the top of the "Begin Experiment" code block (`condition_order`, `rating_start`).
3. Press Run (green play button) or export to Python and run directly.

**Running offline (no BIOPAC/serial trigger box):** The serial trigger flag is set to `False` by default — `USE_REAL_SERIAL = False` in the "Begin Experiment" code block. The experiment will run normally and print trigger events to the console instead of sending them to hardware. Set `USE_REAL_SERIAL = True` in the lab when the trigger box is connected on COM3.

---

## Setup for a new machine

1. Install [Box Drive](https://www.box.com/resources/downloads) and sync `Project_Biosignals_study_2`.
2. Clone this repo.
3. Copy `config_template.R` → `config.R` and set `SERVER_ROOT` to the Box path on your machine. Do the same for `config_template.m` (MATLAB) if needed. (`config.R` and `config.m` are gitignored — never committed.)
4. R analysis: open any `.Rmd` in `analysis/` in RStudio. Each script sources `config.R` automatically via `here::here("config.R")`.
