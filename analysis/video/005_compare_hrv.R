#!/usr/bin/env Rscript
# =============================================================================
# 005_compare_hrv.R
# =============================================================================
# Compares heart rate variability (HRV) per block from three sources:
#
#   ECG         Kubios HRV report (the ground truth)
#   webcam      WebcamBiometrics beats (003_run_webcam_biometrics.py output)
#   webcam_optimize  the same video through the optimised beat detector (003 --optimize; linear-phase
#               FIR filter + sub-sample peak timing - WebcamBiometrics docs/beat-timing.md). Optional:
#               used when <id>_webcam_beats_optimize.csv exists, so current and optimised sit side by side.
#   FaceReader  FaceReader "heart beat log" (if one exists for the participant)
#
# and works out WHY each webcam source differs from the ECG.
#
# HOW TO RUN
#   From a terminal, in this folder:
#     Rscript 005_compare_hrv.R r2433 s0723      (named participants)
#     Rscript 005_compare_hrv.R --all            (everyone with webcam beats + a Kubios report)
#     Rscript 005_compare_hrv.R --all --pilots   (... including pilot participants)
#   Pilots: INCLUDE_PILOTS below (or --pilots / --no-pilots on the command line) decides whether
#   pilot participants (analysis/participant_status.csv) are in --all and in the pooled all_*
#   files and agreement plots. Test sessions and rejected participants are always left out of
#   those. IDs you name yourself are always run individually.
#   From RStudio: put the IDs in PIDS below and click Source.
#   Only base R is used - nothing to install.
#
# WHAT IT NEEDS (per participant)
#   3_Data/webcam_biometrics/<id>_webcam_beats.csv     from 003_run_webcam_biometrics.py
#   optional: <id>_webcam_beats_optimize.csv           from 003_run_webcam_biometrics.py --optimize
#   3_Data/ecg_video_offsets.csv                       written by 003 (ECG -> video clock offset)
#   Kubios HRV report  <id>_*hrv*.csv                  in 3_Data/kubios or next to the trimmed .acq
#   optional: <id>_*heart beat log.txt                 FaceReader export (D:/Biosignals2_video,
#             + <id>_frame_timestamps.csv               3_Data/facereader or 3_Data/video)
#   optional: FaceReader detailed log (.txt or .xlsx)  the same export 03_facial_expression_analysis.Rmd
#             with its heart rate / HRV columns         reads; found by its "Filename" row (any file
#                                                       name), in 3_Data/facereader or the folders above.
#                                                       .xlsx needs the readxl package.
#
# HOW THE COMPARISON IS MADE FAIR
#   * Same time windows: the Kubios sample limits for each block are used for all three sources.
#   * Same clock: webcam and FaceReader beats are moved onto the ECG clock with the ECG->video
#     offset. FaceReader times are first corrected through the real frame timestamps (FaceReader
#     only knows "frame number / nominal fps").
#   * Same maths: RMSSD, SDNN etc. are computed by THIS script for all three, including the ECG
#     (from Kubios' RR intervals). Kubios' own numbers are kept as a separate row
#     (version = kubios_report) as a check on the script, not used as the reference.
#   * Two versions of each webcam source:
#       as_is   the intervals exactly as the tool reports them (what you'd get using its output)
#       cleaned the same intervals after a simple, identical clean-up: drop intervals outside
#               0.30-2.00 s, drop intervals more than 20% away from the median of their 11
#               neighbours, and (webcam only) drop beats flagged near_gap. Dropped intervals
#               are removed, not interpolated, and successive differences are never taken
#               across a removed interval. This is NOT Kubios' correction algorithm.
#
# CHECK: FACEREADER'S OWN HRV vs ITS HEART BEAT LOG
#   FaceReader also reports HRV itself (RMSSD or SDNN, whichever it was set to) as a moving-window
#   value in the detailed log, post-processed at the end of the analysis; Noldus doesn't publish the
#   window or the filtering. The block median of that value is added as version "facereader_own"
#   and compared with the same measure computed here from the heart beat log (as_is and cleaned)
#   and with the ECG. If its own value sits close to the CLEANED beat log, FaceReader is filtering
#   intervals internally and the raw beat log shouldn't be used as-is. If FaceReader's HRV column
#   name doesn't say RMSSD or SDNN, set SETTINGS$facereader_hrv_measure (the script says when it
#   had to assume).
#
# HOW THE ERRORS ARE DIAGNOSED (per block, per source)
#   1. Pulse delay ("lag"): a webcam beat is the pulse arriving at the face, ~100-300 ms after
#      the ECG R-peak. The typical delay is estimated per source per participant and removed
#      before matching. A delay outside -50..450 ms usually means the ECG->video offset is wrong.
#   2. Beat matching: each webcam beat is paired with the ECG beat within +-150 ms (after the
#      delay is removed). Unpaired ECG beats = MISSED, unpaired webcam beats = EXTRA (false).
#   3. Face-loss gaps: intervals > 2 s, or a new webcam segment (face lost > 0.5 s).
#   4. Timing noise: on beats that were matched, how much the webcam beat time wobbles around
#      the R-peak (jitter, ms; a lower bound, because beats more than 150 ms off aren't matched -
#      those are counted as "mistimed": detected, but too far off to pair). Random timing noise inflates RMSSD even when no beat is missed:
#      noise_rmssd_ms is the RMSSD of the error itself.
#   5. Frame quantisation: if beat times can only fall on video frames, every beat is off by up
#      to half a frame. At 30 fps this alone adds ~24 ms to RMSSD (in quadrature) - the floor
#      no amount of beat detection can beat without sub-frame timing.
#   6. RMSSD error split into three parts that add up to (as_is - ECG):
#        artefacts  = RMSSD(all as_is intervals)  - RMSSD(matched intervals only)
#                     -> missed/extra beats and gaps
#        timing     = RMSSD(matched, webcam times) - RMSSD(same intervals, ECG times)
#                     -> jitter + quantisation on beats that WERE found
#        selection  = RMSSD(same intervals, ECG)   - RMSSD(all ECG intervals)
#                     -> the matched beats aren't a typical sample (e.g. lost during movement)
#
# OUTPUTS  (3_Data/hrv_comparison/)
#   <id>_hrv_by_block.csv      one row per block x source x version: n_intervals, pct_removed,
#                              mean_hr, mean_rr_ms, sdnn_ms, rmssd_ms, pnn50, sd1_ms, sd2_ms,
#                              lf_hf, hf_nu
#   <id>_hrv_diagnostics.csv   one row per block x webcam source: everything in "diagnosed" above
#   <id>_hrv_diagnosis.txt     the same in plain sentences (also printed)
#   <id>_facereader_own_vs_beatlog.csv   per block: FaceReader's own HRV (median, mean, % of block
#                              with a value) vs from its beat log (as_is, cleaned) vs ECG, + HR
#   <id>_hrv_plots.pdf         per block: RR series of all sources, timing errors, missed/extra
#                              beats; then a summary of RMSSD / SDNN / HR per block
#   all_hrv_by_block.csv, all_hrv_diagnostics.csv   every participant run so far, merged
#   all_hrv_agreement.csv      bias, limits of agreement, MAE, r per metric x source x version
#   all_hrv_agreement.pdf      Bland-Altman plots (once there are >= 3 blocks)
#
# CAVEATS
#   * LF/HF and HF n.u. use a Lomb-Scargle spectrum on each 3-min block. Compare sources with
#     each other on these; they will not equal Kubios' FFT values (different method, and 3 min
#     is short for LF).
#   * The delay is fitted on the same data it is scored on (one number per source/participant).
#   * Blocks with fewer than 30 intervals get NA metrics (e.g. s0723's 3-s blocks).
# =============================================================================

PIDS <- c()            # for RStudio, e.g. c("r2433", "s0723"); ignored when IDs are given on the command line
INCLUDE_PILOTS <- FALSE  # TRUE = pilots count in --all and in the pooled all_* outputs (CLI: --pilots / --no-pilots)

SETTINGS <- list(
  match_tol_s   = 0.150,        # +- window for pairing a webcam beat with an R-peak (after delay removed)
  lag_search_s  = c(-0.30, 0.60),
  lag_ok_s      = c(-0.05, 0.45),
  min_rr_s      = 0.30,         # cleaned: shortest plausible interval (200 bpm)
  max_rr_s      = 2.00,         # cleaned: longest plausible interval (30 bpm); longer = gap
  local_dev     = 0.20,         # cleaned: max deviation from local median
  local_k       = 11,           # cleaned: neighbours in the local median (odd)
  drop_near_gap = TRUE,         # cleaned: drop webcam beats flagged near_gap
  min_intervals = 30,           # fewer intervals in a block -> metrics NA
  facereader_retime = "auto",   # "auto" (from the video named in the log), "header", "avg", "30" or "none" - see fr_retime()
  facereader_hrv_window_s = 180,  # = FaceReader's "Heart rate variability period" (File > Settings > Advanced settings; default 5 min).
                                  #   Your projects used 3 min: HRV first appears at 179 s in r2433, r4755, s0943. Change if a project differs.
  facereader_hrv_measure = "rmssd"  # what FaceReader's HRV column holds if neither its name nor the log says (FaceReader setting: RMSSD or SDNN)
)

BLOCKS <- c("baseline", "negative_induction", "negative_recovery",
            "positive_induction", "positive_recovery")
SOURCES <- c("webcam", "webcam_optimize", "facereader")
COLS <- c(ecg = "black", kubios = "grey55", webcam = "#1f6fb4", webcam_optimize = "#2a9d4b", facereader = "#d95f02")
SOURCE_LABELS <- c(webcam = "Webcam", webcam_optimize = "Webcam opt.", facereader = "FaceReader")

