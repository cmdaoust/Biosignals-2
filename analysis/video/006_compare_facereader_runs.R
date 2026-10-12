#!/usr/bin/env Rscript
# =============================================================================
# 006_compare_facereader_runs.R
# =============================================================================
# Compares two FaceReader runs of the SAME participant frame by frame, e.g. the run on the
# 1:1 .mkv (which showed the "frame rate / bit rate / resolution is too low" warning) against
# the run on the same frames copied into an FFV1 .avi (no warning).
#
# Question it answers: did the warning change FaceReader's output, or was it only a message?
#
# HOW TO RUN
#   Rscript 006_compare_facereader_runs.R r2433 <folder A> <folder B>
#   defaults: folder A = 3_Data/facereader, folder B = 3_Data/facereader/test_ffv1_avi
#   RStudio: set PID / DIR_A / DIR_B below and click Source.
#   Needs readxl for .xlsx exports (install.packages("readxl")); .txt exports need nothing.
#
# WHAT IT READS (in each folder; found by the "Filename" row inside the file, not the file name)
#   the detailed log      (header row "Video Time", one row per frame)
#   the heart beat log    (header row "Time", "Interbeat Interval (s)")
#
# WHAT IT REPORTS
#   1. Header: which video each run read, frame rate, calibration, number of frames.
#   2. Vital signs per frame (Heart Rate, HRV RMSSD, HRV SDNN, heart rate confidence):
#      - whether each frame has a number / Unknown / FIT_FAILED / FIND_FAILED in each run
#      - on frames where both have a number: % identical, mean and max difference, correlation
#   3. Heart rate warnings: how often each message appears in each run.
#   4. Face analysis (emotions, valence, arousal, action units): % of frames identical, max difference.
#      These don't depend on the bit-rate warning, so they should match exactly - if they don't,
#      FaceReader decoded the two videos differently.
#   5. Heart beat log: number of beats, beats at the same time (within half a frame), interval differences.
#   6. Verdict, plus a CSV of the per-column numbers and a PDF of HR / RMSSD / SDNN over time.
#   7. WHICH RUN IS CLOSER TO THE ECG: both runs scored per block against the Kubios report,
#      with the same readers/maths as 005_compare_hrv.R (needs 005 in the same folder, the Kubios
#      report in 3_Data/kubios, 3_Data/ecg_video_offsets.csv and <pid>_frame_timestamps.csv):
#        - FaceReader's own HR and HRV (value at block end; block median) vs Kubios
#        - RMSSD / SDNN / HR computed from each run's heart beat log (as is, cleaned) vs Kubios
#        - beat by beat: % of R-peaks found within +-150 ms, % false beats, timing wobble
#      With only a few blocks per participant, treat "closer" as a hint, not a test; the
#      beat-level numbers (hundreds of beats) are the most sensitive comparison.
#   Output files go to folder B: <pid>_run_comparison.csv, <pid>_run_comparison_vs_kubios.csv,
#   <pid>_run_comparison.pdf
# =============================================================================

PID   <- "r2433"
DIR_A <- NULL   # NULL = 3_Data/facereader
DIR_B <- NULL   # NULL = 3_Data/facereader/test_ffv1_avi

# ---- paths -----------------------------------------------------------------------
script_dir <- function() {
  a <- commandArgs(FALSE)
  f <- sub("^--file=", "", a[grep("^--file=", a)])
  if (length(f)) return(dirname(normalizePath(f)))
  for (i in rev(seq_len(sys.nframe()))) { of <- sys.frame(i)$ofile; if (!is.null(of)) return(dirname(normalizePath(of))) }
  getwd()
}
HERE <- script_dir()
cfg <- Filter(file.exists, file.path(c(HERE, dirname(HERE), dirname(dirname(HERE))), "config.R"))  # repo root is 2 up
if (length(cfg)) source(cfg[1])
if (!exists("SERVER_ROOT")) SERVER_ROOT <- "C:/Users/carme/Box/Project_Biosignals_study_2/3_Data"
FR_DIR <- get0("FACEREADER_RESULTS_DIR", ifnotfound = file.path(SERVER_ROOT, "facereader"))

args <- commandArgs(TRUE)
if (length(args) >= 1) PID <- args[1]
if (length(args) >= 2) DIR_A <- args[2]
if (length(args) >= 3) DIR_B <- args[3]
if (is.null(DIR_A)) DIR_A <- FR_DIR
if (is.null(DIR_B)) DIR_B <- file.path(FR_DIR, "test_ffv1_avi")

