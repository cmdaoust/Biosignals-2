#!/usr/bin/env Rscript
# =============================================================================
# 08_combine_timeseries.R
# =============================================================================
# Stacks the detailed (time-series / per-beat / per-sample) outputs of every
# MAIN-STUDY participant into one file per data source. Pilots, test sessions
# and excluded participants (participant_status.csv) are left out.
#
# OUTPUT  (SHAREABLE_DATA_DIR = Box 3_Data/clean_combined_data/shareable) - the files to share
#   biosignals2_questionnaires_scores.csv     Questionnaire scores (from 04), minus DROP_COLUMNS
#   biosignals2_self-report_rating.csv        Self-report ratings (from 01), minus trigger_name
#   biosignals2_ts_webcambiometrics_offline.csv  Webcam beats from 002_run_webcam_biometrics.py (OFFLINE,
#                                             variant WEBCAM_OFFLINE_VARIANT), one row per beat, by block
#   (off) biosignals2_ts_webcambiometrics_online.csv  PsychoPy's live (ONLINE) stream from 01
#   biosignals2_ts_ecg_kubios.csv             ECG: Kubios per-beat RR series, all 5 blocks
#   biosignals2_ts_facereader_kubios.csv      FaceReader heart beats: Kubios per-beat RR series
#   biosignals2_ts_facereader_au.csv          FaceReader action units, one row per video frame, on
#                                             the recording clock, labelled with block + video
#   biosignals2_ts_eda_ledalab.csv            Ledalab: every detected SCR (onset, amplitude, ...),
#                                             labelled with the block it falls in
#   Block level (one row per participant x block):
#   biosignals2_block_eda_ledalab.csv         Ledalab ERA per block  <- clean_combined_data/temp/biosignals2_eda.csv (05)
#   biosignals2_block_ecg_kubios.csv          ECG Kubios per block   <- kubios/KubiosHRVresults.csv (batch export)
#   biosignals2_block_facereader_kubios.csv   FaceReader Kubios per block <- facereader/KubiosHRVresults.csv (batch export)
#   biosignals2_clock_offsets.csv             Webcam -> BIOPAC clock offset per participant <- 3_Data/ecg_video_offsets.csv (002)
#   biosignals2_README.md + biosignals2_data_dictionary.csv  What every file / column is, clocks,
#                                             caveats - generated each run from data_dictionary.R
#   Every file: participant_id (code) + block (BLOCK_LEVELS in data_dictionary.R) first.
#   Switched off for now (toggles below): Kubios spectrum (KUBIOS_SPECTRUM), demographics
#   (WRITE_DEMOGRAPHICS), Ledalab continuous decomposition (LEDALAB_CONTINUOUS).
#   Columns removed before writing: DROP_COLUMNS below.
#   Participant IDs are replaced by codes P01, P02, ... from the ONE key shared with the interim
#   report (07): 3_Data/private/interim_report_id_key.csv, see analysis/id_key.R. The two check
#   files below are saved in 3_Data/private/ too (they hold real IDs).
#      biosignals2_ts_sources.csv             Which input file each participant's rows came from,
#                                             and what was skipped and why
#   (off) biosignals2_ts_demographics.csv     Baseline (Demographics) survey: participant_id + the survey
#                                             answers only - no Qualtrics metadata (dates, IP, location,
#                                             ResponseId, recipient fields) and nothing email-related
#                                             Answer codes turned into answer text (DEMOGRAPHICS_LABELS)
#      biosignals2_ts_demographics_questions.csv  Column -> question text for that file
#      biosignals2_ts_coverage.csv            One row per participant: which sources they have,
#                                             blocks found, complete yes/no, written yes/no
#
# INPUT  (paths from config.R)
#   ECG Kubios report         <pid>_*hrv*.csv  in KUBIOS_RESULTS_DIR or RAW_PHYSIOLOGY_DIR
#                             (not facereader / webcam reports; must contain "RR INTERVAL DATA")
#   FaceReader Kubios report  <pid>_*facereader*_hrv.csv in FACEREADER_RESULTS_DIR, its kubios/
#                             subfolder, or KUBIOS_RESULTS_DIR
#   FaceReader detailed log   .txt / .xlsx in FACEREADER_RESULTS_DIR with a "Video Time" header row
#                             (participant = the log's Filename row, as in 03_facial_expression_analysis).
#                             1:1 / _recording videos: times remapped to real time through
#                             <pid>_frame_timestamps.csv (FRAME_TIMESTAMP_DIRS). Realtime videos: as is.
#                             Labels from FACEREADER_ONSETS_DIR/<pid>_video_events.csv (onset_s/offset_s).
#                             .xlsx needs readxl.
#   Webcam ONLINE             COMBINED_PSYCHO_DIR/biosignals2_webcambiometrics_online.csv (run 01 first)
#   Webcam OFFLINE            WEBCAM_HR_DIR/<pid>_webcam_beats_<variant>.csv (002_run_webcam_biometrics.py)
#   Self-report ratings       COMBINED_PSYCHO_DIR/biosignals2_selfreport_ratings.csv (run 01 first)
#   Questionnaire scores      COMBINED_PSYCHO_DIR/biosignals2_questionnaires_scored.csv (run 04 first)
#   Ledalab                   LEDALAB_RESULTS_DIR/<pid>_scrlist.txt (+ <pid>.mat for continuous)
#                             BLOCK_ONSETS_DIR/<pid>_events_blocks_biopac_ledalab.txt and
#                             nid_map_biopac_ledalab.txt (block onsets used to label the SCRs)
#   Demographics              QUESTIONNAIRE_DIR/Demographics_combined.csv (combine_qualtrics_exports.R;
#                             3 Qualtrics header rows). Completed responses only (Finished, Progress 100);
#                             ID = QID7_1, as in 04_questionnaire_analysis.Rmd; several responses with
#                             one ID -> the latest (EndDate) is used, the others are listed.
#
# If a participant has several candidate files of one kind, the newest is used and the
# others are listed in biosignals2_ts_sources.csv. IDs are lower-cased in every output.
#
# HOW TO RUN
#   Rscript analysis/08_combine_timeseries.R     (or open in RStudio and click Source)
#   Base R only. Optional: data.table (faster for the big PsychoPy file), R.matlab
#   (Ledalab continuous decomposition).
# =============================================================================

# ── Options ───────────────────────────────────────────────────────────────────
# COMPLETE_CASES_ONLY
#   FALSE = every main-study participant goes into every file they have data for.
#   TRUE  = first check which participants have data in ALL the sources in REQUIRED_SOURCES,
#           then write only those participants, in every output file (the same IDs everywhere).
#   Either way, biosignals2_ts_coverage.csv shows who has what (one row per participant).
#   "Has data" = a usable file was read for that source (Ledalab: an SCR list, even if it holds
#   no SCRs). It does not check that all 5 blocks are present - see n_blocks in the coverage file.
COMPLETE_CASES_ONLY <- TRUE
REQUIRED_SOURCES    <- c("ecg_kubios", "facereader_kubios", "facereader_au",
                         "ledalab_scr", "questionnaires", "ratings",
                         "block_eda", "block_kubios_ecg", "block_kubios_facereader")
#   webcam offline is not required (or written) while WRITE_WEBCAM_OFFLINE is FALSE - when it is
#   turned on, add "webcambiometrics_offline" here too
#   add "demographics" here only if WRITE_DEMOGRAPHICS is TRUE

# Which outputs are made (FALSE = not read, not written, not counted for complete cases)
WRITE_DEMOGRAPHICS <- FALSE  # biosignals2_ts_demographics.csv (+ _questions.csv)
# Webcam biometrics: ONLINE = computed live by PsychoPy during the session (01's
# biosignals2_webcambiometrics_online.csv); OFFLINE = 002_run_webcam_biometrics.py on the 1:1 video.
WRITE_WEBCAM_ONLINE    <- FALSE        # biosignals2_ts_webcambiometrics_online.csv (01 labels pilots only)
WRITE_WEBCAM_OFFLINE   <- FALSE        # biosignals2_ts_webcambiometrics_offline.csv - off until the offline
                                       # beats are less noisy (Carmen, 29 Oct); TRUE + add to REQUIRED_SOURCES
WEBCAM_OFFLINE_VARIANT <- "optimized"  # which 002 code version: baseline / faceloss / optimized
KUBIOS_SPECTRUM    <- FALSE  # biosignals2_ts_*_kubios_spectrum.csv - to revisit later

# Columns removed from each shared file. A listed column that isn't in the data is reported
# in the console (so a typo or a renamed column shows up), never an error.
kubios_drop <- c("source_file", "ecg_mv", "marker", "block_order", "block_start_s", "block_end_s",
                 "t_from_block_start_s")
DROP_COLUMNS <- list(
  "biosignals2_questionnaires_scores.csv" = c("gad7_severity", "phq9_severity", "gad7_n_missing",
      "phq9_n_missing", "aq10_n_missing", "paq_n_missing", "das_sf1_n_missing", "das_sf2_n_missing",
      "phq9_item9_flagged"),
  "biosignals2_self-report_rating.csv"    = c("trigger_name", "conditionOrder"),  # conditionOrder: same for everyone (always negative first)
  "biosignals2_ts_ecg_kubios.csv"         = kubios_drop,
  "biosignals2_ts_facereader_kubios.csv"  = kubios_drop,
  "biosignals2_ts_facereader_au.csv"      = c("source_file", "block_order"),
  "biosignals2_ts_webcambiometrics_offline.csv" = c("source_file"),
  "biosignals2_ts_eda_ledalab.csv"        = c("source_file"),
  "biosignals2_block_ecg_kubios.csv"        = c("block_order"),
  "biosignals2_block_facereader_kubios.csv" = c("block_order")
)
#   add "ledalab_continuous" to also require the Ledalab .mat decomposition (needs R.matlab)

# Demographics survey (Qualtrics)
DEMOGRAPHICS_FILE       <- "Demographics_combined.csv"   # in QUESTIONNAIRE_DIR
DEMOGRAPHICS_ID_IMPORT  <- "QID7_1"                      # ImportId of the participant ID question
DEMOGRAPHICS_EMAIL_COLS <- c("Q51")                      # the email question (as in questionniare_followup_dates.R);
                                                         # any other column whose name or question text mentions
                                                         # email is dropped too; an email address typed into any
                                                         # other answer (e.g. a comment) is blanked

