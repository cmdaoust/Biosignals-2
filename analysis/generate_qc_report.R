# generate_qc_report.R
# Reads cleaned data outputs and writes biosignals2_qc.html to analysis/.
# Main-study participants only. For the pilot participants run generate_qc_report_pilot.R,
# which sources this script with QC_MODE = "pilot" and writes biosignals2_qc_pilot.html.
#
# Covers: PsychoPy self-report | Ledalab (EDA) | Kubios (HRV) | Webcam biometrics | Video | FaceReader |
#         Questionnaires
# Each section degrades gracefully when files are not yet present.
#
# Run from RStudio (open script → Source), or from the R console:
#   source("C:/Users/carme/OneDrive/Documents/GitHub/Biosignals2/analysis/generate_qc_report.R")

suppressPackageStartupMessages({
  library(dplyr)
  library(readr)
  library(purrr)
  library(stringr)
  library(tidyr)
})

# ── 1. Locate project root & source config ─────────────────────────────────────
find_project_root <- function() {
  # TRUE when x is a single usable string. The lookups below can return
  # character(0), and `is.na(character(0)) || ...` is an error in R >= 4.3.
  has_path <- function(x) length(x) == 1 && !is.na(x) && nzchar(x)

  start <- tryCatch({
    ctx <- rstudioapi::getSourceEditorContext()
    if (!is.null(ctx) && has_path(ctx$path))
      dirname(normalizePath(ctx$path, winslash = "/", mustWork = FALSE))
    else NA_character_
  }, error = function(e) NA_character_)

  # source() — the calling frame holds the file being sourced
  if (!has_path(start)) {
    ofile <- tryCatch(sys.frame(1)$ofile, error = function(e) NULL)
    if (has_path(ofile))
      start <- dirname(normalizePath(ofile, winslash = "/", mustWork = FALSE))
  }

  if (!has_path(start)) {
    args     <- commandArgs(trailingOnly = FALSE)
    file_arg <- grep("^--file=", args, value = TRUE)
    if (length(file_arg))
      start <- dirname(normalizePath(sub("^--file=", "", file_arg[1]),
                                     winslash = "/", mustWork = FALSE))
  }

  if (!has_path(start)) start <- getwd()

  current <- normalizePath(start, winslash = "/", mustWork = FALSE)
  for (i in seq_len(15)) {
    if (file.exists(file.path(current, "config.R"))) return(current)
    parent <- dirname(current)
    if (parent == current)
      stop("Could not find config.R in this directory or any parent directory.")
    current <- parent
  }
  stop("Could not find config.R after 15 levels up.")
}

project_dir <- find_project_root()
message("Project root: ", project_dir)
source(file.path(project_dir, "config.R"))

DATA_PATH   <- file.path(COMBINED_PSYCHO_DIR, "biosignals2_selfreport_ratings.csv")
BIOMETRICS_COMBINED_PATH <- file.path(COMBINED_PSYCHO_DIR, "biosignals2_webcambiometrics.csv")
QUESTIONNAIRE_PATH <- file.path(COMBINED_PSYCHO_DIR, "biosignals2_questionnaires_scored.csv")
# config.R lives at the repo root; this also copes with an old copy in analysis/
analysis_dir <- if (basename(project_dir) == "analysis") project_dir else file.path(project_dir, "analysis")
OUTPUT_PATH  <- file.path(analysis_dir, if (exists("QC_MODE", inherits = FALSE) && QC_MODE == "pilot")
                                          "biosignals2_qc_pilot.html" else "biosignals2_qc.html")
message("Output path:  ", OUTPUT_PATH)
dir.create(dirname(OUTPUT_PATH), showWarnings = FALSE, recursive = TRUE)

# ── 1.5 Pilot / test / rejected participants ──────────────────────────────────
# All come from analysis/participant_status.csv (read by participant_status.R) — edit
# that file, not this script. Test sessions and rejected participants are left out of
# both reports; pilots go only in the pilot report (generate_qc_report_pilot.R); anyone
# not listed is a main-study participant. Files on disk are never touched.
PARTICIPANT_STATUS_PATH <- file.path(analysis_dir, "participant_status.csv")
source(file.path(analysis_dir, "participant_status.R"), local = TRUE)
EXCLUDED_PIDS <- excluded_ids()
PILOT_PIDS    <- pilot_ids()

# QC_MODE is set to "pilot" by generate_qc_report_pilot.R; otherwise this is the main report.
QC_MODE <- if (exists("QC_MODE", inherits = FALSE)) QC_MODE else "main"
if (!QC_MODE %in% c("main", "pilot")) stop('QC_MODE must be "main" or "pilot", not "', QC_MODE, '"')
message("Report:       ", QC_MODE, " participants")

# ── 2. Shared helpers ──────────────────────────────────────────────────────────
qc_norm_id   <- function(x) toupper(trimws(as.character(x)))
# Dropped = test sessions always, plus pilots (main report) or non-pilots (pilot report).
is_excluded  <- function(x) {
  id       <- qc_norm_id(x)
  is_pilot <- id %in% qc_norm_id(PILOT_PIDS)
  id %in% qc_norm_id(EXCLUDED_PIDS) | (if (QC_MODE == "pilot") !is_pilot else is_pilot)
}
keep_ids     <- function(x) x[!is_excluded(x)]
# Drop excluded participants from a data frame by its ID column.
drop_excluded <- function(df, col = "participant_id") {
  if (!col %in% names(df)) return(df)
  df[!is_excluded(df[[col]]), , drop = FALSE]
}
# Drop file paths whose leading "<pid>_" names an excluded participant.
keep_files <- function(paths) paths[!is_excluded(str_extract(basename(paths), "^[^_]+"))]

INDUCTION <- c("positive_induction", "negative_induction")
RECOVERY  <- c("post_positive_induction_recovery", "post_negative_induction_recovery")

fmt_delta <- function(x) {
  x <- round(x, 1)
  if_else(x >= 0, paste0("+", x), as.character(x))
}

make_rating_row <- function(label, vals) {
  vals  <- vals[!is.na(vals)]
  n_out <- sum(vals < 1 | vals > 7)
  status <- if (n_out == 0) "<td class='status-ok'>✓ none</td>" else
    paste0("<td class='status-warn'>⚠ ", n_out, "</td>")
  paste0("<tr><td class='mono'>", label, "</td>",
         "<td>", length(vals), "</td>",
         "<td>", min(vals), "</td>",
         "<td>", max(vals), "</td>",
         "<td>1–7</td>", status, "</tr>")
}

placeholder_section <- function(title, msg) {
  paste0('<div class="placeholder-box">',
         '<div class="placeholder-title">', title, '</div>',
         '<div class="placeholder-msg">', msg, '</div>',
         '</div>')
}

# Cache for slow inputs that rarely change (the combined biometrics file, video frame timestamps).
# A result is saved in analysis/.qc_cache/ and reused while every source file keeps the same size
# and modification time. Delete the folder to force a full re-read; bump QC_CACHE_VERSION when the
# cached computation changes.
QC_CACHE_VERSION <- 1
QC_CACHE_DIR     <- file.path(analysis_dir, ".qc_cache")

cached <- function(name, files, compute) {
  info      <- file.info(files)
  signature <- paste(QC_CACHE_VERSION, normalizePath(files, winslash = "/", mustWork = FALSE),
                     info$size, as.numeric(info$mtime), collapse = "|")
  path <- file.path(QC_CACHE_DIR, paste0(name, ".rds"))
  if (file.exists(path)) {
    hit <- tryCatch(readRDS(path), error = function(e) NULL)
    if (!is.null(hit) && identical(hit$signature, signature)) return(hit$value)
  }
  value <- compute()
  dir.create(QC_CACHE_DIR, showWarnings = FALSE, recursive = TRUE)
  saveRDS(list(signature = signature, value = value), path)
  value
}

# ── 3. PsychoPy / self-report data ────────────────────────────────────────────
# Read once; the questionnaire and completeness sections reuse it
selfreport <- tryCatch(
  read_csv(DATA_PATH, show_col_types = FALSE) |> drop_excluded(),
  error = function(e) e)