# ---- paths -------------------------------------------------------------------
script_dir <- function() {
  a <- commandArgs(FALSE)
  f <- sub("^--file=", "", a[grep("^--file=", a)])
  if (length(f)) return(dirname(normalizePath(f)))
  for (i in rev(seq_len(sys.nframe()))) {
    of <- sys.frame(i)$ofile
    if (!is.null(of)) return(dirname(normalizePath(of)))
  }
  if (requireNamespace("rstudioapi", quietly = TRUE) && rstudioapi::isAvailable()) {
    p <- rstudioapi::getSourceEditorContext()$path
    if (nzchar(p)) return(dirname(p))
  }
  getwd()
}

HERE <- script_dir()
cfg <- Filter(file.exists, file.path(c(HERE, dirname(HERE), dirname(dirname(HERE))), "config.R"))  # repo root is 2 up
if (length(cfg)) source(cfg[1])
if (!exists("SERVER_ROOT")) SERVER_ROOT <- "C:/Users/carme/Box/Project_Biosignals_study_2/3_Data"

# Participant status (pilot / test / excluded) from analysis/participant_status.csv.
# If it can't be read, everyone is kept and a warning is printed (so 006 etc. still work).
ps_helper <- file.path(dirname(HERE), "participant_status.R")
PS_OK <- file.exists(ps_helper) && !inherits(tryCatch({
  PARTICIPANT_STATUS_PATH <- file.path(dirname(HERE), "participant_status.csv")
  source(ps_helper, local = TRUE)
}, error = function(e) { warning("participant_status not used: ", conditionMessage(e)); e }), "error")
if (!PS_OK) {
  participant_keep     <- function(x, include_pilots = FALSE) rep(TRUE, length(x))
  participants_dropped <- function(x, include_pilots = FALSE) data.frame()
}
pid_of_output <- function(f) sub("_.*", "", basename(f))
GROUP_LABEL <- if (!PS_OK) "all participants (participant_status.csv not read)" else if (INCLUDE_PILOTS) "main study + pilots" else "main study"

WEBCAM_HR_DIR   <- get0("WEBCAM_HR_DIR", ifnotfound = file.path(SERVER_ROOT, "webcam_biometrics"))
OFFSETS_FILE    <- file.path(SERVER_ROOT, "ecg_video_offsets.csv")
KUBIOS_DIRS     <- c(file.path(SERVER_ROOT, "kubios"),
                     file.path(SERVER_ROOT, "raw_physiology", "experimental_protocol_duration"))
FACEREADER_DIRS <- c("D:/Biosignals2_video", file.path(SERVER_ROOT, "facereader"),
                     file.path(SERVER_ROOT, "video"))
FACEREADER_DIRS_ALL <- unique(c(get0("FACEREADER_RESULTS_DIR", ifnotfound = file.path(SERVER_ROOT, "facereader")), FACEREADER_DIRS))
TIMESTAMP_DIRS  <- c("D:/Biosignals2_video", "D:/Biosignals2_png_data", file.path(SERVER_ROOT, "video"))
OUT_DIR         <- get0("HRV_COMPARISON_DIR", ifnotfound = file.path(SERVER_ROOT, "hrv_comparison"))

# ---- small helpers -----------------------------------------------------------
num <- function(x) suppressWarnings(as.numeric(x))
say <- function(...) cat(sprintf(...), "\n", sep = "")

hms <- function(s) {
  p <- num(strsplit(trimws(s), ":", fixed = TRUE)[[1]])
  if (length(p) != 3 || anyNA(p)) return(NA_real_)
  p[1] * 3600 + p[2] * 60 + p[3]
}

norm_block <- function(x) {
  x <- tolower(trimws(sub("\\(\\d+\\)$", "", trimws(x))))
  x <- gsub("[ -]+", "_", x)
  vapply(strsplit(x, "_", fixed = TRUE), function(p) {
    p[p == "neg"] <- "negative"; p[p == "pos"] <- "positive"; paste(p, collapse = "_")
  }, "")
}

find_files <- function(dirs, pattern) {
  dirs <- dirs[dir.exists(dirs)]
  as.character(unique(unlist(lapply(dirs, list.files, pattern = pattern, ignore.case = TRUE, full.names = TRUE))))
}

esc <- function(s) gsub("([][{}()+*^$|\\\\?.])", "\\\\\\1", s)

# ---- readers -------------------------------------------------------------------
find_kubios <- function(pid) {
  hits <- find_files(KUBIOS_DIRS, paste0("^", esc(pid), "_.*hrv.*\\.csv$"))
  hits <- hits[vapply(hits, function(h) any(grepl("RR INTERVAL DATA", readLines(h, warn = FALSE), fixed = TRUE)), TRUE)]
  if (length(hits) > 1) stop(pid, ": more than one Kubios report, can't choose:\n  ", paste(hits, collapse = "\n  "))
  if (!length(hits)) return(NULL)
  hits
}

# Kubios HRV report CSV -> list(blocks = per-block table incl. Kubios' own metrics, rr = beats)
read_kubios <- function(path) {
  L <- readLines(path, warn = FALSE, encoding = "UTF-8")
  L[1] <- sub("^\ufeff", "", L[1])
  f <- lapply(L, function(l) trimws(strsplit(l, ",", fixed = TRUE)[[1]]))
  first <- vapply(f, function(x) if (length(x)) x[1] else "", "")

  i_names <- which(vapply(f, function(x) length(x) > 1 && x[1] == "" && grepl("\\(\\d+\\)$", x[2]), TRUE))[1]
  if (is.na(i_names)) stop(path, ": can't find the Kubios sample names row")
  raw <- f[[i_names]][-1]; raw <- raw[raw != ""]
  nb <- length(raw)
  row <- function(label, every = 1) {
    i <- which(startsWith(first, label))[1]
    if (is.na(i)) return(rep(NA_real_, nb))
    v <- f[[i]][-1]
    if (every == 2) v <- v[seq(1, length(v), by = 2)] else v <- v[v != ""]
    length(v) <- nb
    num(v)
  }
  lim <- f[[which(startsWith(first, "Sample limits"))[1]]][-1]
  lim <- lim[lim != ""]
  win <- t(vapply(strsplit(lim, "-", fixed = TRUE), function(p) c(hms(p[1]), hms(p[2])), c(0, 0)))

  blocks <- data.frame(
    block = norm_block(raw), start = win[, 1], end = win[, 2],
    beats_corrected_pct = row("Beats corrected (%)"),
    k_mean_rr_ms = row("Mean RR", 2), k_sdnn_ms = row("SDNN (ms)", 2), k_mean_hr = row("Mean HR", 2),
    k_rmssd_ms = row("RMSSD (ms)", 2), k_pnn50 = row("pNNxx (%)", 2),
    k_sd1_ms = row("SD1 (ms)", 2), k_sd2_ms = row("SD2 (ms)", 2),
    k_lf_hf = row("LF/HF ratio", 2), k_hf_nu = row("HF (n.u.)", 2),
    stringsAsFactors = FALSE)

  i_rr <- which(startsWith(first, "RR INTERVAL DATA"))[1]
  hdr <- f[[i_rr + 1]]
  cols <- which(hdr != "")
  bl <- norm_block(hdr[cols])
  out <- list()
  i <- i_rr + 5
  while (i <= length(f) && length(f[[i]]) >= 3) {
    r <- f[[i]]
    for (k in seq_along(cols)) {
      j <- cols[k]
      tt <- if (j <= length(r)) num(r[j]) else NA
      rr <- if (j + 1 <= length(r)) num(r[j + 1]) else NA
      if (!is.na(tt) && !is.na(rr)) out[[length(out) + 1]] <- c(k, tt, rr)
    }
    i <- i + 1
  }
  m <- do.call(rbind, out)
  rr <- data.frame(block = bl[m[, 1]], t = m[, 2], rr = m[, 3], stringsAsFactors = FALSE)
  rr <- rr[order(rr$t), ]
  list(blocks = blocks, rr = rr, path = path)
}

read_offset <- function(pid) {
  if (!file.exists(OFFSETS_FILE)) stop("No ", OFFSETS_FILE, " - run 003_run_webcam_biometrics.py first.")
  o <- read.csv(OFFSETS_FILE, colClasses = "character", strip.white = TRUE)
  v <- num(o$offset_s[tolower(o$pid) == tolower(pid)])
  if (!length(v) || is.na(v[1]))
    stop(pid, ": no offset in ", OFFSETS_FILE, " - run 003_run_webcam_biometrics.py ", pid, " (it estimates it).")
  v[1]
}

# webcam beats -> data.frame(t = ECG clock, rr = as reported, segment, near_gap)
# suffix "_optimize": the optimised beat detector (003 --optimize -> <id>_webcam_beats_optimize.csv).
read_webcam <- function(pid, offset, suffix = "") {
  p <- file.path(WEBCAM_HR_DIR, paste0(pid, "_webcam_beats", suffix, ".csv"))
  if (!file.exists(p)) {
    say("  webcam%s: no %s%s", suffix, p, if (nzchar(suffix)) " (run 003_run_webcam_biometrics.py --optimize to make it)" else "")
    return(NULL)
  }
  d <- read.csv(p)
  t <- d$time_video_s + offset
  if ("time_s" %in% names(d) && any(!is.na(d$time_s))) {
    dd <- median(d$time_s - t, na.rm = TRUE)
    if (abs(dd) > 0.005)
      say("  WARNING: %s was made with a different ECG->video offset (%+.3f s from the offsets file).\n           Using the offsets file. Rerun 003 %s to refresh the CSV.", basename(p), dd, pid)
  }
  w <- data.frame(t = t, rr = d$rr_s, t_video = d$time_video_s,
                  segment = if ("segment" %in% names(d)) d$segment else NA,
                  near_gap = if ("near_gap" %in% names(d)) d$near_gap %in% 1 else FALSE)
  if (!"segment" %in% names(d)) say("  note: %s has no segment/near_gap columns (made before the gap fix) - rerun 003 %s.", basename(p), pid)
  w <- w[order(w$t), ]
  attr(w, "file") <- p
  w
}

