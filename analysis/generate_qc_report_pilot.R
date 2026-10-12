# generate_qc_report_pilot.R
# QC report for the PILOT participants only (PILOT_PIDS in generate_qc_report.R).
# Writes biosignals2_qc_pilot.html to analysis/. The main-study report is generate_qc_report.R.
#
# Run from the analysis folder:  Rscript generate_qc_report_pilot.R
# or in RStudio: open this file and Source it.

this_file <- tryCatch(
  normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1])),
  error = function(e) NA_character_)
if (is.na(this_file) && requireNamespace("rstudioapi", quietly = TRUE) && rstudioapi::isAvailable())
  this_file <- rstudioapi::getSourceEditorContext()$path
script_dir <- if (is.na(this_file) || this_file == "") getwd() else dirname(this_file)

# Run in its own environment so QC_MODE = "pilot" does not linger and turn the next
# main-report run in the same R session into a pilot report.
local({
  QC_MODE <- "pilot"
  source(file.path(script_dir, "generate_qc_report.R"), local = TRUE)
})
