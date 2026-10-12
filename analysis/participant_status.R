# participant_status.R
# Reads analysis/participant_status.csv: the ONE place to list participants who are
# not normal main-study participants. Source this file from any R script or Rmd:
#
#   PARTICIPANT_STATUS_PATH <- file.path(analysis_dir, "participant_status.csv")  # optional
#   source(file.path(analysis_dir, "participant_status.R"), local = TRUE)
#   pilot_ids()      # pilot participants
#   excluded_ids()   # test sessions + rejected participants (leave out of everything)
#   main_filter(df)  # keep main-study rows only (drops pilot, test, excluded)
#   participant_keep(ids, include_pilots = FALSE)      # TRUE for IDs to analyse
#   participants_dropped(ids, include_pilots = FALSE)  # who was left out, and why
#
# participant_status.csv columns:
#   participant_id  ID as used in file names (matching ignores case and spaces)
#   status          pilot    - pilot participant (pilot QC report only)
#                   test     - test / development session, not a participant
#                   excluded - main-study participant whose data is rejected (reason required)
#   reason          why (required for excluded; optional otherwise)
#   date_added      when the row was added (YYYY-MM-DD)
# Anyone NOT in the file is a main-study participant, so new participants need no row.
#
# Edit it in RStudio or a text editor, not Excel: Excel turns IDs like 001 into 1.

PARTICIPANT_STATUS_VALUES <- c("pilot", "test", "excluded")

# Set PARTICIPANT_STATUS_PATH before sourcing to point at the file; otherwise it is
# looked for in the working directory and in analysis/ under it.
if (!exists("PARTICIPANT_STATUS_PATH", inherits = TRUE)) {
  local({
    cands <- c(file.path(getwd(), "participant_status.csv"),
               file.path(getwd(), "analysis", "participant_status.csv"))
    hit <- cands[file.exists(cands)]
    if (length(hit) == 0) stop("participant_status.csv not found (looked in: ",
                               paste(cands, collapse = "; "), "). Set PARTICIPANT_STATUS_PATH first.")
    PARTICIPANT_STATUS_PATH <<- hit[1]
  })
}

norm_participant_id <- function(x) toupper(gsub("\\s+", "", as.character(x)))

read_participant_status <- function(path = PARTICIPANT_STATUS_PATH) {
  ps <- utils::read.csv(path, colClasses = "character", na.strings = character(0),
                        strip.white = TRUE, check.names = FALSE, encoding = "UTF-8")
  need <- c("participant_id", "status", "reason")
  miss <- setdiff(need, names(ps))
  if (length(miss)) stop("participant_status.csv is missing column(s): ", paste(miss, collapse = ", "))
  ps <- ps[nzchar(ps$participant_id), , drop = FALSE]
  ps$participant_id <- norm_participant_id(ps$participant_id)
  ps$status <- tolower(trimws(ps$status))

  bad <- ps$participant_id[!ps$status %in% PARTICIPANT_STATUS_VALUES]
  if (length(bad)) stop("participant_status.csv: unknown status for ", paste(bad, collapse = ", "),
                        ". Use one of: ", paste(PARTICIPANT_STATUS_VALUES, collapse = ", "))
  dup <- unique(ps$participant_id[duplicated(ps$participant_id)])
  if (length(dup)) stop("participant_status.csv: listed more than once: ", paste(dup, collapse = ", "))
  noreason <- ps$participant_id[ps$status == "excluded" & !nzchar(ps$reason)]
  if (length(noreason)) stop("participant_status.csv: excluded without a reason: ",
                             paste(noreason, collapse = ", "))
  ps
}

PARTICIPANT_STATUS <- read_participant_status()

pilot_ids    <- function() PARTICIPANT_STATUS$participant_id[PARTICIPANT_STATUS$status == "pilot"]
test_ids     <- function() PARTICIPANT_STATUS$participant_id[PARTICIPANT_STATUS$status == "test"]
rejected_ids <- function() PARTICIPANT_STATUS$participant_id[PARTICIPANT_STATUS$status == "excluded"]
excluded_ids <- function() c(test_ids(), rejected_ids())

participant_status_of <- function(x) {
  s <- PARTICIPANT_STATUS$status[match(norm_participant_id(x), PARTICIPANT_STATUS$participant_id)]
  ifelse(is.na(s), "main", s)
}

# Keep main-study rows only.
main_filter <- function(df, col = "participant_id") df[participant_status_of(df[[col]]) == "main", , drop = FALSE]

# ── For analysis scripts ──────────────────────────────────────────────────────
# TRUE for IDs to analyse: main-study participants, plus pilots if include_pilots = TRUE.
participant_keep <- function(x, include_pilots = FALSE) {
  s <- participant_status_of(x)
  s == "main" | (include_pilots & s == "pilot")
}

# The IDs in x that participant_keep() drops, with status and reason (one row each).
participants_dropped <- function(x, include_pilots = FALSE) {
  ids <- unique(as.character(x[!is.na(x)]))
  ids <- ids[!participant_keep(ids, include_pilots)]
  i   <- match(norm_participant_id(ids), PARTICIPANT_STATUS$participant_id)
  out <- data.frame(participant_id = ids, status = PARTICIPANT_STATUS$status[i],
                    reason = PARTICIPANT_STATUS$reason[i], stringsAsFactors = FALSE)
  out[order(out$status, out$participant_id), , drop = FALSE]
}