read_frame_clock <- function(pid) {
  p <- find_files(TIMESTAMP_DIRS, paste0("^", esc(pid), "_frame_timestamps\\.csv$"))
  if (!length(p)) return(NULL)
  d <- read.csv(p[1])
  col <- if ("time_since_recording_start" %in% names(d)) d$time_since_recording_start else d[[3]]
  attr(col, "file") <- p[1]
  col
}

# FaceReader heart beat log -> data.frame(t = ECG clock, rr = FaceReader's IBI)
# FaceReader only knows frame number / nominal fps. Which nominal fps it assumed depends on the
# video it read (see 000_convert_png_to_avi.py / sussex.pick_facereader):
#   *_1to1*      the 1:1 video, nominal fps = average real fps            -> "avg"
#   *_recording* older sessions' 1:1 AVI at a nominal 30.000 fps          -> "30"
#   *realtime* / *_facereader* (without 1to1): already real time          -> "none"
read_facereader <- function(pid, offset, clock) {
  logs <- find_files(FACEREADER_DIRS_ALL, paste0("^", esc(pid), "_.*heart beat log\\.(txt|xlsx)$"))
  if (!length(logs)) { say("  FaceReader: no heart beat log found."); return(NULL) }
  if (length(logs) > 1) {
    l1 <- logs[grepl("1to1", basename(logs), ignore.case = TRUE)]
    if (length(l1) != 1) stop(pid, ": several FaceReader heart beat logs, can't choose:\n  ", paste(logs, collapse = "\n  "))
    logs <- l1
  }
  g <- read_fr_grid(logs)
  if (is.null(g)) return(NULL)
  h <- which(g[[1]] == "Time")[1]
  if (is.na(h)) stop(logs, ": no 'Time' header row - not a FaceReader heart beat log?")
  m <- fr_meta(g, h)
  tt <- fr_time_to_s(g[[1]][-seq_len(h)])
  ibi <- num(g[[2]][-seq_len(h)])
  ok <- !is.na(tt) & !is.na(ibi); tt <- tt[ok]; ibi <- ibi[ok]
  rt <- fr_retime(tt, m$video, clock, pid, m$fps)
  if (is.null(rt)) return(NULL)
  say("  FaceReader heart beat log: %s (video %s; %d beats; times %s)", basename(logs), basename(m$video), length(tt), rt$how)
  fr <- data.frame(t = rt$tv + offset, rr = ibi, t_nominal = tt, segment = NA, near_gap = FALSE)
  fr <- fr[order(fr$t), ]
  attr(fr, "file") <- logs; attr(fr, "nominal_fps") <- rt$fps
  fr
}

# metadata rows above the header: "Filename" = the video FaceReader analysed, "Frame rate" = the
# rate it used to turn frame numbers into its Time / Video Time column
fr_meta <- function(g, hdr) {
  key <- g[[1]][seq_len(hdr - 1)]; val <- g[[2]][seq_len(hdr - 1)]
  fn <- val[grepl("^file ?name", key, ignore.case = TRUE)][1]
  fps <- num(val[grepl("^frame rate", key, ignore.case = TRUE)][1])
  list(video = if (is.na(fn)) "" else gsub("\\\\", "/", fn), fps = fps)
}

# FaceReader time (frame / nominal fps) -> real time since recording start. `video` = the video
# FaceReader analysed (the log's Filename row); `fps_header` = the log's Frame rate row, which is
# exactly the rate FaceReader used (1:1 videos: the average real fps; older *_recording.avi: the
# rate stored in the AVI, e.g. 29.992 - not 30).
#   *1to1* or *_recording*  -> frame / fps_header, mapped through the real frame timestamps
#   *realtime* or *_facereader* (no 1to1): resampled real-time video, times already real -> as is
fr_retime <- function(tt, video, clock, pid, fps_header = NA) {
  mode <- SETTINGS$facereader_retime
  if (mode == "auto") {
    mode <- if (grepl("1to1|recording", video, ignore.case = TRUE)) "header"
            else if (grepl("realtime|_facereader", video, ignore.case = TRUE)) "none"
            else stop("'", video, "': can't tell which kind of video FaceReader analysed - set SETTINGS$facereader_retime.")
  }
  if (mode == "none") return(list(tv = tt, fps = NA, how = "used as they are (real-time video - NOT the same frames as the webcam analysis)"))
  if (is.null(clock)) { say("  FaceReader: no %s_frame_timestamps.csv to correct its times - FaceReader skipped.", pid); return(NULL) }
  fps <- switch(mode, header = if (is.na(fps_header)) (length(clock) - 1) / (clock[length(clock)] - clock[1]) else fps_header,
                avg = (length(clock) - 1) / (clock[length(clock)] - clock[1]), "30" = 30)
  list(tv = approx(seq_along(clock) - 1, clock, xout = tt * fps, rule = 2)$y, fps = fps,
       how = sprintf("corrected from frame/%.4f fps via the frame timestamps", fps))
}

# ---- FaceReader's OWN heart rate / HRV (detailed log) ------------------------------------
# FaceReader's detailed log (the export 03_facial_expression_analysis.Rmd reads: a few metadata
# rows incl. "Filename", then a header row starting "Video Time", one row per frame) also carries
# its vital-signs columns when the RPPG module ran: heart rate and heart rate variability (RMSSD
# or SDNN, whichever FaceReader was set to). FaceReader computes that HRV over a moving window
# and post-processes it at the end of the analysis; Noldus doesn't publish the window or the
# filtering, so it can't be reproduced from the heart beat log - hence this check.
# FaceReader Help ("Analysis in phases", "Advanced options"): HR uses the pulses of the previous
# 10 s; HRV needs the "Heart rate variability period" (1-60 min, default 5) before its first value;
# RPPG recalibrates for 8.5 s at the start and whenever the face is found again. The method paper
# it cites (Gudi et al. 2020) drops IBIs outside 250-2000 ms and beyond 3 SD, and for RMSSD keeps
# only IBIs within 1 SD of the mean - which would explain FaceReader's values being 10-25% below
# RMSSD/SDNN of its own beat log (whether FaceReader 10 uses exactly that filter isn't stated).
# Each block gets the median of FaceReader's HRV values inside it.
.fr_peek_cache <- new.env()

read_fr_grid <- function(path, n_max = Inf) {
  if (grepl("\\.xlsx?$", path, ignore.case = TRUE)) {
    if (!requireNamespace("readxl", quietly = TRUE)) {
      say("  (readxl not installed - can't read %s; install.packages(\"readxl\") or export the detailed log as .txt)", basename(path))
      return(NULL)
    }
    g <- readxl::read_excel(path, sheet = 1, col_names = FALSE, col_types = "text",
                            .name_repair = "minimal", n_max = n_max, progress = FALSE)
    g <- as.data.frame(g, stringsAsFactors = FALSE)
  } else {
    L <- readLines(path, warn = FALSE, encoding = "UTF-8", n = if (is.finite(n_max)) n_max else -1L)
    L[1] <- sub("^\ufeff", "", L[1])
    x <- strsplit(L, "\t", fixed = TRUE)
    n <- max(1L, lengths(x))
    g <- as.data.frame(do.call(rbind, lapply(x, function(r) { length(r) <- n; r })), stringsAsFactors = FALSE)
  }
  g[] <- lapply(g, function(col) trimws(as.character(col)))
  g
}

fr_time_to_s <- function(x) {
  x <- sub(",", ".", as.character(x), fixed = TRUE)
  out <- rep(NA_real_, length(x))
  is_hms <- grepl(":", x)
  out[is_hms] <- vapply(x[is_hms], hms, 0)
  out[!is_hms] <- num(x[!is_hms]) * 86400          # Excel turned it into a day fraction
  out
}

pid_of <- function(f) tolower(sub("_.*$", "", basename(gsub("\\\\", "/", f))))

find_fr_detailed <- function(pid) {
  files <- find_files(FACEREADER_DIRS_ALL, "\\.(txt|xlsx)$")
  files <- files[!grepl("heart beat log|^~\\$", basename(files), ignore.case = TRUE)]
  hits <- character(0); srcs <- character(0)
  for (f in files) {
    pk <- .fr_peek_cache[[f]]
    if (is.null(pk)) {
      g <- tryCatch(read_fr_grid(f, n_max = 40), error = function(e) NULL)
      pk <- list(detailed = FALSE)
      title <- if (!is.null(g)) tolower(g[[1]][1]) else ""
      if (!is.null(g) && ncol(g) >= 2 && any(g[[1]] == "Video Time", na.rm = TRUE) &&
          !grepl("state log|heart beat log", title)) {
        fn <- g[[2]][grepl("^file ?name", g[[1]], ignore.case = TRUE)][1]
        pk <- list(detailed = TRUE, src = if (is.na(fn)) f else fn)
      }
      assign(f, pk, envir = .fr_peek_cache)
    }
    if (pk$detailed && pid_of(pk$src) == tolower(pid)) { hits <- c(hits, f); srcs <- c(srcs, pk$src) }
  }
  if (!length(hits)) return(NULL)
  if (length(hits) > 1) {
    k <- grepl("1to1", srcs, ignore.case = TRUE)
    if (sum(k) != 1) stop(pid, ": several FaceReader detailed logs, can't choose:\n  ", paste(hits, collapse = "\n  "))
    hits <- hits[k]; srcs <- srcs[k]
  }
  list(path = hits, src = srcs)
}

