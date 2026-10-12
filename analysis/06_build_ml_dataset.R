# 05_build_ml_dataset.R
# ======================
# Merges EDA (SCR), HRV, and self-report ratings into a single ML-ready dataset.
#
# Inputs (from COMBINED_DATA_DIR defined in config.R):
#   biosignals2_eda.csv                           — SCR/EDA summary (from 04_analyse_ledalab_scr.Rmd)
#   biosignals2_KubiosHRVresults.csv              — Kubios HRV batch results (all segments)
#   psychopy/biosignals2_selfreport_ratings.csv   — Self-report ratings (block + stimulus level)
#
# Output (saved to COMBINED_DATA_DIR):
#   biosignals2_ml_long.csv  — one row per participant × condition (5 rows per participant)
#   biosignals2_ml_wide.csv  — one row per participant (conditions spread into column prefixes)
#
# Usage:
#   source("05_build_ml_dataset.R")  from the analysis/ directory
#   or: Rscript analysis/05_build_ml_dataset.R

# ── CONFIGURATION ─────────────────────────────────────────────────────────────

source(here::here("config.R"))

# ── Participant selection ── edit analysis/participant_status.csv, not this block.
# Main-study participants only by default; set TRUE to also analyse the pilots.
INCLUDE_PILOTS <- FALSE
analysis_dir <- local({ d <- dirname(normalizePath(here::here("config.R"))); if (basename(d) == "analysis") d else file.path(d, "analysis") })
PARTICIPANT_STATUS_PATH <- file.path(analysis_dir, "participant_status.csv")
source(file.path(analysis_dir, "participant_status.R"), local = TRUE)

# Toggle output format: "long", "wide", or "both"
OUTPUT_FORMAT <- "both"

# Condition levels — must match across all three datasets after remapping
CONDITION_LEVELS <- c("baseline", "neg_induction", "neg_recovery",
                      "pos_induction", "pos_recovery")

# ── LIBRARIES ─────────────────────────────────────────────────────────────────

library(here)
library(dplyr)
library(tidyr)
library(stringr)
library(readr)
library(purrr)

# ── HELPERS ───────────────────────────────────────────────────────────────────

clean_colname <- function(x) {
  x |>
    str_replace_all("[^a-zA-Z0-9]+", "_") |>
    str_remove("_$") |>
    str_remove("^_")
}

# ── 1. LOAD EDA (SCR) ─────────────────────────────────────────────────────────

cat("Loading EDA data...\n")

eda_path <- file.path(COMBINED_DATA_DIR, "biosignals2_eda.csv")
stopifnot(file.exists(eda_path))

eda <- read_csv(eda_path, show_col_types = FALSE) |>
  mutate(
    pid       = as.character(pid),
    condition = factor(condition, levels = CONDITION_LEVELS)
  ) |>
  select(-any_of(c("Event.nid", "Event.Nr", "Event.Name")))  # drop Ledalab bookkeeping cols

cat("  EDA:", nrow(eda), "rows,", n_distinct(eda$pid), "participants\n")

# ── 2. LOAD HRV ───────────────────────────────────────────────────────────────

cat("Loading HRV data...\n")

hrv_path <- file.path(COMBINED_DATA_DIR, "biosignals2_KubiosHRVresults.csv")
stopifnot(file.exists(hrv_path))

# Kubios batch file has 2 header lines before the column names row
hrv_raw <- read_csv(hrv_path, skip = 2, show_col_types = FALSE)

# Segment → condition mapping (S1-S5 order from Kubios Samples output)
seg_to_condition <- c(
  S1 = "baseline",
  S2 = "neg_induction",
  S3 = "neg_recovery",
  S4 = "pos_induction",
  S5 = "pos_recovery"
)

hrv <- hrv_raw |>
  # Extract participant ID from filename (e.g. "g2313_physiology_trimmed.acq" → "g2313")
  mutate(pid = str_extract(FileName, "^[^_]+")) |>
  select(pid, starts_with("S1_"), starts_with("S2_"), starts_with("S3_"),
         starts_with("S4_"), starts_with("S5_")) |>
  # Pivot to long: one row per pid × segment × metric
  pivot_longer(
    cols      = -pid,
    names_to  = c("segment", "metric"),
    names_pattern = "^(S[1-5])_(.*)"
  ) |>
  mutate(
    condition = factor(seg_to_condition[segment], levels = CONDITION_LEVELS),
    # Clean metric names for use as column names
    metric    = paste0("HRV_", clean_colname(metric))
  ) |>
  select(-segment) |>
  # Suppress conversion warnings from NaN/NaT strings
  mutate(value = suppressWarnings(as.numeric(value))) |>
  # Pivot wide: one row per pid × condition, all HRV metrics as columns
  pivot_wider(names_from = metric, values_from = value)

cat("  HRV:", nrow(hrv), "rows,", n_distinct(hrv$pid), "participants,",
    ncol(hrv) - 2, "HRV features\n")

# ── 3. LOAD RATINGS ───────────────────────────────────────────────────────────

cat("Loading self-report ratings...\n")

ratings_path <- file.path(COMBINED_DATA_DIR, "psychopy", "biosignals2_selfreport_ratings.csv")
stopifnot(file.exists(ratings_path))