# Answer codes -> answer text (e.g. QID3: 0 -> "Male"). The values export stores the choice code.
#   DEMOGRAPHICS_LABELS = TRUE  replace codes with the answer text
#   Labels come from (first that has the column):
#     1. the survey file (.qsf): Qualtrics > survey > Tools > Import/Export > Export survey. Save it in
#        RAW_QUESTIONNAIRE_DIR or QUESTIONNAIRE_DIR (or set DEMOGRAPHICS_QSF). This is exact for
#        every question - recommended. Needs jsonlite.
#     2. DEMOGRAPHICS_CODE_LABELS below (copied from 04_questionnaire_analysis.Rmd).
#   A code with no label stays visible as "code <n>" (never guessed). Columns with no labels at all
#   (age, free text, any question not listed) are left as they are. The questions file says which.
DEMOGRAPHICS_LABELS <- TRUE
DEMOGRAPHICS_QSF    <- NA_character_   # NA = look for a *.qsf in the questionnaire folders
lab <- function(...) { x <- c(...); setNames(unname(x), names(x)) }
DEMOGRAPHICS_CODE_LABELS <- list(
  # column ImportId (exact) or prefix ending in "_" (all its items) = c(code = "text")
  # 04 says only the sex / gender / ethnicity codes seen in the pilot data were verified.
  QID3 = lab("0" = "Male", "1" = "Female"),                                    # sex at birth
  QID4 = lab("1" = "Yes"),                                                     # gender identity
  QID5 = lab("1" = "Asian (any background)", "2" = "Black (any background)",   # ethnicity
             "3" = "Mixed (any background)", "4" = "White (any background)"),
  QID8_  = lab("0" = "Not at all", "1" = "Several days",                       # GAD-7
               "2" = "More than half the days", "3" = "Nearly every day"),
  QID10_ = lab("0" = "Not at all", "1" = "Several days",                       # PHQ-9 items 1-5
               "2" = "More than half of the days", "3" = "Nearly every day"),
  QID32_ = lab("0" = "Not at all", "1" = "Several days",                       # PHQ-9 items 6-9
               "2" = "More than half of the days", "3" = "Nearly every day"),
  QID42_ = lab("1" = "Definitely agree", "2" = "Slightly agree",               # AQ-10
               "3" = "Slightly disagree", "4" = "Definitely disagree"),
  # PAQ-24 (1-7). In the survey only some points have text, so 2/3/5/6 use 04's wording.
  QID43_ = (paq <- lab("1" = "Strongly disagree", "2" = "Disagree", "3" = "Slightly disagree",
                       "4" = "Neither agree nor disagree", "5" = "Slightly agree", "6" = "Agree",
                       "7" = "Strongly agree")),
  QID44_ = paq, QID45_ = paq, QID51_ = paq, QID52_ = paq, QID53_ = paq,
  # DAS-SF 1 + 2 (1-7). Direction as in 04 (marked "verify against your scoring key" there).
  QID59_ = (das <- lab("1" = "Totally Disagree", "2" = "Disagree", "3" = "Slightly Disagree",
                       "4" = "Neutral", "5" = "Slightly Agree", "6" = "Agree", "7" = "Totally Agree")),
  QID60_ = das
)

# Participant codes instead of IDs (PSEUDONYMISE_IDS = TRUE)
#   In every data file the participant ID (e.g. s1250) becomes a code P01, P02, ... - in the
#   participant_id column AND anywhere else it appears (e.g. file names in source_file).
#   The key is the interim report's (07) key, 3_Data/private/interim_report_id_key.csv, handled by
#   analysis/id_key.R: one code per person in every output. Codes are kept from run to run and never
#   reused; new participants get the next free numbers in a random order. The run stops rather than
#   start a new key if the key is missing (with backups present), unreadable or inconsistent.
#   The two check files (sources, coverage) list real IDs and file names, so they are saved in
#   3_Data/private/ too, not in clean_combined_data.
PSEUDONYMISE_IDS <- TRUE

LEDALAB_CONTINUOUS <- FALSE # also export the Ledalab decomposition from <pid>.mat (needs R.matlab)
BLOCK_WINDOW_S     <- 180    # Ledalab block length used to label SCRs / samples (= ERA window 0-180 s)
FR_EXTRA_COLUMNS   <- FALSE  # TRUE = also keep FaceReader emotions, valence and arousal next to the AUs
MIN_VIDEO_FPS      <- 5      # a FaceReader 'Frame rate' below this is a reduced export rate (as in 03)

# ── Config + participant status ──────────────────────────────────────────────
find_project_root <- function() {
  f <- sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE))
  of <- NULL
  for (i in rev(seq_len(sys.nframe()))) { of <- sys.frame(i)$ofile; if (!is.null(of)) break }
  starts <- c(if (length(f)) dirname(f[1]), if (!is.null(of)) dirname(of),
              tryCatch(dirname(rstudioapi::getSourceEditorContext()$path), error = function(e) NA_character_),
              getwd())
  for (d in starts[!is.na(starts) & nzchar(starts)]) {
    d <- normalizePath(d, winslash = "/", mustWork = FALSE)
    repeat {
      if (file.exists(file.path(d, "config.R"))) return(d)
      parent <- dirname(d); if (parent == d) break; d <- parent
    }
  }
  stop("config.R not found in this script's folder or any folder above it.")
}
config_path <- file.path(find_project_root(), "config.R")
source(config_path)
analysis_dir <- local({ d <- dirname(normalizePath(config_path)); if (basename(d) == "analysis") d else file.path(d, "analysis") })

# Main study only, so the status file is required (no silent "keep everyone" fallback).
PARTICIPANT_STATUS_PATH <- get0("PARTICIPANT_STATUS_PATH", ifnotfound = file.path(SERVER_ROOT, "participant_status.csv"))
source(file.path(analysis_dir, "participant_status.R"), local = TRUE)
is_main <- function(pid) participant_keep(pid, include_pilots = FALSE)

KUBIOS_RESULTS_DIR     <- get0("KUBIOS_RESULTS_DIR",     ifnotfound = file.path(SERVER_ROOT, "kubios"))
RAW_PHYSIOLOGY_DIR     <- get0("RAW_PHYSIOLOGY_DIR",     ifnotfound = file.path(SERVER_ROOT, "raw_physiology", "experimental_protocol_duration"))
FACEREADER_RESULTS_DIR <- get0("FACEREADER_RESULTS_DIR", ifnotfound = file.path(SERVER_ROOT, "facereader"))
COMBINED_DATA_DIR      <- get0("COMBINED_DATA_DIR",      ifnotfound = file.path(SERVER_ROOT, "clean_combined_data"))
COMBINED_PSYCHO_DIR    <- get0("COMBINED_PSYCHO_DIR",    ifnotfound = file.path(COMBINED_DATA_DIR, "temp"))
LEDALAB_RESULTS_DIR    <- get0("LEDALAB_RESULTS_DIR",    ifnotfound = file.path(SERVER_ROOT, "ledalab"))
BLOCK_ONSETS_DIR       <- get0("BLOCK_ONSETS_DIR",       ifnotfound = file.path(SERVER_ROOT, "event_onsets", "blocks"))
FACEREADER_ONSETS_DIR  <- get0("FACEREADER_ONSETS_DIR",  ifnotfound = file.path(SERVER_ROOT, "event_onsets", "facereader_video"))
FRAME_TIMESTAMP_DIRS   <- get0("FRAME_TIMESTAMP_DIRS",   ifnotfound = c(file.path(SERVER_ROOT, "video"),
                                                                       "D:/Biosignals2_video", "D:/Biosignals2_png_data"))
QUESTIONNAIRE_DIR      <- get0("QUESTIONNAIRE_DIR",      ifnotfound = file.path(SERVER_ROOT, "raw_questionnaire", "combined"))

SHAREABLE_DATA_DIR     <- get0("SHAREABLE_DATA_DIR",     ifnotfound = file.path(COMBINED_DATA_DIR, "shareable"))
OUT_DIR <- SHAREABLE_DATA_DIR  # Box 3_Data/clean_combined_data/shareable (from config.R)
dir.create(OUT_DIR, showWarnings = FALSE, recursive = TRUE)
PRIVATE_DIR <- file.path(SERVER_ROOT, "private")          # ID key + check files with real IDs
source(file.path(analysis_dir, "id_key.R"), local = TRUE)
source(file.path(analysis_dir, "data_dictionary.R"), local = TRUE)   # README + data dictionary, canon_block()
ID_KEY_PATH <- id_key_path(SERVER_ROOT)                   # shared with 07_interim_summary.Rmd
LOG_DIR     <- if (PSEUDONYMISE_IDS) PRIVATE_DIR else OUT_DIR

# ── Helpers ───────────────────────────────────────────────────────────────────
say <- function(...) cat(sprintf(...), "\n", sep = "")
num <- function(x) suppressWarnings(as.numeric(x))
pid_of <- function(f) tolower(sub("_.*$", "", sub("\\.[^.]*$", "", basename(f))))

list_files <- function(dirs, pattern) {
  dirs <- unique(dirs[dir.exists(dirs)])
  as.character(unique(unlist(lapply(dirs, list.files, pattern = pattern, ignore.case = TRUE, full.names = TRUE))))
}

clean_names <- function(x) {
  x <- tolower(trimws(x))
  x <- gsub("%", "pct", x, fixed = TRUE)
  x <- gsub("[^a-z0-9]+", "_", x)
  x <- gsub("^_+|_+$", "", x)
  x[!nzchar(x)] <- "col"
  make.unique(x, sep = "_")
}

hms <- function(s) {
  p <- num(strsplit(trimws(s), ":", fixed = TRUE)[[1]])
  if (length(p) == 3 && !anyNA(p)) return(p[1] * 3600 + p[2] * 60 + p[3])
  num(s)
}

