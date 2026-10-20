# config_template.R
# =================
# Copy this file to config.R at the repo root and fill in the paths.
# config.R is gitignored: never commit it.
# Same variables as config_template.py (plus a few R-only ones at the end).

SERVER_ROOT <- ""  # e.g. "C:/Users/you/Box/Project_Biosignals_study_2/3_Data"

# ── Physiology ────────────────────────────────────────────────────────────────
# The BIOPAC recordings live in three stages. Analyses run on the TRIMMED
# recordings (cut to the experimental protocol), because event onsets are
# measured from the start of the file and must match the data being analysed.
PHYSIOLOGY_ROOT        <- file.path(SERVER_ROOT, "raw_physiology")
PHYSIOLOGY_SESSION_DIR <- file.path(PHYSIOLOGY_ROOT, "entire_session_duration")         # as recorded
PHYSIOLOGY_TRIMMED_DIR <- file.path(PHYSIOLOGY_ROOT, "experimental_protocol_duration")  # cut to protocol
PHYSIOLOGY_EXPORTS_DIR <- file.path(PHYSIOLOGY_ROOT, "exports")                         # .mat for Ledalab

# What analyses should use.
RAW_PHYSIOLOGY_DIR        <- PHYSIOLOGY_TRIMMED_DIR
PSYCHOPY_DATA_DIR         <- file.path(SERVER_ROOT, "raw_psychopy")
RAW_QUESTIONNAIRE_DIR     <- file.path(SERVER_ROOT, "raw_questionnaire")
COMBINED_DATA_DIR         <- file.path(SERVER_ROOT, "clean_combined_data")
COMBINED_PSYCHO_DIR       <- file.path(COMBINED_DATA_DIR, "psychopy")
COMBINED_QUEST_DIR        <- file.path(COMBINED_DATA_DIR, "questionnaires")
COMBINED_PSYCHO_QUEST_DIR <- file.path(COMBINED_DATA_DIR, "psychopy_questionnaire")
PROCESSED_PHYSIO_DIR      <- file.path(SERVER_ROOT, "pspm", "preprocessed")
BLOCK_ONSETS_DIR          <- file.path(SERVER_ROOT, "event_onsets", "blocks")
VIDEO_ONSETS_DIR          <- file.path(SERVER_ROOT, "event_onsets", "stimulus_videos")
FACEREADER_ONSETS_DIR     <- file.path(SERVER_ROOT, "event_onsets", "facereader_video")  # events in FaceReader AVI time
FACEREADER_RESULTS_DIR    <- file.path(SERVER_ROOT, "facereader")  # FaceReader exports

# Webcam (<id>_frames/, <id>_frame_timestamps.csv, <id>_facereader.avi)
WEBCAM_PNG_EXTERNAL_DIR   <- ""  # e.g. "D:/Biosignals2_png_data"; external hard drive: <id>_frames/ + <id>_frame_timestamps.csv
# Where the video analyses SAVE and READ the video files (1to1 .mkv, realtime / 1to1-facereader AVIs,
# plus a copy of each <id>_frame_timestamps.csv): the external hard drive. The PNG originals are
# archived on Box; these videos are working copies that can be rebuilt from them.
VIDEO_EXTERNAL_DIR        <- ""  # e.g. "D:/Biosignals2_video"; external hard drive (not Box)
# WebcamBiometrics code (used by 002_run_webcam_biometrics.py)
WEBCAM_BIOMETRICS_REPO    <- ""  # e.g. "C:/Users/you/Documents/WebcamBiometrics"
# Webcam, older sessions recorded straight to AVI (<id>_frame_timestamps.csv, <id>_recording.avi)
VIDEO_BOX_DIR             <- file.path(SERVER_ROOT, "video")   # Box
LEDALAB_RESULTS_DIR       <- file.path(SERVER_ROOT, "ledalab")
# Ledalab input: EDA-only .mat files prepared for Ledalab
LEDALAB_INPUT_DIR         <- file.path(SERVER_ROOT, "ledalab", "input")

# ── R only ────────────────────────────────────────────────────────────────────
QUESTIONNAIRE_DIR         <- RAW_QUESTIONNAIRE_DIR   # used by 04 and the QC report
KUBIOS_RESULTS_DIR        <- file.path(SERVER_ROOT, "kubios")      # Kubios HRV reports (QC report, 003_compare_hrv.R)
KUBIOS_DIR                <- KUBIOS_RESULTS_DIR                    # old name, pilot HR-comparison Rmds
FACEREADER_DIR            <- file.path(SERVER_ROOT, "video")       # pilot HR-comparison Rmds
SF_STATS_DIR              <- file.path(SERVER_ROOT, "pspm", "outputs")
