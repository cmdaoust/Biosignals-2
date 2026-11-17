# check_kubios_missing_samples.R
# Flags participants with missing Kubios samples (blocks) in a Kubios batch export
# (KubiosHRVresults.csv). Default input: FACEREADER_RESULTS_DIR/KubiosHRVresults.csv
# (Box 3_Data/facereader). Reads the file the same way as 08_combine_timeseries.R
# (read_kubios_batch_blocks): header = the line starting with FileName, lines split by hand,
# participant = FileName basename up to the first _ or ., S1..S5 = BLOCK_ORDER, last row wins.
#
# A participant is flagged when:
#   NOT IN FILE  - in the reference file (ECG batch export, 3_Data/kubios/KubiosHRVresults.csv)
#                  but has no row in this file
#   MISSING      - a block (S1..S5) has no values at all (every measure empty / NaN)
#   PARTIAL      - a block has some measures empty that are filled for other participants
#                  (columns empty for EVERYONE, e.g. ECG morphology in the FaceReader file, are ignored)
#   NO COLUMNS   - the file has no S<i>_ columns for a block (affects everyone)
# Duplicate rows for a participant are reported as a note (the last row is the one checked, as in 08).
#
# Usage (from the repo, any folder):
#   Rscript analysis/kubios/check_kubios_missing_samples.R                  # FaceReader file
#   Rscript analysis/kubios/check_kubios_missing_samples.R path/to/KubiosHRVresults.csv
#   options: --reference <file>   compare against another batch file for "NOT IN FILE"
#            --no-reference       skip the "NOT IN FILE" check
#            --include-pilots     also check pilots (test/excluded sessions are always left out)
# Output: console summary + <input name>_missing_samples.csv next to the input (flagged rows only;
# real IDs, so it stays on Box with the input). Writes nothing else.

BLOCK_ORDER  <- c("baseline", "negative_induction", "negative_recovery", "positive_induction", "positive_recovery")
EMPTY_VALUES <- c("", "na", "nan", "n/a", "-", "inf", "-inf")

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
root <- find_project_root()
source(file.path(root, "config.R"))
PARTICIPANT_STATUS_PATH <- get0("PARTICIPANT_STATUS_PATH", ifnotfound = file.path(SERVER_ROOT, "participant_status.csv"))
source(file.path(root, "analysis", "participant_status.R"), local = TRUE)

# ── Arguments ────────────────────────────────────────────────────────────────
args <- commandArgs(trailingOnly = TRUE)
include_pilots <- "--include-pilots" %in% args
no_reference   <- "--no-reference" %in% args
ref_i <- match("--reference", args)
ref_arg <- if (!is.na(ref_i)) args[ref_i + 1] else NA_character_
pos <- args[!startsWith(args, "--") & !(seq_along(args) %in% (ref_i + 1))]

ecg_file <- file.path(KUBIOS_RESULTS_DIR, "KubiosHRVresults.csv")
in_file  <- if (length(pos)) pos[1] else file.path(FACEREADER_RESULTS_DIR, "KubiosHRVresults.csv")
same_file <- function(a, b) normalizePath(a, winslash = "/", mustWork = FALSE) == normalizePath(b, winslash = "/", mustWork = FALSE)
is_ecg_input <- same_file(in_file, ecg_file)
ref_file <- if (no_reference) NA_character_ else if (!is.na(ref_arg)) ref_arg else if (!is_ecg_input) ecg_file else NA_character_
if (!file.exists(in_file)) stop("Input not found: ", in_file)

# ── Reader (same parsing as 08) ──────────────────────────────────────────────
read_batch <- function(path, other_stream_rx) {
  L <- readLines(path, warn = FALSE, encoding = "UTF-8"); L[1] <- sub("^﻿", "", L[1])
  split <- function(l) trimws(gsub('^"|"$', "", strsplit(l, ",", fixed = TRUE)[[1]]))
  h <- which(startsWith(sub('^"', "", L), "FileName"))[1]
  if (is.na(h)) stop(path, ": no header line starting with FileName")
  hdr <- split(L[h]); while (length(hdr) && !nzchar(hdr[length(hdr)])) hdr <- hdr[-length(hdr)]
  rows <- lapply(L[-seq_len(h)], function(l) {
    x <- split(l)
    if (length(x) > length(hdr) && any(nzchar(x[-seq_along(hdr)])))
      message(sprintf("  WARNING: row '%s' has values beyond the last header column - check for a column shift", x[1]))
    length(x) <- length(hdr); x[is.na(x)] <- ""; x })
  rows  <- rows[vapply(rows, function(x) nzchar(x[1]), TRUE)]
  fname <- basename(gsub("\\\\", "/", vapply(rows, `[`, "", 1)))
  other <- grepl(other_stream_rx, fname, ignore.case = TRUE)
  if (any(other)) cat(sprintf("  %d row(s) from the other stream left out: %s\n", sum(other), paste(fname[other], collapse = ", ")))
  list(hdr = hdr, rows = rows[!other], fname = fname[!other],
       pid = tolower(sub("[_.].*$", "", fname[!other])))
}
other_rx <- function(path) if (same_file(path, ecg_file)) "facereader|heart beat log|webcam" else "physiology|webcam"
is_empty <- function(v) tolower(trimws(v)) %in% EMPTY_VALUES