# "neg_induction(2)", "negative_reconvery(3)" -> negative_induction, negative_recovery
norm_block <- function(x) {
  x <- tolower(trimws(sub("\\(\\d+\\)$", "", trimws(x))))
  x <- gsub("[ -]+", "_", x)
  x <- sub("^neg_", "negative_", x); x <- sub("^pos_", "positive_", x)
  sub("reconvery", "recovery", x)
}

# Bind data frames with different columns (base R).
rbind_fill <- function(dfs) {
  dfs <- Filter(function(d) !is.null(d) && nrow(d) > 0, dfs)
  if (!length(dfs)) return(data.frame())
  cols <- unique(unlist(lapply(dfs, names)))
  do.call(rbind, lapply(dfs, function(d) {
    for (m in setdiff(cols, names(d))) d[[m]] <- NA
    d[, cols, drop = FALSE]
  }))
}

# Data files are held back (PENDING) until the end, so the complete-cases filter can be applied
# to all of them at once. Files without a source (the logs) are written straight away.
PENDING <- list()
write_out <- function(df, name, source = NULL) {
  if (!is.null(source)) { PENDING[[name]] <<- list(df = df, source = source); return(invisible(NULL)) }
  write_file(df, name)
}
write_file <- function(df, name, dir = OUT_DIR) {
  dir.create(dir, showWarnings = FALSE, recursive = TRUE)
  path <- file.path(dir, name)
  if (!nrow(df)) { say("  %s: no rows - not written", name); return(invisible(NULL)) }
  if (requireNamespace("data.table", quietly = TRUE)) data.table::fwrite(df, path)
  else utils::write.csv(df, path, row.names = FALSE, na = "")
  if ("participant_id" %in% names(df)) say("  -> %s  (%d rows, %d participants)", name, nrow(df), length(unique(df$participant_id)))
  else say("  -> %s  (%d rows)", name, nrow(df))
}

# Source log: one row per participant x source.
sources <- list()
log_src <- function(source, pid, status, file = NA_character_, note = NA_character_)
  sources[[length(sources) + 1]] <<- data.frame(source = source, participant_id = pid, status = status,
                                                file = file, note = note, stringsAsFactors = FALSE)

# Newest file per participant (main study only); everything else is logged.
pick_per_pid <- function(files, source) {
  if (!length(files)) return(character(0))
  pids <- pid_of(files)
  drop <- !is_main(pids)
  for (p in unique(pids[drop])) log_src(source, p, "left out", note = participant_status_of(p))
  files <- files[!drop]; pids <- pids[!drop]
  out <- character(0)
  for (p in unique(pids)) {
    f <- files[pids == p]
    f <- f[order(file.mtime(f), decreasing = TRUE)]
    if (length(f) > 1) log_src(source, p, "not used (older duplicate)", basename(f[-1]))
    out[p] <- f[1]
  }
  out
}

# ── Kubios report reader: the RR INTERVAL DATA section, all columns ───────────
# Kubios report CSV (no quoting). The RR section is:
#   RR INTERVAL DATA
#   , <sample 1 name>, ..., , <sample 2 name>, ...   <- block name above each block's first column
#   (1-3 header rows with column names, e.g. "Time (s)", "RR interval (s)")
#   numeric rows ... until a blank line or the next section title
# Each block's columns run from its name to the next block's name. Columns whose header mentions
# frequency / PSD / spectrum are per-frequency, not per-beat, and go to a separate spectrum table.
read_kubios_timeseries <- function(path) {
  L <- readLines(path, warn = FALSE, encoding = "UTF-8")
  L[1] <- sub("^﻿", "", L[1])
  f <- lapply(L, function(l) trimws(gsub('^"|"$', "", strsplit(l, ",", fixed = TRUE)[[1]])))
  first <- vapply(f, function(x) if (length(x)) x[1] else "", "")

  i_rr <- which(startsWith(toupper(first), "RR INTERVAL DATA"))[1]
  if (is.na(i_rr)) stop("no 'RR INTERVAL DATA' section")

  # block windows from "Sample limits (hh:mm:ss):, 00:01:00-00:04:00, ..."
  i_lim <- which(startsWith(first, "Sample limits"))[1]
  win <- NULL
  if (!is.na(i_lim)) {
    lim <- f[[i_lim]][-1]; lim <- lim[nzchar(lim)]
    win <- t(vapply(strsplit(lim, "-", fixed = TRUE), function(p) c(hms(p[1]), hms(p[2])), c(0, 0)))
  }

  hdr  <- f[[i_rr + 1]]
  cols <- which(nzchar(hdr))
  if (!length(cols)) stop("RR INTERVAL DATA: no block names on the line below the section title")
  blocks <- norm_block(hdr[cols])

  # data rows: from the first row with a number in a block column, until blank / next section
  is_num_row <- function(x) any(!is.na(num(x[intersect(cols, seq_along(x))])))
  i <- i_rr + 2
  while (i <= length(f) && !is_num_row(f[[i]])) i <- i + 1
  if (i > length(f)) stop("RR INTERVAL DATA: no numeric rows")
  head_rows <- if (i > i_rr + 2) (i_rr + 2):(i - 1) else integer(0)
  j <- i
  while (j <= length(f) && any(nzchar(f[[j]])) &&
         !(grepl("^[A-Za-z]", first[j]) && is.na(num(first[j])) && !is_num_row(f[[j]]))) j <- j + 1
  body <- f[i:(j - 1)]
  width <- max(lengths(c(body, f[head_rows])), max(cols))
  pad <- function(x) { length(x) <- width; x[is.na(x)] <- ""; x }
  M <- do.call(rbind, lapply(body, pad))
  H <- if (length(head_rows)) do.call(rbind, lapply(f[head_rows], pad)) else matrix("", 0, width)
  colname <- vapply(seq_len(width), function(k) paste(H[nzchar(H[, k]), k], collapse = " "), "")

  ends <- c(cols[-1] - 1, width)
  beats <- list(); spec <- list()
  for (b in seq_along(cols)) {
    idx <- cols[b]:ends[b]
    nm  <- colname[idx]
    keep <- nzchar(nm) | apply(M[, idx, drop = FALSE], 2, function(v) any(nzchar(v)))
    idx <- idx[keep]; nm <- nm[keep]
    if (!length(idx)) next
    nm[!nzchar(nm)] <- paste0("col", which(!nzchar(nm)))
    is_spec <- grepl("freq|psd|spectr|power|hz", nm, ignore.case = TRUE)
    mk <- function(ii, nn) {
      d <- as.data.frame(lapply(ii, function(k) { v <- M[, k]; if (all(is.na(num(v[nzchar(v)])))) v else num(v) }),
                         stringsAsFactors = FALSE)
      names(d) <- clean_names(nn)
      d[apply(d, 1, function(r) any(!is.na(r) & r != "")), , drop = FALSE]
    }
    bstart <- if (!is.null(win) && b <= nrow(win)) win[b, 1] else NA_real_
    bend   <- if (!is.null(win) && b <= nrow(win)) win[b, 2] else NA_real_
    if (any(!is_spec)) {
      d <- mk(idx[!is_spec], nm[!is_spec])
      tcol <- grep("time", names(d), value = TRUE)[1]; if (is.na(tcol)) tcol <- names(d)[1]
      d <- d[!is.na(num(d[[tcol]])), , drop = FALSE]
      if (nrow(d)) {
        d <- cbind(block = blocks[b], block_order = b, block_start_s = bstart, block_end_s = bend,
                   beat = seq_len(nrow(d)), d, stringsAsFactors = FALSE)
        d$t_from_block_start_s <- num(d[[tcol]]) - bstart
        beats[[length(beats) + 1]] <- d
      }
    }
    if (any(is_spec)) {
      d <- mk(idx[is_spec], nm[is_spec])
      if (nrow(d)) spec[[length(spec) + 1]] <- cbind(block = blocks[b], block_order = b, d, stringsAsFactors = FALSE)
    }
  }
  list(beats = rbind_fill(beats), spectrum = rbind_fill(spec))
}

combine_kubios <- function(files, source, out_name) {
  say("\n== %s: %d candidate Kubios report(s)", source, length(files))
  picked <- pick_per_pid(files, source)
  beats <- list(); spec <- list()
  for (p in names(picked)) {
    r <- tryCatch(read_kubios_timeseries(picked[[p]]), error = function(e) e)
    if (inherits(r, "error")) { log_src(source, p, "skipped (unreadable)", basename(picked[[p]]), conditionMessage(r)); next }
    if (!nrow(r$beats)) { log_src(source, p, "skipped (no RR rows)", basename(picked[[p]])); next }
    meta <- data.frame(participant_id = p, source_file = basename(picked[[p]]), stringsAsFactors = FALSE)
    beats[[p]] <- cbind(meta, r$beats, row.names = NULL)
    if (nrow(r$spectrum)) spec[[p]] <- cbind(meta, r$spectrum, row.names = NULL)
    log_src(source, p, "included", basename(picked[[p]]),
            sprintf("%d beats, %d blocks", nrow(r$beats), length(unique(r$beats$block))))
  }
  b <- rbind_fill(beats)
  if (nrow(b)) say("  columns: %s", paste(setdiff(names(b), c("participant_id", "source_file")), collapse = ", "))
  write_out(b, out_name, source)
  if (KUBIOS_SPECTRUM && length(spec)) write_out(rbind_fill(spec), sub("\\.csv$", "_spectrum.csv", out_name), source)
  invisible(b)
}

# ── 1. ECG Kubios ─────────────────────────────────────────────────────────────
ecg_files <- list_files(c(KUBIOS_RESULTS_DIR, RAW_PHYSIOLOGY_DIR), "^[^_]+_.*hrv.*\\.csv$")
ecg_files <- ecg_files[!grepl("facereader|webcam|heart beat log", basename(ecg_files), ignore.case = TRUE)]
ecg_files <- ecg_files[vapply(ecg_files, function(h)
  any(grepl("RR INTERVAL DATA", readLines(h, warn = FALSE), fixed = TRUE)), TRUE)]
combine_kubios(ecg_files, "ecg_kubios", "biosignals2_ts_ecg_kubios.csv")

