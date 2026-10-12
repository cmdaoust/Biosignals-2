# Biosignals2 — Project Data & Code Overview

This document is for collaborators. It covers where data lives, what each file/folder contains, and how the two storage locations relate to each other.

---

## Storage locations

| Location | Purpose |
|---|---|
| **Box** — `Project_Biosignals_study_2/3_Data/` | All raw and processed data (shared server) |
| **GitHub** — `Biosignals-2/` | Analysis code, config, protocols and QC reports (no data) |

Box is not included in the GitHub repo. Code references Box paths via `config.py` (see below).

> **Note:** this repo (`Biosignals-2`) replaced the earlier `Biosignals2` repo on 12 Oct 2026. It started
> with a fresh history from the last `Biosignals2` commit (`384e31d`). `manuscripts/` and `pilot_data/`
> are gitignored and are not in this repo or its history. The old `Biosignals2` repo is kept for its
> history only.

---

## Quality-check reports

| Report | Covers | Regenerate with |
|---|---|---|
| [Main-study QC dashboard](https://cmdaoust.github.io/Biosignals-2/analysis/biosignals2_qc.html) | Main-study participants | `analysis/generate_qc_report.R` |
| [Pilot QC report](https://cmdaoust.github.io/Biosignals-2/analysis/biosignals2_qc_pilot.html) | Pilot participants only | `analysis/generate_qc_report_pilot.R` |

Each report checks PsychoPy self-report, Ledalab (EDA), Kubios (HRV), webcam biometrics, video,
FaceReader and questionnaires. Sections for data that isn't available yet are left out rather than failing.
The reports are snapshots: re-run the script and commit the new `.html` to update them.

The links open the live pages on GitHub Pages, which show whatever was last pushed to `main`.
After regenerating a report, push the new `.html` (Pages takes a minute or two to update).

**Session protocol checklist:** [biosignals2-protocol-checklist.html](https://cmdaoust.github.io/Biosignals-2/protocol_instructions/biosignals2-protocol-checklist.html)
(source: `protocol_instructions/biosignals2-protocol-checklist.html`).

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

Root: `C:\Users\carme\Documents\Biosignals-2\` (outside OneDrive, which can lock or revert files in `.git`)

```
Biosignals-2/
├── config.py                    # Maps Box subdirectory paths — update SERVER_ROOT for your machine
├── config.R                     # Same paths for R scripts
├── config.m                     # Same paths for MATLAB scripts
├── config_template.py / .R / .m # Templates with placeholder paths (for new machines)
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
│   ├── generate_qc_report.R     # Builds biosignals2_qc.html (main-study QC dashboard)
│   ├── generate_qc_report_pilot.R  # Builds biosignals2_qc_pilot.html (pilot participants)
│   ├── biosignals2_qc.html      # Main-study QC dashboard (see "Quality-check reports" above)
│   ├── biosignals2_qc_pilot.html   # Pilot QC report
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
├── pilot_data/                  # NOT IN GIT (gitignored). Local pilot data copies for offline
│                                #   troubleshooting without Box. Pilot 001: EDA + PsychoPy only.
│                                #   Pilot 002: full dataset (ECG/Kubios, FaceReader, webcam, PsychoPy, EDA).
│                                #   Get the files from Box; the analysis normally reads Box directly.
├── experiment/                  # PsychoPy experiment files (.psyexp, .py) and stimulus lists
└── manuscripts/                 # NOT IN GIT (gitignored). Preregistration and manuscript drafts
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

**Ledalab output files** (in Box `ledalab/`; participant 001 copies may also be in your local, untracked `pilot_data/`):
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
2. Clone this repo. It contains no data: `pilot_data/` and `manuscripts/` are gitignored, so copy them from Box if you need them.
3. At the repo root, copy each template and fill in your paths: `config_template.py` → `config.py` (Python), `config_template.R` → `config.R` (R) and `config_template.m` → `config.m` (MATLAB). There is **one** config per language, at the repo root; every script finds it there. Don't put copies in `analysis/` or its subfolders. All three are gitignored and never committed.
4. R analysis: open any `.Rmd` in `analysis/` in RStudio. Each script sources `config.R` automatically via `here::here("config.R")`.