num <- function(x) suppressWarnings(as.numeric(x))
`%||%` <- function(a, b) if (is.null(a) || length(a) == 0 || is.na(a)) b else a
say <- function(...) cat(sprintf(...), "\n", sep = "")

# ---- reading FaceReader exports ------------------------------------------------------
read_grid <- function(path, n_max = Inf) {
  if (grepl("\\.xlsx?$", path, ignore.case = TRUE)) {
    if (!requireNamespace("readxl", quietly = TRUE)) stop("install.packages(\"readxl\") to read ", basename(path))
    g <- as.data.frame(readxl::read_excel(path, sheet = 1, col_names = FALSE, col_types = "text",
                                          .name_repair = "minimal", n_max = n_max, progress = FALSE),
                       stringsAsFactors = FALSE)
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

meta_of <- function(g, hdr) {
  key <- g[[1]][seq_len(hdr - 1)]; val <- g[[2]][seq_len(hdr - 1)]
  get <- function(k) val[grepl(k, key, ignore.case = TRUE)][1]
  list(video = gsub("\\\\", "/", get("^file ?name")), fps = num(get("^frame rate")),
       calibration = get("^calibration"), face_model = get("^face model"))
}

# find the detailed log / heart beat log for PID in a folder (top level), by the Filename row
find_export <- function(dir, kind) {
  files <- list.files(dir, pattern = "\\.(txt|xlsx)$", full.names = TRUE, ignore.case = TRUE)
  files <- files[!grepl("^~\\$", basename(files))]
  hits <- character(0)
  for (f in files) {
    g <- tryCatch(read_grid(f, n_max = 40), error = function(e) NULL)
    if (is.null(g) || ncol(g) < 2) next
    title <- tolower(g[[1]][1])
    if (!grepl(kind, title)) next
    fn <- g[[2]][grepl("^file ?name", g[[1]], ignore.case = TRUE)][1]
    if (!is.na(fn) && startsWith(tolower(basename(gsub("\\\\", "/", fn))), tolower(PID))) hits <- c(hits, f)
  }
  if (!length(hits)) stop("no FaceReader ", kind, " for ", PID, " in ", dir)
  if (length(hits) > 1) stop("several FaceReader ", kind, "s for ", PID, " in ", dir, ":\n  ", paste(hits, collapse = "\n  "))
  hits
}

read_detailed <- function(path) {
  g <- read_grid(path)
  hdr <- which(g[[1]] == "Video Time")[1]
  H <- as.character(unlist(g[hdr, ])); H[is.na(H) | H == ""] <- paste0("col", which(is.na(H) | H == ""))
  D <- g[-seq_len(hdr), , drop = FALSE]; names(D) <- H
  D <- D[!is.na(D[["Video Time"]]) & D[["Video Time"]] != "", , drop = FALSE]
  list(meta = meta_of(g, hdr), data = D, file = path)
}

read_beats <- function(path) {
  g <- read_grid(path)
  hdr <- which(g[[1]] == "Time")[1]
  tt <- g[[1]][-seq_len(hdr)]; ibi <- num(g[[2]][-seq_len(hdr)])
  to_s <- function(x) vapply(x, function(s) { p <- num(strsplit(s, ":", fixed = TRUE)[[1]]); if (length(p) == 3 && !anyNA(p)) sum(p * c(3600, 60, 1)) else NA_real_ }, 0)
  t <- to_s(tt); ok <- !is.na(t)
  list(meta = meta_of(g, hdr), t = unname(t[ok]), ibi = ibi[ok], file = path)
}

status_of <- function(x) {
  s <- ifelse(is.na(num(x)), x, "number"); s[is.na(s) | s == ""] <- "(blank)"; s
}

# ---- compare ---------------------------------------------------------------------------
say("FaceReader run comparison for %s\n  A: %s\n  B: %s", PID, DIR_A, DIR_B)
A <- read_detailed(find_export(DIR_A, "detailed log"))
B <- read_detailed(find_export(DIR_B, "detailed log"))
say("\n1. HEADERS")
for (nm in c("A", "B")) {
  r <- get(nm)
  say("  %s: %s | video %s | frame rate %s | calibration %s | %d frames", nm, basename(r$file),
      basename(r$meta$video), format(r$meta$fps, digits = 10), r$meta$calibration, nrow(r$data))
}
n <- min(nrow(A$data), nrow(B$data))
if (nrow(A$data) != nrow(B$data))
  say("  WARNING: different numbers of frames (%d vs %d) - comparing the first %d by frame number.", nrow(A$data), nrow(B$data), n)
if (!identical(A$meta$calibration, B$meta$calibration))
  say("  WARNING: different expression calibration settings - face columns will differ for that reason.")
if (!isTRUE(abs(A$meta$fps - B$meta$fps) < 1e-4))
  say("  note: frame rates differ, so Video Time differs; frames are compared by frame number.")
a <- A$data[seq_len(n), , drop = FALSE]; b <- B$data[seq_len(n), , drop = FALSE]
frame_t <- seq_len(n) - 1   # frame index; seconds below use A's frame rate
sec <- frame_t / A$meta$fps

compare_col <- function(col) {
  x <- a[[col]]; y <- b[[col]]
  sx <- status_of(x); sy <- status_of(y)
  both <- sx == "number" & sy == "number"
  d <- num(y[both]) - num(x[both])
  data.frame(column = col,
             frames_same_status_pct = 100 * mean(sx == sy),
             numeric_A_pct = 100 * mean(sx == "number"), numeric_B_pct = 100 * mean(sy == "number"),
             both_numeric = sum(both),
             identical_pct = if (any(both)) 100 * mean(abs(d) < 1e-9) else NA,
             mean_diff_B_minus_A = if (any(both)) mean(d) else NA,
             mean_abs_diff = if (any(both)) mean(abs(d)) else NA,
             max_abs_diff = if (any(both)) max(abs(d)) else NA,
             r = if (sum(both) > 2 && sd(num(x[both])) > 0 && sd(num(y[both])) > 0) cor(num(x[both]), num(y[both])) else NA,
             stringsAsFactors = FALSE)
}

vital <- intersect(c("Heart Rate", "Heart Rate Variability (RMSSD)", "Heart Rate Variability (SDNN)",
                     "Heart rate confidence", "Breathing Rate"), intersect(names(a), names(b)))
face <- setdiff(intersect(names(a), names(b)), c("Video Time", vital, "Heart Rate Warnings", "Breathing Rate Warnings",
                                                   "Breathing rate confidence"))
face <- face[vapply(face, function(cn) mean(!is.na(num(a[[cn]]))) > 0.05, TRUE)]   # numeric columns only

res_v <- do.call(rbind, lapply(vital, compare_col))
res_f <- do.call(rbind, lapply(face, compare_col))

say("\n2. VITAL SIGNS, frame by frame")
for (i in seq_len(nrow(res_v))) {
  r <- res_v[i, ]
  say("  %-32s numeric in A %5.1f%% / B %5.1f%% | same status %5.1f%% | on %d shared frames: identical %5.1f%%, mean diff %+.3f, max |diff| %.3f, r %s",
      r$column, r$numeric_A_pct, r$numeric_B_pct, r$frames_same_status_pct, r$both_numeric,
      ifelse(is.na(r$identical_pct), NA, r$identical_pct), ifelse(is.na(r$mean_diff_B_minus_A), NA, r$mean_diff_B_minus_A),
      ifelse(is.na(r$max_abs_diff), NA, r$max_abs_diff), ifelse(is.na(r$r), "NA", sprintf("%.4f", r$r)))
  if (r$frames_same_status_pct < 100) {
    tb <- table(A = status_of(a[[r$column]]), B = status_of(b[[r$column]]))
    print(tb[rowSums(tb) > 0, colSums(tb) > 0, drop = FALSE])
  }
}

say("\n3. HEART RATE WARNINGS (frames per message)")
if ("Heart Rate Warnings" %in% names(a)) {
  wa <- table(a[["Heart Rate Warnings"]]); wb <- table(b[["Heart Rate Warnings"]])
  msgs <- union(names(wa), names(wb))
  for (m in msgs) say("  %-55s A %6d | B %6d", substr(m, 1, 55), as.integer(wa[m] %||% 0), as.integer(wb[m] %||% 0))
}

say("\n4. FACE ANALYSIS (%d numeric columns)", nrow(res_f))
if (!is.null(res_f) && nrow(res_f)) {
  say("  columns identical on every shared frame: %d of %d; largest difference anywhere: %.4f (%s)",
      sum(res_f$identical_pct == 100, na.rm = TRUE), nrow(res_f), max(res_f$max_abs_diff, na.rm = TRUE),
      res_f$column[which.max(res_f$max_abs_diff)])
  say("  frames where face found/failed status differs: up to %.2f%% of frames", 100 - min(res_f$frames_same_status_pct))
}

say("\n5. HEART BEAT LOG")
BA <- tryCatch(read_beats(find_export(DIR_A, "heart beat log")), error = function(e) { say("  A: %s", conditionMessage(e)); NULL })
BB <- tryCatch(read_beats(find_export(DIR_B, "heart beat log")), error = function(e) { say("  B: %s", conditionMessage(e)); NULL })
beat_summary <- NULL
if (!is.null(BA) && !is.null(BB)) {
  fa <- BA$t * BA$meta$fps; fb <- BB$t * BB$meta$fps          # beat times as frame numbers
  k <- findInterval(fb, fa); k <- pmax(1, pmin(k, length(fa)))
  k2 <- ifelse(k < length(fa) & abs(fa[pmin(k + 1, length(fa))] - fb) < abs(fa[k] - fb), k + 1, k)
  dfr <- fb - fa[k2]
  same <- abs(dfr) < 0.5
  say("  beats: A %d | B %d | B beats on the same frame as an A beat: %.1f%% | within 1 frame: %.1f%%",
      length(fa), length(fb), 100 * mean(same), 100 * mean(abs(dfr) <= 1.01))
  j <- which(same)
  ia <- BA$ibi[k2[j]]; ib <- BB$ibi[j]
  say("  interbeat interval on matched beats: identical %.1f%%, max |diff| %.1f ms",
      100 * mean(abs(ia - ib) < 1e-6, na.rm = TRUE), 1000 * max(abs(ia - ib), na.rm = TRUE))
  beat_summary <- data.frame(column = "heart beat log", frames_same_status_pct = NA, numeric_A_pct = NA, numeric_B_pct = NA,
                             both_numeric = length(j), identical_pct = 100 * mean(same), mean_diff_B_minus_A = mean(dfr),
                             mean_abs_diff = mean(abs(dfr)), max_abs_diff = max(abs(dfr)), r = NA)
}

# ---- verdict ---------------------------------------------------------------------------
say("\n6. VERDICT")
vit_same <- all(res_v$frames_same_status_pct == 100) && all(res_v$identical_pct %in% 100 | is.na(res_v$identical_pct))
face_same <- is.null(res_f) || (all(res_f$frames_same_status_pct == 100) && all(res_f$identical_pct == 100, na.rm = TRUE))
hrv <- res_v[grepl("Variability", res_v$column), ]
if (vit_same && face_same) {
  say("  IDENTICAL: the two runs give the same values on every frame. The warning was only a message -")
  say("  results from the .mkv run can be kept; either format can be used.")
} else if (face_same && !vit_same) {
  say("  FACE ANALYSIS IDENTICAL, VITAL SIGNS DIFFER: FaceReader decoded the same frames, but the heart")
  say("  rate / HRV processing differs between the runs - i.e. the warning (or the settings) changed it.")
  say("  Largest HRV difference: %s ms (mean |diff| %s ms). Re-run everyone, r2433 included, on the .avi.",
      format(max(hrv$max_abs_diff, na.rm = TRUE), digits = 3), format(mean(hrv$mean_abs_diff, na.rm = TRUE), digits = 3))
} else {
  say("  BOTH DIFFER: face analysis differs too, so FaceReader did not process the two videos identically")
  say("  (different decoding, settings or calibration). Check section 1 before concluding anything about the warning.")
}

# ---- 7. which run is closer to the ECG ------------------------------------------------
kub <- NULL
say("\n7. WHICH RUN IS CLOSER TO THE ECG (Kubios)")
f005 <- file.path(HERE, "005_compare_hrv.R")
if (!file.exists(f005)) {
  say("  skipped: needs 005_compare_hrv.R in %s", HERE)
} else {
  E5 <- new.env()                                 # 005's readers + maths, kept apart from this script's objects
  assign("HRV_NO_MAIN", TRUE, envir = E5)
  sys.source(f005, envir = E5, keep.source = FALSE)
  for (v in c("PID", "A", "B", "BA", "BB")) assign(v, get(v), envir = E5)
  fmt <- E5$fmt
  kub <- evalq(tryCatch({
    kp <- find_kubios(PID)
    if (is.null(kp)) stop("no Kubios report for ", PID)
    k <- read_kubios(kp); offset <- read_offset(PID); clock <- read_frame_clock(PID)
    blocks <- k$blocks[k$blocks$block %in% BLOCKS, ]
    say("  Kubios: %s | ECG->video offset %.3f s | frame timestamps: %s", basename(kp), offset,
        if (is.null(clock)) "NOT FOUND" else basename(attr(clock, "file")))
    rows <- list()
    for (run in c("A", "B")) {
      R <- if (run == "A") A else B; BL <- if (run == "A") BA else BB
      rt <- fr_retime(fr_time_to_s(R$data[["Video Time"]]), R$meta$video, clock, PID, R$meta$fps)
      if (is.null(rt)) stop("can't put run ", run, " on the ECG clock")
      own <- data.frame(t = rt$tv + offset, hr = num(R$data[["Heart Rate"]]),
                        rmssd_ms = num(R$data[["Heart Rate Variability (RMSSD)"]]),
                        sdnn_ms = num(R$data[["Heart Rate Variability (SDNN)"]]))
      src <- NULL; lag <- NA; q <- NA
      if (!is.null(BL)) {
        rb <- fr_retime(BL$t, BL$meta$video, clock, PID, BL$meta$fps)
        src <- data.frame(t = rb$tv + offset, rr = BL$ibi, t_nominal = BL$t, segment = NA, near_gap = FALSE)
        src <- src[order(src$t), ]; attr(src, "nominal_fps") <- rb$fps
        lag <- estimate_lag(src$t, k$rr$t); q <- quant_step(src, clock)
      }
      for (i in seq_len(nrow(blocks))) {
        b <- blocks[i, ]
        o <- facereader_own_block(own, b)
        e <- hrv(data.frame(t = k$rr$t[k$rr$block == b$block], rr = k$rr$rr[k$rr$block == b$block]))
        d <- if (!is.null(src)) diagnose_block("facereader", src, k$rr, b, lag, q) else NULL
        g <- function(v, m) if (is.null(d)) NA else d$metrics[[v]][[m]]
        gd <- function(m) if (is.null(d) || is.null(d$diag[[m]])) NA else d$diag[[m]]
        rows[[length(rows) + 1]] <- data.frame(pid = PID, block = b$block, run = run,
          ecg_hr = e[["mean_hr"]], ecg_rmssd = e[["rmssd_ms"]], ecg_sdnn = e[["sdnn_ms"]],
          own_hr = o[["mean_hr"]], own_rmssd_end = o[["rmssd_ms"]], own_rmssd_median = o[["rmssd_median_ms"]],
          own_sdnn_end = o[["sdnn_ms"]], own_sdnn_median = o[["sdnn_median_ms"]],
          log_hr = g("as_is", "mean_hr"), log_rmssd_as_is = g("as_is", "rmssd_ms"), log_rmssd_cleaned = g("cleaned", "rmssd_ms"),
          log_sdnn_as_is = g("as_is", "sdnn_ms"), log_sdnn_cleaned = g("cleaned", "sdnn_ms"),
          rpeaks_found_pct = gd("recall_pct"), false_beats_pct = 100 - gd("precision_pct"),
          jitter_ms = gd("jitter_ms"), pulse_delay_ms = 1000 * lag)
      }
    }
    do.call(rbind, rows)
  }, error = function(e) { say("  skipped: %s", conditionMessage(e)); NULL }), E5)

  if (!is.null(kub)) {
    kub <- kub[!is.na(kub$ecg_rmssd), ]
    say("  %d block(s) with ECG HRV. Mean absolute error vs Kubios (lower = closer to the ECG):", length(unique(kub$block)))
    mets <- c(own_hr = "FaceReader's own HR (bpm)", own_rmssd_end = "own RMSSD, block end (ms)",
              own_rmssd_median = "own RMSSD, block median (ms)", own_sdnn_end = "own SDNN, block end (ms)",
              log_hr = "beat log HR (bpm)", log_rmssd_as_is = "beat log RMSSD, as is (ms)",
              log_rmssd_cleaned = "beat log RMSSD, cleaned (ms)", log_sdnn_cleaned = "beat log SDNN, cleaned (ms)")
    ref <- c(own_hr = "ecg_hr", own_rmssd_end = "ecg_rmssd", own_rmssd_median = "ecg_rmssd", own_sdnn_end = "ecg_sdnn",
             log_hr = "ecg_hr", log_rmssd_as_is = "ecg_rmssd", log_rmssd_cleaned = "ecg_rmssd", log_sdnn_cleaned = "ecg_sdnn")
    say("  %-32s %10s %10s   closer", "", "A", "B")
    wins <- c(A = 0, B = 0)
    for (m in names(mets)) {
      ea <- with(kub[kub$run == "A", ], mean(abs(get(m) - get(ref[[m]])), na.rm = TRUE))
      eb <- with(kub[kub$run == "B", ], mean(abs(get(m) - get(ref[[m]])), na.rm = TRUE))
      cl <- if (is.nan(ea) || is.nan(eb)) "-" else if (abs(ea - eb) < 0.05 * max(ea, eb, 1e-9)) "same" else if (ea < eb) "A" else "B"
      if (cl %in% c("A", "B")) wins[cl] <- wins[cl] + 1
      say("  %-32s %10s %10s   %s", mets[[m]], fmt(ea), fmt(eb), cl)
    }
    say("  beat by beat (all blocks):")
    for (m in c("rpeaks_found_pct", "false_beats_pct", "jitter_ms", "pulse_delay_ms"))
      say("  %-32s %10s %10s", c(rpeaks_found_pct = "R-peaks found within 150 ms (%)", false_beats_pct = "false beats (%)",
                                  jitter_ms = "timing wobble, MAD (ms)", pulse_delay_ms = "pulse delay (ms)")[[m]],
          fmt(mean(kub[[m]][kub$run == "A"], na.rm = TRUE)), fmt(mean(kub[[m]][kub$run == "B"], na.rm = TRUE)))
    say("  per block (RMSSD, ms): ECG | A own-end, A log-cleaned | B own-end, B log-cleaned")
    for (bl in unique(kub$block)) {
      ra <- kub[kub$block == bl & kub$run == "A", ]; rb <- kub[kub$block == bl & kub$run == "B", ]
      say("    %-20s %6s | %6s %6s | %6s %6s", bl, fmt(ra$ecg_rmssd), fmt(ra$own_rmssd_end), fmt(ra$log_rmssd_cleaned),
          fmt(rb$own_rmssd_end), fmt(rb$log_rmssd_cleaned))
    }
    say("  Overall: closer on %d metric(s) for A, %d for B. With %d blocks this is indicative only; the beat-by-beat",
        wins[["A"]], wins[["B"]], length(unique(kub$block)))
    say("  rows (hundreds of beats) are the most reliable sign of which video FaceReader handled better.")
    write.csv(kub, file.path(DIR_B, paste0(PID, "_run_comparison_vs_kubios.csv")), row.names = FALSE, na = "")
  }
}

out <- rbind(res_v, beat_summary, res_f)
dir.create(DIR_B, showWarnings = FALSE, recursive = TRUE)
csv <- file.path(DIR_B, paste0(PID, "_run_comparison.csv"))
write.csv(out, csv, row.names = FALSE, na = "")

pdf_f <- file.path(DIR_B, paste0(PID, "_run_comparison.pdf"))
pdf(pdf_f, width = 11, height = 8.5)
par(mfrow = c(length(vital[vital != "Breathing Rate"]), 1), mar = c(3, 5, 2, 1))
for (cn in setdiff(vital, "Breathing Rate")) {
  ya <- num(a[[cn]]); yb <- num(b[[cn]])
  if (all(is.na(ya)) && all(is.na(yb))) { plot.new(); next }
  plot(sec / 60, ya, type = "l", col = "grey40", lwd = 2, xlab = "", ylab = cn, main = if (cn == vital[1]) paste(PID, "- A (grey) vs B (orange)") else "",
       ylim = range(c(ya, yb), na.rm = TRUE))
  lines(sec / 60, yb, col = "#d95f02", lwd = 1)
}
mtext("minutes into video", side = 1, line = 2, cex = 0.8)
dev.off()
say("\n  saved %s and %s", csv, pdf_f)