cat(sprintf("Checking %s\n", in_file))
b <- read_batch(in_file, other_rx(in_file))
keep <- participant_keep(b$pid, include_pilots = include_pilots)
if (any(!keep)) cat(sprintf("  left out (pilot/test/excluded): %s\n", paste(unique(b$pid[!keep]), collapse = ", ")))
pids <- unique(b$pid[keep])

# columns per block; measures empty for everyone are ignored for PARTIAL
cols <- lapply(seq_along(BLOCK_ORDER), function(i) which(startsWith(b$hdr, paste0("S", i, "_"))))
last_row <- lapply(setNames(pids, pids), function(p) b$rows[[max(which(b$pid == p))]])
used_cols <- lapply(cols, function(k) {
  if (!length(k) || !length(last_row)) return(k)
  filled <- vapply(k, function(j) any(!vapply(last_row, function(x) is_empty(x[j]), TRUE)), TRUE)
  k[filled]
})

flags <- list()
add <- function(p, block, sample, status, n_empty = NA_integer_, n_measures = NA_integer_, detail = "")
  flags[[length(flags) + 1]] <<- data.frame(participant_id = p, block = block, sample = sample, status = status,
                                           n_empty = n_empty, n_measures = n_measures, detail = detail,
                                           stringsAsFactors = FALSE)

for (i in seq_along(BLOCK_ORDER)) if (!length(cols[[i]]))
  add("(all)", BLOCK_ORDER[i], paste0("S", i), "NO COLUMNS", detail = sprintf("no S%d_ columns in the header", i))

for (p in pids) {
  r <- which(b$pid == p); x <- last_row[[p]]
  if (length(r) > 1) add(p, NA, NA, "note: duplicate rows",
                         detail = sprintf("%d rows (%s); the last one was checked", length(r), paste(b$fname[r], collapse = "; ")))
  for (i in seq_along(BLOCK_ORDER)) {
    k <- used_cols[[i]]; if (!length(k)) next
    e <- is_empty(x[k])
    if (all(e)) add(p, BLOCK_ORDER[i], paste0("S", i), "MISSING", sum(e), length(k))
    else if (any(e)) add(p, BLOCK_ORDER[i], paste0("S", i), "PARTIAL", sum(e), length(k),
                         paste(sub("^S\\d+_", "", b$hdr[k][e]), collapse = "; "))
  }
}

if (!is.na(ref_file)) {
  if (!file.exists(ref_file)) {
    cat(sprintf("  reference %s not found - NOT IN FILE check skipped\n", ref_file))
  } else {
    rb <- read_batch(ref_file, other_rx(ref_file))
    ref_ids <- unique(rb$pid[participant_keep(rb$pid, include_pilots = include_pilots)])
    for (p in sort(setdiff(ref_ids, pids)))
      add(p, NA, NA, "NOT IN FILE", detail = sprintf("in %s but no row here", basename(dirname(ref_file))))
  }
}

# ── Report ───────────────────────────────────────────────────────────────────
out <- if (length(flags)) do.call(rbind, flags) else
  data.frame(participant_id = character(), block = character(), sample = character(), status = character(),
             n_empty = integer(), n_measures = integer(), detail = character())
real <- out[!startsWith(out$status, "note"), , drop = FALSE]
flagged <- sort(unique(real$participant_id[real$participant_id != "(all)"]))

cat(sprintf("\n%d participant(s) checked, %d flagged\n", length(pids), length(flagged)))
for (p in c(if ("(all)" %in% out$participant_id) "(all)", sort(unique(out$participant_id[out$participant_id != "(all)"])))) {
  d <- out[out$participant_id == p, , drop = FALSE]
  cat(sprintf("  %s\n", p))
  for (j in seq_len(nrow(d))) cat(sprintf("    %-20s %-19s %s\n", d$status[j],
      ifelse(is.na(d$block[j]), "", sprintf("%s (%s)", d$sample[j], d$block[j])),
      if (d$status[j] %in% c("MISSING", "PARTIAL")) sprintf("%d/%d empty%s", d$n_empty[j], d$n_measures[j],
          if (nzchar(d$detail[j])) paste0(": ", d$detail[j]) else "") else d$detail[j]))
}
if (!nrow(out)) cat("  nothing missing\n")

out_file <- file.path(dirname(in_file), sub("\\.csv$", "_missing_samples.csv", basename(in_file), ignore.case = TRUE))
utils::write.csv(out, out_file, row.names = FALSE, na = "")
cat(sprintf("\nWritten: %s\n", out_file))
