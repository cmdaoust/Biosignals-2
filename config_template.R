# config_template.R — copy to config.R and fill in your paths
# config.R is gitignored — never commit it.

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
RAW_PHYSIOLOGY_DIR     <- PHYSIOLOGY_TRIMMED_DIR
PSYCHOPY_DATA_DIR         <- file.path(SERVER_ROOT, "raw_psychopy")
RAW_QUESTIONNAIRE_DIR     <- file.path(SERVER_ROOT, "raw_questionnaire")

COMBINED_DATA_DIR         <- file.path(SERVER_ROOT, "clean_combined_data")
COMBINED_PSYCHO_DIR       <- file.path(COMBINED_DATA_DIR, "psychopy")
COMBINED_QUEST_DIR        <- file.path(COMBINED_DATA_DIR, "questionnaires")
COMBINED_PSYCHO_QUEST_DIR <- file.path(COMBINED_DATA_DIR, "psychopy_questionnaire")

PROCESSED_PHYSIO_DIR      <- file.path(SERVER_ROOT, "pspm", "preprocessed")

BLOCK_ONSETS_DIR          <- file.path(SERVER_ROOT, "event_onsets", "blocks")
VIDEO_ONSETS_DIR          <- file.path(SERVER_ROOT, "event_onsets", "stimulus_videos")

SF_STATS_DIR              <- file.path(SERVER_ROOT, "pspm", "outputs")

LEDALAB_RESULTS_DIR       <- file.path(SERVER_ROOT, "ledalab")

KUBIOS_DIR                <- file.path(SERVER_ROOT, "kubios")
FACEREADER_DIR            <- file.path(SERVER_ROOT, "video")       # pilot HR-comparison Rmds
VIDEO_BOX_DIR                 <- file.path(SERVER_ROOT, "video")       # Box: webcam recordings + frame timestamps
FACEREADER_RESULTS_DIR    <- file.path(SERVER_ROOT, "facereader")  # FaceReader exports (QC report)