# ── 2. FaceReader Kubios ──────────────────────────────────────────────────────
fr_dirs  <- c(FACEREADER_RESULTS_DIR, file.path(FACEREADER_RESULTS_DIR, "kubios"),
              KUBIOS_RESULTS_DIR, file.path(KUBIOS_RESULTS_DIR, "kubios"))
fr_files <- list_files(fr_dirs, "^[^_]+_.*facereader.*_hrv\\.csv$")
combine_kubios(fr_files, "facereader_kubios", "biosignals2_ts_facereader_kubios.csv")

# ── 2b. FaceReader action units (detailed log) ────────────────────────────────
# Reading follows 03_facial_expression_analysis.Rmd §2.2 / §3.5: metadata rows, then a header row
# starting "Video Time" (hh:mm:ss.fff); AU columns "Action Unit 12 - Lip Corner Puller" and
# "Action Unit 12 - Left - ..." -> au12 / au12_left; failed frames are FIND_FAILED / FIT_FAILED (-> NA,
# fr_valid = FALSE); AU letter codes A-E (other export setting) -> bin midpoints.
say("\n== facereader_au")
read_grid <- function(path, n_max = Inf) {
  if (grepl("\\.xlsx?$", path, ignore.case = TRUE)) {
    if (!requireNamespace("readxl", quietly = TRUE)) stop("readxl not installed (needed for .xlsx logs)")
    g <- as.data.frame(readxl::read_excel(path, sheet = 1, col_names = FALSE, col_types = "text",
                                          .name_repair = "minimal", n_max = n_max, progress = FALSE),
                       stringsAsFactors = FALSE)
  } else {
    L <- readLines(path, warn = FALSE, encoding = "UTF-8", n = if (is.finite(n_max)) n_max else -1L)
    L[1] <- sub("^﻿", "", L[1])
    x <- strsplit(L, "\t", fixed = TRUE)
    n <- max(1L, lengths(x))
    g <- as.data.frame(do.call(rbind, lapply(x, function(r) { length(r) <- n; r })), stringsAsFactors = FALSE)
  }
  g[] <- lapply(g, function(col) trimws(as.character(col)))
  g
}
fr_time_to_s <- function(x) {
  x <- sub(",", ".", as.character(x), fixed = TRUE)
  out <- num(x) * 86400                                   # Excel day fraction
  is_hms <- grepl(":", x)
  out[is_hms] <- vapply(x[is_hms], hms, 0)
  out
}
au_letter <- c(NotActive = 0, A = 0.11, B = 0.35, C = 0.62, D = 0.85, E = 0.97)
parse_au <- function(x) { x <- trimws(x); v <- num(x); l <- x %in% names(au_letter); v[l] <- au_letter[x[l]]; v }
fr_names <- function(x) {
  m <- regmatches(x, regexec("^Action Unit (\\d+)(?: - (Left|Right))? - ", x))
  vapply(seq_along(x), function(i) {
    r <- m[[i]]
    if (length(r)) paste0("au", sprintf("%02d", as.integer(r[2])), if (nzchar(r[3])) paste0("_", tolower(r[3])) else "")
    else clean_names(x[i])
  }, "")
}
find_timestamps <- function(pid) {
  for (d in FRAME_TIMESTAMP_DIRS[dir.exists(FRAME_TIMESTAMP_DIRS)]) {
    h <- list.files(d, pattern = paste0("^", pid, "_frame_timestamps\\.csv$"), ignore.case = TRUE, full.names = TRUE)
    if (length(h)) return(h[1])
  }
  NA_character_
}

# Index the detailed logs (peek at the first 40 rows)
fr_cand <- list_files(FACEREADER_RESULTS_DIR, "\\.(txt|xlsx)$")
fr_cand <- fr_cand[!grepl("heart beat log|state log|^~\\$", basename(fr_cand), ignore.case = TRUE)]
fr_idx <- rbind_fill(lapply(fr_cand, function(f) {
  g <- tryCatch(read_grid(f, n_max = 40), error = function(e) NULL)
  if (is.null(g) || ncol(g) < 2 || !any(g[[1]] == "Video Time", na.rm = TRUE)) return(NULL)
  if (grepl("state log|heart beat log", tolower(g[[1]][1]))) return(NULL)
  src <- g[[2]][grepl("^file ?name", g[[1]], ignore.case = TRUE)][1]
  data.frame(path = f, src = ifelse(is.na(src), basename(f), src),
             pid = pid_of(gsub("\\\\", "/", ifelse(is.na(src), f, src))), stringsAsFactors = FALSE)
}))
say("  %d FaceReader detailed log(s) found", nrow(fr_idx))

fr_out <- list()
if (nrow(fr_idx)) for (p in unique(fr_idx$pid)) {
  if (!is_main(p)) { log_src("facereader_au", p, "left out", note = participant_status_of(p)); next }
  cand <- fr_idx[fr_idx$pid == p, , drop = FALSE]
  if (nrow(cand) > 1) {                                   # prefer the 1:1 video, then newest
    cand <- cand[order(!grepl("1to1", cand$src, ignore.case = TRUE), -as.numeric(file.mtime(cand$path))), ]
    log_src("facereader_au", p, "not used (other log)", paste(basename(cand$path[-1]), collapse = "; "))
  }
  f <- cand$path[1]; src <- cand$src[1]
  g <- tryCatch(read_grid(f), error = function(e) e)
  if (inherits(g, "error")) { log_src("facereader_au", p, "skipped (unreadable)", basename(f), conditionMessage(g)); next }
  hdr  <- which(g[[1]] == "Video Time")[1]
  fps_hdr <- num(g[[2]][grepl("^frame rate", g[[1]][seq_len(hdr - 1)], ignore.case = TRUE)][1])
  D <- g[-seq_len(hdr), , drop = FALSE]
  names(D) <- fr_names(ifelse(is.na(unlist(g[hdr, ])), "", unlist(g[hdr, ])))
  D <- D[!is.na(D$video_time) & nzchar(D$video_time), , drop = FALSE]
  au_cols <- grep("^au\\d{2}", names(D), value = TRUE)
  if (!length(au_cols)) { log_src("facereader_au", p, "skipped (no Action Unit columns)", basename(f)); next }
  extra <- c("quality", if (FR_EXTRA_COLUMNS) c("neutral", "happy", "sad", "angry", "surprised", "scared",
                                                 "disgusted", "contempt", "valence", "arousal"))
  extra <- intersect(extra, names(D))
  vt <- fr_time_to_s(D$video_time)

  # video time -> recording time (same rules as 03 §3.5)
  v <- tolower(src)
  kind <- if (grepl("1to1|_recording", v)) "frames" else if (grepl("realtime|_facereader", v)) "realtime" else "unknown"
  rec <- vt; how <- "as is (real-time video)"
  if (kind == "unknown") { log_src("facereader_au", p, "note", basename(f), "video type unknown from Filename row - times used as is") }
  if (kind == "frames") {
    tsf <- find_timestamps(p)
    if (is.na(tsf)) { log_src("facereader_au", p, "skipped (no frame timestamps)", basename(f),
                              paste0("1:1/recording video needs ", p, "_frame_timestamps.csv")); next }
    ts <- utils::read.csv(tsf, stringsAsFactors = FALSE)
    t_ts <- num(ts$time_since_recording_start)
    fps <- if (!is.na(fps_hdr) && fps_hdr >= MIN_VIDEO_FPS) fps_hdr
           else if (abs(nrow(D) - length(t_ts)) <= 2) (nrow(D) - 1) / max(vt, na.rm = TRUE) else NA
    if (is.na(fps)) { log_src("facereader_au", p, "skipped (reduced export rate)", basename(f),
                              "log not exported with every frame - re-export"); next }
    k <- round(vt * fps)
    rec <- ifelse(k + 1 <= length(t_ts), t_ts[pmin(k + 1, length(t_ts))], NA_real_)
    how <- sprintf("via %s at %.3f fps", basename(tsf), fps)
  }

  out <- data.frame(participant_id = p, source_file = basename(f), frame = seq_len(nrow(D)) - 1L,
                    video_time_s = vt, time_s = rec,
                    fr_valid = !is.na(parse_au(D[[au_cols[1]]])),
                    stringsAsFactors = FALSE)

  # labels from <pid>_video_events.csv (recording clock): block event + video event
  out$block <- NA_character_; out$video_event <- NA_character_; out$stimulus <- NA_character_
  out$t_from_block_start_s <- NA_real_
  evf <- list_files(FACEREADER_ONSETS_DIR, paste0("^", p, "_video_events\\.csv$"))
  if (length(evf)) {
    ev <- utils::read.csv(evf[1], stringsAsFactors = FALSE)
    ev$onset_s <- num(ev$onset_s); ev$offset_s <- num(ev$offset_s)
    is_vid <- grepl("video", ev$event, ignore.case = TRUE)
    for (i in which(!is_vid)) {
      w <- !is.na(out$time_s) & out$time_s >= ev$onset_s[i] & out$time_s < ev$offset_s[i]
      out$block[w] <- norm_block(ev$event[i]); out$t_from_block_start_s[w] <- out$time_s[w] - ev$onset_s[i]
    }
    for (i in which(is_vid)) {
      w <- !is.na(out$time_s) & out$time_s >= ev$onset_s[i] & out$time_s < ev$offset_s[i]
      out$video_event[w] <- norm_block(ev$event[i])
      if ("stimulus" %in% names(ev)) out$stimulus[w] <- ev$stimulus[i]
    }
  } else log_src("facereader_au", p, "note", basename(f), "no _video_events.csv - rows not labelled")

  for (cn in au_cols) out[[cn]] <- parse_au(D[[cn]])
  for (cn in extra) out[[paste0("fr_", cn)]] <- num(D[[cn]])
  fr_out[[p]] <- out
  log_src("facereader_au", p, "included", basename(f),
          sprintf("%d frames, %d AU columns, %.0f%% face found; times %s",
                  nrow(out), length(au_cols), 100 * mean(out$fr_valid), how))
}
write_out(rbind_fill(fr_out), "biosignals2_ts_facereader_au.csv", "facereader_au")