read_facereader_own <- function(pid, offset, clock) {
  f <- find_fr_detailed(pid)
  if (is.null(f)) { say("  FaceReader detailed log: none found for %s - no check of FaceReader's own HRV.", pid); return(NULL) }
  g <- read_fr_grid(f$path)
  if (is.null(g)) return(NULL)
  hdr <- which(g[[1]] == "Video Time")[1]
  H <- as.character(unlist(g[hdr, ])); H[is.na(H)] <- ""
  meta <- tolower(paste(unlist(g[seq_len(hdr - 1), ]), collapse = " "))
  D <- g[-seq_len(hdr), , drop = FALSE]
  i_hr <- which(grepl("^heart ?rate( \\(bpm\\))?$", H, ignore.case = TRUE))[1]
  i_hrv <- which(grepl("heart ?rate ?var|\\bhrv\\b|rmssd|sdnn", H, ignore.case = TRUE))
  if (!length(i_hrv)) {
    say("  FaceReader detailed log %s has no heart rate variability column (was the vital signs / RPPG module on when exporting?).", basename(f$path))
    return(NULL)
  }
  tt <- fr_time_to_s(D[[1]])
  m0 <- fr_meta(g, hdr)
  rt <- fr_retime(tt, if (nzchar(m0$video)) m0$video else f$src, clock, pid, m0$fps)
  if (is.null(rt)) return(NULL)
  out <- data.frame(t = rt$tv + offset, hr = if (is.na(i_hr)) NA_real_ else num(D[[i_hr]]))
  notes <- character(0)
  for (j in i_hrv) {
    m <- if (grepl("rmssd", H[j], ignore.case = TRUE)) "rmssd"
         else if (grepl("sdnn", H[j], ignore.case = TRUE)) "sdnn"
         else if (grepl("rmssd", meta) && !grepl("sdnn", meta)) "rmssd"
         else if (grepl("sdnn", meta) && !grepl("rmssd", meta)) "sdnn"
         else SETTINGS$facereader_hrv_measure
    v <- num(D[[j]])
    if (median(v, na.rm = TRUE) < 1) { v <- v * 1000; notes <- c(notes, sprintf("'%s' looked like seconds - converted to ms", H[j])) }
    out[[paste0(m, "_ms")]] <- v
    notes <- c(notes, sprintf("'%s' read as %s%s", H[j], toupper(m),
                              if (m == SETTINGS$facereader_hrv_measure && !grepl(m, tolower(paste(H[j], meta)))) " (ASSUMED - set SETTINGS$facereader_hrv_measure if FaceReader was set to the other one)" else ""))
  }
  out <- out[!is.na(out$t), ]
  hrv_col <- if ("rmssd_ms" %in% names(out)) out$rmssd_ms else out$sdnn_ms
  attr(out, "first_hrv_t") <- suppressWarnings(min(out$t[!is.na(hrv_col)]))
  notes <- c(notes, sprintf("first HRV value %.0f s into the video", attr(out, "first_hrv_t") - offset))
  say("  FaceReader detailed log: %s (%d rows; times %s); %s", basename(f$path), nrow(out), rt$how, paste(notes, collapse = "; "))
  attr(out, "file") <- f$path
  out
}

# per block: FaceReader's own values vs the same measure computed here from its heart beat log
# FaceReader's HRV at time t describes the PREVIOUS ~180 s, so a value early in a block mostly
# describes the block before. The block's value is therefore the last valid value in the final
# 10 s of the block (its window is then ~the block itself; blocks here are ~3 min). The median over
# the block is kept as a second number. window_in_block_pct = how much of that last window lies
# inside the block (< 100 when the block is shorter than the window).
facereader_own_block <- function(own, b) {
  w <- own[own$t >= b$start & own$t <= b$end, ]
  e <- w[w$t >= b$end - 10, ]
  last <- function(col) { if (!col %in% names(e)) return(NA_real_); v <- e[[col]][!is.na(e[[col]])]; if (length(v)) v[length(v)] else NA_real_ }
  pick <- function(col, f) if (col %in% names(w) && any(!is.na(w[[col]]))) f(w[[col]], na.rm = TRUE) else NA_real_
  valid <- if ("rmssd_ms" %in% names(w)) w$rmssd_ms else w$sdnn_ms
  c(mean_hr = pick("hr", mean), rmssd_ms = last("rmssd_ms"), sdnn_ms = last("sdnn_ms"),
    rmssd_median_ms = pick("rmssd_ms", median), sdnn_median_ms = pick("sdnn_ms", median),
    valid_pct = if (nrow(w)) 100 * mean(!is.na(valid)) else NA_real_,
    window_in_block_pct = min(100, 100 * (b$end - b$start) / SETTINGS$facereader_hrv_window_s))
}

# ---- HRV metrics ---------------------------------------------------------------
# intervals: data.frame(t = time of the beat that ENDS the interval, rr = s). Successive
# differences are only taken between intervals that share a beat (no gap / removal between).
lomb_bands <- function(t, y) {
  y <- y - mean(y)
  fr <- seq(0.005, 0.40, by = 0.0025)
  P <- vapply(2 * pi * fr, function(w) {
    tau <- atan2(sum(sin(2 * w * t)), sum(cos(2 * w * t))) / (2 * w)
    cc <- cos(w * (t - tau)); ss <- sin(w * (t - tau))
    (sum(y * cc)^2 / sum(cc^2) + sum(y * ss)^2 / sum(ss^2)) / 2
  }, 0)
  lf <- sum(P[fr >= 0.04 & fr < 0.15]); hf <- sum(P[fr >= 0.15 & fr < 0.40])
  c(lf_hf = lf / hf, hf_nu = 100 * hf / (lf + hf))
}

succ_diff <- function(iv) {
  n <- nrow(iv)
  if (n < 2) return(numeric(0))
  adj <- abs((iv$t[-1] - iv$rr[-1]) - iv$t[-n]) < 0.05
  diff(iv$rr)[adj]
}

# Kubios' smoothness-priors detrending (Tarvainen et al. 2002), lambda 500, applied as Kubios does:
# to the RR series interpolated at 4 Hz. Removes slow drifts (below ~0.035 Hz). Checked on r2433 + s0723:
# SDNN within 1 ms and RMSSD within 0.7 ms of Kubios' own values. The trend is subtracted at each beat.
sp_trend <- function(z, lambda = 500) {
  n <- length(z)
  D2 <- diff(diag(n), differences = 2)
  solve(diag(n) + lambda^2 * crossprod(D2), z)
}
detrend_rr <- function(t, rr) {
  if (length(rr) < 4) return(rr - mean(rr))
  tg <- seq(min(t), max(t), by = 0.25)
  if (length(tg) > 2400) return(rr - sp_trend(rr, 38))      # > 10 min: beat-wise equivalent, avoids a huge matrix
  y <- spline(t, rr, xout = tg, method = "natural")$y
  rr - approx(tg, sp_trend(y), xout = t, rule = 2)$y
}

hrv <- function(iv) {
  iv <- iv[!is.na(iv$rr), ]
  na <- c(n_intervals = nrow(iv), mean_hr = NA, mean_rr_ms = NA, sdnn_ms = NA, rmssd_ms = NA,
          pnn50 = NA, sd1_ms = NA, sd2_ms = NA, lf_hf = NA, hf_nu = NA)
  if (nrow(iv) < SETTINGS$min_intervals) return(na)
  rr_raw <- iv$rr * 1000
  rr <- detrend_rr(iv$t, rr_raw) + mean(rr_raw)
  d <- succ_diff(iv) * 1000          # RMSSD/pNN50/SD1 on the raw series, SDNN/SD2/spectrum detrended - as Kubios
  if (length(d) < SETTINGS$min_intervals / 2) return(na)
  sdnn <- sd(rr); sd1 <- sqrt(var(d) / 2)
  c(n_intervals = nrow(iv), mean_hr = 60000 / mean(rr_raw), mean_rr_ms = mean(rr_raw), sdnn_ms = sdnn,
    rmssd_ms = sqrt(mean(d^2)), pnn50 = 100 * mean(abs(d) > 50), sd1_ms = sd1,
    sd2_ms = sqrt(max(2 * sdnn^2 - sd1^2, 0)), lomb_bands(iv$t, rr))
}

clean_intervals <- function(iv) {
  n0 <- sum(!is.na(iv$rr))
  keep <- !is.na(iv$rr) & iv$rr >= SETTINGS$min_rr_s & iv$rr <= SETTINGS$max_rr_s
  if (sum(keep) >= SETTINGS$local_k) {
    med <- rep(NA_real_, nrow(iv))
    med[keep] <- runmed(iv$rr[keep], SETTINGS$local_k, endrule = "median")
    keep <- keep & abs(iv$rr - med) <= SETTINGS$local_dev * med
  }
  if (SETTINGS$drop_near_gap) keep <- keep & !iv$near_gap
  out <- iv[keep, ]
  attr(out, "pct_removed") <- if (n0) 100 * (1 - nrow(out) / n0) else NA
  out
}

