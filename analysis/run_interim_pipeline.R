# run_interim_pipeline.R  (Biosignals-2 analysis)
#
# Weekly rebuild of everything from data cleaning onwards (NOT preprocessing:
# Kubios, FaceReader, Ledalab and the video/event scripts are run by hand and
# their latest outputs are used as they are).
#
# Core (needed for the interim report; stops at the first failure):
#   01_data_cleaning.Rmd -> 04_questionnaire_analysis.Rmd -> 07_interim_summary.Rmd
# Separate analyses (a failure is logged and the run carries on):
#   02_ratings_analysis.Rmd, 03_facial_expression_analysis.Rmd, 05_analyse_ledalab_scr.Rmd
#   (06_build_ml_dataset.R is no longer run: not used - Carmen, 29 Oct. The shared files from 08
#   replace it; run it by hand if ever needed.)
# Shared datasets: 08_combine_timeseries.R (the files to share, in clean_combined_data/shareable). Runs only
#   if 01, 04 and 05 all succeeded in THIS run - its inputs come from them, so otherwise it would
#   share stale data. Skipped (with the reason) if not.
# Last: generate_qc_report.R, whose Completeness tab shows missing preprocessing.
#
# Each step runs in its own fresh R session. Started weekly by run_interim_pipeline.bat.

analysis_dir <- "C:/Users/carme/Documents/Biosignals-2/analysis"
source(file.path(dirname(analysis_dir), "config.R"))

core   <- c("01_data_cleaning.Rmd", "04_questionnaire_analysis.Rmd", "07_interim_summary.Rmd")
extras <- c("02_ratings_analysis.Rmd", "03_facial_expression_analysis.Rmd",
            "05_analyse_ledalab_scr.Rmd")
shared <- "08_combine_timeseries.R"
shared_needs <- c("01_data_cleaning.Rmd", "04_questionnaire_analysis.Rmd", "05_analyse_ledalab_scr.Rmd")
last   <- "generate_qc_report.R"

# ---- pandoc (knitting needs it; RStudio ships it, a scheduled run can't see it) ----
if (!nzchar(Sys.which("pandoc")) && !nzchar(Sys.getenv("RSTUDIO_PANDOC"))) {
  cands <- c("C:/Program Files/RStudio/resources/app/bin/quarto/bin/tools",
             "C:/Program Files/RStudio/resources/app/bin/quarto/bin/tools/x86_64",
             "C:/Program Files/RStudio/bin/quarto/bin/tools",
             "C:/Program Files/RStudio/bin/pandoc",
             file.path(Sys.getenv("LOCALAPPDATA"), "Programs/Quarto/bin/tools"),
             "C:/Program Files/Quarto/bin/tools")
  hit <- cands[file.exists(file.path(cands, "pandoc.exe"))][1]
  if (is.na(hit)) stop("pandoc not found. Set RSTUDIO_PANDOC to the folder containing pandoc.exe ",
                       "(in RStudio run: Sys.getenv('RSTUDIO_PANDOC')).")
  Sys.setenv(RSTUDIO_PANDOC = hit)   # inherited by every step below
}

rscript <- file.path(R.home("bin"), "Rscript.exe")
if (!file.exists(rscript)) rscript <- file.path(R.home("bin"), "Rscript")

run_step <- function(f) {
  path <- file.path(analysis_dir, f)
  if (!file.exists(path)) return(list(ok = FALSE, msg = "file not found", secs = 0))
  t0 <- Sys.time()
  args <- if (grepl("\\.Rmd$", f)) {
    c("-e", shQuote(sprintf("rmarkdown::render('%s', envir = new.env(), quiet = TRUE)", path)))
  } else shQuote(path)
  out <- suppressWarnings(system2(rscript, args, stdout = TRUE, stderr = TRUE))
  status <- attr(out, "status"); if (is.null(status)) status <- 0
  secs <- round(as.numeric(difftime(Sys.time(), t0, units = "secs")))
  if (status == 0) {
    cat(paste0("    | ", tail(out, 15)), sep = "\n")   # last lines of the step's output
  } else if (length(out)) {
    # Failed: show where the error starts (its message), then the last lines (where it stopped).
    # The traceback alone hides the message, e.g. which column didn't match.
    i <- grep("^\\s*(Error|Fehler)\\b|^\\s*! ", out)[1]
    if (!is.na(i)) {
      cat(paste0("    | ", out[i:min(length(out), i + 14)]), sep = "\n")
      if (i + 14 < length(out) - 10) cat("    | ...\n")
    }
    shown <- if (is.na(i)) integer(0) else i:min(length(out), i + 14)
    rest  <- setdiff(max(1, length(out) - 9):length(out), shown)
    if (length(rest)) cat(paste0("    | ", out[rest]), sep = "\n")
  }
  list(ok = status == 0, msg = if (status == 0) "ok" else paste("exit code", status), secs = secs)
}

results <- data.frame(step = character(), result = character(), secs = numeric())
log_step <- function(f, r) {
  cat(sprintf("  %-36s %-14s %5ds\n", f, r$msg, r$secs))
  results[nrow(results) + 1, ] <<- list(f, r$msg, r$secs)
}

cat("Interim pipeline started", format(Sys.time(), "%Y-%m-%d %H:%M"), "\n\nCore:\n")
core_ok <- TRUE
for (f in core) {
  cat("  ->", f, "\n"); r <- run_step(f); log_step(f, r)
  if (!r$ok) { core_ok <- FALSE; cat("\n  STOPPED: the interim report was NOT rebuilt because", f, "failed.\n"); break }
}

cat("\nSeparate analyses:\n")
for (f in extras) { cat("  ->", f, "\n"); log_step(f, run_step(f)) }

cat("\nShared datasets:\n")
needs_ok <- shared_needs %in% results$step[results$result == "ok"]
if (all(needs_ok)) {
  cat("  ->", shared, "\n"); log_step(shared, run_step(shared))
} else {
  cat("  ", shared, "NOT run - these steps did not succeed in this run:",
      paste(shared_needs[!needs_ok], collapse = ", "), "\n")
  cat("   The shared files in clean_combined_data/shareable were left as they were (not updated).\n")
  results[nrow(results) + 1, ] <- list(shared, "SKIPPED", 0)
}

cat("\nQC report:\n  ->", last, "\n"); log_step(last, run_step(last))

cat("\nSummary:\n"); print(results, row.names = FALSE)
failed <- results$result != "ok" & results$result != "SKIPPED"
cat("\nFinished", format(Sys.time(), "%H:%M"), "-",
    if (!core_ok) "INTERIM REPORT NOT REBUILT" else if (any(failed)) "interim report rebuilt; some separate steps failed" else "all ok", "\n")
if (any(results$step == shared & results$result != "ok"))
  cat("SHARED DATASETS NOT UPDATED (08", results$result[results$step == shared], ")\n")
quit(save = "no", status = if (core_ok) 0 else 1)