# ── 3. Webcam biometrics ONLINE (computed live by PsychoPy; cleaned + labelled by 01) ──
# Off by default (WRITE_WEBCAM_ONLINE): 01 labels it for the pilots only, and the main study uses
# the OFFLINE results (section 3b).
pp_path <- file.path(COMBINED_PSYCHO_DIR, "biosignals2_webcambiometrics_online.csv")
if (!WRITE_WEBCAM_ONLINE) {
  say("\n== webcambiometrics_online: switched off (WRITE_WEBCAM_ONLINE = FALSE)")
} else if (!file.exists(pp_path)) {
  say("\n== webcambiometrics_online")
  say("  %s not found - run 01_data_cleaning.Rmd first", pp_path)
  log_src("webcambiometrics_online", NA, "skipped (file missing)", basename(pp_path))
} else {
  say("\n== webcambiometrics_online")
  pp <- if (requireNamespace("data.table", quietly = TRUE)) data.table::fread(pp_path, data.table = FALSE)
        else utils::read.csv(pp_path, stringsAsFactors = FALSE, check.names = FALSE)
  pp$participant_id <- tolower(trimws(as.character(pp$participant_id)))
  keep <- is_main(pp$participant_id)
  for (p in unique(pp$participant_id[!keep])) log_src("webcambiometrics_online", p, "left out", note = participant_status_of(p))
  pp <- pp[keep, , drop = FALSE]
  # time order within participant (mono_time = biometrics clock, seconds)
  if ("mono_time" %in% names(pp)) {
    pp <- pp[order(pp$participant_id, num(pp$mono_time)), , drop = FALSE]
    pp$t_from_first_sample_s <- ave(num(pp$mono_time), pp$participant_id, FUN = function(x) x - min(x, na.rm = TRUE))
  }
  for (p in unique(pp$participant_id))
    log_src("webcambiometrics_online", p, "included", basename(pp_path), sprintf("%d samples", sum(pp$participant_id == p)))
  write_out(pp, "biosignals2_ts_webcambiometrics_online.csv", "webcambiometrics_online")
}

# ── 3b. Webcam biometrics OFFLINE (002_run_webcam_biometrics.py on the 1:1 video) ──
# WEBCAM_HR_DIR/<pid>_webcam_beats_<WEBCAM_OFFLINE_VARIANT>.csv: one row per detected beat, already
# labelled with its block by 002 (Baseline / Negative Induction ...). Raw beats, no artefact
# correction; near_gap flags beats next to a face-loss gap (nothing removed). See 002's docstring.
if (!WRITE_WEBCAM_OFFLINE) {
  say("\n== webcambiometrics_offline: switched off (WRITE_WEBCAM_OFFLINE = FALSE)")
} else {
say("\n== webcambiometrics_offline (variant %s)", WEBCAM_OFFLINE_VARIANT)
WEBCAM_HR_DIR <- get0("WEBCAM_HR_DIR", ifnotfound = file.path(SERVER_ROOT, "webcam_biometrics"))
wc_files <- list_files(WEBCAM_HR_DIR, paste0("^[^_]+_webcam_beats_", WEBCAM_OFFLINE_VARIANT, "\\.csv$"))
wc_out <- list()
for (p in names(wc_pick <- pick_per_pid(wc_files, "webcambiometrics_offline"))) {
  f <- wc_pick[[p]]
  d <- tryCatch(utils::read.csv(f, stringsAsFactors = FALSE, check.names = FALSE, na.strings = c("", "NA")),
                error = function(e) e)
  if (inherits(d, "error")) { log_src("webcambiometrics_offline", p, "skipped (unreadable)", basename(f), conditionMessage(d)); next }
  if (!nrow(d)) { log_src("webcambiometrics_offline", p, "skipped (no beats)", basename(f)); next }
  if ("block" %in% names(d)) d$block <- ifelse(is.na(d$block) | !nzchar(trimws(d$block)), NA_character_, norm_block(d$block))
  wc_out[[p]] <- cbind(participant_id = p, source_file = basename(f), d, stringsAsFactors = FALSE)
  log_src("webcambiometrics_offline", p, "included", basename(f),
          sprintf("%d beats, %d blocks", nrow(d), length(unique(na.omit(wc_out[[p]]$block)))))
}
say("  %d participant(s) with %s beats in %s", length(wc_out), WEBCAM_OFFLINE_VARIANT, WEBCAM_HR_DIR)
write_out(rbind_fill(wc_out), "biosignals2_ts_webcambiometrics_offline.csv", "webcambiometrics_offline")
}

# ── 3a. Self-report ratings and questionnaire scores (one file each, from 01 / 04) ──
read_table_file <- function(path, source, out_name) {
  say("\n== %s", source)
  if (!file.exists(path)) {
    say("  %s not found - run %s first", path, if (source == "ratings") "01_data_cleaning.Rmd" else "04_questionnaire_analysis.Rmd")
    log_src(source, NA, "skipped (file missing)", basename(path)); return(invisible(NULL))
  }
  d <- utils::read.csv(path, stringsAsFactors = FALSE, check.names = FALSE, na.strings = c("", "NA"))
  if (!"participant_id" %in% names(d)) stop(basename(path), ": no participant_id column")
  d$participant_id <- tolower(trimws(as.character(d$participant_id)))
  d <- d[!is.na(d$participant_id) & nzchar(d$participant_id), , drop = FALSE]
  # 01 calls the block "condition" (post_negative_induction_recovery ...): same name as everywhere else
  if ("condition" %in% names(d) && !"block" %in% names(d)) names(d)[names(d) == "condition"] <- "block"
  keep <- is_main(d$participant_id)
  for (p in unique(d$participant_id[!keep])) log_src(source, p, "left out", note = participant_status_of(p))
  d <- d[keep, , drop = FALSE]
  for (p in unique(d$participant_id))
    log_src(source, p, "included", basename(path), sprintf("%d rows", sum(d$participant_id == p)))
  write_out(d, out_name, source)
}
read_table_file(file.path(COMBINED_PSYCHO_DIR, "biosignals2_selfreport_ratings.csv"), "ratings",
                "biosignals2_self-report_rating.csv")
read_table_file(file.path(COMBINED_PSYCHO_DIR, "biosignals2_questionnaires_scored.csv"), "questionnaires",
                "biosignals2_questionnaires_scores.csv")

# ── 3b. Demographics survey (survey answers + participant ID only) ────────────
# Only when WRITE_DEMOGRAPHICS is TRUE (switched off: the questionnaire scores file is shared instead).
# Qualtrics CSV: row 1 = column names (Q51, QID7_1, StartDate, ...), row 2 = question text,
# row 3 = ImportId JSON ({"ImportId":"QID7_1"}). Survey answers are the columns whose ImportId starts
# with "QID"; everything else is Qualtrics metadata or embedded data (StartDate, EndDate, IPAddress,
# LocationLatitude, ResponseId, RecipientEmail, ...) and is dropped. Columns are named by ImportId,
# as in 04_questionnaire_analysis.Rmd. Email: DEMOGRAPHICS_EMAIL_COLS, plus any column whose name or
# question text mentions email, are dropped; an email address typed into any other answer is blanked.
# Qualtrics survey file (.qsf, JSON) -> list(ImportId column = c(exported value = answer text)).
#   single choice (MC SAVR/DL/...)  column QIDn        value = recode value (else choice id) of the choice
#   multiple choice (MAVR/MAHR/...) column QIDn_<id>   value = that choice's recode value (or 1)
#   matrix                          column QIDn_<row>  value = recode value (else id) of the answer column
read_qsf_labels <- function(path) {
  j <- jsonlite::fromJSON(path, simplifyVector = FALSE)
  strip <- function(s) trimws(gsub("\\s+", " ", gsub("&nbsp;", " ", gsub("<[^>]+>", "", s))))
  disp  <- function(ch) vapply(ch, function(c) strip(if (is.null(c$Display)) "" else c$Display), "")
  codes <- function(ids, recode) vapply(ids, function(k) if (!is.null(recode[[k]])) as.character(recode[[k]]) else k, "")
  out <- list()
  for (el in j$SurveyElements) {
    if (!identical(el$Element, "SQ") || !is.list(el$Payload)) next
    P <- el$Payload; qid <- if (!is.null(P$QuestionID)) P$QuestionID else el$PrimaryAttribute
    rec <- if (is.list(P$RecodeValues)) P$RecodeValues else list()
    ch  <- if (is.list(P$Choices)) P$Choices else list()
    if (identical(P$QuestionType, "MC") && length(ch)) {
      ids <- names(ch)
      if (grepl("^MA", if (is.null(P$Selector)) "" else P$Selector) || identical(P$Selector, "MSB")) {
        for (k in ids) out[[paste0(qid, "_", k)]] <- setNames(rep(disp(ch[k]), 2), c(codes(k, rec), "1"))
      } else out[[qid]] <- setNames(disp(ch), codes(ids, rec))
    } else if (identical(P$QuestionType, "Matrix") && is.list(P$Answers) && length(P$Answers)) {
      a <- P$Answers
      m <- setNames(disp(a), codes(names(a), rec))
      for (k in names(ch)) out[[paste0(qid, "_", k)]] <- m
    }
  }
  out
}

