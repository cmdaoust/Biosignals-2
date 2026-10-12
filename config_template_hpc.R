# config_template_hpc.R
# ======================
# HPC (CISC2 cluster) version of config.R.
# Copy this file to config.R on the HPC and verify paths as needed.
# config.R is gitignored — never commit it.
#
# All R scripts in analysis/ load this automatically.

# The GitHub repo is cloned directly into Biosignals2/; data lives in
# Biosignals2/data/ with the same subfolder structure as the Box 3_Data folder
# (raw_physiology/, pspm/, event_onsets/, etc.).
SERVER_ROOT <- "/mnt/research/cisc2/projects/sdl_emotioncontrol/Biosignals2/data"

# ── Physiology ────────────────────────────────────────────────────────────────
# The BIOPAC recordings live in three stages. Analyses run on the TRIMMED
# recordings (cut to the experimental protocol), because event onsets are
# measured from the start of the file and must match the data being analysed.
PHYSIOLOGY_ROOT        <- file.path(SERVER_ROOT, "raw_physiology")
PHYSIOLOGY_SESSION_DIR <- file.path(PHYSIOLOGY_ROOT, "entire_session_duration")         # as recorded
PHYSIOLOGY_TRIMMED_DIR <- file.path(PHYSIOLOGY_ROOT, "experimental_protocol_duration")  # cut to protocol
PHYSIOLOGY_EXPORTS_DIR <- file.path(PHYSIOLOGY_ROOT, "exports")                         # .mat for Ledalab

# What analyses should use.
RAW_PHYSIOLOGY_DIR     <- PHYSIOLOGY_TRIMMED_DIR
PSYCHOPY_DATA_DIR         <- file.path(SERVER_ROOT, "raw_psychopy")
RAW_QUESTIONNAIRE_DIR     <- file.path(SERVER_ROOT, "raw_questionnaire")
QUESTIONNAIRE_DIR         <- RAW_QUESTIONNAIRE_DIR   # used by 04 and the QC report

COMBINED_DATA_DIR         <- file.path(SERVER_ROOT, "clean_combined_data")
COMBINED_PSYCHO_DIR       <- file.path(COMBINED_DATA_DIR, "psychopy")
COMBINED_QUEST_DIR        <- file.path(COMBINED_DATA_DIR, "questionnaires")
COMBINED_PSYCHO_QUEST_DIR <- file.path(COMBINED_DATA_DIR, "psychopy_questionnaire")

PROCESSED_PHYSIO_DIR      <- file.path(SERVER_ROOT, "pspm", "preprocessed")

BLOCK_ONSETS_DIR          <- file.path(SERVER_ROOT, "event_onsets", "blocks")
VIDEO_ONSETS_DIR          <- file.path(SERVER_ROOT, "event_onsets", "stimulus_videos")

SF_STATS_DIR              <- file.path(SERVER_ROOT, "pspm", "outputs")
