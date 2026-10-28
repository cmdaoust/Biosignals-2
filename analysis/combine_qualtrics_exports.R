# combine_qualtrics_exports.R  (Biosignals-2 analysis)
#
# The automated Qualtrics SFTP exports only contain NEW responses since the
# previous export (e.g. Demographics_2026-10-28_060312425.csv has just the 3
# people from 27 Oct). This script stacks every automated export into one file
# per survey, so the rest of the pipeline sees all participants:
#
#   raw_questionnaire/Demographics_<date>_<time>.csv  ->  raw_questionnaire/combined/Demographics_combined.csv
#   raw_questionnaire/Follow-up_<date>_<time>.csv     ->  raw_questionnaire/combined/Follow-up_combined.csv
#
# - Only files named <Survey>_YYYY-MM-DD_<digits>.csv (the automated exports)
#   are used. Manual exports (old_exports/, other names) are ignored.
# - All files must have the same 3 Qualtrics header rows as the newest export.
#   A file that doesn't (e.g. exported with choice text instead of values, or
#   re-saved in Excel) is skipped and listed, so formats are never mixed.
# - A response (ResponseId) in several exports is kept once, from the newest file.
# - The combined file is only replaced if it has at least as many responses as
#   before, so a missing/moved raw file can't silently drop participants.
#
# QUESTIONNAIRE_DIR in config.R points at raw_questionnaire/combined, so
# questionniare_followup_dates.R, send_followup_emails.R, 04_questionnaire_analysis.Rmd
# and the QC report all read the combined files.
#
# Run: Rscript "C:/Users/carme/Documents/Biosignals-2/analysis/combine_qualtrics_exports.R"
# Scheduled: run_combine_questionnaires.bat (Windows Task Scheduler, weekday mornings).
# Base R only (no packages needed).

SURVEYS <- c("Demographics", "Follow-up")

# ------------------------------------------------------------------------------

analysis_dir <- "C:/Users/carme/Documents/Biosignals-2/analysis"
config_candidates <- file.path(c(analysis_dir, dirname(analysis_dir)), "config.R")
config_file <- config_candidates[file.exists(config_candidates)][1]
if (is.na(config_file)) stop("config.R not found in: ", paste(dirname(config_candidates), collapse = " or "))
source(config_file)

in_dir  <- RAW_QUESTIONNAIRE_DIR
out_dir <- file.path(RAW_QUESTIONNAIRE_DIR, "combined")
if (!dir.exists(in_dir)) stop("RAW_QUESTIONNAIRE_DIR not found: ", in_dir)
dir.create(out_dir, showWarnings = FALSE)

cat("=== Combine Qualtrics exports:", format(Sys.time(), "%Y-%m-%d %H:%M"), "===\n")

read_qualtrics <- function(path) {
  # Read as UTF-8 without re-encoding (works whatever the R session's locale is).
  m <- read.csv(path, header = FALSE, colClasses = "character", na.strings = character(0),
                check.names = FALSE, encoding = "UTF-8", strip.white = FALSE)
  m[1, 1] <- sub("^\ufeff", "", m[1, 1])                            # drop the byte-order mark
  if (nrow(m) < 3) stop(basename(path), ": fewer than 3 rows - not a Qualtrics export?")
  list(header = m[1:3, , drop = FALSE], data = m[-(1:3), , drop = FALSE])
}

count_responses <- function(path) {
  if (!file.exists(path)) return(0L)
  nrow(read_qualtrics(path)$data)
}

problems <- character(0)

for (survey in SURVEYS) {
  cat("\n--", survey, "--\n")
  pattern <- paste0("^", gsub("-", "[-_ ]?", survey), "_[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]+\\.csv$")
  files <- list.files(in_dir, pattern = pattern, full.names = TRUE, ignore.case = TRUE)
  if (length(files) == 0) {
    problems <- c(problems, paste0(survey, ": no automated exports found"))
    cat("No exports matching", pattern, "in", in_dir, "\n")
    next
  }
  stamp <- regmatches(basename(files), regexpr("[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]+", basename(files)))
  files <- files[order(stamp, decreasing = TRUE)]      # newest first

  parts <- lapply(files, read_qualtrics)
  ref <- parts[[1]]$header
  same_format <- vapply(parts, function(p) ncol(p$header) == ncol(ref) && all(p$header == ref), logical(1))
  if (any(!same_format)) {
    cat("SKIPPED (header rows differ from the newest export - different export format?):\n",
        paste0("  ", basename(files[!same_format]), collapse = "\n"), "\n", sep = "")
    problems <- c(problems, paste0(survey, ": skipped ", sum(!same_format), " file(s) with a different format"))
  }
  parts <- parts[same_format]
  used  <- files[same_format]

  data <- do.call(rbind, lapply(seq_along(parts), function(i) {
    d <- parts[[i]]$data
    d$.file <- basename(used[i])
    d
  }))
  names(data)[seq_len(ncol(ref))] <- as.character(ref[1, ])

  n_rows <- nrow(data)
  if ("ResponseId" %in% names(data)) {
    has_id <- nzchar(data$ResponseId)
    data <- data[!(has_id & duplicated(data$ResponseId)), , drop = FALSE]  # newest file first, so newest kept
  } else {
    problems <- c(problems, paste0(survey, ": no ResponseId column - duplicates not removed"))
  }
  if ("StartDate" %in% names(data)) data <- data[order(data$StartDate), , drop = FALSE]

  per_file <- table(factor(data$.file, levels = basename(used)))
  cat(sprintf("  %-45s %3d kept\n", names(per_file), as.integer(per_file)), sep = "")
  cat(n_rows, "rows read,", nrow(data), "unique responses.\n")
  data$.file <- NULL

  out_file <- file.path(out_dir, paste0(survey, "_combined.csv"))
  n_before <- count_responses(out_file)
  if (nrow(data) < n_before) {
    problems <- c(problems, paste0(survey, ": NOT updated - would drop from ", n_before, " to ",
                                   nrow(data), " responses (raw export missing or moved?)"))
    cat("NOT UPDATED:", out_file, "has", n_before, "responses; the new combination has only",
        nrow(data), ". Check raw_questionnaire before re-running.\n")
    next
  }

  out <- rbind(ref, setNames(data, names(ref)))
  tmp <- file.path(out_dir, paste0(".", survey, "_combined.tmp"))
  csv_lines <- apply(out, 1, function(x) paste0('"', gsub('"', '""', x, fixed = TRUE), '"', collapse = ","))
  con <- file(tmp, open = "wb")
  writeLines(enc2utf8(csv_lines), con, sep = "\r\n", useBytes = TRUE)
  close(con)
  if (!file.copy(tmp, out_file, overwrite = TRUE)) stop("Could not write ", out_file, " (open in Excel?)")
  unlink(tmp)
  cat("Saved", nrow(data), "responses to", out_file, if (n_before) paste0("(was ", n_before, ")"), "\n")
}

if (length(problems)) {
  cat("\nCHECK:\n", paste0("  - ", problems, collapse = "\n"), "\n", sep = "")
}
cat("\nDone.\n")
# Exit code 1 (shown in the run log) if a combined file could not be updated.
if (!interactive()) quit(save = "no", status = if (any(grepl("NOT updated|no automated", problems))) 1 else 0)