dem_path <- file.path(QUESTIONNAIRE_DIR, DEMOGRAPHICS_FILE)
if (!WRITE_DEMOGRAPHICS) {
  say("\n== demographics: switched off (WRITE_DEMOGRAPHICS = FALSE)")
} else if (!file.exists(dem_path)) {
  say("\n== demographics")
  say("  %s not found - run combine_qualtrics_exports.R first", dem_path)
  log_src("demographics", NA, "skipped (file missing)", basename(dem_path))
} else {
  say("\n== demographics")
  q <- utils::read.csv(dem_path, header = FALSE, colClasses = "character", na.strings = character(0),
                       fileEncoding = "UTF-8-BOM", check.names = FALSE)
  if (nrow(q) < 3 || !any(grepl('"ImportId"', unlist(q[3, ]), fixed = TRUE)))
    stop(basename(dem_path), ": expected 3 Qualtrics header rows (names, question text, ImportId)")
  qname  <- trimws(unlist(q[1, ])); qtext <- trimws(unlist(q[2, ]))
  import <- sub('.*"ImportId"\\s*:\\s*"([^"]+)".*', "\\1", unlist(q[3, ]))
  import[!grepl('"ImportId"', unlist(q[3, ]), fixed = TRUE)] <- NA
  R <- q[-(1:3), , drop = FALSE]
  R <- R[apply(R, 1, function(r) any(nzchar(r))), , drop = FALSE]
  col_of <- function(imp, nm) { i <- which(import == imp | qname == nm)[1]; if (is.na(i)) NULL else R[[i]] }

  # completed responses only (labels export: TRUE/FALSE; values export: 1/0)
  fin <- col_of("finished", "Finished"); prog <- col_of("progress", "Progress")
  ok  <- rep(TRUE, nrow(R))
  if (!is.null(fin))  ok <- ok & toupper(trimws(fin)) %in% c("TRUE", "1")
  if (!is.null(prog)) ok <- ok & num(prog) %in% 100
  say("  %d of %d responses complete", sum(ok), nrow(R))
  end_t <- col_of("endDate", "EndDate"); if (is.null(end_t)) end_t <- rep("", nrow(R))

  i_id <- which(import == DEMOGRAPHICS_ID_IMPORT)[1]
  if (is.na(i_id)) stop(basename(dem_path), ": no participant ID column (ImportId ", DEMOGRAPHICS_ID_IMPORT, ")")
  pid <- tolower(gsub("\\s+", "", R[[i_id]]))

  # answer columns, minus anything email-related
  answer <- which(!is.na(import) & startsWith(import, "QID") & seq_along(import) != i_id)
  email  <- answer[qname[answer] %in% DEMOGRAPHICS_EMAIL_COLS |
                   grepl("e-?mail", qname[answer], ignore.case = TRUE) |
                   grepl("e-?mail", qtext[answer], ignore.case = TRUE)]
  answer <- setdiff(answer, email)
  say("  %d answer columns kept; dropped %d email-related (%s) and %d metadata/embedded columns",
      length(answer), length(email), paste(qname[email], collapse = ", "),
      ncol(R) - length(answer) - length(email) - 1)
  # an email address typed into some other answer (e.g. a free-text comment): blank that cell
  email_rx <- "[^@[:space:]]+@[^@[:space:]]+\\.[^@[:space:]]+"
  for (j in answer) {
    hit <- grepl(email_rx, R[[j]])
    if (any(hit)) {
      R[[j]][hit] <- ""
      say("  %s: %d answer(s) contained an email address - blanked", qname[j], sum(hit))
    }
  }

  dem <- data.frame(participant_id = pid, R[, answer, drop = FALSE], stringsAsFactors = FALSE, check.names = FALSE)
  names(dem) <- c("participant_id", import[answer])
  dem[dem == ""] <- NA

  # codes -> answer text
  labels_from <- setNames(rep("", length(answer)), import[answer])
  if (DEMOGRAPHICS_LABELS) {
    qsf_maps <- list()
    qsf <- DEMOGRAPHICS_QSF
    if (is.na(qsf)) {
      cand <- list_files(c(QUESTIONNAIRE_DIR, get0("RAW_QUESTIONNAIRE_DIR", ifnotfound = dirname(QUESTIONNAIRE_DIR))), "\\.qsf$")
      pref <- cand[grepl("demograph|biosignals", basename(cand), ignore.case = TRUE)]
      if (length(pref)) cand <- pref
      qsf <- if (length(cand)) cand[which.max(file.mtime(cand))] else NA_character_
    }
    if (!is.na(qsf) && !requireNamespace("jsonlite", quietly = TRUE)) {
      say("  survey file %s found but jsonlite is not installed - using the built-in labels", basename(qsf)); qsf <- NA
    }
    if (!is.na(qsf)) {
      qsf_maps <- tryCatch(read_qsf_labels(qsf), error = function(e) {
        say("  survey file %s unreadable (%s) - using the built-in labels", basename(qsf), conditionMessage(e)); list() })
      if (length(qsf_maps)) say("  answer labels from survey file %s (%d columns)", basename(qsf), length(qsf_maps))
    } else say("  no survey .qsf found - answer labels from DEMOGRAPHICS_CODE_LABELS (see the top of the script)")

    builtin_for <- function(id) {
      if (!is.null(DEMOGRAPHICS_CODE_LABELS[[id]])) return(DEMOGRAPHICS_CODE_LABELS[[id]])
      pre <- names(DEMOGRAPHICS_CODE_LABELS)[endsWith(names(DEMOGRAPHICS_CODE_LABELS), "_")]
      hit <- pre[startsWith(id, pre)]
      if (length(hit)) DEMOGRAPHICS_CODE_LABELS[[hit[which.max(nchar(hit))]]] else NULL
    }
    unknown <- character(0)
    for (id in import[answer]) {
      m <- qsf_maps[[id]]; from <- "survey file"
      if (is.null(m)) { m <- builtin_for(id); from <- "script (DEMOGRAPHICS_CODE_LABELS)" }
      if (is.null(m)) next
      x <- trimws(dem[[id]])
      out <- unname(m[x])
      is_code <- !is.na(x) & is.na(out) & grepl("^-?\\d+(\\.\\d+)?$", x)   # a code with no label
      out[is_code] <- paste("code", x[is_code])
      keep_txt <- !is.na(x) & is.na(out)                                  # already text: leave it
      out[keep_txt] <- x[keep_txt]
      if (any(is_code)) unknown <- c(unknown, sprintf("%s (%s)", id, paste(sort(unique(x[is_code])), collapse = "/")))
      dem[[id]] <- out
      labels_from[id] <- from
    }
    if (length(unknown)) say("  codes with no label, shown as 'code <n>': %s", paste(unknown, collapse = ", "))
  }

  # which response per participant: complete, valid ID, main study, latest EndDate
  bad_id <- !nzchar(pid) | grepl("@", pid)
  if (any(ok & bad_id)) say("  %d complete response(s) with a blank or email-like ID - not used", sum(ok & bad_id))
  keep <- ok & !bad_id
  for (p in unique(pid[keep & !is_main(pid)])) log_src("demographics", p, "left out", note = participant_status_of(p))
  keep <- keep & is_main(pid)
  ord  <- order(pid, end_t, decreasing = TRUE)
  ord  <- ord[keep[ord]]
  first <- ord[!duplicated(pid[ord])]
  for (p in unique(pid[ord][duplicated(pid[ord])]))
    log_src("demographics", p, "not used (older duplicate)", basename(dem_path),
            sprintf("%d complete responses with this ID - latest EndDate used", sum(pid[ord] == p)))
  dem <- dem[sort(first), , drop = FALSE]
  for (p in dem$participant_id) log_src("demographics", p, "included", basename(dem_path))

  questions <- data.frame(column = c("participant_id", import[answer]),
                          qualtrics_name = c(qname[i_id], qname[answer]),
                          question = c(qtext[i_id], qtext[answer]),
                          answer_labels_from = c("", ifelse(nzchar(labels_from), labels_from, "none (values as exported)")),
                          stringsAsFactors = FALSE)
  write_out(dem, "biosignals2_ts_demographics.csv", "demographics")
  write_file(questions, "biosignals2_ts_demographics_questions.csv")
}

# ── 4. Ledalab ────────────────────────────────────────────────────────────────
say("\n== ledalab")
nid_path <- file.path(BLOCK_ONSETS_DIR, "nid_map_biopac_ledalab.txt")
nid_map  <- if (file.exists(nid_path)) utils::read.delim(nid_path, stringsAsFactors = FALSE) else NULL
if (is.null(nid_map)) say("  %s not found - SCRs will not be labelled by block", nid_path)

read_events <- function(pid) {
  f <- list_files(BLOCK_ONSETS_DIR, paste0("^", pid, "_events_blocks_biopac_ledalab\\.txt$"))
  if (!length(f) || is.null(nid_map)) return(NULL)
  e <- utils::read.delim(f[1], stringsAsFactors = FALSE)
  e$block <- norm_block(nid_map$condition[match(e$nid, nid_map$nid)])
  e[order(e$time), , drop = FALSE]
}

# Label times t (s, Ledalab clock) with the block whose window [onset, onset + BLOCK_WINDOW_S) holds them.
label_blocks <- function(t, ev) {
  out <- data.frame(block = rep(NA_character_, length(t)), t_from_block_start_s = NA_real_)
  if (is.null(ev) || !nrow(ev)) return(out)
  k <- findInterval(t, ev$time)
  ok <- k > 0 & !is.na(t)
  ok[ok] <- t[ok] < ev$time[k[ok]] + BLOCK_WINDOW_S
  out$block[ok] <- ev$block[k[ok]]
  out$t_from_block_start_s[ok] <- t[ok] - ev$time[k[ok]]
  out
}

# 4a. SCR list
scr_files <- pick_per_pid(list_files(LEDALAB_RESULTS_DIR, "_scrlist\\.txt$"), "ledalab_scr")
scr <- list()
for (p in names(scr_files)) {
  f <- scr_files[[p]]
  if (is.na(file.size(f)) || file.size(f) == 0) { log_src("ledalab_scr", p, "skipped (empty file)", basename(f)); next }
  d <- tryCatch(utils::read.table(f, header = TRUE, sep = "\t", stringsAsFactors = FALSE, fill = TRUE),
                error = function(e) e)
  if (inherits(d, "error")) { log_src("ledalab_scr", p, "skipped (unreadable)", basename(f), conditionMessage(d)); next }
  if (!nrow(d)) { log_src("ledalab_scr", p, "included (no SCRs detected)", basename(f)); next }
  onset <- intersect(c("CDA.SCR.Onset", "CDA.SCR-Onset", "onset", "SCR.Onset", "onset_t", "t"), names(d))[1]
  lab <- if (!is.na(onset)) label_blocks(num(d[[onset]]), read_events(p)) else label_blocks(rep(NA_real_, nrow(d)), NULL)
  scr[[p]] <- cbind(participant_id = p, source_file = basename(f), scr_nr = seq_len(nrow(d)), lab, d,
                    stringsAsFactors = FALSE)
  log_src("ledalab_scr", p, "included", basename(f), sprintf("%d SCRs", nrow(d)))
}
write_out(rbind_fill(scr), "biosignals2_ts_eda_ledalab.csv", "ledalab_scr")