# Remap condition names to match HRV/EDA convention
condition_remap <- c(
  "baseline"                        = "baseline",
  "negative_induction"              = "neg_induction",
  "post_negative_induction_recovery"= "neg_recovery",
  "positive_induction"              = "pos_induction",
  "post_positive_induction_recovery"= "pos_recovery"
)

ratings_raw <- read_csv(ratings_path, show_col_types = FALSE) |>
  mutate(condition = condition_remap[condition])

# Block-level ratings: block_end_valence / block_end_arousal.
# Within each pid × condition, these values are the same across all rows
# (they are collected once at the end of the block and repeated).
# Also grab conditionOrder (consistent per participant).
block_ratings <- ratings_raw |>
  group_by(participant_id, condition) |>
  summarise(
    conditionOrder      = first(conditionOrder),
    block_end_valence   = first(na.omit(block_end_valence)),
    block_end_arousal   = first(na.omit(block_end_arousal)),
    .groups = "drop"
  )

# Stimulus-level ratings: mean per condition (only present for induction blocks).
# NA for baseline and recovery conditions.
stim_ratings <- ratings_raw |>
  group_by(participant_id, condition) |>
  summarise(
    stim_valence_mean   = mean(stim_valence,          na.rm = TRUE),
    stim_arousal_mean   = mean(stim_arousal,          na.rm = TRUE),
    stim_approach_mean  = mean(stim_approach,         na.rm = TRUE),
    stim_intensity_mean = mean(stim_emotion_intensity, na.rm = TRUE),
    .groups = "drop"
  ) |>
  # mean of all-NA returns NaN — convert to NA
  mutate(across(starts_with("stim_"), ~ ifelse(is.nan(.x), NA_real_, .x)))

ratings <- block_ratings |>
  left_join(stim_ratings, by = c("participant_id", "condition")) |>
  rename(pid = participant_id) |>
  mutate(condition = factor(condition, levels = CONDITION_LEVELS))

cat("  Ratings:", nrow(ratings), "rows,", n_distinct(ratings$pid), "participants\n")

# ── 4. MERGE ──────────────────────────────────────────────────────────────────

cat("Merging datasets...\n")

# Main-study participants only (plus pilots if INCLUDE_PILOTS) — see participant_status.csv
dropped <- participants_dropped(unique(c(eda$pid, hrv$pid, ratings$pid)), INCLUDE_PILOTS)
if (nrow(dropped) > 0) {
  cat("  Left out (", nrow(dropped), "), INCLUDE_PILOTS = ", INCLUDE_PILOTS, ":\n", sep = "")
  print(dropped, row.names = FALSE)
}
eda     <- eda     |> filter(participant_keep(pid, INCLUDE_PILOTS))
hrv     <- hrv     |> filter(participant_keep(pid, INCLUDE_PILOTS))
ratings <- ratings |> filter(participant_keep(pid, INCLUDE_PILOTS))

ml_long <- eda |>
  full_join(hrv,     by = c("pid", "condition")) |>
  full_join(ratings, by = c("pid", "condition")) |>
  arrange(pid, condition)

# Report any participants missing from one or more sources
pids_eda     <- unique(eda$pid)
pids_hrv     <- unique(hrv$pid)
pids_ratings <- unique(ratings$pid)
pids_all     <- union(union(pids_eda, pids_hrv), pids_ratings)

missing <- tibble(
  pid          = pids_all,
  has_eda      = pid %in% pids_eda,
  has_hrv      = pid %in% pids_hrv,
  has_ratings  = pid %in% pids_ratings
) |>
  filter(!has_eda | !has_hrv | !has_ratings)

if (nrow(missing) > 0) {
  cat("  Warning: data missing for some participants:\n")
  print(missing)
} else {
  cat("  All participants present in all three datasets.\n")
}

cat("  Long dataset:", nrow(ml_long), "rows ×", ncol(ml_long), "columns\n")

# ── 5. WIDE FORMAT ────────────────────────────────────────────────────────────

if (OUTPUT_FORMAT %in% c("wide", "both")) {
  cat("Building wide format...\n")

  # Columns that should NOT be spread across conditions
  id_cols <- c("pid", "conditionOrder")

  ml_wide <- ml_long |>
    select(-any_of(setdiff(id_cols, "pid"))) |>  # keep conditionOrder only once
    pivot_wider(
      id_cols      = pid,
      names_from   = condition,
      values_from  = setdiff(names(ml_long), c("pid", "condition", "conditionOrder")),
      names_glue   = "{condition}__{.value}"
    ) |>
    left_join(
      ratings |> select(pid, conditionOrder) |> distinct(),
      by = "pid"
    )

  cat("  Wide dataset:", nrow(ml_wide), "rows ×", ncol(ml_wide), "columns\n")
}

# ── 6. SAVE ───────────────────────────────────────────────────────────────────

if (OUTPUT_FORMAT %in% c("long", "both")) {
  out_long <- file.path(COMBINED_DATA_DIR, "biosignals2_ml_long.csv")
  write_csv(ml_long, out_long)
  cat("Saved:", out_long, "\n")
}

if (OUTPUT_FORMAT %in% c("wide", "both")) {
  out_wide <- file.path(COMBINED_DATA_DIR, "biosignals2_ml_wide.csv")
  write_csv(ml_wide, out_wide)
  cat("Saved:", out_wide, "\n")
}

cat("Done.\n")