psychopy_html <- tryCatch({

  if (inherits(selfreport, "error")) stop(conditionMessage(selfreport))
  df <- selfreport |>
    mutate(condition = as.character(condition))

  stim_rows <- df |> filter(condition %in% INDUCTION)
  n_sessions <- n_distinct(df$participant_id)
  n_vid_rows  <- nrow(stim_rows)

  n_trig_ok <- sum(!is.na(stim_rows$trigger_name) & trimws(stim_rows$trigger_name) != "")
  trig_rate <- paste0(n_trig_ok, "/", n_vid_rows)

  # Manipulation check
  postbl <- df |> filter(condition == "baseline") |>
    select(participant_id, postbl_valence = block_end_valence,
           postbl_arousal = block_end_arousal)

  postind <- df |> filter(condition %in% INDUCTION) |>
    group_by(participant_id, condition) |>
    summarise(postind_valence = mean(block_end_valence, na.rm = TRUE),
              postind_arousal = mean(block_end_arousal, na.rm = TRUE),
              .groups = "drop") |>
    mutate(emotion_condition = if_else(condition == "positive_induction",
                                       "positive", "negative"))

  manip <- postind |>
    left_join(postbl, by = "participant_id") |>
    mutate(
      delta_valence = postind_valence - postbl_valence,
      delta_arousal = postind_arousal - postbl_arousal,
      manip_ok = case_when(
        emotion_condition == "positive" ~ delta_valence > 0,
        emotion_condition == "negative" ~ delta_valence < 0,
        TRUE ~ NA
      )
    )

  n_manip_ok    <- sum(manip$manip_ok, na.rm = TRUE)
  n_manip_total <- sum(!is.na(manip$manip_ok))
  manip_rate    <- paste0(n_manip_ok, "/", n_manip_total)

  # Participant table
  part_rows_html <- stim_rows |>
    group_by(participant_id) |>
    mutate(cond_order = first(conditionOrder)) |>
    group_by(participant_id, cond_order) |>
    summarise(
      pos_vids = { v <- sort(unique(video_id[condition == "positive_induction"]))
        paste0(length(v), " (", paste(v, collapse = ", "), ")") },
      neg_vids = { v <- sort(unique(video_id[condition == "negative_induction"]))
        paste0(length(v), " (", paste(v, collapse = ", "), ")") },
      total = n(), .groups = "drop"
    ) |>
    arrange(participant_id) |>
    rowwise() |>
    mutate(html = paste0(
      "<tr><td class='mono'>", participant_id, "</td>",
      "<td>", cond_order, "</td>",
      "<td>", pos_vids, "</td><td>", neg_vids, "</td>",
      "<td>", total, "</td></tr>"
    )) |> pull(html) |> paste(collapse = "\n")

  # Trigger table
  trig_rows_html <- stim_rows |>
    select(participant_id, video_id, condition, trigger_name) |>
    arrange(participant_id, condition, video_id) |>
    mutate(
      cond_html = if_else(condition == "positive_induction",
        "<span class='cond-pos'>positive</span>",
        "<span class='cond-neg'>negative</span>"),
      status_html = if_else(
        !is.na(trigger_name) & trimws(trigger_name) != "",
        "<td class='status-ok'>✓ captured</td>",
        "<td class='status-warn'>✗ missing</td>"),
      html = paste0(
        "<tr><td class='mono'>", participant_id, "</td>",
        "<td class='mono'>", video_id, "</td>",
        "<td>", cond_html, "</td>",
        "<td class='mono'>", trigger_name, "</td>",
        status_html, "</tr>")
    ) |> pull(html) |> paste(collapse = "\n")

  # Rating ranges
  phase_rating <- list(
    list(label = "stim_valence",            df_filt = stim_rows,                              col = "stim_valence"),
    list(label = "stim_arousal",            df_filt = stim_rows,                              col = "stim_arousal"),
    list(label = "stim_approach",           df_filt = stim_rows,                              col = "stim_approach"),
    list(label = "postind_valence (block_end)", df_filt = df |> filter(condition %in% INDUCTION), col = "block_end_valence"),
    list(label = "postind_arousal (block_end)", df_filt = df |> filter(condition %in% INDUCTION), col = "block_end_arousal"),
    list(label = "postrec_valence (block_end)", df_filt = df |> filter(condition %in% RECOVERY),  col = "block_end_valence"),
    list(label = "postrec_arousal (block_end)", df_filt = df |> filter(condition %in% RECOVERY),  col = "block_end_arousal"),
    list(label = "prebl_valence (block_start)", df_filt = df |> filter(condition == "baseline"),   col = "block_start_valence"),
    list(label = "prebl_arousal (block_start)", df_filt = df |> filter(condition == "baseline"),   col = "block_start_arousal"),
    list(label = "postbl_valence (block_end)",  df_filt = df |> filter(condition == "baseline"),   col = "block_end_valence"),
    list(label = "postbl_arousal (block_end)",  df_filt = df |> filter(condition == "baseline"),   col = "block_end_arousal")
  )
  rating_rows_html <- sapply(phase_rating, function(s)
    make_rating_row(s$label, s$df_filt[[s$col]])) |> paste(collapse = "\n")

  # RT tiles
  rt_cols <- intersect(c("stim_valence_rt", "stim_arousal_rt", "stim_approach_rt"), names(stim_rows))
  rt_tiles_html <- sapply(rt_cols, function(col) {
    vals <- stim_rows[[col]][!is.na(stim_rows[[col]])]
    paste0("<div class='rt-tile'><span class='rt-name'>", col, "</span>",
           "<span class='rt-range'>",
           sprintf("%.2f", min(vals)), "–", sprintf("%.2f", max(vals)),
           "</span></div>")
  }) |> paste(collapse = "\n")

  n_fast <- sum(sapply(rt_cols, function(col)
    sum(stim_rows[[col]] < 0.5, na.rm = TRUE)))
  rt_note <- if (n_fast == 0) {
    "no fast responses (&lt; 0.5 s) detected"
  } else {
    paste0("<strong>", n_fast, " fast response(s) (&lt; 0.5 s) detected — flag for review.</strong>")
  }

  # Manipulation check cards
  pos_dv <- manip |> filter(emotion_condition == "positive") |> pull(delta_valence) |> mean(na.rm = TRUE)
  pos_da <- manip |> filter(emotion_condition == "positive") |> pull(delta_arousal) |> mean(na.rm = TRUE)
  neg_dv <- manip |> filter(emotion_condition == "negative") |> pull(delta_valence) |> mean(na.rm = TRUE)
  neg_da <- manip |> filter(emotion_condition == "negative") |> pull(delta_arousal) |> mean(na.rm = TRUE)

  manip_table_rows <- manip |>
    arrange(participant_id, emotion_condition) |>
    mutate(
      cond_html = if_else(emotion_condition == "positive",
        "<span class='cond-pos'>positive</span>",
        "<span class='cond-neg'>negative</span>"),
      dv_col  = if_else(emotion_condition == "positive", "var(--pos)", "var(--neg)"),
      ok_html = if_else(manip_ok,
        "<td class='status-ok'>✓ TRUE</td>",
        "<td class='status-warn'>✗ FALSE</td>"),
      html = paste0(
        "<tr><td class='mono'>", participant_id, "</td>",
        "<td>", cond_html, "</td>",
        "<td>", round(postbl_valence, 1), "</td>",
        "<td>", round(postind_valence, 1), "</td>",
        "<td style='color:", dv_col, "; font-weight:600; font-variant-numeric:tabular-nums;'>",
        fmt_delta(delta_valence), "</td>",
        ok_html, "</tr>")
    ) |> pull(html) |> paste(collapse = "\n")

  pos_check_txt <- if (all(manip$manip_ok[manip$emotion_condition == "positive"], na.rm = TRUE)) {
    "Valence increased after induction — direction correct for all sessions"
  } else {
    "⚠ Some sessions did not show expected direction — review table below"
  }
  neg_check_txt <- if (all(manip$manip_ok[manip$emotion_condition == "negative"], na.rm = TRUE)) {
    "Valence decreased after induction — direction correct for all sessions"
  } else {
    "⚠ Some sessions did not show expected direction — review table below"
  }

  # Stimulus ratings
  stim_summary <- stim_rows |>
    group_by(video_id, condition) |>
    summarise(
      valence  = round(mean(stim_valence,  na.rm = TRUE), 1),
      arousal  = round(mean(stim_arousal,  na.rm = TRUE), 1),
      approach = round(mean(stim_approach, na.rm = TRUE), 1),
      .groups = "drop"
    ) |> arrange(condition, video_id)

  stim_table_rows <- stim_summary |>
    mutate(
      cond_html = if_else(condition == "positive_induction",
        "<span class='cond-pos'>positive</span>",
        "<span class='cond-neg'>negative</span>"),
      html = paste0(
        "<tr><td class='mono'>", video_id, "</td>",
        "<td>", cond_html, "</td>",
        "<td>", valence, "</td><td>", arousal, "</td><td>", approach, "</td></tr>")
    ) |> pull(html) |> paste(collapse = "\n")

  pos_means <- stim_summary |> filter(condition == "positive_induction") |>
    summarise(v = mean(valence, na.rm = TRUE), a = mean(arousal, na.rm = TRUE),
              ap = mean(approach, na.rm = TRUE))
  neg_means <- stim_summary |> filter(condition == "negative_induction") |>
    summarise(v = mean(valence, na.rm = TRUE), a = mean(arousal, na.rm = TRUE),
              ap = mean(approach, na.rm = TRUE))

  stim_pos_js <- paste0("[", round(pos_means$v, 2), ", ", round(pos_means$a, 2), ", ",
                         round(pos_means$ap, 2), "]")
  stim_neg_js <- paste0("[", round(neg_means$v, 2), ", ", round(neg_means$a, 2), ", ",
                         round(neg_means$ap, 2), "]")

  # State trajectories
  fmt_js_arr <- function(...) paste0("[", paste(round(c(...), 2), collapse = ", "), "]")

  prebl      <- df |> filter(condition == "baseline") |>
    summarise(v = mean(block_start_valence, na.rm = TRUE), a = mean(block_start_arousal, na.rm = TRUE))
  postbl_avg <- df |> filter(condition == "baseline") |>
    summarise(v = mean(block_end_valence, na.rm = TRUE), a = mean(block_end_arousal, na.rm = TRUE))
  traj_pos <- df |> filter(condition == "positive_induction") |>
    group_by(participant_id) |>
    summarise(pv = mean(block_end_valence, na.rm = TRUE),
              pa = mean(block_end_arousal, na.rm = TRUE), .groups = "drop") |>
    summarise(v = mean(pv, na.rm = TRUE), a = mean(pa, na.rm = TRUE))
  traj_neg <- df |> filter(condition == "negative_induction") |>
    group_by(participant_id) |>
    summarise(pv = mean(block_end_valence, na.rm = TRUE),
              pa = mean(block_end_arousal, na.rm = TRUE), .groups = "drop") |>
    summarise(v = mean(pv, na.rm = TRUE), a = mean(pa, na.rm = TRUE))
  rec_pos <- df |> filter(condition == "post_positive_induction_recovery") |>
    summarise(v = mean(block_end_valence, na.rm = TRUE), a = mean(block_end_arousal, na.rm = TRUE))
  rec_neg <- df |> filter(condition == "post_negative_induction_recovery") |>
    summarise(v = mean(block_end_valence, na.rm = TRUE), a = mean(block_end_arousal, na.rm = TRUE))

  pos_v_js <- fmt_js_arr(prebl$v, postbl_avg$v, traj_pos$v, rec_pos$v)
  neg_v_js <- fmt_js_arr(prebl$v, postbl_avg$v, traj_neg$v, rec_neg$v)
  pos_a_js <- fmt_js_arr(prebl$a, postbl_avg$a, traj_pos$a, rec_pos$a)
  neg_a_js <- fmt_js_arr(prebl$a, postbl_avg$a, traj_neg$a, rec_neg$a)

  # Counterbalancing
  cond_order_counts <- df |>
    distinct(participant_id, conditionOrder) |>
    count(conditionOrder, name = "n_sessions")

  all_orders <- data.frame(conditionOrder = c("pos_first", "neg_first"),
                           stringsAsFactors = FALSE) |>
    left_join(cond_order_counts, by = "conditionOrder") |>
    mutate(n_sessions = coalesce(n_sessions, 0L)) |>
    mutate(total = sum(n_sessions),
           pct   = if (total[1] > 0) round(100 * n_sessions / total) else rep(0L, n()),
           total = NULL)

  cb_rows_html <- all_orders |>
    mutate(
      only_one_group = sum(n_sessions > 0) == 1,
      status_html = case_when(
        n_sessions == 0  ~ "<td class='status-warn'>⚠ not yet recorded</td>",
        only_one_group   ~ "<td class='status-warn'>⚠ only group seen</td>",
        TRUE             ~ "<td class='status-ok'>✓</td>"
      ),
      html = paste0(
        "<tr><td class='mono'>", conditionOrder, "</td>",
        "<td>", n_sessions, "</td><td>", pct, "%</td>",
        status_html, "</tr>")
    ) |> pull(html) |> paste(collapse = "\n")

  # Summary tile classes
  trig_cls  <- if (n_trig_ok  == n_vid_rows)     "ok"   else "warn"
  manip_cls <- if (n_manip_ok == n_manip_total)   "ok"   else "warn"

  # ── PsychoPy HTML ──
  paste0(
  '<div class="status-row">
    <div class="tile blue"><div class="tile-value">', n_sessions, '</div>
      <div class="tile-label">Sessions<br>recorded</div></div>
    <div class="tile blue"><div class="tile-value">', n_vid_rows, '</div>
      <div class="tile-label">Video rating<br>rows</div></div>
    <div class="tile ', trig_cls, '"><div class="tile-value">', trig_rate, '</div>
      <div class="tile-label">Trigger names<br>captured</div></div>
    <div class="tile ', manip_cls, '"><div class="tile-value">', manip_rate, '</div>
      <div class="tile-label">Manipulation<br>checks passed</div></div>
  </div>

  <section>
    <div class="section-head">
      <div class="section-label">Pipeline &amp; Completeness</div>
      <h2>Data collection and trigger capture</h2>
      <p>Long-format output from 01_data_cleaning.Rmd. One row per video per participant
         for induction phases, plus one row per participant for baseline and recovery.</p>
    </div>
    <div class="table-wrap"><table>
      <thead><tr><th>Participant</th><th>Condition order</th>
        <th>Positive videos</th><th>Negative videos</th><th>Total stim rows</th></tr></thead>
      <tbody>', part_rows_html, '</tbody>
    </table></div>
    <div style="margin-top:1.5rem;">
      <div class="section-label" style="margin-bottom:.6rem;">
        Trigger name lookup — all ', n_vid_rows, ' stimulus rows</div>
      <div class="table-wrap"><table>
        <thead><tr><th>Participant</th><th>Video ID</th><th>Condition</th>
          <th>Trigger name</th><th>Status</th></tr></thead>
        <tbody>', trig_rows_html, '</tbody>
      </table></div>
      <div class="note-ok">', n_trig_ok, '/', n_vid_rows,
        ' trigger–video pairings resolved successfully.</div>
    </div>
  </section>

  <section>
    <div class="section-head">
      <div class="section-label">Rating Quality</div>
      <h2>Scale range checks</h2>
      <p>All slider responses should fall 1–7. Stimulus RTs below 0.5 s are flagged.</p>
    </div>
    <div class="table-wrap"><table>
      <thead><tr><th>Scale</th><th>N responses</th><th>Observed min</th>
        <th>Observed max</th><th>Expected range</th><th>Out of range</th></tr></thead>
      <tbody>', rating_rows_html, '</tbody>
    </table></div>
    <div style="margin-top:1.5rem;">
      <div class="section-label" style="margin-bottom:.5rem;">
        Stimulus reaction time ranges (seconds) — ', rt_note, '</div>
      <div class="rt-grid">', rt_tiles_html, '</div>
    </div>
  </section>

  <section>
    <div class="section-head">
      <div class="section-label">Manipulation Check</div>
      <h2>Did induction shift valence in the expected direction?</h2>
      <p>&#916; valence = post-induction block_end_valence &#8722; post-baseline block_end_valence.</p>
    </div>
    <div class="grid-2">
      <div class="manip-card pos-card">
        <div class="manip-cond pos">Positive condition</div>
        <div class="manip-deltas">
          <div class="manip-delta-item">
            <div class="delta-val pos-val">', fmt_delta(pos_dv), '</div>
            <div class="delta-lbl">&#916; valence</div></div>
          <div class="manip-delta-item">
            <div class="delta-val pos-val">', fmt_delta(pos_da), '</div>
            <div class="delta-lbl">&#916; arousal</div></div></div>
        <div class="check-row">
          <span class="check-icon">&#10003;</span>
          <span>', pos_check_txt, '</span></div></div>
      <div class="manip-card neg-card">
        <div class="manip-cond neg">Negative condition</div>
        <div class="manip-deltas">
          <div class="manip-delta-item">
            <div class="delta-val neg-val">', fmt_delta(neg_dv), '</div>
            <div class="delta-lbl">&#916; valence</div></div>
          <div class="manip-delta-item">
            <div class="delta-val ', if (neg_da >= 0) "pos-val" else "neg-val", '">',
            fmt_delta(neg_da), '</div>
            <div class="delta-lbl">&#916; arousal</div></div></div>
        <div class="check-row">
          <span class="check-icon">&#10003;</span>
          <span>', neg_check_txt, '</span></div></div>
    </div>
    <div style="margin-top:1.5rem;" class="table-wrap"><table>
      <thead><tr><th>Participant</th><th>Condition</th>
        <th>Post-baseline valence</th><th>Post-induction valence</th>
        <th>&#916; valence</th><th>Direction correct</th></tr></thead>
      <tbody>', manip_table_rows, '</tbody>
    </table></div>
    <div class="note-ok">', n_manip_ok, '/', n_manip_total,
      ' manipulation checks in the expected direction.</div>
  </section>

  <section>
    <div class="section-head">
      <div class="section-label">Stimulus Ratings</div>
      <h2>Valence, arousal, and approach by condition</h2>
      <p>Means per video, averaged across participants (1–7 scale).</p>
    </div>
    <div class="chart-wrap">
      <div class="chart-title">Mean stimulus ratings by condition</div>
      <canvas id="stimChart" height="220"></canvas>
    </div>
    <div style="margin-top:1.25rem;" class="table-wrap"><table>
      <thead><tr><th>Video</th><th>Condition</th>
        <th>Valence</th><th>Arousal</th><th>Approach</th></tr></thead>
      <tbody>', stim_table_rows, '</tbody>
    </table></div>
  </section>

  <section>
    <div class="section-head">
      <div class="section-label">State Trajectories</div>
      <h2>Momentary ratings across the session timeline</h2>
      <p>Pre-baseline and post-baseline shared. Lines diverge at post-induction.</p>
    </div>
    <div class="grid-2">
      <div class="chart-wrap" style="margin-top:0;">
        <div class="chart-title">State valence</div>
        <canvas id="valenceChart" height="220"></canvas></div>
      <div class="chart-wrap" style="margin-top:0;">
        <div class="chart-title">State arousal</div>
        <canvas id="arousalChart" height="220"></canvas></div>
    </div>
  </section>

  <section>
    <div class="section-head">
      <div class="section-label">Study Status</div>
      <h2>Counterbalancing and collection progress</h2>
    </div>
    <div class="table-wrap"><table>
      <thead><tr><th>Condition order</th><th>Sessions recorded</th>
        <th>% of pilot</th><th>Status</th></tr></thead>
      <tbody>', cb_rows_html, '</tbody>
    </table></div>
    <div class="note">
      <strong>Counterbalancing:</strong> Models include <code>conditionOrder</code> as a covariate.
      Both order groups required before mixed models will run.</div>
    <div class="note-ok" style="margin-top:.75rem;">
      <strong>Pipeline:</strong> Raw CSVs &#8594; 01_data_cleaning.Rmd &#8594;
      biosignals2_selfreport_ratings.csv &#8594; 02_ratings_analysis.Rmd</div>
  </section>

  <script>
  (function() {
    function css(v) { return getComputedStyle(document.documentElement).getPropertyValue(v).trim(); }
    const POS=css("--pos"), NEG=css("--neg"), BORD=css("--border"), T2=css("--text-2");
    const gridOpts = {color:BORD, lineWidth:1};
    Chart.defaults.font.family = "\'IBM Plex Sans\',sans-serif";
    Chart.defaults.font.size = 11;
    Chart.defaults.color = css("--text-3");

    new Chart(document.getElementById("stimChart").getContext("2d"), {
      type: "bar",
      data: {
        labels: ["Valence","Arousal","Approach"],
        datasets: [
          {label:"Positive", data:', stim_pos_js, ', backgroundColor:POS+"33",
           borderColor:POS, borderWidth:1.5, borderRadius:2},
          {label:"Negative", data:', stim_neg_js, ', backgroundColor:NEG+"33",
           borderColor:NEG, borderWidth:1.5, borderRadius:2}
        ]
      },
      options:{responsive:true, maintainAspectRatio:true,
        plugins:{legend:{position:"top",align:"end",
          labels:{boxWidth:12,boxHeight:12,padding:14,color:T2}},
          tooltip:{mode:"index",intersect:false}},
        scales:{x:{grid:{display:false},ticks:{color:T2},border:{color:BORD}},
          y:{min:0,max:7,ticks:{stepSize:1,color:T2},grid:gridOpts,border:{color:BORD}}}}
    });

    function makeTraj(id, posData, negData) {
      new Chart(document.getElementById(id).getContext("2d"), {
        type:"line",
        data:{
          labels:["Pre-baseline","Post-baseline","Post-induction","Post-recovery"],
          datasets:[
            {label:"Positive", data:posData, borderColor:POS, backgroundColor:POS+"22",
             borderWidth:2, pointBackgroundColor:POS, pointRadius:4, tension:0.15},
            {label:"Negative", data:negData, borderColor:NEG, backgroundColor:NEG+"22",
             borderWidth:2, pointBackgroundColor:NEG, pointRadius:4, tension:0.15}
          ]
        },
        options:{responsive:true, maintainAspectRatio:true,
          plugins:{legend:{position:"top",align:"end",
            labels:{boxWidth:10,boxHeight:10,padding:10,color:T2}},
            tooltip:{mode:"index",intersect:false}},
          scales:{x:{grid:{display:false},ticks:{color:T2,font:{size:9.5},maxRotation:30},
            border:{color:BORD}},
            y:{min:1,max:7,ticks:{stepSize:1,color:T2},grid:gridOpts,border:{color:BORD},
              title:{display:true,text:"Rating (1–7)",color:T2,font:{size:10}}}}}
      });
    }
    makeTraj("valenceChart", ', pos_v_js, ',', neg_v_js, ');
    makeTraj("arousalChart", ', pos_a_js, ',', neg_a_js, ');
  })();
  </script>')

}, error = function(e) {
  placeholder_section("PsychoPy / Self-report data",
    paste0("Could not load data: ", conditionMessage(e),
           "<br>Check that biosignals2_selfreport_ratings.csv exists in COMBINED_PSYCHO_DIR."))
})

# ── 4. Ledalab (EDA) ───────────────────────────────────────────────────────────
ledalab_html <- tryCatch({

  era_files <- keep_files(
    list.files(LEDALAB_RESULTS_DIR, pattern = "_era\\.txt$", full.names = TRUE))
  if (length(era_files) == 0)
    stop("NO_FILES: No _era.txt files found in LEDALAB_RESULTS_DIR.")

  era_raw <- map_dfr(era_files, function(f) {
    pid <- str_extract(basename(f), "^[^_]+")
    read_tsv(f, show_col_types = FALSE) |> mutate(pid = pid)
  })

  # Robustly find NID and event-nr columns
  nid_col <- intersect(c("Event.NID","Event.nid","event.nid","nid","Event_nid"), names(era_raw))[1]
  if (is.na(nid_col)) stop(paste("No NID column found. Columns:", paste(names(era_raw), collapse=", ")))
  era_raw <- rename(era_raw, Event.nid = all_of(nid_col))

  # Join condition labels from NID map if present
  nid_map_path <- file.path(BLOCK_ONSETS_DIR, "nid_map_psychopy_ledalab.txt")
  has_nid_map  <- file.exists(nid_map_path)

  if (has_nid_map) {
    nid_map <- read_tsv(nid_map_path, show_col_types = FALSE) |>
      rename(Event.nid = nid)
    era <- left_join(era_raw, nid_map, by = "Event.nid")
  } else {
    era <- mutate(era_raw, condition = paste0("nid_", Event.nid))
  }

  n_era_pids   <- n_distinct(era$pid)
  n_era_events <- nrow(era)
  n_unmatched  <- if (has_nid_map) sum(is.na(era$condition)) else 0

  LEDA_CONDITIONS <- c("baseline","neg_induction","neg_recovery","pos_induction","pos_recovery")

  # Per-participant x condition summary
  era_summary <- era |>
    filter(!is.na(condition)) |>
    group_by(pid, condition) |>
    summarise(
      n_events  = n(),
      mean_SCR  = round(mean(CDA.SCR,  na.rm = TRUE), 5),
      mean_nSCR = round(mean(CDA.nSCR, na.rm = TRUE), 2),
      .groups = "drop"
    )

  # Responsiveness: participants with few skin conductance responses (CDA.nSCR per ~3-min epoch).
  # Non-responder = no SCRs in any epoch; low responder = mean below LOW_NSCR_PER_EPOCH.
  LOW_NSCR_PER_EPOCH <- 5
  responders <- era |>
    filter(!is.na(CDA.nSCR)) |>
    mutate(epoch_label = coalesce(condition, paste0("nid_", Event.nid))) |>
    group_by(pid) |>
    summarise(
      n_epochs     = n(),
      mean_nSCR    = mean(CDA.nSCR),
      min_nSCR     = min(CDA.nSCR),
      max_nSCR     = max(CDA.nSCR),
      n_low_epochs = sum(CDA.nSCR < LOW_NSCR_PER_EPOCH),
      low_epochs   = paste0(epoch_label[CDA.nSCR < LOW_NSCR_PER_EPOCH], " (",
                            CDA.nSCR[CDA.nSCR < LOW_NSCR_PER_EPOCH], ")", collapse = ", "),
      .groups = "drop"
    ) |>
    mutate(
      responder = case_when(
        max_nSCR == 0                  ~ "non-responder",
        mean_nSCR < LOW_NSCR_PER_EPOCH ~ "low responder",
        n_low_epochs > 0               ~ "some low epochs",
        TRUE                           ~ "ok"),
      low_epochs  = if_else(n_low_epochs == 0, "—", low_epochs),
      status_html = if_else(responder == "ok", "<td class='status-ok'>✓ ok</td>",
                            paste0("<td class='status-warn'>⚠ ", responder, "</td>"))
    )
  n_low_resp <- sum(responders$responder %in% c("non-responder", "low responder"))

  responder_rows_html <- responders |>
    arrange(match(responder, c("non-responder", "low responder", "some low epochs", "ok")), pid) |>
    mutate(html = paste0(
      "<tr><td class='mono'>", pid, "</td>",
      "<td>", n_epochs, "</td>",
      "<td>", round(mean_nSCR, 1), "</td>",
      "<td>", min_nSCR, "</td>",
      "<td>", n_low_epochs, "</td>",
      "<td class='mono' style='font-size:.78rem'>", low_epochs, "</td>",
      status_html, "</tr>")
    ) |> pull(html) |> paste(collapse = "\n")

  # Coverage: which pids have all 5 conditions?
  pid_coverage <- era_summary |>
    group_by(pid) |>
    summarise(n_conds = n_distinct(condition[!is.na(condition)]), .groups = "drop") |>
    mutate(
      status_html = if_else(n_conds >= 5,
        "<td class='status-ok'>✓ complete</td>",
        paste0("<td class='status-warn'>⚠ ", n_conds, "/5 conditions</td>"))
    )

  coverage_rows_html <- pid_coverage |>
    mutate(html = paste0(
      "<tr><td class='mono'>", pid, "</td>",
      "<td>", n_conds, "</td>",
      status_html, "</tr>")
    ) |> pull(html) |> paste(collapse = "\n")

  # CDA.SCR range check (should be ≥ 0; values > 10 µS are unusual)
  scr_vals <- era$CDA.SCR[!is.na(era$CDA.SCR)]
  n_neg_scr <- sum(scr_vals < 0)
  n_high_scr <- sum(scr_vals > 10)
  scr_status <- if (n_neg_scr == 0 && n_high_scr == 0) {
    "<td class='status-ok'>✓ none</td>"
  } else {
    paste0("<td class='status-warn'>⚠ ",
           if (n_neg_scr > 0) paste0(n_neg_scr, " negative") else "",
           if (n_neg_scr > 0 && n_high_scr > 0) "; " else "",
           if (n_high_scr > 0) paste0(n_high_scr, " > 10 µS") else "",
           "</td>")
  }

  # Per-condition mean SCR table
  cond_summary_rows <- era_summary |>
    group_by(condition) |>
    summarise(
      n_pids    = n_distinct(pid),
      mean_SCR  = round(mean(mean_SCR, na.rm = TRUE), 5),
      mean_nSCR = round(mean(mean_nSCR, na.rm = TRUE), 2),
      .groups = "drop"
    ) |>
    mutate(html = paste0(
      "<tr><td class='mono'>", condition, "</td>",
      "<td>", n_pids, "</td>",
      "<td>", mean_SCR, "</td>",
      "<td>", mean_nSCR, "</td></tr>")
    ) |> pull(html) |> paste(collapse = "\n")

  nid_note <- if (has_nid_map) {
    paste0('<div class="note-ok">NID map found — conditions mapped from ',
           basename(nid_map_path), '</div>')
  } else {
    paste0('<div class="note">NID map not found at ',
           nid_map_path, ' — conditions shown as raw NID values. ',
           'Run 02_create_ledalab_events_psychopy.py first.</div>')
  }

  unmatched_note <- if (n_unmatched > 0) {
    paste0('<div class="note"><strong>', n_unmatched,
           ' events</strong> could not be matched to a condition via the NID map.</div>')
  } else ""

  paste0(
  '<div class="status-row">
    <div class="tile blue"><div class="tile-value">', n_era_pids, '</div>
      <div class="tile-label">Participants<br>with ERA files</div></div>
    <div class="tile ', if (n_low_resp == 0) "ok" else "warn", '">
      <div class="tile-value">', n_low_resp, '/', n_era_pids, '</div>
      <div class="tile-label">Low / non-<br>responders</div></div>
    <div class="tile ', if (n_unmatched == 0) "ok" else "warn", '">
      <div class="tile-value">', n_unmatched, '</div>
      <div class="tile-label">Unmatched<br>NIDs</div></div>
    <div class="tile ', if (n_neg_scr == 0 && n_high_scr == 0) "ok" else "warn", '">
      <div class="tile-value">',
        if (n_neg_scr == 0 && n_high_scr == 0) "✓" else paste0(n_neg_scr + n_high_scr), '</div>
      <div class="tile-label">CDA.SCR<br>anomalies</div></div>
  </div>

  ', nid_note, unmatched_note, '

  <section>
    <div class="section-head">
      <div class="section-label">File Coverage</div>
      <h2>ERA files per participant</h2>
      <p>Expect one ERA file per participant with 5 condition epochs
         (baseline, neg_induction, neg_recovery, pos_induction, pos_recovery).</p>
    </div>
    <div class="table-wrap"><table>
      <thead><tr><th>Participant</th><th>Conditions found</th><th>Status</th></tr></thead>
      <tbody>', coverage_rows_html, '</tbody>
    </table></div>
  </section>

  <section>
    <div class="section-head">
      <div class="section-label">CDA Metrics by Condition</div>
      <h2>Mean CDA.SCR and nSCR across participants</h2>
      <p>CDA.SCR = mean phasic driver (µS). CDA.nSCR = number of SCR peaks per epoch
         (0 is valid; consistently 0 across all conditions warrants review).</p>
    </div>
    <div class="table-wrap"><table>
      <thead><tr><th>Condition</th><th>N participants</th>
        <th>Mean CDA.SCR (µS)</th><th>Mean CDA.nSCR</th></tr></thead>
      <tbody>', cond_summary_rows, '</tbody>
    </table></div>
  </section>

  <section>
    <div class="section-head">
      <div class="section-label">Responsiveness</div>
      <h2>Participants with few skin conductance responses</h2>
      <p>Number of SCRs detected by CDA (<code>CDA.nSCR</code>) in each condition epoch (~3 min).
         <strong>Non-responder</strong>: no SCRs in any epoch.
         <strong>Low responder</strong>: fewer than ', LOW_NSCR_PER_EPOCH, ' SCRs per epoch on average.
         <strong>Some low epochs</strong>: at least one epoch with fewer than ', LOW_NSCR_PER_EPOCH, '.
         Check the raw EDA of flagged participants (sensor contact, gel, cold hands) before
         excluding anyone; counts also depend on the minimum SCR amplitude set in Ledalab.</p>
    </div>
    <div class="table-wrap"><table>
      <thead><tr><th>Participant</th><th>Epochs</th><th>Mean nSCR / epoch</th><th>Min nSCR</th>
        <th>Epochs &lt; ', LOW_NSCR_PER_EPOCH, '</th><th>Low epochs (nSCR)</th><th>Status</th></tr></thead>
      <tbody>', responder_rows_html, '</tbody>
    </table></div>
  </section>

  <section>
    <div class="section-head">
      <div class="section-label">Signal Range Check</div>
      <h2>CDA.SCR values</h2>
    </div>
    <div class="table-wrap"><table>
      <thead><tr><th>Metric</th><th>N values</th><th>Min</th><th>Max</th>
        <th>Expected range</th><th>Anomalies</th></tr></thead>
      <tbody>
        <tr>
          <td class="mono">CDA.SCR</td>
          <td>', length(scr_vals), '</td>
          <td>', round(min(scr_vals), 5), '</td>
          <td>', round(max(scr_vals), 5), '</td>
          <td>0 – ~5 µS</td>
          ', scr_status, '
        </tr>
      </tbody>
    </table></div>
  </section>')

}, error = function(e) {
  msg <- conditionMessage(e)
  if (startsWith(msg, "NO_FILES:")) {
    placeholder_section("Ledalab (EDA)",
      "No <code>_era.txt</code> files found in <code>LEDALAB_RESULTS_DIR</code>.
       Run Ledalab batch with ERA export (filetype=2) and save outputs there.")
  } else {
    placeholder_section("Ledalab (EDA) — load error", msg)
  }
})

# ── 5. Kubios (HRV) ────────────────────────────────────────────────────────────
# Participant IDs (file name up to the first "_") are searched for in two Kubios outputs:
#   batch summary  KubiosHRVresults*.csv  one row per .acq file; samples S1..S5 have no labels
#   _hrv files     {pid}_*_hrv.csv        Kubios report per recording, with sample labels
#                                         and beat counts
# Metrics come from the _hrv file when there is one (its labels name the blocks). Otherwise
# they come from the batch summary, assuming samples are in Kubios_Samples.csv order
# (S1 baseline ... S5 positive_recovery). For participants in both, HR is compared between
# the two, which also checks that order.
kubios_html <- tryCatch({

  KUBIOS_BLOCKS <- c("baseline","negative_induction","negative_recovery",
                     "positive_induction","positive_recovery")

  # "neg_induction(2)", "negative_reconvery(3)" (pilot typo) -> names used in KUBIOS_BLOCKS
  norm_block <- function(x) {
    x |> str_trim() |> str_remove("\\(\\d+\\)$") |> str_to_lower() |>
      str_replace("^neg_", "negative_") |> str_replace("^pos_", "positive_") |>
      str_replace("reconvery", "recovery")
  }
  to_num     <- function(x) suppressWarnings(as.numeric(str_trim(x)))
  drop_blank <- function(x) x[nzchar(x)]
  pid_of     <- function(x) str_to_lower(str_extract(basename(x), "^[^_]+"))

  summary_files <- list.files(KUBIOS_RESULTS_DIR, pattern = "^KubiosHRVresults.*\\.csv$",
                              full.names = TRUE, ignore.case = TRUE)
  hrv_files     <- keep_files(
    list.files(KUBIOS_RESULTS_DIR, pattern = "_hrv\\.csv$", full.names = TRUE))

  if (length(summary_files) == 0 && length(hrv_files) == 0)
    stop("NO_FILES: No KubiosHRVresults.csv or _hrv.csv files found in KUBIOS_RESULTS_DIR.")

  # Batch summary: "sep=," and a title line, then the header row
  summary_long <- bind_rows(
    tibble(pid = character(), file = character(), acq_file = character(), block = character(),
           mean_hr_bpm = numeric(), rmssd_ms = numeric(), sdnn_ms = numeric(),
           mtime = as.POSIXct(character())),
    map_dfr(summary_files, function(f) {
      # name_repair: every row ends in a trailing comma, giving one unnamed column
      raw <- read_csv(f, skip = 2, col_types = cols(.default = col_character()),
                      name_repair = "unique_quiet", show_col_types = FALSE)
      if (!"FileName" %in% names(raw)) return(tibble())
      raw <- raw |> filter(!is.na(FileName), nzchar(str_trim(FileName)))
      map_dfr(seq_along(KUBIOS_BLOCKS), function(i) {
        metric <- function(name) {
          col <- paste0("S", i, "_", name)
          if (col %in% names(raw)) to_num(raw[[col]]) else rep(NA_real_, nrow(raw))
        }
        tibble(pid = pid_of(raw$FileName), file = basename(f), acq_file = raw$FileName,
               block = KUBIOS_BLOCKS[i], mean_hr_bpm = metric("Mean HR (bpm)"),
               rmssd_ms = metric("RMSSD (ms)"), sdnn_ms = metric("SDNN (ms)"),
               mtime = file.mtime(f))
      })
    })
  )
  # A KubiosHRVresults batch file can cover several participants, so these rows are
  # filtered by pid rather than by filename.
  summary_long <- drop_excluded(summary_long, "pid")
  summary_rows_per_pid <- summary_long |> distinct(pid, file, acq_file) |>
    count(pid, name = "n_summary_rows")
  summary_long <- summary_long |>
    group_by(pid) |> slice_max(mtime, n = 1, with_ties = TRUE) |>   # newest batch file wins
    group_by(pid, block) |> slice_tail(n = 1) |> ungroup()          # then its last row

  # _hrv file: Kubios text report. Each value row is "label:, v1, , v2, ..." (blank spacer columns)
  hrv_values <- function(lines, label) {
    i <- which(str_detect(lines, fixed(label)))[1]
    if (is.na(i)) return(character(0))
    drop_blank(str_trim(str_split(lines[i], ",")[[1]][-1]))
  }
  hrv_long <- bind_rows(
    tibble(pid = character(), file = character(), block = character(), n_beats = numeric(),
           mean_hr_bpm = numeric(), rmssd_ms = numeric(), sdnn_ms = numeric(),
           mtime = as.POSIXct(character())),
    map_dfr(hrv_files, function(f) {
      lines  <- read_lines(f)
      head_i <- which(str_detect(lines, fixed("RR Interval Samples Selected for Analysis")))[1]
      if (is.na(head_i)) return(tibble())
      labels <- drop_blank(str_trim(str_split(lines[head_i + 1], ",")[[1]][-1]))
      n      <- length(labels)
      if (n == 0) return(tibble())
      values <- function(label) { x <- to_num(hrv_values(lines, label)); length(x) <- n; x }
      tibble(pid = pid_of(f), file = basename(f), block = norm_block(labels),
             n_beats = values("Beats total:"), mean_hr_bpm = values("Mean HR (beats/min):"),
             rmssd_ms = values("RMSSD (ms):"), sdnn_ms = values("SDNN (ms):"),
             mtime = file.mtime(f))
    })
  )
  hrv_files_per_pid <- hrv_long |> distinct(pid, file) |> count(pid, name = "n_hrv_files")
  hrv_long <- hrv_long |> drop_excluded("pid") |>
    group_by(pid) |> slice_max(mtime, n = 1, with_ties = TRUE) |> ungroup()

  ids_summary <- unique(summary_long$pid)
  ids_hrv     <- unique(hrv_long$pid)
  kub_pids    <- sort(union(ids_summary, ids_hrv))
  n_kub_pids  <- length(kub_pids)
  if (n_kub_pids == 0)
    stop("NO_FILES: Kubios files were found, but no participant results could be read from them.")

  # Metrics: _hrv file where available, batch summary otherwise
  kubios <- bind_rows(
    hrv_long |> mutate(source = "_hrv"),
    summary_long |> filter(!pid %in% ids_hrv) |> mutate(source = "summary", n_beats = NA_real_)
  ) |> filter(block %in% KUBIOS_BLOCKS, !is.na(mean_hr_bpm))

  hr_mismatch <- inner_join(
      hrv_long |> filter(block %in% KUBIOS_BLOCKS) |> select(pid, block, hr_hrv = mean_hr_bpm),
      summary_long |> select(pid, block, hr_summary = mean_hr_bpm),
      by = c("pid", "block")) |>
    filter(!is.na(hr_hrv), !is.na(hr_summary), abs(hr_hrv - hr_summary) > 0.01) |>
    distinct(pid) |> pull(pid)

  coverage <- tibble(pid = kub_pids) |>
    mutate(in_summary = pid %in% ids_summary, in_hrv = pid %in% ids_hrv) |>
    left_join(kubios |> group_by(pid) |> summarise(n_blocks = n_distinct(block), .groups = "drop"),
              by = "pid") |>
    left_join(summary_rows_per_pid, by = "pid") |>
    left_join(hrv_files_per_pid, by = "pid") |>
    mutate(
      n_blocks       = coalesce(n_blocks, 0L),
      n_summary_rows = coalesce(n_summary_rows, 0L),
      n_hrv_files    = coalesce(n_hrv_files, 0L),
      files_found    = case_when(in_summary & in_hrv ~ "both",
                                 in_summary          ~ "batch summary only",
                                 TRUE                ~ "_hrv file only"),
      metrics_from   = if_else(in_hrv, "_hrv file", "batch summary"),
      issues = pmap_chr(
        list(in_summary, in_hrv, n_blocks, n_summary_rows, n_hrv_files, pid %in% hr_mismatch),
        function(s, h, nb, ns, nh, mm) {
          paste(c(if (!s) "not in batch summary",
                  if (!h) "no _hrv file",
                  if (nb < 5) paste0(nb, "/5 blocks"),
                  if (ns > 1) paste0(ns, " batch summary rows (newest used)"),
                  if (nh > 1) paste0(nh, " _hrv files (newest used)"),
                  if (mm) "mean HR differs between batch summary and _hrv file"),
                collapse = "; ")
        }),
      status_html = if_else(issues == "", "<td class='status-ok'>✓ OK</td>",
                            paste0("<td class='status-warn'>⚠ ", issues, "</td>"))
    )

  present_cell <- function(x) if_else(x,
    "<td class='status-ok' style='text-align:center'>&#10003;</td>",
    "<td class='status-warn' style='text-align:center'>&#10007;</td>")

  coverage_rows_html <- coverage |>
    arrange(issues == "", pid) |>
    mutate(html = paste0(
      "<tr><td class='mono'>", pid, "</td>",
      present_cell(in_summary), present_cell(in_hrv),
      "<td>", files_found, "</td>",
      "<td>", metrics_from, "</td>",
      "<td>", n_blocks, "</td>",
      status_html, "</tr>")
    ) |> pull(html) |> paste(collapse = "\n")

  n_both         <- sum(coverage$in_summary & coverage$in_hrv)
  n_complete_kub <- sum(coverage$n_blocks >= 5)

  # HR / RMSSD range checks
  range_cells <- function(v) if (length(v) == 0) "<td>—</td><td>—</td>" else
    paste0("<td>", round(min(v), 1), "</td><td>", round(max(v), 1), "</td>")

  hr_vals <- kubios$mean_hr_bpm[!is.na(kubios$mean_hr_bpm)]
  hr_flag <- sum(hr_vals < 40 | hr_vals > 120)
  hr_status <- if (hr_flag == 0) "<td class='status-ok'>✓ none</td>" else
    paste0("<td class='status-warn'>⚠ ", hr_flag, " outside 40–120</td>")

  rmssd_vals <- kubios$rmssd_ms[!is.na(kubios$rmssd_ms)]
  rmssd_flag <- sum(rmssd_vals < 5 | rmssd_vals > 200)
  rmssd_status <- if (rmssd_flag == 0) "<td class='status-ok'>✓ none</td>" else
    paste0("<td class='status-warn'>⚠ ", rmssd_flag, " outside 5–200</td>")

  # HRV metrics by block
  hrv_block_rows <- kubios |>
    group_by(block) |>
    summarise(
      n_pids     = n_distinct(pid),
      mean_hr    = round(mean(mean_hr_bpm, na.rm = TRUE), 1),
      mean_rmssd = round(mean(rmssd_ms,    na.rm = TRUE), 1),
      mean_sdnn  = round(mean(sdnn_ms,     na.rm = TRUE), 1),
      .groups = "drop"
    ) |>
    arrange(match(block, KUBIOS_BLOCKS)) |>
    mutate(html = paste0(
      "<tr><td class='mono'>", block, "</td>",
      "<td>", n_pids, "</td>",
      "<td>", mean_hr, "</td>",
      "<td>", mean_rmssd, "</td>",
      "<td>", mean_sdnn, "</td></tr>")
    ) |> pull(html) |> paste(collapse = "\n")

  # Beat counts ("Beats total" in the _hrv files)
  beats <- hrv_long |> filter(block %in% KUBIOS_BLOCKS, !is.na(n_beats))
  rr_beats_html <- ""
  if (nrow(beats) > 0) {
    beat_rows <- beats |>
      arrange(pid, match(block, KUBIOS_BLOCKS)) |>
      mutate(html = paste0(
        "<tr><td class='mono'>", pid, "</td>",
        "<td class='mono'>", block, "</td>",
        "<td>", n_beats, "</td>",
        if_else(n_beats >= 100, "<td class='status-ok'>✓</td>", "<td class='status-warn'>⚠ low</td>"),
        "</tr>")
      ) |> pull(html)
    rr_beats_html <- paste0(
      '<section>
        <div class="section-head">
          <div class="section-label">Beat Counts</div>
          <h2>Beats per block (from _hrv files)</h2>
          <p>Flag blocks with &lt; 100 beats (expect ~150–250 for a 3-minute block).</p>
        </div>
        <div class="table-wrap"><table>
          <thead><tr><th>Participant</th><th>Block</th>
            <th>N beats</th><th>Status</th></tr></thead>
          <tbody>', paste(beat_rows, collapse = "\n"), '</tbody>
        </table></div>
      </section>')
  }

  paste0(
  '<div class="status-row">
    <div class="tile blue"><div class="tile-value">', n_kub_pids, '</div>
      <div class="tile-label">Participants<br>with Kubios files</div></div>
    <div class="tile ', if (n_both == n_kub_pids) "ok" else "warn", '">
      <div class="tile-value">', n_both, '/', n_kub_pids, '</div>
      <div class="tile-label">In batch summary<br>and _hrv files</div></div>
    <div class="tile ', if (n_complete_kub == n_kub_pids) "ok" else "warn", '">
      <div class="tile-value">', n_complete_kub, '/', n_kub_pids, '</div>
      <div class="tile-label">Complete<br>block sets</div></div>
    <div class="tile ', if (hr_flag + rmssd_flag == 0) "ok" else "warn", '">
      <div class="tile-value">', if (hr_flag + rmssd_flag == 0) "✓" else hr_flag + rmssd_flag, '</div>
      <div class="tile-label">HR / RMSSD<br>out-of-range values</div></div>
  </div>

  <section>
    <div class="section-head">
      <div class="section-label">File Coverage</div>
      <h2>Kubios files per participant</h2>
      <p>Participant IDs are looked for in the batch summary (<code>KubiosHRVresults*.csv</code>,
         column <code>FileName</code>) and in <code>{pid}_*_hrv.csv</code> files. Metrics come from
         the <code>_hrv</code> file when there is one, otherwise from the batch summary (samples S1–S5
         taken as baseline, negative_induction, negative_recovery, positive_induction,
         positive_recovery). Expect both files and 5 blocks per participant.</p>
    </div>
    <div class="table-wrap"><table>
      <thead><tr><th>Participant</th><th>Batch summary</th><th>_hrv file</th>
        <th>Files found</th><th>Metrics from</th><th>Blocks</th><th>Status</th></tr></thead>
      <tbody>', coverage_rows_html, '</tbody>
    </table></div>
  </section>

  <section>
    <div class="section-head">
      <div class="section-label">HRV Metrics by Block</div>
      <h2>Mean HR and HRV across participants</h2>
      <p>HR in bpm; RMSSD and SDNN in ms. Flag: HR outside 40–120 bpm, RMSSD outside 5–200 ms.</p>
    </div>
    <div class="table-wrap"><table>
      <thead><tr><th>Block</th><th>N participants</th><th>Mean HR (bpm)</th>
        <th>Mean RMSSD (ms)</th><th>Mean SDNN (ms)</th></tr></thead>
      <tbody>', hrv_block_rows, '</tbody>
    </table></div>
    <div class="table-wrap" style="margin-top:1rem;"><table>
      <thead><tr><th>Metric</th><th>N values</th><th>Min</th><th>Max</th>
        <th>Expected range</th><th>Anomalies</th></tr></thead>
      <tbody>
        <tr><td class="mono">mean_hr_bpm</td><td>', length(hr_vals), '</td>',
          range_cells(hr_vals), '<td>40–120 bpm</td>', hr_status, '</tr>
        <tr><td class="mono">rmssd_ms</td><td>', length(rmssd_vals), '</td>',
          range_cells(rmssd_vals), '<td>5–200 ms</td>', rmssd_status, '</tr>
      </tbody>
    </table></div>
  </section>

  ', rr_beats_html)

}, error = function(e) {
  msg <- conditionMessage(e)
  if (startsWith(msg, "NO_FILES:")) {
    placeholder_section("Kubios (HRV)",
      paste0(sub("^NO_FILES: ", "", msg),
       " Expected <code>KubiosHRVresults*.csv</code> (batch summary) and/or
       <code>{pid}_*_hrv.csv</code> files in <code>KUBIOS_RESULTS_DIR</code>."))
  } else {
    placeholder_section("Kubios (HRV) — load error", msg)
  }
})

# ── 6. Webcam biometrics ───────────────────────────────────────────────────────
# Raw files per session in PSYCHOPY_DATA_DIR, written by biometrics_server.py during the
# experiment:  <id>_..._biometrics.csv  and  <id>_..._clocksync.json
# plus the combined biosignals2_webcambiometrics.csv made by 01_data_cleaning.Rmd.
MIN_BIOMETRICS_MB <- 1   # a raw _biometrics.csv smaller than this holds (almost) no frames
CLOCKSYNC_KEYS    <- c("t_main", "t_wall", "t_mono", "mono_reset", "global_reset")

pid_from_file <- function(x) str_to_lower(str_extract(basename(x), "^[^_]+"))
yes_no_cell   <- function(x) if_else(x,
  "<td class='status-ok' style='text-align:center'>&#10003;</td>",
  "<td class='status-warn' style='text-align:center'>&#10007;</td>")
status_cell   <- function(issues) if_else(issues == "",
  "<td class='status-ok'>✓ OK</td>", paste0("<td class='status-warn'>⚠ ", issues, "</td>"))

# The combined file is large (~73 columns, one row per frame). Only the 4 columns used here are read,
# and the summaries are cached (see `cached`), so it is only re-read when the file changes.
summarise_combined_biometrics <- function(path) {
  bm <- read_csv(path, show_col_types = FALSE,
                 col_types = cols_only(participant_id = col_character(), condition = col_character(),
                                       hr_peak = col_character(), bpm_peak = col_character())) |>
    mutate(is_peak  = toupper(hr_peak) == "TRUE",
           bpm_peak = suppressWarnings(as.numeric(bpm_peak)))
  list(
    ids          = unique(bm$participant_id),
    n_rows       = nrow(bm),
    by_condition = bm |>
      group_by(participant_id, condition) |>
      summarise(
        n_frames  = n(),
        peak_rate = round(100 * mean(is_peak, na.rm = TRUE), 1),
        bpm_min   = suppressWarnings(round(min(bpm_peak, na.rm = TRUE), 1)),
        bpm_max   = suppressWarnings(round(max(bpm_peak, na.rm = TRUE), 1)),
        .groups = "drop"
      ),
    n_bpm_flag   = sum(bm$bpm_peak < 40 | bm$bpm_peak > 120, na.rm = TRUE),
    n_low_peak   = bm |>
      group_by(participant_id) |>
      summarise(overall_peak_rate = round(100 * mean(is_peak, na.rm = TRUE), 1), .groups = "drop") |>
      pull(overall_peak_rate) |> (\(r) sum(r < 1, na.rm = TRUE))()
  )
}

bm_combined <- tryCatch(
  if (file.exists(BIOMETRICS_COMBINED_PATH))
    cached("combined_biometrics_summary", BIOMETRICS_COMBINED_PATH,
           function() summarise_combined_biometrics(BIOMETRICS_COMBINED_PATH)) else NULL,
  error = function(e) e)
# Applied after `cached()` so that editing EXCLUDED_PIDS does not force a slow re-read
# of the ~178 MB combined biometrics file.
if (is.list(bm_combined) && !inherits(bm_combined, "error")) {
  bm_combined$ids          <- keep_ids(bm_combined$ids)
  bm_combined$by_condition <- drop_excluded(bm_combined$by_condition)
}
has_combined <- is.list(bm_combined) && !inherits(bm_combined, "error")

biometrics_raw_html <- tryCatch({

  bio_files  <- keep_files(
    list.files(PSYCHOPY_DATA_DIR, pattern = "_biometrics\\.csv$",  full.names = TRUE))
  sync_files <- keep_files(
    list.files(PSYCHOPY_DATA_DIR, pattern = "_clocksync\\.json$", full.names = TRUE))
  data_files <- keep_files(
    setdiff(list.files(PSYCHOPY_DATA_DIR, pattern = "Psychopy.*\\.csv$", full.names = TRUE),
            bio_files))
  if (length(bio_files) == 0 && length(sync_files) == 0)
    stop("NO_FILES: No _biometrics.csv or _clocksync.json files found in PSYCHOPY_DATA_DIR.")

  bio <- tibble(path = bio_files) |>
    mutate(pid       = pid_from_file(path),
           size_mb   = file.size(path) / 1024^2,
           header_ok = map_lgl(path, function(f) {
             h <- readLines(f, n = 1, warn = FALSE)
             length(h) == 1 && all(str_detect(h, c("^time,", "face", "bpm_fft")))
           }))
  sync <- tibble(path = sync_files) |>
    mutate(pid     = pid_from_file(path),
           keys_ok = map_lgl(path, function(f) {
             txt <- paste(readLines(f, warn = FALSE), collapse = "")
             all(str_detect(txt, paste0('"', CLOCKSYNC_KEYS, '"\\s*:\\s*-?[0-9]')))
           }))
  combined_ids <- if (has_combined) str_to_lower(bm_combined$ids) else character(0)

  raw_cov <- tibble(pid = sort(unique(c(bio$pid, sync$pid, pid_from_file(data_files))))) |>
    left_join(bio |> group_by(pid) |>
                summarise(n_bio = n(), size_mb = sum(size_mb), header_ok = all(header_ok), .groups = "drop"),
              by = "pid") |>
    left_join(sync |> group_by(pid) |>
                summarise(n_sync = n(), keys_ok = all(keys_ok), .groups = "drop"),
              by = "pid") |>
    mutate(
      n_bio       = coalesce(n_bio, 0L),
      n_sync      = coalesce(n_sync, 0L),
      in_combined = pid %in% combined_ids,
      issues = pmap_chr(list(n_bio, size_mb, header_ok, n_sync, keys_ok, in_combined),
        function(nb, mb, ho, ns, ko, ic) {
          paste(c(if (nb == 0) "no _biometrics.csv",
                  if (nb > 1) paste0(nb, " _biometrics.csv files"),
                  if (nb > 0 && mb < MIN_BIOMETRICS_MB)
                    paste0("_biometrics.csv only ", round(mb * 1024), " KB (almost no frames)"),
                  if (nb > 0 && !ho) "unexpected _biometrics.csv header",
                  if (ns == 0) "no _clocksync.json",
                  if (ns > 1) paste0(ns, " _clocksync.json files"),
                  if (ns > 0 && !ko) "_clocksync.json missing values",
                  if (nb > 0 && has_combined && !ic) "not in combined file"),
                collapse = "; ")
        }),
      status_html = status_cell(issues)
    )

  raw_rows_html <- raw_cov |>
    arrange(issues == "", pid) |>
    mutate(html = paste0(
      "<tr><td class='mono'>", pid, "</td>",
      yes_no_cell(n_bio > 0),
      "<td>", if_else(is.na(size_mb), "—", sprintf("%.1f", size_mb)), "</td>",
      yes_no_cell(n_sync > 0),
      if (has_combined) yes_no_cell(in_combined) else "<td style='text-align:center'>—</td>",
      status_html, "</tr>")
    ) |> pull(html) |> paste(collapse = "\n")

  n_raw_pids  <- nrow(raw_cov)
  n_bio_pids  <- sum(raw_cov$n_bio > 0)
  n_sync_pids <- sum(raw_cov$n_sync > 0)
  n_raw_issue <- sum(raw_cov$issues != "")

  paste0(
  '<div class="status-row">
    <div class="tile blue"><div class="tile-value">', n_raw_pids, '</div>
      <div class="tile-label">Sessions in<br>raw_psychopy</div></div>
    <div class="tile ', if (n_bio_pids == n_raw_pids) "ok" else "warn", '">
      <div class="tile-value">', n_bio_pids, '/', n_raw_pids, '</div>
      <div class="tile-label">With<br>_biometrics.csv</div></div>
    <div class="tile ', if (n_sync_pids == n_raw_pids) "ok" else "warn", '">
      <div class="tile-value">', n_sync_pids, '/', n_raw_pids, '</div>
      <div class="tile-label">With<br>_clocksync.json</div></div>
    <div class="tile ', if (n_raw_issue == 0) "ok" else "warn", '">
      <div class="tile-value">', if (n_raw_issue == 0) "✓" else n_raw_issue, '</div>
      <div class="tile-label">Sessions<br>with issues</div></div>
  </div>

  <section>
    <div class="section-head">
      <div class="section-label">Raw Files</div>
      <h2>Biometrics and clock-sync files per session</h2>
      <p>From <code>PSYCHOPY_DATA_DIR</code>: <code>{pid}_*_biometrics.csv</code> (webcam frames
         streamed during the experiment) and <code>{pid}_*_clocksync.json</code> (clock readings
         needed to align them: ', paste(CLOCKSYNC_KEYS, collapse = ", "), '). Sessions with a
         PsychoPy data file but no biometrics are listed too. Files under ', MIN_BIOMETRICS_MB,
         ' MB are flagged as almost empty.',
         if (has_combined) ' <em>In combined</em> = participant appears in
         <code>biosignals2_webcambiometrics.csv</code>.' else '', '</p>
    </div>
    <div class="table-wrap"><table>
      <thead><tr><th>Participant</th><th>_biometrics.csv</th><th>Size (MB)</th>
        <th>_clocksync.json</th><th>In combined</th><th>Status</th></tr></thead>
      <tbody>', raw_rows_html, '</tbody>
    </table></div>
  </section>')

}, error = function(e) {
  msg <- conditionMessage(e)
  if (startsWith(msg, "NO_FILES:")) {
    placeholder_section("Webcam Biometrics — raw files",
      "No <code>_biometrics.csv</code> or <code>_clocksync.json</code> files found in
       <code>PSYCHOPY_DATA_DIR</code>.")
  } else {
    placeholder_section("Webcam Biometrics — raw files load error", msg)
  }
})

biometrics_combined_html <- tryCatch({

  if (is.null(bm_combined))
    stop("NO_FILES: biosignals2_webcambiometrics.csv not found in COMBINED_PSYCHO_DIR.")
  if (inherits(bm_combined, "error")) stop(conditionMessage(bm_combined))

  n_bm_pids  <- length(bm_combined$ids)
  n_bm_rows  <- bm_combined$n_rows

  COND_ORDER <- c("baseline","negative_induction","post_negative_induction_recovery",
                  "positive_induction","post_positive_induction_recovery")

  # Per-participant x condition frame counts + peak rate (from summarise_combined_biometrics)
  bm_qc <- bm_combined$by_condition |>
    mutate(
      bpm_min = ifelse(is.infinite(bpm_min), NA, bpm_min),
      bpm_max = ifelse(is.infinite(bpm_max), NA, bpm_max),
      frame_status = if_else(n_frames >= 500,
        "<td class='status-ok'>✓</td>",
        "<td class='status-warn'>⚠ low</td>"),
      peak_status = if_else(peak_rate >= 1,
        "<td class='status-ok'>✓</td>",
        "<td class='status-warn'>⚠ &lt;1%</td>"),
      html = paste0(
        "<tr><td class='mono'>", participant_id, "</td>",
        "<td class='mono'>", condition, "</td>",
        "<td>", n_frames, "</td>",
        frame_status,
        "<td>", peak_rate, "%</td>",
        peak_status,
        "<td>", ifelse(is.na(bpm_min), "—", bpm_min), "</td>",
        "<td>", ifelse(is.na(bpm_max), "—", bpm_max), "</td></tr>")
    )

  bm_rows_html <- bm_qc |>
    arrange(participant_id, match(condition, COND_ORDER)) |>
    pull(html) |> paste(collapse = "\n")

  n_bpm_flag <- bm_combined$n_bpm_flag   # BPM values outside 40–120
  n_low_peak <- bm_combined$n_low_peak   # participants with overall peak rate < 1%

  paste0(
  '<div class="status-row" style="margin-top:2.75rem">
    <div class="tile blue"><div class="tile-value">', n_bm_pids, '</div>
      <div class="tile-label">Participants in<br>combined file</div></div>
    <div class="tile blue"><div class="tile-value">',
      format(n_bm_rows, big.mark = ","), '</div>
      <div class="tile-label">Total<br>frames</div></div>
    <div class="tile ', if (n_low_peak == 0) "ok" else "warn", '">
      <div class="tile-value">', if (n_low_peak == 0) "✓" else n_low_peak, '</div>
      <div class="tile-label">Participants<br>low peak rate</div></div>
    <div class="tile ', if (n_bpm_flag == 0) "ok" else "warn", '">
      <div class="tile-value">', if (n_bpm_flag == 0) "✓" else n_bpm_flag, '</div>
      <div class="tile-label">BPM values<br>outside 40–120</div></div>
  </div>

  <section>
    <div class="section-head">
      <div class="section-label">Combined File — Frame Counts &amp; Signal Quality</div>
      <h2>Frames per participant per condition</h2>
      <p>From <code>biosignals2_webcambiometrics.csv</code>. Low frame count (&lt; 500) may indicate
         recording gaps. Peak rate &lt; 1% suggests rPPG peak detection failed for that phase.</p>
    </div>
    <div class="table-wrap"><table>
      <thead><tr>
        <th>Participant</th><th>Condition</th>
        <th>Frames</th><th>Frame QC</th>
        <th>Peak rate</th><th>Peak QC</th>
        <th>BPM min</th><th>BPM max</th>
      </tr></thead>
      <tbody>', bm_rows_html, '</tbody>
    </table></div>
  </section>')

}, error = function(e) {
  msg <- conditionMessage(e)
  if (startsWith(msg, "NO_FILES:")) {
    placeholder_section("Webcam Biometrics — combined file",
      "<code>biosignals2_webcambiometrics.csv</code> not found in <code>COMBINED_PSYCHO_DIR</code>.
       Re-knit 01_data_cleaning.Rmd to generate it.")
  } else {
    placeholder_section("Webcam Biometrics — combined file load error", msg)
  }
})

biometrics_html <- paste0(biometrics_raw_html, biometrics_combined_html)

# ── 6.1 Video recordings ───────────────────────────────────────────────────────
# Box video folder (VIDEO_BOX_DIR, top level only). Every PNG participant needs all three:
#   <id>_frames.zip            zipped PNG frames (the lossless original)
#   <id>_1to1_ffv1.avi         1:1 FFV1 video made from the PNGs (000_convert_png_to_avi.py)
#   <id>_frame_timestamps.csv  one row per frame
# Old sessions recorded straight to AVI (no PNGs) need <id>_recording.avi + <id>_frame_timestamps.csv.
# Subfolders (png_data, pilot_archive, ...) are not searched.
MIN_CAMERA_FPS <- 20
VIDEO_PATTERNS <- c(zip     = "_frames\\.zip$",
                    avi     = "_1to1_ffv1\\.avi$",
                    ts      = "_frame_timestamps\\.csv$",
                    old_avi = "_recording\\.avi$",
                    mkv     = "_1to1\\.mkv$")

video_html <- tryCatch({

  if (!dir.exists(VIDEO_BOX_DIR))
    stop(paste0("NO_FILES: VIDEO_BOX_DIR does not exist: ", VIDEO_BOX_DIR))
  entries <- keep_files(list.files(VIDEO_BOX_DIR, full.names = TRUE))
  entries <- entries[!dir.exists(entries)]

  vfiles <- map_dfr(names(VIDEO_PATTERNS), function(k) {
    hits <- entries[str_detect(basename(entries), regex(VIDEO_PATTERNS[[k]], ignore_case = TRUE))]
    tibble(path = hits, kind = rep(k, length(hits)))
  })
  if (nrow(vfiles) == 0)
    stop("NO_FILES: No frame zips, 1to1_ffv1 videos, recordings or frame timestamps found in VIDEO_BOX_DIR.")
  vfiles <- vfiles |> mutate(pid = pid_from_file(path), size_gb = file.size(path) / 1024^3)

  ts_files <- vfiles$path[vfiles$kind == "ts"]
  timestamps <- bind_rows(
    tibble(pid = character(), n_frames = integer(), duration_min = numeric(), fps = numeric()),
    map_dfr(ts_files, function(f) {
      # only the time column is read; the result is cached per file
      cached(paste0("timestamps_", str_remove(basename(f), "\\.csv$")), f, function() {
        header <- names(read_csv(f, n_max = 0, show_col_types = FALSE))
        t <- if ("time_since_recording_start" %in% header)
          read_csv(f, show_col_types = FALSE,
                   col_types = cols_only(time_since_recording_start = col_double()))$time_since_recording_start
        else numeric(0)
        t <- t[!is.na(t)]
        span <- if (length(t) > 1) max(t) - min(t) else NA_real_
        tibble(pid = pid_from_file(f), n_frames = length(t), duration_min = span / 60,
               fps = if (!is.na(span) && span > 0) (length(t) - 1) / span else NA_real_)
      })
    })
  )

  n_of  <- function(k) vfiles |> filter(kind == k) |> count(pid, name = paste0("n_", k))
  gb_of <- function(k) vfiles |> filter(kind == k) |> group_by(pid) |>
    summarise("{k}_gb" := sum(size_gb, na.rm = TRUE), .groups = "drop")

  vcov <- tibble(pid = sort(unique(vfiles$pid))) |>
    left_join(n_of("zip"), by = "pid") |> left_join(n_of("avi"), by = "pid") |>
    left_join(n_of("ts"), by = "pid")  |> left_join(n_of("old_avi"), by = "pid") |>
    left_join(n_of("mkv"), by = "pid") |>
    left_join(gb_of("zip"), by = "pid") |> left_join(gb_of("avi"), by = "pid") |>
    left_join(gb_of("old_avi"), by = "pid") |>
    left_join(timestamps |> group_by(pid) |>
                summarise(n_frames = first(n_frames), duration_min = first(duration_min),
                          fps = first(fps), .groups = "drop"),
              by = "pid") |>
    mutate(
      across(c(n_zip, n_avi, n_ts, n_old_avi, n_mkv), ~ coalesce(.x, 0L)),
      # old AVI session = has <id>_recording.avi and no PNG-pipeline files
      old_session = n_old_avi > 0 & n_zip == 0 & n_avi == 0,
      type = if_else(old_session, "Old AVI", "PNG"),
      issues = pmap_chr(list(old_session, n_zip, n_avi, n_ts, n_old_avi, n_mkv, fps),
                        function(old, nz, na, nt, no, nm, fp) {
        paste(c(if (!old && nz == 0) "no frames zip",
                if (!old && na == 0 && nm > 0) "no 1to1_ffv1.avi (only _1to1.mkv: run 004)",
                if (!old && na == 0 && nm == 0) "no 1to1_ffv1.avi",
                if (nt == 0) "no frame timestamps",
                if (nz > 1) paste0(nz, " frames zips"),
                if (na > 1) paste0(na, " 1to1_ffv1 videos"),
                if (nt > 1) paste0(nt, " timestamps files (first used)"),
                if (!is.na(fp) && fp < MIN_CAMERA_FPS) sprintf("camera only %.1f fps", fp)),
              collapse = "; ")
      }),
      complete = issues == "" | (str_detect(issues, "^camera only") & n_ts > 0),
      status_html = status_cell(issues)
    )

  na_cell <- "<td style='text-align:center;color:var(--text-3)'>n/a</td>"
  gb_txt  <- function(x) if_else(is.na(x), "—", sprintf("%.2f", x))

  video_rows_html <- vcov |>
    arrange(issues == "", type, pid) |>
    mutate(html = paste0(
      "<tr><td class='mono'>", pid, "</td>",
      "<td>", type, "</td>",
      if_else(old_session, na_cell, yes_no_cell(n_zip > 0)),
      if_else(old_session, na_cell, yes_no_cell(n_avi > 0)),
      yes_no_cell(n_ts > 0),
      "<td>", if_else(old_session, "—", gb_txt(zip_gb)), "</td>",
      "<td>", if_else(old_session, gb_txt(old_avi_gb), gb_txt(avi_gb)), "</td>",
      "<td>", if_else(is.na(n_frames), "—", format(n_frames, big.mark = ",")), "</td>",
      "<td>", if_else(is.na(duration_min), "—", sprintf("%.1f", duration_min)), "</td>",
      "<td>", if_else(is.na(fps), "—", sprintf("%.2f", fps)), "</td>",
      status_html, "</tr>")
    ) |> pull(html) |> paste(collapse = "\n")

  n_png      <- sum(!vcov$old_session)
  n_png_ok   <- sum(!vcov$old_session & vcov$complete)
  n_old      <- sum(vcov$old_session)
  n_low_fps  <- sum(!is.na(vcov$fps) & vcov$fps < MIN_CAMERA_FPS)

  paste0(
  '<div class="status-row">
    <div class="tile blue"><div class="tile-value">', nrow(vcov), '</div>
      <div class="tile-label">Participants<br>in video folder</div></div>
    <div class="tile ', if (n_png_ok == n_png) "ok" else "warn", '">
      <div class="tile-value">', n_png_ok, '/', n_png, '</div>
      <div class="tile-label">PNG participants with<br>zip + 1:1 AVI + timestamps</div></div>
    <div class="tile blue"><div class="tile-value">', n_old, '</div>
      <div class="tile-label">Old AVI<br>sessions</div></div>
    <div class="tile ', if (n_low_fps == 0) "ok" else "warn", '">
      <div class="tile-value">', if (n_low_fps == 0) "✓" else n_low_fps, '</div>
      <div class="tile-label">Camera below<br>', MIN_CAMERA_FPS, ' fps</div></div>
  </div>

  <section>
    <div class="section-head">
      <div class="section-label">Video Recordings</div>
      <h2>Video files per participant (Box video folder)</h2>
      <p>Every PNG participant should have three files directly in <code>VIDEO_BOX_DIR</code>:
         <code>{pid}_frames.zip</code> (zipped PNG frames), <code>{pid}_1to1_ffv1.avi</code>
         (1:1 FFV1 video from 000_convert_png_to_avi.py) and <code>{pid}_frame_timestamps.csv</code>.
         Old sessions recorded straight to AVI need <code>{pid}_recording.avi</code> and
         <code>{pid}_frame_timestamps.csv</code>. Subfolders (e.g. <code>png_data</code>,
         <code>pilot_archive</code>) are not searched. Camera fps is worked out from the frame
         timestamps; below ', MIN_CAMERA_FPS, ' fps the video is probably not usable for FaceReader.</p>
    </div>
    <div class="table-wrap"><table>
      <thead><tr><th>Participant</th><th>Type</th><th>Frames zip</th><th>1:1 FFV1 AVI</th>
        <th>Timestamps</th><th>Zip (GB)</th><th>AVI (GB)</th><th>Frames</th><th>Duration (min)</th>
        <th>Camera fps</th><th>Status</th></tr></thead>
      <tbody>', video_rows_html, '</tbody>
    </table></div>
  </section>')

}, error = function(e) {
  msg <- conditionMessage(e)
  if (startsWith(msg, "NO_FILES:")) {
    placeholder_section("Video", sub("^NO_FILES: ", "", msg))
  } else {
    placeholder_section("Video — load error", msg)
  }
})

# ── 6.2 FaceReader ─────────────────────────────────────────────────────────────
# FACEREADER_RESULTS_DIR: FaceReader exports per participant
#   <id>_detailed.txt  <id>_heart beat log.txt  <id>_state.txt
# and <id>_hrv_per_block.csv from 03_compute_hrv_per_block_facereader.py.
FACEREADER_FILES <- c(detailed       = "_detailed\\.txt$",
                      heart_beat_log = "_heart beat log\\.txt$",
                      state          = "_state\\.txt$",
                      hrv_per_block  = "_hrv_per_block\\.csv$")
MIN_FACEREADER_BEATS <- 100

facereader_html <- tryCatch({

  if (!dir.exists(FACEREADER_RESULTS_DIR))
    stop(paste0("NO_FILES: FACEREADER_RESULTS_DIR does not exist: ", FACEREADER_RESULTS_DIR))
  fr_all <- keep_files(list.files(FACEREADER_RESULTS_DIR, full.names = TRUE))
  fr <- bind_rows(
    tibble(pid = character(), kind = character(), path = character()),
    bind_rows(imap(FACEREADER_FILES, function(pattern, kind) {
      f <- fr_all[str_detect(basename(fr_all), pattern)]
      tibble(pid = pid_from_file(f), kind = rep(kind, length(f)), path = f)
    }))
  )
  if (nrow(fr) == 0)
    stop("NO_FILES: No FaceReader exports found in FACEREADER_RESULTS_DIR.")

  # FaceReader exports start with a short tab-separated header ("Frame rate<TAB>29.992", ...)
  header_value <- function(f, key) {
    h <- readLines(f, n = 12, warn = FALSE)
    v <- str_match(h, paste0("^", key, "\\t(.*)$"))[, 2]
    v <- v[!is.na(v)]
    if (length(v) > 0) str_trim(v[1]) else NA_character_
  }
  count_beats <- function(f) {
    l <- readLines(f, warn = FALSE)
    h <- which(str_detect(l, "^Time\\tInterbeat"))[1]
    if (is.na(h)) NA_integer_ else sum(str_detect(l[-seq_len(h)], "^\\d{2}:\\d{2}:\\d{2}"))
  }
  count_blocks <- function(f) tryCatch({
    x <- read_csv(f, show_col_types = FALSE)
    if ("block" %in% names(x)) n_distinct(x$block) else nrow(x)
  }, error = function(e) NA_integer_)

  first_of <- function(kind_name, fun) {
    fr |> filter(kind == kind_name) |> group_by(pid) |> slice_head(n = 1) |> ungroup() |>
      mutate(value = map(path, fun)) |> select(pid, value)
  }
  beats      <- first_of("heart_beat_log", count_beats) |> transmute(pid, n_beats = as.integer(unlist(value)))
  video_name <- first_of("heart_beat_log", ~ header_value(.x, "Filename")) |>
    transmute(pid, video_file = str_extract(unlist(value), "[^\\\\/]+$"))
  video_fps  <- first_of("heart_beat_log", ~ header_value(.x, "Frame rate")) |>
    transmute(pid, video_fps = suppressWarnings(as.numeric(unlist(value))))
  hrv_blocks <- first_of("hrv_per_block", count_blocks) |> transmute(pid, n_blocks = as.integer(unlist(value)))

  fcov <- tibble(pid = sort(unique(fr$pid)))
  for (k in names(FACEREADER_FILES)) fcov[[paste0("has_", k)]] <- fcov$pid %in% fr$pid[fr$kind == k]
  fcov <- fcov |>
    left_join(beats, by = "pid") |> left_join(video_name, by = "pid") |>
    left_join(video_fps, by = "pid") |> left_join(hrv_blocks, by = "pid") |>
    mutate(
      issues = pmap_chr(list(has_detailed, has_heart_beat_log, has_state, has_hrv_per_block, n_beats, n_blocks),
        function(d, h, s, b, nb, nbl) {
          paste(c(if (!d) "no detailed log",
                  if (!h) "no heart beat log",
                  if (!s) "no state log",
                  if (!b) "no hrv_per_block.csv",
                  if (h && !is.na(nb) && nb < MIN_FACEREADER_BEATS) paste0("only ", nb, " beats"),
                  if (b && !is.na(nbl) && nbl < 5) paste0(nbl, "/5 HRV blocks")),
                collapse = "; ")
        }),
      status_html = status_cell(issues)
    )

  fr_rows_html <- fcov |>
    arrange(issues == "", pid) |>
    mutate(html = paste0(
      "<tr><td class='mono'>", pid, "</td>",
      yes_no_cell(has_detailed), yes_no_cell(has_heart_beat_log),
      yes_no_cell(has_state), yes_no_cell(has_hrv_per_block),
      "<td>", if_else(is.na(n_beats), "—", as.character(n_beats)), "</td>",
      "<td>", if_else(is.na(n_blocks), "—", as.character(n_blocks)), "</td>",
      "<td class='mono' style='font-size:.78rem'>", coalesce(video_file, "—"), "</td>",
      "<td>", if_else(is.na(video_fps), "—", sprintf("%.3f", video_fps)), "</td>",
      status_html, "</tr>")
    ) |> pull(html) |> paste(collapse = "\n")

  n_fr_pids   <- nrow(fcov)
  n_all_files <- sum(fcov$has_detailed & fcov$has_heart_beat_log & fcov$has_state & fcov$has_hrv_per_block)
  n_hrv5      <- sum(!is.na(fcov$n_blocks) & fcov$n_blocks >= 5)
  n_fr_issue  <- sum(fcov$issues != "")

  paste0(
  '<div class="status-row">
    <div class="tile blue"><div class="tile-value">', n_fr_pids, '</div>
      <div class="tile-label">Participants with<br>FaceReader files</div></div>
    <div class="tile ', if (n_all_files == n_fr_pids) "ok" else "warn", '">
      <div class="tile-value">', n_all_files, '/', n_fr_pids, '</div>
      <div class="tile-label">All four<br>files present</div></div>
    <div class="tile ', if (n_hrv5 == n_fr_pids) "ok" else "warn", '">
      <div class="tile-value">', n_hrv5, '/', n_fr_pids, '</div>
      <div class="tile-label">HRV for<br>all 5 blocks</div></div>
    <div class="tile ', if (n_fr_issue == 0) "ok" else "warn", '">
      <div class="tile-value">', if (n_fr_issue == 0) "✓" else n_fr_issue, '</div>
      <div class="tile-label">Participants<br>with issues</div></div>
  </div>

  <section>
    <div class="section-head">
      <div class="section-label">FaceReader Exports</div>
      <h2>FaceReader files per participant</h2>
      <p>From <code>FACEREADER_RESULTS_DIR</code>: <code>{pid}_detailed.txt</code>,
         <code>{pid}_heart beat log.txt</code>, <code>{pid}_state.txt</code> and
         <code>{pid}_hrv_per_block.csv</code> (from 03_compute_hrv_per_block_facereader.py).
         Beats = heartbeats in the heart beat log (flag below ', MIN_FACEREADER_BEATS, ').
         Video and fps are read from the heart beat log header.</p>
    </div>
    <div class="table-wrap"><table>
      <thead><tr><th>Participant</th><th>Detailed</th><th>Heart beat log</th><th>State</th>
        <th>HRV per block</th><th>Beats</th><th>HRV blocks</th><th>Analysed video</th>
        <th>Video fps</th><th>Status</th></tr></thead>
      <tbody>', fr_rows_html, '</tbody>
    </table></div>
  </section>')

}, error = function(e) {
  msg <- conditionMessage(e)
  if (startsWith(msg, "NO_FILES:")) {
    placeholder_section("FaceReader", sub("^NO_FILES: ", "", msg))
  } else {
    placeholder_section("FaceReader — load error", msg)
  }
})

# ── 6.3 Raw physiology (BIOPAC AcqKnowledge) ───────────────────────────────────
# This section is the one place that looks across all three pipeline stages, so it
# walks PHYSIOLOGY_ROOT rather than RAW_PHYSIOLOGY_DIR (which config.R points at the
# trimmed recordings, because that is what analyses run on):
#   entire_session_duration/        {pid}_physiology.acq          — full session, as recorded
#   experimental_protocol_duration/ {pid}_physiology_trimmed.acq  — cut to the protocol
#                                   {pid}_eda_trimmed.acq         — EDA channel, cut to the protocol
#   exports/                        {pid}_physiology.mat, {pid}_eda.mat — for Ledalab / PsPM
# A session recording well under this size is almost certainly a truncated take.
MIN_PHYSIO_ACQ_MB <- 10

physiology_html <- tryCatch({

  if (!dir.exists(PHYSIOLOGY_ROOT))
    stop(paste0("NO_FILES: PHYSIOLOGY_ROOT does not exist: ", PHYSIOLOGY_ROOT))

  physio_files <- function(sub, pattern) {
    d <- file.path(PHYSIOLOGY_ROOT, sub)
    if (!dir.exists(d)) return(tibble(pid = character(), path = character(), size_mb = numeric()))
    f <- keep_files(list.files(d, pattern = pattern, full.names = TRUE, ignore.case = TRUE))
    tibble(pid = pid_from_file(f), path = f, size_mb = file.size(f) / 1024^2)
  }

  session   <- physio_files("entire_session_duration",        "_physiology\\.acq$")
  trim_phys <- physio_files("experimental_protocol_duration", "_physiology_trimmed\\.acq$")
  trim_eda  <- physio_files("experimental_protocol_duration", "_eda_trimmed\\.acq$")
  exp_phys  <- physio_files("exports",                        "_physiology\\.mat$")
  exp_eda   <- physio_files("exports",                        "_eda\\.mat$")

  all_pids <- sort(unique(c(session$pid, trim_phys$pid, trim_eda$pid, exp_phys$pid, exp_eda$pid)))
  if (length(all_pids) == 0)
    stop("NO_FILES: No .acq or .mat files found under PHYSIOLOGY_ROOT.")

  pcov <- tibble(pid = all_pids) |>
    mutate(
      has_session   = pid %in% session$pid,
      session_mb    = session$size_mb[match(pid, session$pid)],
      has_trim_phys = pid %in% trim_phys$pid,
      has_trim_eda  = pid %in% trim_eda$pid,
      has_exp_phys  = pid %in% exp_phys$pid,
      has_exp_eda   = pid %in% exp_eda$pid
    ) |>
    mutate(
      issues = pmap_chr(list(has_session, session_mb, has_trim_phys, has_trim_eda,
                             has_exp_phys, has_exp_eda),
        function(sess, mb, tp, te, ep, ee) {
          x <- character(0)
          if (!sess)                        x <- c(x, "no session recording")
          if (sess && !is.na(mb) && mb < MIN_PHYSIO_ACQ_MB)
            x <- c(x, sprintf("session file only %.1f MB", mb))
          if (!tp)                          x <- c(x, "not trimmed (physiology)")
          if (!te)                          x <- c(x, "not trimmed (EDA)")
          if (!ep && !ee)                   x <- c(x, "no .mat export")
          else if (!ep)                     x <- c(x, "no physiology .mat")
          else if (!ee)                     x <- c(x, "no EDA .mat")
          paste(x, collapse = "; ")
        }),
      status_html = status_cell(issues)
    )

  physio_rows_html <- pcov |>
    arrange(issues == "", pid) |>
    mutate(html = paste0(
      "<tr><td class='mono'>", pid, "</td>",
      yes_no_cell(has_session),
      "<td>", if_else(is.na(session_mb), "—", sprintf("%.1f", session_mb)), "</td>",
      yes_no_cell(has_trim_phys), yes_no_cell(has_trim_eda),
      yes_no_cell(has_exp_phys), yes_no_cell(has_exp_eda),
      status_html, "</tr>")
    ) |> pull(html) |> paste(collapse = "\n")

  n_phys_pids <- nrow(pcov)
  n_sess      <- sum(pcov$has_session)
  n_trimmed   <- sum(pcov$has_trim_phys & pcov$has_trim_eda)
  n_exported  <- sum(pcov$has_exp_phys & pcov$has_exp_eda)
  n_phys_issue <- sum(pcov$issues != "")

  paste0(
  '<div class="status-row">
    <div class="tile blue"><div class="tile-value">', n_phys_pids, '</div>
      <div class="tile-label">Participants with<br>physiology files</div></div>
    <div class="tile ', if (n_sess == n_phys_pids) "ok" else "warn", '">
      <div class="tile-value">', n_sess, '/', n_phys_pids, '</div>
      <div class="tile-label">Session<br>recording</div></div>
    <div class="tile ', if (n_trimmed == n_phys_pids) "ok" else "warn", '">
      <div class="tile-value">', n_trimmed, '/', n_phys_pids, '</div>
      <div class="tile-label">Trimmed to<br>protocol</div></div>
    <div class="tile ', if (n_exported == n_phys_pids) "ok" else "warn", '">
      <div class="tile-value">', n_exported, '/', n_phys_pids, '</div>
      <div class="tile-label">Exported<br>to .mat</div></div>
  </div>

  <section>
    <div class="section-head">
      <div class="section-label">Raw Physiology</div>
      <h2>BIOPAC files per participant</h2>
      <p>From <code>PHYSIOLOGY_ROOT</code>, following the recording through the pipeline:
         <code>entire_session_duration/{pid}_physiology.acq</code> as recorded, then
         <code>experimental_protocol_duration/{pid}_physiology_trimmed.acq</code> and
         <code>{pid}_eda_trimmed.acq</code> cut to the protocol, then
         <code>exports/{pid}_physiology.mat</code> and <code>{pid}_eda.mat</code> for
         Ledalab / PsPM. Session size flags a recording under ', MIN_PHYSIO_ACQ_MB, ' MB.</p>
    </div>
    <div class="table-wrap"><table>
      <thead><tr><th>Participant</th><th>Session .acq</th><th>Size (MB)</th>
        <th>Trimmed physiology</th><th>Trimmed EDA</th>
        <th>.mat physiology</th><th>.mat EDA</th><th>Status</th></tr></thead>
      <tbody>', physio_rows_html, '</tbody>
    </table></div>
  </section>')

}, error = function(e) {
  msg <- conditionMessage(e)
  if (startsWith(msg, "NO_FILES:")) {
    placeholder_section("Raw physiology", sub("^NO_FILES: ", "", msg))
  } else {
    placeholder_section("Raw physiology — load error", msg)
  }
})

# ── 7. Questionnaires (scored, from 04_questionnaire_analysis.Rmd) ─────────────
questionnaire_html <- tryCatch({

  if (!file.exists(QUESTIONNAIRE_PATH))
    stop("NO_FILES: biosignals2_questionnaires_scored.csv not found in COMBINED_PSYCHO_DIR.")

  q <- read_csv(QUESTIONNAIRE_PATH, show_col_types = FALSE) |>
    mutate(participant_id = as.character(participant_id)) |>
    drop_excluded()

  html_esc <- function(x) {
    x |> str_replace_all("&", "&amp;") |> str_replace_all("<", "&lt;") |> str_replace_all(">", "&gt;")
  }
  fmt_num <- function(x) if (is.na(x)) "—" else as.character(round(x, 1))
  # Qualtrics IDs are upper-case (N2026); PsychoPy IDs are lower-case (n2026)
  norm_id <- function(x) str_to_upper(str_squish(as.character(x)))
  is_true <- function(x) str_to_upper(as.character(x)) %in% "TRUE"

  n_q_pids <- n_distinct(q$participant_id)
  dup_ids  <- q |> count(participant_id) |> filter(n > 1) |> pull(participant_id)

  # Scale completeness & score ranges
  SCALES <- tibble(
    scale       = c("GAD-7", "PHQ-9", "AQ-10", "PAQ-24", "DAS-SF1", "DAS-SF2"),
    total_col   = c("gad7_total", "phq9_total", "aq10_total", "paq_total", "das_sf1_total", "das_sf2_total"),
    missing_col = c("gad7_n_missing", "phq9_n_missing", "aq10_n_missing", "paq_n_missing",
                    "das_sf1_n_missing", "das_sf2_n_missing"),
    n_items     = c(7, 9, 10, 24, 9, 9),
    lo          = c(0, 0, 0, 24, 9, 9),
    hi          = c(21, 27, 10, 168, 63, 63)   # PAQ-24 is 7-point: 24 x 7 = 168
  ) |> filter(total_col %in% names(q))

  scale_stats <- pmap_dfr(SCALES, function(scale, total_col, missing_col, n_items, lo, hi) {
    tot  <- q[[total_col]]
    miss <- if (missing_col %in% names(q)) q[[missing_col]] else rep(NA_real_, nrow(q))
    vals <- tot[!is.na(tot)]
    tibble(
      scale, n_items, lo, hi,
      n_scored  = length(vals),
      n_partial = sum(miss > 0 & miss < n_items, na.rm = TRUE),
      n_blank   = sum(miss >= n_items, na.rm = TRUE),
      min_val   = if (length(vals)) min(vals) else NA_real_,
      max_val   = if (length(vals)) max(vals) else NA_real_,
      n_out     = sum(vals < lo | vals > hi)
    )
  })

  scale_rows_html <- scale_stats |>
    mutate(
      status_html = case_when(
        n_scored == 0 ~ "<td class='status-warn'>⚠ no scores</td>",
        n_out > 0     ~ paste0("<td class='status-warn'>⚠ ", n_out, " out of range</td>"),
        n_scored < n_q_pids ~ paste0("<td class='status-warn'>⚠ ", n_q_pids - n_scored, " unscored</td>"),
        TRUE          ~ "<td class='status-ok'>✓ complete</td>"
      ),
      html = paste0(
        "<tr><td class='mono'>", scale, "</td>",
        "<td>", n_items, "</td>",
        "<td>", n_scored, "/", n_q_pids, "</td>",
        "<td>", n_partial, "</td>",
        "<td>", n_blank, "</td>",
        "<td>", map_chr(min_val, fmt_num), "</td>",
        "<td>", map_chr(max_val, fmt_num), "</td>",
        "<td>", lo, "–", hi, "</td>",
        status_html, "</tr>")
    ) |> pull(html) |> paste(collapse = "\n")

  n_scales_complete <- sum(scale_stats$n_scored == n_q_pids & scale_stats$n_out == 0)

  # Participant cross-check against PsychoPy sessions
  psy_ids <- tryCatch(
    if (inherits(selfreport, "error")) character(0) else unique(selfreport$participant_id),
    error = function(e) character(0)
  )
  xcheck <- tibble(pid = sort(union(norm_id(q$participant_id), norm_id(psy_ids)))) |>
    mutate(in_q = pid %in% norm_id(q$participant_id), in_psy = pid %in% norm_id(psy_ids))
  n_matched <- sum(xcheck$in_q & xcheck$in_psy)

  xcheck_rows_html <- xcheck |>
    mutate(
      status_html = case_when(
        in_q & in_psy ~ "<td class='status-ok'>✓ matched</td>",
        in_q          ~ "<td class='status-warn'>⚠ no PsychoPy session</td>",
        TRUE          ~ "<td class='status-warn'>⚠ no questionnaire</td>"
      ),
      html = paste0(
        "<tr><td class='mono'>", html_esc(pid), "</td>",
        "<td>", if_else(in_q, "✓", "—"), "</td>",
        "<td>", if_else(in_psy, "✓", "—"), "</td>",
        status_html, "</tr>")
    ) |> pull(html) |> paste(collapse = "\n")

  psy_note <- if (length(psy_ids) == 0) {
    '<div class="note">PsychoPy ratings file could not be read — cross-check shows questionnaire IDs only.</div>'
  } else ""
  dup_note <- if (length(dup_ids) > 0) {
    paste0('<div class="note"><strong>Duplicate questionnaire IDs:</strong> ',
           html_esc(paste(dup_ids, collapse = ", ")), '</div>')
  } else ""

  # Clinical screening flags
  FLAGS <- tibble(
    label = c("GAD-7 ≥ 10 (possible GAD)", "PHQ-9 ≥ 10 (possible depression)",
              "PHQ-9 item 9 ≥ 1 (suicidal ideation)", "AQ-10 ≥ 6 (possible autism)"),
    col   = c("gad7_flag", "phq9_flag", "phq9_item9_flagged", "aq10_flag")
  ) |> filter(col %in% names(q))

  flag_stats <- pmap_dfr(FLAGS, function(label, col) {
    hit <- is_true(q[[col]])
    tibble(label, col, n = sum(hit),
           ids = paste(sort(q$participant_id[hit]), collapse = ", "))
  })
  n_item9 <- sum(flag_stats$n[flag_stats$col == "phq9_item9_flagged"])

  flag_rows_html <- flag_stats |>
    mutate(
      status_html = case_when(
        n == 0                            ~ "<td class='status-ok'>✓ none</td>",
        col == "phq9_item9_flagged"       ~ "<td class='status-warn'>⚠ follow up per protocol</td>",
        TRUE                              ~ "<td class='status-warn'>⚠ flagged</td>"
      ),
      html = paste0(
        "<tr><td>", label, "</td>",
        "<td>", n, "</td>",
        "<td class='mono'>", if_else(ids == "", "—", html_esc(ids)), "</td>",
        status_html, "</tr>")
    ) |> pull(html) |> paste(collapse = "\n")

  # Demographics
  ages <- suppressWarnings(as.numeric(q$age))
  ages <- ages[!is.na(ages)]
  age_txt <- if (length(ages)) {
    paste0(sprintf("%.1f", mean(ages)), " (SD ", sprintf("%.1f", sd(ages)), "), range ",
           min(ages), "–", max(ages), " · n = ", length(ages))
  } else "—"
  count_txt <- function(col) {
    if (!col %in% names(q)) return("—")
    q |> count(.data[[col]]) |>
      mutate(lbl = paste0(html_esc(coalesce(as.character(.data[[col]]), "missing")), " (", n, ")")) |>
      pull(lbl) |> paste(collapse = " · ")
  }

  # Known export problems (see 04_questionnaire_analysis.Rmd)
  scored <- setNames(scale_stats$n_scored, scale_stats$scale)
  export_notes <- paste0(
    if (isTRUE(scored["PAQ-24"] == 0))
      '<div class="note"><strong>PAQ-24 has no complete scores.</strong> PAQ-24 can only be scored
       from a Qualtrics <em>values</em> export (unlabelled scale points export as <code>---</code>).
       Re-export as values, then re-knit 04_questionnaire_analysis.Rmd — this report reads the
       scored CSV it writes, not the Qualtrics export.</div>' else "",
    if (isTRUE(scored["DAS-SF1"] == 0) && isTRUE(scored["DAS-SF2"] == 0))
      '<div class="note"><strong>DAS-SF1/SF2 are empty</strong> for every participant — check that
       the block is displayed in the Qualtrics survey flow.</div>' else ""
  )

  paste0(
  '<div class="status-row">
    <div class="tile blue"><div class="tile-value">', n_q_pids, '</div>
      <div class="tile-label">Participants<br>scored</div></div>
    <div class="tile ', if (n_matched == nrow(xcheck)) "ok" else "warn", '">
      <div class="tile-value">', n_matched, '/', nrow(xcheck), '</div>
      <div class="tile-label">IDs matched<br>to PsychoPy</div></div>
    <div class="tile ', if (n_scales_complete == nrow(scale_stats)) "ok" else "warn", '">
      <div class="tile-value">', n_scales_complete, '/', nrow(scale_stats), '</div>
      <div class="tile-label">Scales fully<br>scored</div></div>
    <div class="tile ', if (n_item9 == 0) "ok" else "warn", '">
      <div class="tile-value">', if (n_item9 == 0) "✓" else n_item9, '</div>
      <div class="tile-label">PHQ-9 item 9<br>flags</div></div>
  </div>

  ', export_notes, '

  <section>
    <div class="section-head">
      <div class="section-label">Scale Completeness</div>
      <h2>Scored totals and range checks</h2>
      <p>Totals are only computed when every item is answered. Partial = some items missing;
         blank = all items missing.</p>
    </div>
    <div class="table-wrap"><table>
      <thead><tr><th>Scale</th><th>Items</th><th>Scored</th><th>Partial</th><th>Blank</th>
        <th>Min</th><th>Max</th><th>Valid range</th><th>Status</th></tr></thead>
      <tbody>', scale_rows_html, '</tbody>
    </table></div>
  </section>

  <section>
    <div class="section-head">
      <div class="section-label">Participant Cross-check</div>
      <h2>Questionnaire IDs vs PsychoPy sessions</h2>
      <p>IDs compared case-insensitively. Mismatches usually mean a typo in the Qualtrics
         participant ID field or a session not yet run.</p>
    </div>
    ', psy_note, dup_note, '
    <div class="table-wrap"><table>
      <thead><tr><th>Participant</th><th>Questionnaire</th><th>PsychoPy</th>
        <th>Status</th></tr></thead>
      <tbody>', xcheck_rows_html, '</tbody>
    </table></div>
  </section>

  <section>
    <div class="section-head">
      <div class="section-label">Clinical Screening</div>
      <h2>Participants above screening cut-offs</h2>
      <p>Screening flags only, not diagnoses.</p>
    </div>
    <div class="table-wrap"><table>
      <thead><tr><th>Flag</th><th>N</th><th>Participants</th><th>Status</th></tr></thead>
      <tbody>', flag_rows_html, '</tbody>
    </table></div>
  </section>

  <section>
    <div class="section-head">
      <div class="section-label">Demographics</div>
      <h2>Sample characteristics</h2>
    </div>
    <div class="table-wrap"><table>
      <thead><tr><th>Variable</th><th>Summary</th></tr></thead>
      <tbody>
        <tr><td class="mono">age</td><td>', age_txt, '</td></tr>
        <tr><td class="mono">sex_at_birth</td><td>', count_txt("sex_at_birth"), '</td></tr>
        <tr><td class="mono">gender_id</td><td>', count_txt("gender_id"), '</td></tr>
        <tr><td class="mono">ethnicity</td><td>', count_txt("ethnicity"), '</td></tr>
      </tbody>
    </table></div>
    <div class="note-ok" style="margin-top:.75rem;">
      <strong>Pipeline:</strong> Qualtrics export &#8594; 04_questionnaire_analysis.Rmd &#8594;
      biosignals2_questionnaires_scored.csv</div>
  </section>')

}, error = function(e) {
  msg <- conditionMessage(e)
  if (startsWith(msg, "NO_FILES:")) {
    placeholder_section("Questionnaires",
      "<code>biosignals2_questionnaires_scored.csv</code> not found in <code>COMBINED_PSYCHO_DIR</code>.
       Knit 04_questionnaire_analysis.Rmd to generate it.")
  } else {
    placeholder_section("Questionnaires — load error", msg)
  }
})

# ── 7.5 Cross-source participant completeness ───────────────────────────────────
completeness_html <- tryCatch({

  norm_id_c <- function(x) {
    x <- trimws(as.character(x))
    x <- x[!is.na(x) & nzchar(x)]
    toupper(x)
  }

  get_ids <- function(expr) {
    tryCatch(keep_ids(unique(norm_id_c(expr))), error = function(e) character(0))
  }

  ids_of_files <- function(dir, pattern, recursive_dirs = character(0)) {
    dirs <- c(dir, file.path(dir, recursive_dirs))
    f <- unlist(map(dirs[dir.exists(dirs)], ~ list.files(.x, pattern = pattern, ignore.case = TRUE)))
    str_extract(f, "^[^_]+")
  }

  ids_psychopy <- get_ids(
    if (inherits(selfreport, "error")) character(0) else selfreport$participant_id
  )

  ids_questionnaire <- get_ids({
    if (file.exists(QUESTIONNAIRE_PATH))
      read_csv(QUESTIONNAIRE_PATH, show_col_types = FALSE, col_select = "participant_id")$participant_id
    else character(0)
  })

  ids_ledalab <- get_ids(ids_of_files(LEDALAB_RESULTS_DIR, "_era\\.txt$"))

  # Kubios: IDs from the batch summary (FileName column) and from _hrv files
  ids_kubios <- get_ids({
    f_summary <- list.files(KUBIOS_RESULTS_DIR, pattern = "^KubiosHRVresults.*\\.csv$",
                            full.names = TRUE, ignore.case = TRUE)
    ids_summary <- unlist(map(f_summary, function(f) {
      x <- read_csv(f, skip = 2, col_types = cols(.default = col_character()),
                    name_repair = "unique_quiet", show_col_types = FALSE)
      if ("FileName" %in% names(x)) str_extract(basename(x$FileName[!is.na(x$FileName)]), "^[^_]+")
      else character(0)
    }))
    c(ids_summary, ids_of_files(KUBIOS_RESULTS_DIR, "_hrv\\.csv$"))
  })

  # Video: any video-pipeline file at the top level of the Box video folder (see section 6.1)
  ids_video <- get_ids(ids_of_files(VIDEO_BOX_DIR,
    "_recording\\.avi$|_frames\\.zip$|_1to1_ffv1\\.avi$|_frame_timestamps\\.csv$"))

  # Raw physiology: the BIOPAC session recording is the source of truth for a
  # participant having been run at all.
  ids_physiology <- get_ids(ids_of_files(PHYSIOLOGY_SESSION_DIR, "_physiology\\.acq$"))

  # Webcam biometrics: raw _biometrics.csv files written during the experiment
  ids_biometrics <- get_ids(ids_of_files(PSYCHOPY_DATA_DIR, "_biometrics\\.csv$"))

  ids_facereader <- get_ids(ids_of_files(FACEREADER_RESULTS_DIR,
                                         "_detailed\\.txt$|_heart beat log\\.txt$|_state\\.txt$|_hrv_per_block\\.csv$"))

  # ── Raw files not yet in the combined CSVs ──
  # PsychoPy and Questionnaires above come from combined CSVs written by 01_data_cleaning.Rmd
  # and 04_questionnaire_analysis.Rmd. IDs that are in the raw files but not in those CSVs
  # usually mean the Rmd hasn't been re-knitted since the participant was run.
  # Raw PsychoPy: every non-biometrics .csv in PSYCHOPY_DATA_DIR (as 01 reads them).
  raw_psy_files <- list.files(PSYCHOPY_DATA_DIR, pattern = "\\.csv$", full.names = TRUE)
  raw_psy_files <- raw_psy_files[!grepl("_biometrics\\.csv$", raw_psy_files, ignore.case = TRUE)]
  ids_raw_psychopy <- get_ids(str_extract(basename(raw_psy_files), "^[^_]+"))

  # Raw questionnaire: the newest Biosignals2*.csv in QUESTIONNAIRE_DIR, completed responses
  # only (Finished = TRUE/1 and Progress = 100), ID in column QID7_1 — the same rules as 04.
  qfiles <- list.files(QUESTIONNAIRE_DIR, pattern = "^Biosignals2.*\\.csv$", full.names = TRUE)
  qfiles <- qfiles[order(file.mtime(qfiles), decreasing = TRUE)]
  ids_raw_questionnaire <- get_ids({
    if (length(qfiles) == 0) character(0) else {
      hdr <- read_csv(qfiles[1], n_max = 3, col_names = FALSE,
                      col_types = cols(.default = "c"), show_col_types = FALSE)
      import_ids <- str_extract(as.character(hdr[3, ]), '(?<="ImportId":")[^"]+')
      import_ids <- if_else(is.na(import_ids), as.character(hdr[1, ]), import_ids)
      raw_q <- read_csv(qfiles[1], skip = 3, col_names = make.unique(import_ids),
                        col_types = cols(.default = "c"), show_col_types = FALSE)
      if (!"QID7_1" %in% names(raw_q)) character(0) else {
        done <- rep(TRUE, nrow(raw_q))
        if ("finished" %in% names(raw_q)) done <- done & str_to_upper(raw_q$finished) %in% c("TRUE", "1")
        if ("progress" %in% names(raw_q)) done <- done & suppressWarnings(as.integer(raw_q$progress)) %in% 100L
        str_squish(raw_q$QID7_1[done])
      }
    }
  })

  not_combined <- list(
    PsychoPy       = setdiff(ids_raw_psychopy, ids_psychopy),
    Questionnaires = setdiff(ids_raw_questionnaire, ids_questionnaire)
  )
  reknit_script <- c(PsychoPy = "01_data_cleaning.Rmd", Questionnaires = "04_questionnaire_analysis.Rmd")

  sources <- list(
    PsychoPy       = ids_psychopy,
    Questionnaires = ids_questionnaire,
    Physiology     = ids_physiology,
    Ledalab        = ids_ledalab,
    Kubios         = ids_kubios,
    Video          = ids_video,
    Biometrics     = ids_biometrics,
    FaceReader     = ids_facereader
  )
  src_names <- names(sources)

  all_ids <- sort(unique(c(unlist(sources, use.names = FALSE), unlist(not_combined, use.names = FALSE))))
  if (length(all_ids) == 0)
    stop("NO_FILES: No participant IDs found in any data source yet.")

  n_sources <- length(sources)
  matrix_df <- tibble(pid = all_ids)
  for (nm in src_names) matrix_df[[nm]] <- matrix_df$pid %in% sources[[nm]]
  matrix_df$n_present   <- rowSums(matrix_df[src_names])
  matrix_df$is_complete <- matrix_df$n_present == n_sources
  matrix_df <- arrange(matrix_df, is_complete, pid)
  matrix_df$missing_from <- map_chr(seq_len(nrow(matrix_df)), function(i) {
    miss <- src_names[!unlist(matrix_df[i, src_names])]
    pid  <- matrix_df$pid[i]
    paste(map_chr(miss, function(nm)
      if (nm %in% names(not_combined) && pid %in% not_combined[[nm]])
        paste0(nm, " (raw file present &mdash; re-knit ", reknit_script[[nm]], ")") else nm),
      collapse = ", ")
  })

  n_total    <- nrow(matrix_df)
  n_complete <- sum(matrix_df$is_complete)

  cell_html <- function(present, raw_only = FALSE) {
    if (raw_only) "<td class='status-warn' style='text-align:center' title='In the raw files but not the combined CSV: re-knit'>&#10227; re-knit</td>"
    else if (present) "<td class='status-ok' style='text-align:center'>&#10003;</td>"
    else "<td class='status-warn' style='text-align:center'>&#10007;</td>"
  }

  matrix_rows_html <- map_chr(seq_len(nrow(matrix_df)), function(i) {
    r <- matrix_df[i, ]
    paste0("<tr><td class='mono'>", r$pid, "</td>",
           paste(map_chr(src_names, ~ cell_html(r[[.x]],
             raw_only = !r[[.x]] && .x %in% names(not_combined) && r$pid %in% not_combined[[.x]])),
             collapse = ""),
           "<td>", r$n_present, "/", n_sources, "</td>",
           if (r$is_complete) "<td class='status-ok'>&#10003; complete</td>"
           else "<td class='status-warn'>&#9888; incomplete</td>",
           "</tr>")
  }) |> paste(collapse = "\n")

  missing_summary <- filter(matrix_df, !is_complete)

  missing_note <- if (nrow(missing_summary) > 0) {
    items <- paste0("<li><span class='mono'>", missing_summary$pid, "</span> &mdash; missing: ",
                     missing_summary$missing_from, "</li>", collapse = "\n")
    paste0('<div class="note"><strong>', nrow(missing_summary),
           ' participant(s) missing data from at least one source:</strong>
           <ul style="margin-top:.5rem;margin-left:1.2rem;line-height:1.8;">',
           items, '</ul></div>')
  } else {
    paste0('<div class="note-ok"><strong>Every participant ID has data in all ', n_sources,
           ' sources.</strong></div>')
  }

  reknit_note <- {
    hits <- names(not_combined)[lengths(not_combined) > 0]
    if (length(hits) == 0) "" else paste0(
      '<div class="note"><strong>&#10227; Combined data out of date.</strong> These participants are in
       the raw files but not in the combined CSV this report reads:<ul style="margin-top:.5rem;
       margin-left:1.2rem;line-height:1.8;">',
      paste0("<li>", hits, ": <span class='mono'>", map_chr(hits, ~ paste(not_combined[[.x]], collapse = ", ")),
             "</span> &mdash; re-knit <code>", reknit_script[hits], "</code></li>", collapse = "\n"),
      '</ul>Then re-run this report. If someone is still listed after re-knitting, the Rmd is
       dropping their file (e.g. the filename filter in 01, or an incomplete Qualtrics response).</div>')
  }

  paste0(reknit_note,
  '<div class="status-row">
    <div class="tile blue"><div class="tile-value">', n_total, '</div>
      <div class="tile-label">Unique participant<br>IDs observed</div></div>
    <div class="tile ', if (n_complete == n_total) "ok" else "warn", '">
      <div class="tile-value">', n_complete, '/', n_total, '</div>
      <div class="tile-label">Participants with<br>complete dataset</div></div>
    <div class="tile blue"><div class="tile-value">', length(ids_psychopy), '/',
      length(ids_questionnaire), '/', length(ids_ledalab), '/', length(ids_kubios), '</div>
      <div class="tile-label">PsychoPy / Quest. /<br>Ledalab / Kubios IDs</div></div>
    <div class="tile blue"><div class="tile-value">', length(ids_video), '/',
      length(ids_biometrics), '/', length(ids_facereader), '</div>
      <div class="tile-label">Video / Biometrics /<br>FaceReader IDs</div></div>
  </div>

  <section>
    <div class="section-head">
      <div class="section-label">Cross-Source Completeness</div>
      <h2>Does every participant have a complete dataset?</h2>
      <p>A participant is <strong>complete</strong> when their ID appears in all ', n_sources, ' sources:
         PsychoPy self-report, Qualtrics questionnaires, Ledalab (EDA), Kubios (HRV),
         video recordings (Box video folder), webcam biometrics (raw <code>_biometrics.csv</code>)
         and FaceReader exports. IDs are compared case-insensitively and whitespace-trimmed
         (Qualtrics exports upper-case IDs; the other sources use lower-case).</p>
    </div>
    ', missing_note, '
    <div class="table-wrap" style="margin-top:1rem;"><table>
      <thead><tr><th>Participant</th>', paste0("<th>", src_names, "</th>", collapse = ""),
        '<th>Sources</th><th>Status</th></tr></thead>
      <tbody>', matrix_rows_html, '</tbody>
    </table></div>
  </section>')

}, error = function(e) {
  msg <- conditionMessage(e)
  if (startsWith(msg, "NO_FILES:")) {
    placeholder_section("Participant Completeness",
      "No participant IDs could be read from any data source yet. This section will
       populate once at least one of PsychoPy, questionnaire, Ledalab, Kubios, video,
       biometrics or FaceReader data is available.")
  } else {
    placeholder_section("Participant Completeness — load error", msg)
  }
})

# ── 8. CSS ─────────────────────────────────────────────────────────────────────
css <- '
<style>
@import url("https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Serif:ital,wght@0,600;0,700;1,400&display=swap");

:root{--bg:#F3F6FC;--surface:#FFFFFF;--surface-2:#EBF0F9;--text-1:#192040;
  --text-2:#495A7A;--text-3:#8499C0;--accent:#1C5CA8;--border:#D0DAF0;
  --pos:#C85F2A;--neg:#3B74B2;--pos-bg:#FBF0EA;--neg-bg:#EAF1FB;
  --ok:#1A7A50;--ok-bg:#E5F5EE;--warn:#966B10;--warn-bg:#FBF3E0;
  --tab-h:3rem}
@media(prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#0D1422;--surface:#15213A;--surface-2:#1A2B4A;--text-1:#D8E4F8;
  --text-2:#7B90B8;--text-3:#435278;--accent:#4D8FDC;--border:#213060;
  --pos:#E07B54;--neg:#5B8DB8;--pos-bg:#2A1508;--neg-bg:#081525;
  --ok:#28A86E;--ok-bg:#0A2018;--warn:#D49020;--warn-bg:#201500}}
:root[data-theme="dark"]{--bg:#0D1422;--surface:#15213A;--surface-2:#1A2B4A;
  --text-1:#D8E4F8;--text-2:#7B90B8;--text-3:#435278;--accent:#4D8FDC;
  --border:#213060;--pos:#E07B54;--neg:#5B8DB8;--pos-bg:#2A1508;--neg-bg:#081525;
  --ok:#28A86E;--ok-bg:#0A2018;--warn:#D49020;--warn-bg:#201500}

*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{font-family:"IBM Plex Sans",system-ui,sans-serif;font-size:.9375rem;
  line-height:1.65;color:var(--text-1);background:var(--bg);
  padding-inline:max(1.25rem,4vw);padding-block:2.5rem 4rem}
.page{max-width:920px;margin-inline:auto}

/* Header */
.page-header{display:flex;justify-content:space-between;align-items:flex-start;
  padding-bottom:1.5rem;border-bottom:1.5px solid var(--border);
  margin-bottom:2rem;flex-wrap:wrap;gap:1rem}
.header-left{display:flex;flex-direction:column;gap:.4rem}
.badge{display:inline-block;font-family:"IBM Plex Mono",monospace;font-size:.65rem;
  font-weight:500;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);
  border:1px solid var(--accent);padding:.2rem .45rem;width:fit-content}
h1{font-family:"IBM Plex Serif",Georgia,serif;font-size:1.7rem;font-weight:700;
  line-height:1.2}
.header-meta{font-family:"IBM Plex Mono",monospace;font-size:.72rem;
  color:var(--text-3);line-height:1.9}
.header-meta strong{color:var(--text-2);font-weight:500}

/* Tabs */
.tab-bar{display:flex;gap:0;border-bottom:2px solid var(--border);
  margin-bottom:2rem;overflow-x:auto}
.tab-btn{font-family:"IBM Plex Mono",monospace;font-size:.72rem;letter-spacing:.07em;
  text-transform:uppercase;color:var(--text-3);background:none;border:none;
  padding:.7rem 1.2rem;cursor:pointer;border-bottom:2px solid transparent;
  margin-bottom:-2px;white-space:nowrap;transition:color .15s,border-color .15s}
.tab-btn:hover{color:var(--text-2)}
.tab-btn.active{color:var(--accent);border-bottom-color:var(--accent);font-weight:500}
.tab-content{display:none}.tab-content.active{display:block}

/* Status tiles */
.status-row{display:grid;grid-template-columns:repeat(4,1fr);gap:.6rem;margin-bottom:2.75rem}
@media(max-width:640px){.status-row{grid-template-columns:repeat(2,1fr)}}
.tile{background:var(--surface);border:1px solid var(--border);
  border-left:3px solid var(--accent);padding:1rem 1.1rem .9rem}
.tile.ok{border-left-color:var(--ok)}.tile.warn{border-left-color:var(--warn)}
.tile-value{font-family:"IBM Plex Serif",serif;font-size:2rem;font-weight:700;
  line-height:1;margin-bottom:.4rem;font-variant-numeric:tabular-nums}
.tile.ok .tile-value{color:var(--ok)}.tile.warn .tile-value{color:var(--warn)}
.tile.blue .tile-value{color:var(--accent)}
.tile-label{font-family:"IBM Plex Mono",monospace;font-size:.68rem;
  letter-spacing:.09em;text-transform:uppercase;color:var(--text-3);line-height:1.4}

/* Sections */
section{margin-bottom:3rem}
section+section{padding-top:2.25rem;border-top:1px solid var(--border)}
.section-head{margin-bottom:1.25rem}
.section-head h2{font-family:"IBM Plex Serif",serif;font-size:1.1rem;
  font-weight:600;line-height:1.3}
.section-head p{font-size:.86rem;color:var(--text-2);margin-top:.3rem;max-width:68ch}
.section-label{font-family:"IBM Plex Mono",monospace;font-size:.65rem;
  letter-spacing:.12em;text-transform:uppercase;color:var(--text-3);margin-bottom:.3rem}

/* Tables */
.table-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:.875rem;font-variant-numeric:tabular-nums}
thead th{font-family:"IBM Plex Mono",monospace;font-size:.67rem;letter-spacing:.09em;
  text-transform:uppercase;color:var(--text-3);text-align:left;padding:.35rem .8rem;
  border-bottom:2px solid var(--border);white-space:nowrap;background:var(--surface)}
tbody tr td{padding:.55rem .8rem;border-bottom:1px solid var(--border);
  color:var(--text-2);background:var(--surface)}
tbody tr:hover td{background:var(--surface-2)}
tbody td:first-child{color:var(--text-1);font-weight:500}
tbody td.mono{font-family:"IBM Plex Mono",monospace;font-size:.83rem;color:var(--text-2)}
.status-ok{color:var(--ok);font-family:"IBM Plex Mono",monospace;font-size:.82rem;font-weight:500}
.status-warn{color:var(--warn);font-family:"IBM Plex Mono",monospace;font-size:.82rem;font-weight:500}
.cond-pos{color:var(--pos);font-weight:600}.cond-neg{color:var(--neg);font-weight:600}

/* Manipulation check cards */
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:.75rem}
@media(max-width:560px){.grid-2{grid-template-columns:1fr}}
.manip-card{background:var(--surface);border:1px solid var(--border);
  padding:1.25rem 1.4rem;display:flex;flex-direction:column;gap:.9rem}
.manip-card.pos-card{border-top:3px solid var(--pos)}
.manip-card.neg-card{border-top:3px solid var(--neg)}
.manip-cond{font-family:"IBM Plex Mono",monospace;font-size:.7rem;
  letter-spacing:.1em;text-transform:uppercase;font-weight:500}
.manip-cond.pos{color:var(--pos)}.manip-cond.neg{color:var(--neg)}
.manip-deltas{display:grid;grid-template-columns:1fr 1fr;gap:.75rem}
.manip-delta-item{display:flex;flex-direction:column;gap:.15rem}
.delta-val{font-family:"IBM Plex Serif",serif;font-size:2.2rem;font-weight:700;
  line-height:1;font-variant-numeric:tabular-nums}
.delta-val.pos-val{color:var(--pos)}.delta-val.neg-val{color:var(--neg)}
.delta-lbl{font-family:"IBM Plex Mono",monospace;font-size:.67rem;
  color:var(--text-3);letter-spacing:.07em;text-transform:uppercase}
.check-row{display:flex;align-items:center;gap:.5rem;font-size:.85rem;
  color:var(--text-2);padding-top:.5rem;border-top:1px solid var(--border)}
.check-row .check-icon{color:var(--ok);font-size:1rem}

/* Charts */
.chart-wrap{background:var(--surface);border:1px solid var(--border);
  padding:1.25rem 1.25rem 1rem;margin-top:1rem}
.chart-title{font-family:"IBM Plex Mono",monospace;font-size:.68rem;
  letter-spacing:.09em;text-transform:uppercase;color:var(--text-3);margin-bottom:.75rem}

/* Notes */
.note{padding:.85rem 1rem;font-size:.86rem;color:var(--text-2);
  border-left:3px solid var(--warn);background:var(--warn-bg);
  margin-top:1rem;line-height:1.55}
.note strong{color:var(--text-1)}
.note-ok{padding:.85rem 1rem;font-size:.86rem;color:var(--text-2);
  border-left:3px solid var(--ok);background:var(--ok-bg);
  margin-top:.75rem;line-height:1.55}

/* RT tiles */
.rt-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));
  gap:.5rem;margin-top:.75rem}
.rt-tile{background:var(--surface);border:1px solid var(--border);
  padding:.7rem .9rem;display:flex;justify-content:space-between;align-items:center}
.rt-name{font-family:"IBM Plex Mono",monospace;font-size:.72rem;color:var(--text-3)}
.rt-range{font-family:"IBM Plex Mono",monospace;font-size:.82rem;font-weight:500;
  color:var(--ok);font-variant-numeric:tabular-nums}

/* Placeholder */
.placeholder-box{background:var(--surface);border:1px dashed var(--border);
  padding:2.5rem 2rem;text-align:center;margin-bottom:2rem}
.placeholder-title{font-family:"IBM Plex Mono",monospace;font-size:.72rem;
  letter-spacing:.1em;text-transform:uppercase;color:var(--text-3);margin-bottom:.75rem}
.placeholder-msg{font-size:.9rem;color:var(--text-2);line-height:1.7;max-width:50ch;
  margin-inline:auto}
.placeholder-msg code{font-family:"IBM Plex Mono",monospace;font-size:.83em;
  color:var(--accent)}
</style>'

# ── 9. Assemble & write HTML ───────────────────────────────────────────────────
# Excluded participants are dropped from every section above, so say so up front —
# a QC report that quietly hides data is worse than one that shows too much.
excluded_banner <- local({
  ps  <- PARTICIPANT_STATUS
  esc <- function(x) gsub(">", "&gt;", gsub("<", "&lt;", gsub("&", "&amp;", x, fixed = TRUE), fixed = TRUE), fixed = TRUE)
  out <- ps[ps$status %in% c("test", "excluded"), , drop = FALSE]
  out <- out[order(out$status, out$participant_id), , drop = FALSE]
  out_html <- if (nrow(out) == 0) "" else paste0(
    '<br>Left out of both reports: ',
    paste0("<span class='mono'>", out$participant_id, "</span> (", out$status,
           ifelse(nzchar(out$reason), paste0(": ", esc(out$reason)), ""), ")", collapse = "; "),
    '. ')
  paste0(
    '<div class="note"><strong>',
    if (QC_MODE == "pilot") 'Pilot report:</strong> only the pilot participants (<span class="mono">' else
      'Main study:</strong> pilot participants (<span class="mono">',
    paste(sort(PILOT_PIDS), collapse = ", "),
    if (QC_MODE == "pilot") '</span>) are included; everyone else is in <code>biosignals2_qc.html</code>.' else
      '</span>) are left out; they are in <code>biosignals2_qc_pilot.html</code>.',
    out_html,
    '<br>Edit <code>analysis/participant_status.csv</code> to change who is pilot, test or excluded.',
    ' Files are untouched on disk.</div>')
})

html_out <- paste0(
  '<meta charset="utf-8">',
  '<title>Biosignals2 ', if (QC_MODE == "pilot") "Pilot QC" else "QC Dashboard", '</title>',
  css,
  '<div class="page">

  <header class="page-header">
    <div class="header-left">
      <span class="badge">Biosignals2</span>
      <h1>', if (QC_MODE == "pilot") "Pilot Data Quality" else "Data Quality Dashboard", '</h1>
    </div>
    <div class="header-meta">
      <strong>Generated</strong> <span id="gen-date"></span><br>
      <strong>Participants</strong> ', if (QC_MODE == "pilot") "Pilot" else "Main study", '
    </div>
  </header>

  <nav class="tab-bar">
    <button class="tab-btn active" data-tab="completeness">Completeness</button>
    <button class="tab-btn" data-tab="psychopy">PsychoPy</button>
    <button class="tab-btn" data-tab="ledalab">Ledalab (EDA)</button>
    <button class="tab-btn" data-tab="kubios">Kubios (HRV)</button>
    <button class="tab-btn" data-tab="biometrics">Webcam biometrics</button>
    <button class="tab-btn" data-tab="video">Video</button>
    <button class="tab-btn" data-tab="physiology">Raw physiology</button>
    <button class="tab-btn" data-tab="facereader">FaceReader</button>
    <button class="tab-btn" data-tab="questionnaires">Questionnaires</button>
  </nav>

  <div id="tab-completeness" class="tab-content active">', excluded_banner, completeness_html, '</div>
  <div id="tab-psychopy" class="tab-content">',          psychopy_html, '</div>
  <div id="tab-ledalab"  class="tab-content">',          ledalab_html,  '</div>
  <div id="tab-kubios"   class="tab-content">',          kubios_html,   '</div>
  <div id="tab-biometrics" class="tab-content">',        biometrics_html, '</div>
  <div id="tab-video"    class="tab-content">',          video_html,    '</div>
  <div id="tab-physiology" class="tab-content">',        physiology_html, '</div>
  <div id="tab-facereader" class="tab-content">',        facereader_html, '</div>
  <div id="tab-questionnaires" class="tab-content">',    questionnaire_html, '</div>

</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<script>
document.getElementById("gen-date").textContent =
  new Date().toLocaleDateString("en-GB", {day:"numeric",month:"long",year:"numeric"});

// Tabs
document.querySelectorAll(".tab-btn").forEach(function(btn) {
  btn.addEventListener("click", function() {
    document.querySelectorAll(".tab-btn").forEach(function(b) { b.classList.remove("active"); });
    document.querySelectorAll(".tab-content").forEach(function(c) { c.classList.remove("active"); });
    btn.classList.add("active");
    document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
  });
});
</script>'
)

writeLines(html_out, OUTPUT_PATH)
message("✓ Written to ", OUTPUT_PATH)