# 4b. Continuous decomposition from <pid>.mat (Ledalab 3.49: data.time/conductance, analysis.*)
if (LEDALAB_CONTINUOUS && !requireNamespace("R.matlab", quietly = TRUE)) {
  say("  Ledalab continuous: R.matlab not installed - skipped (install.packages('R.matlab') to add it)")
} else if (LEDALAB_CONTINUOUS) {
  field <- function(s, name) {
    if (is.null(s)) return(NULL)
    if (is.list(s) && !is.null(s[[name]])) return(s[[name]])
    if (!is.null(dimnames(s)) && name %in% dimnames(s)[[1]]) return(s[name, , 1][[1]])
    NULL
  }
  mat_files <- list_files(LEDALAB_RESULTS_DIR, "^[^_]+\\.mat$")
  mat_files <- pick_per_pid(mat_files, "ledalab_continuous")
  cont <- list()
  for (p in names(mat_files)) {
    f <- mat_files[[p]]
    m <- tryCatch(R.matlab::readMat(f), error = function(e) e)
    if (inherits(m, "error")) { log_src("ledalab_continuous", p, "skipped (unreadable .mat)", basename(f), conditionMessage(m)); next }
    dat <- field(m, "data"); an <- field(m, "analysis")
    tt  <- as.numeric(field(dat, "time")); sc <- as.numeric(field(dat, "conductance"))
    if (!length(tt) || length(tt) != length(sc)) {
      log_src("ledalab_continuous", p, "skipped (no data.time / data.conductance)", basename(f)); next
    }
    d <- data.frame(participant_id = p, source_file = basename(f), time_s = tt, conductance_us = sc)
    for (nm in c("tonicData", "phasicData", "driver", "tonicDriver", "phasicRemainder")) {
      v <- as.numeric(field(an, nm))
      if (length(v) == nrow(d)) d[[clean_names(nm)]] <- v
    }
    if (is.null(an)) log_src("ledalab_continuous", p, "note", basename(f), "no analysis struct (raw signal only)")
    d <- cbind(d[, 1:3], label_blocks(d$time_s, read_events(p)), d[, -(1:3), drop = FALSE])
    cont[[p]] <- d
    log_src("ledalab_continuous", p, "included", basename(f), sprintf("%d samples", nrow(d)))
  }
  write_out(rbind_fill(cont), "biosignals2_ts_ledalab_continuous.csv", "ledalab_continuous")
}

# ── 5. Block-level files (one row per participant x block) ────────────────────
# 5a. Ledalab ERA summary per block, as written by 05_analyse_ledalab_scr.Rmd
say("\n== block_eda")
eda_path <- file.path(COMBINED_PSYCHO_DIR, "biosignals2_eda.csv")
if (!file.exists(eda_path)) {
  say("  %s not found - run 05_analyse_ledalab_scr.Rmd first", eda_path)
  log_src("block_eda", NA, "skipped (file missing)", basename(eda_path))
} else {
  d <- utils::read.csv(eda_path, stringsAsFactors = FALSE, check.names = FALSE, na.strings = c("", "NA"))
  idc <- intersect(c("participant_id", "pid"), names(d))[1]
  if (is.na(idc)) stop(basename(eda_path), ": no pid / participant_id column")
  d$participant_id <- tolower(trimws(as.character(d[[idc]])))
  # 05 calls the block "condition" with short names (neg_induction); use 08's "block" + names
  # (negative_induction) so every shared file labels blocks the same way
  if ("condition" %in% names(d) && !"block" %in% names(d)) names(d)[names(d) == "condition"] <- "block"
  if ("block" %in% names(d)) d$block <- norm_block(d$block)
  d <- d[, c("participant_id", intersect("block", names(d)),
             setdiff(names(d), c("participant_id", "pid", "block"))), drop = FALSE]
  keep <- is_main(d$participant_id)
  for (p in unique(d$participant_id[!keep])) log_src("block_eda", p, "left out", note = participant_status_of(p))
  d <- d[keep, , drop = FALSE]
  for (p in unique(d$participant_id))
    log_src("block_eda", p, "included", basename(eda_path), sprintf("%d rows", sum(d$participant_id == p)))
  write_out(d, "biosignals2_block_eda_ledalab.csv", "block_eda")
}

# Kubios block values: the same layout for ECG and FaceReader - participant_id, block,
# block_order, then one column per Kubios measure (names cleaned, e.g. "S1_Mean HR (bpm)" -> mean_hr_bpm).
BLOCK_ORDER <- c("baseline", "negative_induction", "negative_recovery", "positive_induction", "positive_recovery")

# 5b/5c. Kubios batch summaries (Carmen, 29 Oct): ECG = KUBIOS_RESULTS_DIR/KubiosHRVresults.csv
# (Box 3_Data/kubios), FaceReader = FACEREADER_RESULTS_DIR/KubiosHRVresults.csv (Box 3_Data/facereader).
# Samples S1..S5 = BLOCK_ORDER (the Kubios_Samples.csv order, as in 06/07). Header = the line
# starting with FileName (no fixed skip: no "sep=," line, rows end in a varying number of empty
# fields). Participant = FileName up to the first _ or . (FileName may be a full Windows path).
# Rows from the other stream (ECG in the FaceReader file or the reverse) are left out.
read_kubios_batch_blocks <- function(path, source, other_stream_rx) {
  say("\n== %s", source)
  if (!file.exists(path)) {
    say("  %s not found", path)
    log_src(source, NA, "skipped (file missing)", basename(path)); return(data.frame())
  }
  say("  reading %s", path)
  L <- readLines(path, warn = FALSE, encoding = "UTF-8"); L[1] <- sub("^﻿", "", L[1])
  split <- function(l) trimws(gsub('^"|"$', "", strsplit(l, ",", fixed = TRUE)[[1]]))
  h <- which(startsWith(sub('^"', "", L), "FileName"))[1]
  if (is.na(h)) stop(path, ": no header line starting with FileName")
  hdr <- split(L[h]); while (length(hdr) && !nzchar(hdr[length(hdr)])) hdr <- hdr[-length(hdr)]
  rows <- lapply(L[-seq_len(h)], function(l) {
    x <- split(l)
    if (length(x) > length(hdr) && any(nzchar(x[-seq_along(hdr)])))
      say("  WARNING: row '%s' has values beyond the last header column - check for a column shift", x[1])
    length(x) <- length(hdr); x[is.na(x)] <- ""; x })
  rows <- rows[vapply(rows, function(x) nzchar(x[1]), TRUE)]
  fname <- basename(gsub("\\\\", "/", vapply(rows, `[`, "", 1)))
  other <- grepl(other_stream_rx, fname, ignore.case = TRUE)
  if (any(other)) say("  %d row(s) from the other stream left out: %s", sum(other), paste(fname[other], collapse = ", "))
  rows <- rows[!other]; fname <- fname[!other]
  pids <- tolower(sub("[_.].*$", "", fname))
  out <- list()
  for (p in unique(pids)) {
    if (!is_main(p)) { log_src(source, p, "left out", note = participant_status_of(p)); next }
    r <- which(pids == p)
    if (length(r) > 1) log_src(source, p, "not used (older duplicate)", basename(path),
                               sprintf("%d rows for this participant - the last one is used", length(r)))
    x <- rows[[r[length(r)]]]
    per <- lapply(seq_along(BLOCK_ORDER), function(i) {
      k <- which(startsWith(hdr, paste0("S", i, "_")))
      if (!length(k)) return(NULL)
      v <- x[k]; vn <- num(v)
      vals <- lapply(seq_along(k), function(j) if (is.na(vn[j]) && nzchar(v[j])) v[j] else vn[j])
      d <- as.data.frame(setNames(vals, clean_names(sub("^S\\d+_", "", hdr[k]))), stringsAsFactors = FALSE)
      cbind(participant_id = p, block = BLOCK_ORDER[i], block_order = i, d, stringsAsFactors = FALSE)
    })
    out[[p]] <- rbind_fill(per)
    log_src(source, p, "included", basename(path), sprintf("%d blocks (%s)", nrow(out[[p]]), fname[r[length(r)]]))
  }
  d <- rbind_fill(out)
  if (nrow(d)) say("  %d participants; measures: %s", length(out),
                   paste(setdiff(names(d), c("participant_id", "block", "block_order")), collapse = ", "))
  d
}
write_out(read_kubios_batch_blocks(file.path(KUBIOS_RESULTS_DIR, "KubiosHRVresults.csv"), "block_kubios_ecg",
                                   "facereader|heart beat log|webcam"),
          "biosignals2_block_ecg_kubios.csv", "block_kubios_ecg")
write_out(read_kubios_batch_blocks(file.path(FACEREADER_RESULTS_DIR, "KubiosHRVresults.csv"), "block_kubios_facereader",
                                   "physiology|webcam"),
          "biosignals2_block_facereader_kubios.csv", "block_kubios_facereader")