# ---- matching & diagnosis ------------------------------------------------------------
estimate_lag <- function(src_t, ecg_t) {
  r <- SETTINGS$lag_search_s
  d <- unlist(lapply(src_t, function(s) { x <- s - ecg_t; x[x > r[1] & x < r[2]] }))
  if (length(d) < 30) return(NA_real_)
  k <- density(d, bw = 0.010, from = r[1], to = r[2], n = 901)
  k$x[which.max(k$y)]
}

match_beats <- function(src_t, ecg_t, lag) {
  x <- src_t - lag
  k <- findInterval(x, ecg_t)
  lo <- pmax(k, 1); hi <- pmin(k + 1, length(ecg_t))
  i <- ifelse(abs(x - ecg_t[lo]) <= abs(x - ecg_t[hi]), lo, hi)
  e <- x - ecg_t[i]
  p <- data.frame(j = seq_along(src_t), i = i, err = e)
  p <- p[abs(p$err) <= SETTINGS$match_tol_s, ]
  p <- p[order(abs(p$err)), ]
  p <- p[!duplicated(p$i), ]
  p[order(p$j), ]
}

quant_step <- function(src, clock) {
  # beats on real frame times? (webcam beats are picked at frames)
  if (!is.null(clock) && !is.null(src$t_video)) {
    k <- findInterval(src$t_video, clock)
    k <- pmin(pmax(k, 1), length(clock) - 1)
    dmin <- pmin(abs(src$t_video - clock[k]), abs(src$t_video - clock[k + 1]))
    if (mean(dmin < 0.002, na.rm = TRUE) > 0.8) return(median(diff(clock)))
  }
  rr <- src$rr[!is.na(src$rr)]
  steps <- c(1 / 30, if (!is.null(attr(src, "nominal_fps"))) 1 / attr(src, "nominal_fps"))
  for (s in steps[!is.na(steps)]) {
    r <- rr / s
    if (mean(abs(r - round(r)) < 0.1) > 0.8) return(s)
  }
  NA_real_
}

diagnose_block <- function(name, src, ecg, b, lag, qstep) {
  win <- c(b$start, b$end)
  e_in <- ecg[ecg$block == b$block, ]
  ecg_iv <- data.frame(t = e_in$t, rr = e_in$rr)
  s_in <- src[src$t >= win[1] & src$t <= win[2], ]
  as_is <- data.frame(t = s_in$t, rr = s_in$rr, near_gap = s_in$near_gap)
  cleaned <- clean_intervals(as_is)
  m_ecg <- hrv(ecg_iv); m_as <- hrv(as_is); m_cl <- hrv(cleaned)

  d <- list(block = b$block, source = name, ecg_beats = nrow(e_in), src_beats = nrow(s_in))
  # gaps: new segment, or an interval longer than max_rr
  gap_len <- c(diff(s_in$t))
  seg_break <- if (all(is.na(s_in$segment))) rep(FALSE, length(gap_len)) else diff(s_in$segment) != 0
  is_gap <- gap_len > SETTINGS$max_rr_s | seg_break
  d$n_gaps <- sum(is_gap)
  d$longest_gap_s <- if (any(is_gap)) max(gap_len[is_gap]) else 0
  d$time_in_gaps_pct <- 100 * sum(gap_len[is_gap]) / diff(win)
  d$near_gap_pct <- 100 * mean(s_in$near_gap)

  if (is.na(lag) || !nrow(e_in)) {
    d$recall_pct <- d$precision_pct <- NA
  } else {
    lo <- min(e_in$t) - SETTINGS$match_tol_s; hi <- max(e_in$t) + SETTINGS$match_tol_s
    p <- match_beats(src$t, ecg$t, lag)
    ecg_idx <- which(ecg$block == b$block)
    src_idx <- which(src$t - lag >= lo & src$t - lag <= hi)
    pm <- p[p$i %in% ecg_idx & p$j %in% src_idx, ]
    d$matched <- nrow(pm)
    d$missed <- length(ecg_idx) - nrow(pm)
    d$extra <- length(src_idx) - nrow(pm)
    # a missed R-peak with an unmatched webcam beat within half a beat = a beat that WAS detected
    # but more than match_tol_s off ("mistimed"), rather than truly missed + a false beat
    miss_i <- setdiff(ecg_idx, pm$i); extra_j <- setdiff(src_idx, pm$j)
    half <- 0.5 * median(diff(ecg$t[ecg_idx]))
    used <- rep(FALSE, length(extra_j)); d$mistimed <- 0
    for (ii in miss_i) {
      if (!length(extra_j)) break
      dd <- abs(src$t[extra_j] - lag - ecg$t[ii]); dd[used] <- Inf
      w <- which.min(dd)
      if (dd[w] <= half) { used[w] <- TRUE; d$mistimed <- d$mistimed + 1 }
    }
    d$recall_pct <- 100 * nrow(pm) / length(ecg_idx)
    d$precision_pct <- if (length(src_idx)) 100 * nrow(pm) / length(src_idx) else NA
    d$lag_block_ms <- 1000 * (lag + median(pm$err))
    d$jitter_ms <- 1000 * mad(pm$err)
    # matched intervals: consecutive webcam beats matched to consecutive ECG beats, same segment
    q <- which(diff(pm$j) == 1 & diff(pm$i) == 1)
    if (!all(is.na(src$segment))) q <- q[src$segment[pm$j[q]] == src$segment[pm$j[q + 1]]]
    s_iv <- data.frame(t = src$t[pm$j[q + 1]], rr = src$t[pm$j[q + 1]] - src$t[pm$j[q]])
    e_iv <- data.frame(t = ecg$t[pm$i[q + 1]], rr = ecg$t[pm$i[q + 1]] - ecg$t[pm$i[q]])
    err <- (s_iv$rr - e_iv$rr) * 1000
    d$matched_intervals_pct <- 100 * length(q) / max(nrow(ecg_iv), 1)
    d$ibi_err_median_abs_ms <- if (length(err)) median(abs(err)) else NA
    d$ibi_err_within_50ms_pct <- if (length(err)) 100 * mean(abs(err) <= 50) else NA
    ds <- succ_diff(s_iv); de <- succ_diff(e_iv)
    d$noise_rmssd_ms <- if (length(ds) >= 10) 1000 * sqrt(mean((ds - de)^2)) else NA
    m_ms <- hrv(s_iv); m_me <- hrv(e_iv)
    d$rmssd_matched_src_ms <- m_ms[["rmssd_ms"]]
    d$rmssd_matched_ecg_ms <- m_me[["rmssd_ms"]]
    d$attr_artefacts_ms <- m_as[["rmssd_ms"]] - m_ms[["rmssd_ms"]]
    d$attr_timing_ms <- m_ms[["rmssd_ms"]] - m_me[["rmssd_ms"]]
    d$attr_selection_ms <- m_me[["rmssd_ms"]] - m_ecg[["rmssd_ms"]]
    attr(d, "pairs") <- pm
  }
  d$implausible_intervals <- sum(!is.na(as_is$rr) & (as_is$rr < SETTINGS$min_rr_s | as_is$rr > SETTINGS$max_rr_s))
  d$cleaned_removed_pct <- attr(cleaned, "pct_removed")
  d$quant_step_ms <- 1000 * qstep
  d$quant_floor_rmssd_ms <- 1000 * qstep / sqrt(2)
  d$rmssd_ecg_ms <- m_ecg[["rmssd_ms"]]
  d$rmssd_as_is_ms <- m_as[["rmssd_ms"]]
  d$rmssd_cleaned_ms <- m_cl[["rmssd_ms"]]
  list(diag = d, metrics = list(as_is = m_as, cleaned = m_cl, ecg = m_ecg),
       ivs = list(as_is = as_is, cleaned = cleaned))
}

