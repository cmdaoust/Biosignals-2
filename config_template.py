"""
config.py
=========
The ONE Python config for this repo. Every Python script finds it here at the repo root
(do not put copies in analysis/ or its subfolders: they would shadow this file).
TEMPLATE (tracked by git). Copy this file to config.py at the repo root and fill in the paths.
config.py is gitignored: never commit it.
"""
import os


SERVER_ROOT     = r""  # e.g. r"C:\Users\you\Box\Project_Biosignals_study_2\3_Data"

# Data
# ── Physiology ────────────────────────────────────────────────────────────────
# The BIOPAC recordings live in three stages. Analyses run on the TRIMMED
# recordings (cut to the experimental protocol), because event onsets are
# measured from the start of the file and must match the data being analysed.
PHYSIOLOGY_ROOT        = os.path.join(SERVER_ROOT, "raw_physiology")
PHYSIOLOGY_SESSION_DIR = os.path.join(PHYSIOLOGY_ROOT, "entire_session_duration")        # as recorded
PHYSIOLOGY_TRIMMED_DIR = os.path.join(PHYSIOLOGY_ROOT, "experimental_protocol_duration")  # cut to protocol
PHYSIOLOGY_EXPORTS_DIR = os.path.join(PHYSIOLOGY_ROOT, "exports")                        # .mat for Ledalab

# What analyses should use.
RAW_PHYSIOLOGY_DIR     = PHYSIOLOGY_TRIMMED_DIR
PSYCHOPY_DATA_DIR = os.path.join(SERVER_ROOT, "raw_psychopy")
RAW_QUESTIONNAIRE_DIR = os.path.join(SERVER_ROOT, "raw_questionnaire")
COMBINED_DATA_DIR = os.path.join(SERVER_ROOT, "clean_combined_data")
COMBINED_PSYCHO_DIR = os.path.join(COMBINED_DATA_DIR, "psychopy")
COMBINED_QUEST_DIR = os.path.join(COMBINED_DATA_DIR, "questionnaires")
COMBINED_PSYCHO_QUEST_DIR = os.path.join(COMBINED_DATA_DIR, "psychopy_questionnaire")
PROCESSED_PHYSIO_DIR  = os.path.join(SERVER_ROOT, "pspm", "preprocessed")
BLOCK_ONSETS_DIR = os.path.join(SERVER_ROOT, "event_onsets", "blocks")
VIDEO_ONSETS_DIR = os.path.join(SERVER_ROOT, "event_onsets", "stimulus_videos")
FACEREADER_ONSETS_DIR = os.path.join(SERVER_ROOT, "event_onsets", "facereader_video")  # events in FaceReader AVI time

# Webcam (<id>_frames/, <id>_frame_timestamps.csv, <id>_facereader.avi)
WEBCAM_DIR = r""  # e.g. r"D:\Biosignals2_png_data"   # <id>_frames\ + <id>_frame_timestamps.csv
# Where the video analyses SAVE and READ the video files (1to1 .mkv, realtime / 1to1-facereader AVIs,
# plus a copy of each <id>_frame_timestamps.csv): the external hard drive. The PNG originals are
# archived on Box; these videos are working copies that can be rebuilt from them.
VIDEO_EXTERNAL_DIR = r""  # e.g. r"D:\Biosignals2_video"
# WebcamBiometrics code (used by 003_run_webcam_biometrics.py). Moved out of OneDrive on 7 Oct 2026.
WEBCAM_BIOMETRICS_REPO = r""  # e.g. r"C:\Users\you\Documents\WebcamBiometrics"
# Webcam, older sessions recorded straight to AVI (<id>_frame_timestamps.csv, <id>_recording.avi)
OLD_WEBCAM_DIR = os.path.join(SERVER_ROOT, "video")
LEDALAB_RESULTS_DIR = os.path.join(SERVER_ROOT, "ledalab")
# Ledalab input: EDA-only .mat files prepared for Ledalab
LEDALAB_INPUT_DIR = os.path.join(SERVER_ROOT, "ledalab", "input")