# ── 6. Clock offsets: webcam clock -> BIOPAC clock (one row per participant) ──
# From 3_Data/ecg_video_offsets.csv (pid, offset_s), written by video/002_run_webcam_biometrics.py
# from the trigger events: BIOPAC time = webcam time + offset_s. Not a required source: a participant
# without an offset is simply not in this file (it doesn't drop them from the others).
say("\n== clock_offsets")
OFFSETS_PATH <- get0("ECG_VIDEO_OFFSETS_PATH", ifnotfound = file.path(SERVER_ROOT, "ecg_video_offsets.csv"))
if (!file.exists(OFFSETS_PATH)) {
  say("  %s not found - run video/002_run_webcam_biometrics.py first", OFFSETS_PATH)
  log_src("clock_offsets", NA, "skipped (file missing)", basename(OFFSETS_PATH))
} else {
  o <- tryCatch(utils::read.csv(OFFSETS_PATH, colClasses = "character", strip.white = TRUE, check.names = FALSE),
                error = function(e) e)
  if (inherits(o, "error") || !all(c("pid", "offset_s") %in% names(o))) {
    say("  %s: unreadable or no pid / offset_s column - not written", basename(OFFSETS_PATH))
    log_src("clock_offsets", NA, "skipped (unreadable)", basename(OFFSETS_PATH))
  } else {
    d <- data.frame(participant_id = tolower(trimws(o$pid)), offset_s = num(o$offset_s), stringsAsFactors = FALSE)
    d <- d[nzchar(d$participant_id) & !is.na(d$offset_s), , drop = FALSE]
    d <- d[!duplicated(d$participant_id, fromLast = TRUE), , drop = FALSE]   # last row wins, as in 002
    keep <- is_main(d$participant_id)
    for (p in d$participant_id[!keep]) log_src("clock_offsets", p, "left out", note = participant_status_of(p))
    d <- d[keep, , drop = FALSE]
    for (p in d$participant_id) log_src("clock_offsets", p, "included", basename(OFFSETS_PATH))
    say("  %d main-study participant(s) with an offset", nrow(d))
    write_out(d, "biosignals2_clock_offsets.csv", "clock_offsets")
  }
}

# ── Coverage: who has what ────────────────────────────────────────────────────
say("\n== coverage")
src <- rbind_fill(sources)
if (nrow(src)) { src <- src[order(src$source, src$participant_id), ]; write_file(src, "biosignals2_ts_sources.csv", LOG_DIR) }
all_sources <- c("ecg_kubios", "facereader_kubios", "facereader_au",
                 if (WRITE_WEBCAM_OFFLINE) "webcambiometrics_offline",
                 if (WRITE_WEBCAM_ONLINE) "webcambiometrics_online", "ledalab_scr",
                 "questionnaires", "ratings", "block_eda", "block_kubios_ecg", "block_kubios_facereader",
                 "clock_offsets",
                 if (LEDALAB_CONTINUOUS) "ledalab_continuous", if (WRITE_DEMOGRAPHICS) "demographics")
bad_req <- setdiff(REQUIRED_SOURCES, all_sources)
if (length(bad_req)) stop("REQUIRED_SOURCES: unknown or switched-off source(s): ", paste(bad_req, collapse = ", "),
                          ". Use any of: ", paste(all_sources, collapse = ", "))

main_ids <- if (nrow(src)) sort(unique(src$participant_id[!is.na(src$participant_id) & is_main(src$participant_id)])) else character(0)
coverage <- data.frame(participant_id = main_ids, stringsAsFactors = FALSE)
for (s in all_sources) {
  coverage[[s]] <- vapply(main_ids, function(p) {
    st <- src$status[src$source == s & src$participant_id %in% p &
                     !src$status %in% c("note", "not used (older duplicate)", "not used (other log)")]
    if (any(startsWith(st, "included"))) "yes" else if (length(st)) st[1] else "missing"
  }, "")
}
# blocks found per participant (from the data itself), to spot partial recordings
n_blocks <- function(name) {
  d <- PENDING[[name]]$df
  if (is.null(d) || !nrow(d) || !"block" %in% names(d)) return(rep(NA_integer_, length(main_ids)))
  vapply(main_ids, function(p) length(unique(na.omit(d$block[d$participant_id == p]))), 0L)
}
coverage$n_blocks_ecg_kubios        <- n_blocks("biosignals2_ts_ecg_kubios.csv")
coverage$n_blocks_facereader_kubios <- n_blocks("biosignals2_ts_facereader_kubios.csv")
coverage$n_blocks_facereader_au     <- n_blocks("biosignals2_ts_facereader_au.csv")
coverage$complete <- if (nrow(coverage)) apply(coverage[REQUIRED_SOURCES] == "yes", 1, all) else logical(0)

empty_req <- REQUIRED_SOURCES[vapply(REQUIRED_SOURCES, function(s) !any(coverage[[s]] == "yes"), TRUE)]
if (COMPLETE_CASES_ONLY && length(empty_req))
  stop("COMPLETE_CASES_ONLY: nobody has data for ", paste(empty_req, collapse = ", "),
       " (see biosignals2_ts_sources.csv), so no participant can be complete. ",
       "Remove it from REQUIRED_SOURCES or fix the input first.")

keep_ids <- if (COMPLETE_CASES_ONLY) coverage$participant_id[coverage$complete] else main_ids
coverage$written <- coverage$participant_id %in% keep_ids
write_file(coverage, "biosignals2_ts_coverage.csv", LOG_DIR)
print(coverage[, c("participant_id", all_sources, "complete")], row.names = FALSE)
if (COMPLETE_CASES_ONLY) {
  say("\nCOMPLETE_CASES_ONLY: %d of %d main-study participants have all of: %s",
      length(keep_ids), length(main_ids), paste(REQUIRED_SOURCES, collapse = ", "))
  if (any(!coverage$complete))
    say("  left out (incomplete): %s", paste(coverage$participant_id[!coverage$complete], collapse = ", "))
}

# ── Participant codes ─────────────────────────────────────────────────────────
written_ids <- sort(unique(unlist(lapply(PENDING, function(x) {
  d <- x$df; if (!nrow(d)) return(NULL)
  ids <- unique(d$participant_id); if (COMPLETE_CASES_ONLY) intersect(ids, keep_ids) else ids
}))))
if (PSEUDONYMISE_IDS) {
  say("\n== participant codes")
  # One key for 07 and 08 (id_key.R). New participants are added and the key saved first; the run
  # stops if that fails, so no file ever holds codes that aren't recorded.
  code_of <- id_key_codes(written_ids, ID_KEY_PATH)
  if (anyNA(code_of)) stop("No code for: ", paste(names(code_of)[is.na(code_of)], collapse = ", "))
  say("  %d participants coded from %s", length(code_of), ID_KEY_PATH)
  names(code_of) <- tolower(names(code_of))

  # whole ID only (as in fix_participant_id.py): not after a letter/digit, not before a digit
  # (nor before ".<digit>", so a number stored as text, e.g. "7280.5", is never touched)
  id_rx <- function(id) paste0("(?<![A-Za-z0-9.])", gsub("([][{}()+*^$|\\\\?.])", "\\\\\\1", id), "(?![0-9]|\\.[0-9])")
  pseudonymise <- function(d, name) {
    d$participant_id <- unname(code_of[d$participant_id])
    ids <- names(code_of)[names(code_of) %in% written_ids]
    for (cn in setdiff(names(d), "participant_id")) {
      v <- d[[cn]]
      if (!is.character(v)) next
      u <- unique(v); u2 <- u
      for (id in ids) u2 <- gsub(id_rx(id), code_of[[id]], u2, perl = TRUE, ignore.case = TRUE)
      if (!identical(u, u2)) {
        d[[cn]] <- u2[match(v, u)]
        say("  %s: participant IDs replaced by codes in column '%s' too", name, cn)
      }
    }
    d
  }
}

# ── Write the data files ──────────────────────────────────────────────────────
say("\n== writing")
written <- list(); dict <- list(); unknown_blocks <- list()
for (name in names(PENDING)) {
  d <- PENDING[[name]]$df
  if (COMPLETE_CASES_ONLY && nrow(d)) d <- d[d$participant_id %in% keep_ids, , drop = FALSE]
  drop <- DROP_COLUMNS[[name]]
  if (length(drop) && nrow(d)) {
    gone <- intersect(drop, names(d))
    if (length(gone)) d <- d[, setdiff(names(d), gone), drop = FALSE]
    say("  %s: removed %s%s", name, if (length(gone)) paste(gone, collapse = ", ") else "nothing",
        if (length(setdiff(drop, gone))) paste0(" (not in the data: ", paste(setdiff(drop, gone), collapse = ", "), ")") else "")
  }
  # Same keys in every file: block labels -> BLOCK_LEVELS (data_dictionary.R), participant_id + block first
  if ("block" %in% names(d) && nrow(d)) {
    b <- canon_block(d$block)
    bad <- unique(d$block[!is.na(d$block) & nzchar(trimws(as.character(d$block))) & is.na(b)])
    if (length(bad)) {
      say("  WARNING %s: block label(s) not recognised, set to empty: %s", name, paste(bad, collapse = ", "))
      unknown_blocks[[name]] <- bad
    }
    d$block <- b
  }
  d <- d[, c(intersect(c("participant_id", "block"), names(d)), setdiff(names(d), c("participant_id", "block"))), drop = FALSE]
  if (PSEUDONYMISE_IDS && nrow(d)) d <- pseudonymise(d, name)
  write_file(d, name)
  if (nrow(d)) {
    written[[name]] <- list(rows = nrow(d), participants = length(unique(d$participant_id)), columns = ncol(d))
    dict[[name]] <- dictionary_rows(d, name)
  }
}

# ── README + data dictionary (describe exactly the files written in this run) ──
say("\n== README + data dictionary")
dict_df <- rbind_fill(dict)
if (nrow(dict_df)) {
  write_file(dict_df, "biosignals2_data_dictionary.csv")
  write_readme(file.path(OUT_DIR, "biosignals2_README.md"), written)
  say("  -> biosignals2_README.md")
  todo <- dict_df[dict_df$description == "NOT DESCRIBED YET", c("file", "column")]
  if (nrow(todo)) {
    say("  %d column(s) have no description yet - add them to data_dictionary.R:", nrow(todo))
    for (f in unique(todo$file)) say("    %s: %s", f, paste(todo$column[todo$file == f], collapse = ", "))
  }
  nofile <- setdiff(names(written), names(FILE_INFO))
  if (length(nofile)) say("  no README text for: %s (add to FILE_INFO in data_dictionary.R)", paste(nofile, collapse = ", "))
}

# ── Source log ────────────────────────────────────────────────────────────────
say("\n== summary")
if (nrow(src)) print(table(src$source, src$status))
say("\nDone. Data files in %s", OUT_DIR)
if (PSEUDONYMISE_IDS) say("Check files (real IDs) and the ID key in %s", PRIVATE_DIR)