# plain-language summary of one diagnostics row
explain <- function(d, lag_p) {
  lab <- SOURCE_LABELS[[d$source]]
  if (is.na(d$rmssd_ecg_ms)) return(sprintf("  %-10s too few ECG intervals in this block - not scored.", lab))
  if (is.na(d$recall_pct)) return(sprintf("  %-10s no usable beats / delay could not be estimated.", lab))
  s <- sprintf("  %-10s RMSSD %s (cleaned %s) vs ECG %.1f ms.", lab, fmt(d$rmssd_as_is_ms), fmt(d$rmssd_cleaned_ms), d$rmssd_ecg_ms)
  n_e <- d$ecg_beats
  bits <- c(sprintf("of the R-peaks %.0f%% were found on time (+-%.0f ms), %.0f%% found but further off, %.0f%% missed; %d false beat(s) (%.0f%% of its beats)",
                    100 * d$matched / n_e, 1000 * SETTINGS$match_tol_s, 100 * d$mistimed / n_e,
                    100 * (d$missed - d$mistimed) / n_e, as.integer(d$extra - d$mistimed),
                    100 * (d$extra - d$mistimed) / max(d$src_beats, 1)))
  if (d$n_gaps > 0) bits <- c(bits, sprintf("face lost %d x (longest %.1f s, %.0f%% of block)", d$n_gaps, d$longest_gap_s, d$time_in_gaps_pct))
  if (!is.na(d$jitter_ms)) bits <- c(bits, sprintf("on-time beats wobble +-%.0f ms (MAD) around the R-peak", d$jitter_ms))
  s <- paste0(s, "\n             ", paste(bits, collapse = ";\n             "), ".")
  parts <- c(artefacts = d$attr_artefacts_ms, timing = d$attr_timing_ms, selection = d$attr_selection_ms)
  if (all(!is.na(parts))) {
    s <- paste0(s, sprintf("\n             Error split: unmatched beats & gaps %+.1f, timing noise %+.1f, which beats survived %+.1f ms.",
                           parts[1], parts[2], parts[3]))
    main <- names(which.max(abs(parts)))
    why <- switch(main,
      artefacts = if (!is.na(d$mistimed) && d$mistimed >= 0.5 * (d$missed + d$extra - d$mistimed))
                    "Mostly beats that were detected but at the wrong moment (>150 ms off) -> beat timing is the problem more than detection; correction can only delete them."
                  else "Mostly missed/false beats and gaps -> artefact correction or quality gating would help most.",
      timing = "Mostly timing noise on beats that were found -> better beat timing (sub-frame peaks) would help most.",
      selection = "Mostly WHICH beats survived (the hard stretches were dropped) -> the number looks better than the data are.")
    s <- paste0(s, "\n             ", why)
  }
  if (!is.na(d$quant_floor_rmssd_ms) && !is.na(d$noise_rmssd_ms))
    s <- paste0(s, sprintf("\n             Beat times sit on video frames (%.1f ms): that alone adds ~%.0f ms of the %.0f ms timing noise.",
                           d$quant_step_ms, d$quant_floor_rmssd_ms, d$noise_rmssd_ms))
  if (!is.na(d$lag_block_ms) && !is.na(lag_p) && abs(d$lag_block_ms - 1000 * lag_p) > 40)
    s <- paste0(s, sprintf("\n             Pulse delay here %.0f ms vs %.0f ms overall - a change in pulse transit (arousal?) or clock drift.",
                           d$lag_block_ms, 1000 * lag_p))
  s
}
fmt <- function(x) if (is.null(x) || is.na(x)) "NA" else sprintf("%.1f", x)

# Plain-language verdict on FaceReader's own HRV vs what its heart beat log gives (one participant)
own_summary <- function(oc) {
  out <- "FaceReader's own HRV vs its heart beat log:"
  for (m in unique(oc$measure)) {
    x <- oc[oc$measure == m & !is.na(oc$ecg), ]
    if (!nrow(x)) next
    x <- x[!is.na(x$facereader_own_block_end), ]
    if (!nrow(x)) next
    e_own <- mean(abs(x$facereader_own_block_end - x$ecg))
    e_as <- mean(abs(x$from_beat_log_as_is - x$ecg), na.rm = TRUE)
    e_cl <- mean(abs(x$from_beat_log_cleaned - x$ecg), na.rm = TRUE)
    d_as <- mean(abs(x$facereader_own_block_end - x$from_beat_log_as_is), na.rm = TRUE)
    d_cl <- mean(abs(x$facereader_own_block_end - x$from_beat_log_cleaned), na.rm = TRUE)
    out <- c(out, sprintf("  %s, %d block(s): mean error vs ECG - FaceReader's own %.1f ms, beat log as is %s, beat log cleaned %s.",
                          toupper(m), nrow(x), e_own, fmt(e_as), fmt(e_cl)))
    out <- c(out, if (is.na(d_cl) || is.na(d_as)) "  (beat log values missing for these blocks)"
      else if (abs(d_cl - d_as) < 2) sprintf("  Its own value is about as far from the raw beat log (%.1f ms) as from the cleaned one (%.1f ms) - the cleaning removed little here, so this can't tell whether FaceReader filters.", d_as, d_cl)
      else if (d_cl < d_as) sprintf("  Its own value is closer to the CLEANED beat log (%.1f ms apart) than the raw one (%.1f ms) - FaceReader filters out bad intervals itself, so the raw heart beat log should not be used as-is.", d_cl, d_as)
      else sprintf("  Its own value is closer to the RAW beat log (%.1f ms apart) than the cleaned one (%.1f ms) - FaceReader does little filtering beyond what the log shows.", d_as, d_cl))
    if (nrow(x) >= 3) {
      r_own <- suppressWarnings(cor(x$facereader_own_block_end, x$ecg, method = "spearman"))
      ok <- !is.na(x$from_beat_log_cleaned)
      r_cl <- if (sum(ok) >= 3) suppressWarnings(cor(x$from_beat_log_cleaned[ok], x$ecg[ok], method = "spearman")) else NA
      out <- c(out, sprintf("  Does it rank the blocks like the ECG? Spearman rho: own %s, cleaned beat log %s (with %d blocks this is only a rough check).",
                            fmt(r_own), fmt(r_cl), nrow(x)))
    }
  }
  out <- c(out, "  Remember: FaceReader's HRV is a trailing window (its 'Heart rate variability period' setting, 3 min in these projects) that it filters itself (it reads 10-25% below RMSSD/SDNN of its own beat log); the value at block end covers about the block, but not exactly the same beats - expect some difference even if both were perfect. It gives no HRV until that period has passed.")
  out
}

# ---- plots -----------------------------------------------------------------------
plot_block <- function(b, ecg, srcs, res) {
  e <- ecg[ecg$block == b$block, ]
  if (nrow(e) < 2) return(invisible())
  t0 <- b$start
  layout(matrix(1:3, 3), heights = c(5, 3, 2))
  op <- par(mar = c(1, 8, 4, 1), mgp = c(2.4, 0.7, 0))
  yl <- range(e$rr * 1000) + c(-1, 1) * diff(range(e$rr * 1000)) * c(1.2, 1.5)
  clip <- function(y) pmin(pmax(y, yl[1]), yl[2])
  plot(e$t - t0, e$rr * 1000, type = "l", lwd = 1.6, col = COLS["ecg"], ylim = yl, xlim = c(0, b$end - t0),
       xlab = "", ylab = "beat-to-beat interval (ms)", xaxt = "n",
       main = "")
  title(sprintf("%s  -  %s", attr(res, "pid"), gsub("_", " ", b$block)), line = 2.6)
  for (nm in names(srcs)) {
    s <- srcs[[nm]]; s <- s[s$t >= b$start & s$t <= b$end, ]
    if (!nrow(s)) next
    is_gap <- c(FALSE, diff(s$t) > SETTINGS$max_rr_s | (!is.na(s$segment[1]) & diff(s$segment) != 0))
    for (g in which(is_gap)) rect(s$t[g - 1] - t0, yl[1], s$t[g] - t0, yl[2], col = adjustcolor(COLS[nm], 0.12), border = NA)
    y <- s$rr * 1000; y[is_gap] <- NA
    lines(s$t - t0, clip(y), col = COLS[nm])
    out <- !is.na(y) & (y < yl[1] | y > yl[2])
    points(s$t[!out] - t0, y[!out], pch = ifelse(s$near_gap[!out], 1, 16), cex = 0.45, col = COLS[nm])
    points(s$t[out] - t0, clip(y[out]), pch = ifelse(y[out] > yl[2], 24, 25), cex = 0.8, col = COLS[nm], bg = COLS[nm])
  }
  legend("bottom", inset = c(0, 1.0), xpd = NA, horiz = TRUE, c("ECG", names(srcs), "near face-loss", "off scale", "face lost"), bty = "n", cex = 0.8,
         col = c(COLS["ecg"], COLS[names(srcs)], "grey40", "grey40", "grey85"), lty = c(1, rep(1, length(srcs)), NA, NA, NA),
         pch = c(NA, rep(16, length(srcs)), 1, 24, 15), pt.cex = c(1, rep(0.6, length(srcs)), 0.8, 0.8, 1.6))
  par(mar = c(1, 8, 0.5, 1))
  plot(NA, xlim = c(0, b$end - t0), ylim = 1000 * c(-1, 1) * SETTINGS$match_tol_s, xaxt = "n", xlab = "",
       ylab = "beat timing error (ms)\n(after delay removed)")
  abline(h = 0, col = "grey70")
  for (nm in names(srcs)) {
    p <- attr(res[[nm]][[b$block]]$diag, "pairs")
    if (!is.null(p) && nrow(p)) points(srcs[[nm]]$t[p$j] - t0, 1000 * p$err, pch = 16, cex = 0.4, col = COLS[nm])
  }
  par(mar = c(4, 8, 0.5, 1))
  nms <- names(srcs)
  plot(NA, xlim = c(0, b$end - t0), ylim = c(0.5, 2 * length(nms) + 0.5), yaxt = "n", xlab = "seconds into block", ylab = "")
  labs <- character(0)
  for (k in seq_along(nms)) {
    nm <- nms[k]; p <- attr(res[[nm]][[b$block]]$diag, "pairs"); s <- srcs[[nm]]
    if (is.null(p)) next
    ei <- which(ecg$block == b$block); missed <- setdiff(ei, p$i)
    sj <- which(s$t >= b$start & s$t <= b$end); extra <- setdiff(sj, p$j)
    y1 <- 2 * k - 1; y2 <- 2 * k
    if (length(missed)) segments(ecg$t[missed] - t0, y1 - 0.35, ecg$t[missed] - t0, y1 + 0.35, col = COLS[nm], lwd = 1.5)
    if (length(extra)) segments(s$t[extra] - t0, y2 - 0.35, s$t[extra] - t0, y2 + 0.35, col = COLS[nm], lwd = 1.5)
    labs <- c(labs, paste(nm, "missed"), paste(nm, "extra"))
  }
  axis(2, at = seq_along(labs), labels = labs, las = 1, cex.axis = 0.75, tick = FALSE)
  par(op); layout(1)
}

plot_summary <- function(pid, tab) {
  par(mfrow = c(3, 1), mar = c(3, 4.5, 2.5, 1))
  bl <- BLOCKS[BLOCKS %in% tab$block]
  keys <- list(c("ecg", "kubios_report", "kubios", 4), c("ecg", "as_is", "ecg", 16),
               c("webcam", "as_is", "webcam", 1), c("webcam", "cleaned", "webcam", 16),
               c("webcam_optimize", "as_is", "webcam_optimize", 1), c("webcam_optimize", "cleaned", "webcam_optimize", 16),
               c("facereader", "as_is", "facereader", 1), c("facereader", "cleaned", "facereader", 16),
               c("facereader", "facereader_own", "facereader", 17))
  for (m in c("rmssd_ms", "sdnn_ms", "mean_hr")) {
    v <- tab[[m]]
    if (all(is.na(v))) { plot.new(); next }
    lg <- if (m == "mean_hr") "" else "y"
    plot(NA, xlim = c(0.5, length(bl) + 0.5), ylim = range(v, na.rm = TRUE) * c(0.9, 1.1), xaxt = "n", xlab = "", log = lg,
         ylab = paste(m, if (lg == "y") "(log scale)" else ""), main = if (m == "rmssd_ms") paste(pid, "- per block") else "")
    axis(1, at = seq_along(bl), labels = gsub("_", " ", bl), cex.axis = 0.8)
    for (k in seq_along(keys)) {
      ky <- keys[[k]]; r <- tab[tab$source == ky[1] & tab$version == ky[2], ]
      x <- match(r$block, bl) + (k - 5) * 0.07
      points(x, r[[m]], pch = as.integer(ky[4]), col = COLS[ky[3]], cex = 1.2)
    }
    if (m == "rmssd_ms") legend("topleft", c("Kubios report", "ECG (this script)", "webcam as is", "webcam cleaned",
                                             "webcam opt. as is", "webcam opt. cleaned",
                                             "FaceReader as is", "FaceReader cleaned", "FaceReader's own HRV"), bty = "n", cex = 0.7, ncol = 5,
                                pch = c(4, 16, 1, 16, 1, 16, 1, 16, 17),
                                col = COLS[c("kubios", "ecg", "webcam", "webcam", "webcam_optimize", "webcam_optimize", "facereader", "facereader", "facereader")])
  }
  par(mfrow = c(1, 1))
}

# ---- one participant ---------------------------------------------------------------
run_pid <- function(pid) {
  say("\n==== %s ====", pid)
  kp <- find_kubios(pid)
  if (is.null(kp)) { say("  no Kubios report (%s_*hrv*.csv) in %s - skipped.", pid, paste(KUBIOS_DIRS, collapse = " or ")); return(NULL) }
  k <- read_kubios(kp)
  offset <- read_offset(pid)
  clock <- read_frame_clock(pid)
  say("  Kubios: %s | ECG->video offset %.3f s", basename(kp), offset)
  srcs <- Filter(Negate(is.null), list(webcam = read_webcam(pid, offset),
                                       webcam_optimize = read_webcam(pid, offset, "_optimize"),
                                       facereader = read_facereader(pid, offset, clock)))
  if (!length(srcs)) { say("  nothing to compare."); return(NULL) }
  own <- read_facereader_own(pid, offset, clock)
  blocks <- k$blocks[k$blocks$block %in% BLOCKS, ]

  rows <- list(); diags <- list(); res <- list(); text <- character(0)
  for (i in seq_len(nrow(blocks))) {
    b <- blocks[i, ]
    rows[[length(rows) + 1]] <- data.frame(pid = pid, block = b$block, source = "ecg", version = "kubios_report",
      n_intervals = sum(k$rr$block == b$block), pct_removed = b$beats_corrected_pct, mean_hr = b$k_mean_hr,
      mean_rr_ms = b$k_mean_rr_ms, sdnn_ms = b$k_sdnn_ms, rmssd_ms = b$k_rmssd_ms, pnn50 = b$k_pnn50,
      sd1_ms = b$k_sd1_ms, sd2_ms = b$k_sd2_ms, lf_hf = b$k_lf_hf, hf_nu = b$k_hf_nu)
  }
  lags <- list()
  for (nm in names(srcs)) {
    s <- srcs[[nm]]
    lag <- estimate_lag(s$t, k$rr$t)
    lags[[nm]] <- lag
    q <- quant_step(s, clock)
    say("  %s: pulse delay %s ms%s; beat times %s", nm, if (is.na(lag)) "NA" else sprintf("%+.0f", 1000 * lag),
        if (!is.na(lag) && (lag < SETTINGS$lag_ok_s[1] || lag > SETTINGS$lag_ok_s[2])) "  <-- OUTSIDE the usual range: check the ECG->video offset" else "",
        if (is.na(q)) "not locked to video frames" else sprintf("locked to video frames (%.1f ms)", 1000 * q))
    res[[nm]] <- list()
    for (i in seq_len(nrow(blocks))) {
      b <- blocks[i, ]
      r <- diagnose_block(nm, s, k$rr, b, lag, q)
      res[[nm]][[b$block]] <- r
      d <- r$diag
      diags[[length(diags) + 1]] <- data.frame(pid = pid, lag_participant_ms = 1000 * lag,
        d[setdiff(names(d), character(0))], check.names = FALSE)
      for (v in c("as_is", "cleaned"))
        rows[[length(rows) + 1]] <- data.frame(pid = pid, block = b$block, source = nm, version = v,
          as.list(r$metrics[[v]]), pct_removed = if (v == "cleaned") attr(r$ivs$cleaned, "pct_removed") else 0)
      if (nm == names(srcs)[1])
        rows[[length(rows) + 1]] <- data.frame(pid = pid, block = b$block, source = "ecg", version = "as_is",
          as.list(r$metrics$ecg), pct_removed = 0)
    }
  }
  own_chk <- NULL
  if (!is.null(own)) {
    for (i in seq_len(nrow(blocks))) {
      b <- blocks[i, ]; o <- facereader_own_block(own, b)
      rows[[length(rows) + 1]] <- data.frame(pid = pid, block = b$block, source = "facereader", version = "facereader_own",
        n_intervals = NA, pct_removed = 100 - o[["valid_pct"]], mean_hr = o[["mean_hr"]], mean_rr_ms = NA,
        sdnn_ms = o[["sdnn_ms"]], rmssd_ms = o[["rmssd_ms"]], pnn50 = NA, sd1_ms = NA, sd2_ms = NA, lf_hf = NA, hf_nu = NA)
      get <- function(src, v, m) { r <- Filter(function(x) x$block == b$block && x$source == src && x$version == v, rows); if (length(r)) r[[1]][[m]] else NA }
      for (m in c("rmssd_ms", "sdnn_ms")) if (!is.na(o[[m]]) || !is.na(o[[sub("_ms", "_median_ms", m)]]))
        own_chk <- rbind(own_chk, data.frame(pid = pid, block = b$block, measure = sub("_ms", "", m),
          facereader_own_block_end = o[[m]], facereader_own_median = o[[sub("_ms", "_median_ms", m)]],
          own_valid_pct = o[["valid_pct"]], own_window_in_block_pct = o[["window_in_block_pct"]],
          from_beat_log_as_is = get("facereader", "as_is", m), from_beat_log_cleaned = get("facereader", "cleaned", m),
          ecg = get("ecg", "as_is", m), facereader_own_hr = o[["mean_hr"]],
          beat_log_hr = get("facereader", "as_is", "mean_hr"), ecg_hr = get("ecg", "as_is", "mean_hr")))
    }
  }
  tab <- do.call(rbind, lapply(rows, function(r) r[, c("pid", "block", "source", "version", "n_intervals", "pct_removed",
    "mean_hr", "mean_rr_ms", "sdnn_ms", "rmssd_ms", "pnn50", "sd1_ms", "sd2_ms", "lf_hf", "hf_nu")]))
  tab <- tab[order(match(tab$block, BLOCKS), match(tab$source, c("ecg", SOURCES)), tab$version), ]
  dg <- do.call(rbind, lapply(diags, function(x) { x[setdiff(c("matched", "missed", "extra", "recall_pct", "precision_pct",
        "mistimed", "lag_block_ms", "jitter_ms", "matched_intervals_pct", "ibi_err_median_abs_ms", "ibi_err_within_50ms_pct",
        "noise_rmssd_ms", "rmssd_matched_src_ms", "rmssd_matched_ecg_ms", "attr_artefacts_ms", "attr_timing_ms",
        "attr_selection_ms"), names(x))] <- NA; x }))

  # ECG self-check: this script's maths vs Kubios' own numbers
  chk <- merge(tab[tab$source == "ecg" & tab$version == "as_is", c("block", "rmssd_ms", "sdnn_ms", "mean_hr")],
               tab[tab$version == "kubios_report", c("block", "rmssd_ms", "sdnn_ms", "mean_hr")], by = "block", suffixes = c("", "_k"))
  chk <- chk[!is.na(chk$rmssd_ms) & !is.na(chk$rmssd_ms_k), ]
  text <- c(text, sprintf("%s  (Kubios: %s; offset %.3f s)", pid, basename(kp), offset))
  if (nrow(chk)) {
    text <- c(text, sprintf("ECG check, this script vs Kubios: RMSSD differs by up to %.1f ms, SDNN %.1f ms, HR %.2f bpm%s",
      max(abs(chk$rmssd_ms - chk$rmssd_ms_k)), max(abs(chk$sdnn_ms - chk$sdnn_ms_k)), max(abs(chk$mean_hr - chk$mean_hr_k)),
      if (max(abs(chk$sdnn_ms - chk$sdnn_ms_k)) > 3 || max(abs(chk$rmssd_ms - chk$rmssd_ms_k)) > 3) " - larger than expected, check the report's settings (this script assumes smoothness-priors detrending, lambda 500)." else "."))
  }
  bc <- blocks$beats_corrected_pct
  if (any(bc > 5, na.rm = TRUE))
    text <- c(text, sprintf("WARNING: Kubios corrected >5%% of ECG beats in %s - the ground truth itself is shaky there.",
                            paste(blocks$block[bc > 5 & !is.na(bc)], collapse = ", ")))
  for (nm in names(srcs)) if (!is.na(lags[[nm]]))
    text <- c(text, sprintf("%s pulse delay vs R-peak: %+.0f ms%s", nm, 1000 * lags[[nm]],
      if (lags[[nm]] < SETTINGS$lag_ok_s[1] || lags[[nm]] > SETTINGS$lag_ok_s[2]) " - OUTSIDE -50..450 ms: the offset is probably wrong; don't trust beat-level numbers." else ""))
  for (i in seq_len(nrow(blocks))) {
    text <- c(text, "", sprintf("[%s]", gsub("_", " ", blocks$block[i])))
    for (nm in names(srcs)) text <- c(text, explain(res[[nm]][[blocks$block[i]]]$diag, lags[[nm]]))
    oc <- own_chk[!is.null(own_chk) & own_chk$block == blocks$block[i], , drop = FALSE]
    for (r in seq_len(NROW(oc)))
      text <- c(text, sprintf("  FaceReader's own %s (detailed log, value at block end; block median %s): %s ms | from its heart beat log: as is %s, cleaned %s | ECG %s",
                              toupper(oc$measure[r]), fmt(oc$facereader_own_median[r]), fmt(oc$facereader_own_block_end[r]),
                              fmt(oc$from_beat_log_as_is[r]), fmt(oc$from_beat_log_cleaned[r]), fmt(oc$ecg[r])))
  }
  if (!is.null(own_chk)) text <- c(text, "", own_summary(own_chk))

  dir.create(OUT_DIR, showWarnings = FALSE, recursive = TRUE)
  write.csv(rnd(tab), file.path(OUT_DIR, paste0(pid, "_hrv_by_block.csv")), row.names = FALSE, na = "")
  write.csv(rnd(dg), file.path(OUT_DIR, paste0(pid, "_hrv_diagnostics.csv")), row.names = FALSE, na = "")
  writeLines(text, file.path(OUT_DIR, paste0(pid, "_hrv_diagnosis.txt")))
  if (!is.null(own_chk)) write.csv(rnd(own_chk), file.path(OUT_DIR, paste0(pid, "_facereader_own_vs_beatlog.csv")), row.names = FALSE, na = "")
  cat("\n", paste(text, collapse = "\n"), "\n", sep = "")
  attr(res, "pid") <- pid
  pdf(file.path(OUT_DIR, paste0(pid, "_hrv_plots.pdf")), width = 11, height = 8.5)
  plot_summary(pid, tab)
  for (i in seq_len(nrow(blocks))) plot_block(blocks[i, ], k$rr, srcs, res)
  dev.off()
  say("\n  saved %s_hrv_by_block.csv, _hrv_diagnostics.csv, _hrv_diagnosis.txt, _hrv_plots.pdf in %s", pid, OUT_DIR)
  list(tab = tab, diag = dg)
}

rnd <- function(df) { for (n in names(df)) if (is.numeric(df[[n]])) df[[n]] <- round(df[[n]], 3); df }

# ---- across participants -----------------------------------------------------------
merge_all <- function(suffix, out) {
  f <- list.files(OUT_DIR, pattern = paste0(suffix, "$"), full.names = TRUE)
  f <- f[!startsWith(basename(f), "all_")]
  f <- f[participant_keep(pid_of_output(f), INCLUDE_PILOTS)]   # same selection as --all
  if (!length(f)) return(NULL)
  d <- lapply(f, read.csv)
  cols <- unique(unlist(lapply(d, names)))
  d <- do.call(rbind, lapply(d, function(y) { y[setdiff(cols, names(y))] <- NA; y[cols] }))
  write.csv(d, file.path(OUT_DIR, out), row.names = FALSE, na = "")
  d
}

agreement <- function(all) {
  ref <- all[all$source == "ecg" & all$version == "as_is", ]
  out <- list()
  pdf(file.path(OUT_DIR, "all_hrv_agreement.pdf"), width = 11, height = 8.5)
  par(mfrow = c(2, 3), mar = c(4.5, 4.5, 3, 1))
  for (src in SOURCES) for (v in c("as_is", "cleaned", "facereader_own")) {
    s <- all[all$source == src & all$version == v, ]
    if (!nrow(s)) next
    j <- merge(s, ref, by = c("pid", "block"), suffixes = c("", "_ecg"))
    for (m in c("mean_hr", "sdnn_ms", "rmssd_ms", "pnn50", "lf_hf", "hf_nu")) {
      x <- j[[paste0(m, "_ecg")]]; y <- j[[m]]; ok <- !is.na(x) & !is.na(y)
      if (sum(ok) < 2) next
      dd <- y[ok] - x[ok]
      out[[length(out) + 1]] <- data.frame(source = src, version = v, metric = m, n_blocks = sum(ok),
        n_participants = length(unique(j$pid[ok])), ecg_mean = mean(x[ok]), source_mean = mean(y[ok]),
        bias = mean(dd), loa_low = mean(dd) - 1.96 * sd(dd), loa_high = mean(dd) + 1.96 * sd(dd),
        mae = mean(abs(dd)), mape_pct = 100 * mean(abs(dd) / x[ok]),
        r = if (sum(ok) >= 3) cor(x[ok], y[ok]) else NA)
      if (m %in% c("mean_hr", "sdnn_ms", "rmssd_ms") && sum(ok) >= 3) {
        a <- (x[ok] + y[ok]) / 2
        plot(a, dd, pch = 16, col = COLS[src], xlab = paste("mean of ECG and", src), ylab = paste(src, "- ECG"),
             main = sprintf("%s %s: %s (n=%d, %s)", src, v, m, sum(ok), GROUP_LABEL))
        abline(h = c(mean(dd), mean(dd) + c(-1.96, 1.96) * sd(dd)), lty = c(1, 2, 2), col = "grey40")
        abline(h = 0, col = "grey80")
      }
    }
  }
  dev.off()
  if (length(out)) {
    ag <- rnd(do.call(rbind, out))
    write.csv(ag, file.path(OUT_DIR, "all_hrv_agreement.csv"), row.names = FALSE, na = "")
    ag
  }
}

# ---- main ------------------------------------------------------------------------------
main <- function() {
  args <- commandArgs(TRUE)
  if ("--pilots" %in% args)    INCLUDE_PILOTS <<- TRUE
  if ("--no-pilots" %in% args) INCLUDE_PILOTS <<- FALSE
  args <- setdiff(args, c("--pilots", "--no-pilots"))
  GROUP_LABEL <<- if (!PS_OK) "all participants (participant_status.csv not read)" else if (INCLUDE_PILOTS) "main study + pilots" else "main study"
  pids <- if (length(args)) args else PIDS
  if (identical(pids, "--all")) {
    f <- list.files(WEBCAM_HR_DIR, pattern = "_webcam_beats\\.csv$")
    pids <- sub("_webcam_beats\\.csv$", "", f)
    dropped <- participants_dropped(pids, INCLUDE_PILOTS)
    if (nrow(dropped)) {
      say("Left out (participant_status.csv, INCLUDE_PILOTS = %s): %s", INCLUDE_PILOTS,
          paste0(dropped$participant_id, " (", dropped$status, ")", collapse = ", "))
    }
    pids <- pids[participant_keep(pids, INCLUDE_PILOTS)]
    if (!length(pids)) stop("No participants left for --all (INCLUDE_PILOTS = ", INCLUDE_PILOTS,
                            "). Use --pilots to include the pilot participants.")
  } else {
    named_out <- pids[!participant_keep(pids, INCLUDE_PILOTS)]
    if (length(named_out)) say("Note: %s run individually but left out of the pooled all_* files (INCLUDE_PILOTS = %s; use --pilots to pool them).",
                               paste(named_out, collapse = ", "), INCLUDE_PILOTS)
  }
  if (!length(pids)) stop("Give participant IDs: Rscript 005_compare_hrv.R r2433 s0723   (or --all)")
  say("pooled outputs: %s", GROUP_LABEL)
  say("data: %s\nwebcam beats: %s\noutput: %s", SERVER_ROOT, WEBCAM_HR_DIR, OUT_DIR)
  for (p in pids) tryCatch(run_pid(p), error = function(e) say("  %s FAILED: %s", p, conditionMessage(e)))
  all <- merge_all("_hrv_by_block\\.csv", "all_hrv_by_block.csv")
  merge_all("_hrv_diagnostics\\.csv", "all_hrv_diagnostics.csv")
  if (!is.null(all)) {
    ag <- agreement(all)
    if (!is.null(ag)) {
      say("\nAgreement with ECG across all blocks so far (RMSSD; %s):", GROUP_LABEL)
      print(ag[ag$metric == "rmssd_ms", c("source", "version", "n_blocks", "n_participants", "ecg_mean", "source_mean", "bias", "loa_low", "loa_high", "mae")], row.names = FALSE)
    }
  }
}

if (!isTRUE(get0("HRV_NO_MAIN"))) main()   # 006_compare_facereader_runs.R sources this file for its readers
