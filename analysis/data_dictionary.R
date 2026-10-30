# =============================================================================
# data_dictionary.R - descriptions for the shared files written by 08_combine_timeseries.R
# =============================================================================
# 08 sources this file and, after writing the data files, writes two files next to them:
#   biosignals2_README.md            one section per file: what it is, one row per, source,
#                                    clock, processing, caveats + study-wide notes
#   biosignals2_data_dictionary.csv  one row per file x column: type, missing, range / values,
#                                    description
# Edit the text here (not in 08). A column with no description is written as
# "NOT DESCRIBED YET" and listed in 08's console, so new columns can't slip through unexplained.
# Base R only.

BLOCK_LEVELS <- c("baseline", "negative_induction", "negative_recovery",
                  "positive_induction", "positive_recovery")

# Any block label used anywhere in the pipeline -> one of BLOCK_LEVELS (NA if not recognised).
# e.g. "Baseline", "neg_induction(2)", "post_negative_induction_recovery", "Negative Recovery".
canon_block <- function(x) {
  y <- tolower(gsub("[ -]+", "_", trimws(sub("\\(\\d+\\)\\s*$", "", trimws(as.character(x))))))
  neg <- grepl("^neg|_neg|negative", y); pos <- grepl("^pos|_pos|positive", y)
  rec <- grepl("recov|reconv", y);       ind <- grepl("induc", y)
  out <- ifelse(grepl("baseline", y), "baseline",
         ifelse(neg & rec, "negative_recovery", ifelse(pos & rec, "positive_recovery",
         ifelse(neg & ind, "negative_induction", ifelse(pos & ind, "positive_induction", NA_character_)))))
  out[is.na(x) | !nzchar(trimws(as.character(x)))] <- NA_character_
  out
}

# ── Study-wide notes (top of the README) ─────────────────────────────────────
README_GENERAL <- c(
  "## Read this first",
  "",
  "- **Participants.** Main-study participants only: pilots, test sessions and excluded participants are left out. Only participants with data in every file are included (the same people in every file).",
  "- **participant_id** is a pseudonymous code (P01, P02, ...). It is the same code for the same person in every file and every data release, and it is never reused. Real IDs are not in these files.",
  paste0("- **block** is one of: ", paste(BLOCK_LEVELS, collapse = ", "),
         ". Every file uses these names. Every participant did the blocks in this order: the negative induction always came before the positive one (not counterbalanced). `block` is empty for rows outside the five blocks (e.g. rating screens, instructions)."),
  "- **Keys.** Files join on `participant_id` (questionnaires) or `participant_id` + `block` (everything else). The time-series files are NOT on one clock - see **Clocks**.",
  "",
  "## Clocks",
  "",
  "- **BIOPAC clock** - seconds from the start of the trimmed BIOPAC recording (`*_physiology_trimmed.acq`). Used by the ECG Kubios RR series and the Ledalab EDA files.",
  "- **Webcam clock** - seconds since the webcam recording started. Used by the FaceReader action-unit file (`time_s`).",
  "- **FaceReader video clock** - FaceReader's own time in the analysed video (`video_time_s`, and the time axis of the FaceReader Kubios RR series). It is frame number / the video's frame rate, not real time.",
  "- The webcam and BIOPAC clocks differ by a per-participant offset, given in `biosignals2_clock_offsets.csv`: BIOPAC time = webcam time + offset_s. The FaceReader action-unit file has both `time_s` (webcam) and `video_time_s` (FaceReader video) for every frame, which links the FaceReader video clock to the webcam clock.",
  "",
  "## General caveats",
  "",
  "- Small sample, interim data: the study is still recruiting, so files will grow with each release.",
  "- Webcam heart rate (WebcamBiometrics) is not included yet: the beat detection is still being improved."
)

# ── One entry per file ────────────────────────────────────────────────────────
FILE_INFO <- list(
  "biosignals2_questionnaires_scores.csv" = list(
    title = "Questionnaire scores",
    row = "participant",
    source = "Baseline Qualtrics survey, scored by 04_questionnaire_analysis.Rmd.",
    clock = "none",
    notes = c("Totals are NA if any item of that questionnaire is missing (no pro-rating).",
              "PAQ scored as in the PAQ Scoring and Interpretation Manual (Preece et al., 2018): five subscales + total.",
              "DAS-SF scoring direction: higher = more dysfunctional; DAS-SF2 has one reverse-scored item.")),
  "biosignals2_self-report_rating.csv" = list(
    title = "Self-report ratings",
    row = "participant x block, and in the induction blocks one row per video",
    source = "PsychoPy task log, cleaned by 01_data_cleaning.Rmd.",
    clock = "none (reaction times in seconds)",
    notes = c("State ratings were taken before the baseline and at the end of every block, so only the baseline has block_start_* values. For every later block, the starting state is the previous block's end rating (order: baseline, negative induction, negative recovery, positive induction, positive recovery).",
              "stim_* = ratings of each video (induction blocks only; empty otherwise).",
              "Rating scales are as presented in the PsychoPy experiment (see the task documentation for anchors and ranges).")),
  "biosignals2_ts_ecg_kubios.csv" = list(
    title = "ECG: beat-by-beat RR intervals (Kubios)",
    row = "detected heart beat",
    source = "Kubios HRV report of the trimmed BIOPAC ECG, section RR INTERVAL DATA, one Kubios sample per block.",
    clock = "BIOPAC clock",
    notes = c("Values are as exported by Kubios (columns named from the Kubios header).",
              "beat = beat number within the block.")),
  "biosignals2_ts_facereader_kubios.csv" = list(
    title = "FaceReader heart beats: RR intervals (Kubios)",
    row = "detected heart beat",
    source = "FaceReader heart beat log (remote PPG from the face video), imported into Kubios as beat times, same 5 blocks as the ECG.",
    clock = "FaceReader video clock (whether Kubios' time starts at the video start or at the first beat is still being checked)",
    notes = c("Video-based heart beats are noisier than ECG; Kubios artefact correction applies as for the ECG.")),
  "biosignals2_ts_facereader_au.csv" = list(
    title = "FaceReader facial action units",
    row = "video frame",
    source = "FaceReader detailed log of the 1:1 webcam video.",
    clock = "Webcam clock (time_s); FaceReader video clock (video_time_s)",
    notes = c("Action units are FaceReader intensities, 0-1. Empty where FaceReader found no face (fr_valid = FALSE).",
              "video_event / stimulus = the video being shown at that frame, if any.")),
  "biosignals2_ts_eda_ledalab.csv" = list(
    title = "EDA: skin conductance responses (Ledalab)",
    row = "detected skin conductance response (SCR)",
    source = "Ledalab continuous decomposition analysis (CDA) of the BIOPAC EDA, SCR list export.",
    clock = "BIOPAC clock",
    notes = c("block = the block window the SCR onset falls in: block onset to onset + 180 s.",
              "Columns after t_from_block_start_s are Ledalab's own SCR-list columns.")),
  "biosignals2_block_eda_ledalab.csv" = list(
    title = "EDA per block (Ledalab event-related analysis)",
    row = "participant x block",
    source = "Ledalab event-related analysis (ERA), window 0-180 s from each block onset, minimum SCR amplitude 0.05 uS; summarised by 05_analyse_ledalab_scr.Rmd.",
    clock = "none",
    notes = c("CDA.* = continuous decomposition analysis measures; TTP.* = trough-to-peak measures; Global.* = whole-window measures.")),
  "biosignals2_block_ecg_kubios.csv" = list(
    title = "ECG HRV per block (Kubios)",
    row = "participant x block",
    source = "Kubios HRV batch analysis of the trimmed BIOPAC ECG, one sample per block (Kubios results export).",
    clock = "none",
    notes = c("Column names come from the Kubios export, cleaned to lower case with units as a suffix (e.g. mean_hr_bpm, rmssd_ms, lfpow_fft_ms2).",
              "Kubios definitions: see the Kubios HRV user's guide.")),
  "biosignals2_clock_offsets.csv" = list(
    title = "Clock offsets: webcam clock to BIOPAC clock",
    row = "participant",
    source = "Estimated from the trigger events recorded on both clocks (video/002_run_webcam_biometrics.py, 3_Data/ecg_video_offsets.csv).",
    clock = "BIOPAC time = webcam time + offset_s",
    notes = c("Participants without an estimated offset are not in this file.")),
  "biosignals2_block_facereader_kubios.csv" = list(
    title = "FaceReader heart rate / HRV per block (Kubios)",
    row = "participant x block",
    source = "Kubios HRV batch analysis of the FaceReader heart beat times, same 5 blocks as the ECG.",
    clock = "none",
    notes = c("Same columns as biosignals2_block_ecg_kubios.csv. ECG-waveform columns (p_wave_duration, qrs_duration, ...) are empty: there is no ECG waveform for video beats.",
              "Video-based HRV is noisier than ECG HRV."))
)

# ── Column descriptions ───────────────────────────────────────────────────────
# Exact names first: file-specific (FILE_COLS[[file]]), then any file ("*"), then COL_PATTERNS.
COL_ANY <- c(
  participant_id = "Pseudonymous participant code (P01, P02, ...); the same in every file.",
  block = "Experimental block: baseline, negative_induction, negative_recovery, positive_induction, positive_recovery. Empty = outside the five blocks.",
  t_from_block_start_s = "Seconds since the start of this row's block.",
  beat = "Beat number within the block (1 = first beat in the block).",
  scr_nr = "SCR number within the participant (in time order).",
  frame = "Video frame number (0 = first frame).",
  ecg_waveform_time_s = "Time of the beat on Kubios' ECG-waveform time axis (s), as exported by Kubios.",
  n_scr = "Number of SCRs from the SCR list whose onset falls in the block window.",
  mean_amp = "Mean amplitude of those SCRs (uS; empty if there are none).",
  median_amp = "Median amplitude of those SCRs (uS).",
  max_amp = "Largest amplitude of those SCRs (uS).",
  offset_s = "Webcam-to-BIOPAC clock offset (s): BIOPAC time = webcam time + offset_s.",
  time_s = "Time in seconds (clock: see this file's README section).",
  video_time_s = "FaceReader video time in seconds (frame / the video's frame rate).",
  fr_valid = "TRUE if FaceReader found and fitted the face on this frame.",
  fr_quality = "FaceReader fit quality for the frame (0-1).",
  video_event = "Which video was showing at this frame (empty if none).",
  stimulus = "Stimulus video ID showing at this frame (empty if none).",
  conditionOrder = "Block order label from the task. The negative induction always came first, so it is the same for every participant.",
  video_id = "Stimulus video ID (induction blocks; empty otherwise).",
  block_start_valence = "Valence rating at the start of the block (baseline only).",
  block_start_arousal = "Arousal rating at the start of the block (baseline only).",
  block_end_valence = "Valence rating at the end of the block.",
  block_end_arousal = "Arousal rating at the end of the block.",
  stim_valence = "Valence rating of this video.",
  stim_valence_rt = "Reaction time of the video valence rating (s).",
  stim_arousal = "Arousal rating of this video.",
  stim_arousal_rt = "Reaction time of the video arousal rating (s).",
  stim_approach = "Approach-avoidance rating of this video.",
  stim_approach_rt = "Reaction time of the approach-avoidance rating (s).",
  stim_emotion_label = "Emotion the participant chose for this video.",
  stim_emotion_intensity = "Intensity of the chosen emotion.",
  stim_emotion_intensity_rt = "Reaction time of the emotion intensity rating (s).",
  age = "Age in years.",
  sex_at_birth = "Sex at birth (self-report).",
  gender_id = "Gender identity question (self-report).",
  ethnicity = "Ethnicity (self-report).",
  gad7_total = "GAD-7 anxiety total (0-21).",
  gad7_flag = "TRUE if GAD-7 total >= 10 (clinical screening cut-off).",
  phq9_total = "PHQ-9 depression total (0-27).",
  phq9_flag = "TRUE if PHQ-9 total >= 10 (clinical screening cut-off).",
  aq10_total = "AQ-10 autism-spectrum quotient short form total (0-10).",
  aq10_flag = "TRUE if AQ-10 total >= 6 (screening cut-off).",
  paq_N_DIF = "PAQ N-DIF: difficulty identifying negative feelings, items 2, 8, 14, 20 (4-28; higher = more alexithymia).",
  paq_P_DIF = "PAQ P-DIF: difficulty identifying positive feelings, items 5, 11, 17, 23 (4-28).",
  paq_N_DDF = "PAQ N-DDF: difficulty describing negative feelings, items 1, 7, 13, 19 (4-28).",
  paq_P_DDF = "PAQ P-DDF: difficulty describing positive feelings, items 4, 10, 16, 22 (4-28).",
  paq_G_EOT = "PAQ G-EOT: general externally orientated thinking, items 3, 6, 9, 12, 15, 18, 21, 24 (8-56).",
  paq_total = "PAQ-24 total (24-168).",
  das_sf1_total = "DAS-SF1 dysfunctional attitudes, Achievement (9-63; higher = more dysfunctional).",
  das_sf2_total = "DAS-SF2 dysfunctional attitudes, Dependency (9-63; higher = more dysfunctional).",
  Event.nid = "Ledalab event code of the block.",
  Event.Nr = "Ledalab event number.",
  Event.nr = "Ledalab event number.",
  Event.Name = "Ledalab event name.",
  CDA.nSCR = "Number of significant SCRs in the window (CDA).",
  CDA.Latency = "Latency of the first significant SCR from window start (s, CDA).",
  CDA.AmpSum = "Sum of SCR amplitudes of significant SCRs in the window (uS, CDA).",
  CDA.SCR = "Average phasic driver in the window (uS, CDA).",
  CDA.ISCR = "Integrated SCR: time integral of the phasic driver over the window (uS*s, CDA).",
  CDA.PhasicMax = "Maximum phasic activity in the window (uS, CDA).",
  CDA.Tonic = "Mean tonic skin conductance in the window (uS, CDA).",
  TTP.nSCR = "Number of significant SCRs, trough-to-peak method.",
  TTP.AmpSum = "Sum of SCR amplitudes, trough-to-peak (uS).",
  TTP.Latency = "Latency of the first SCR, trough-to-peak (s).",
  Global.Mean = "Mean skin conductance in the window (uS).",
  Global.MaxDeflection = "Maximum positive deflection of skin conductance in the window (uS)."
)
FILE_COLS <- list()

# Patterns (regular expressions on the column name) - mostly Kubios and FaceReader names.
COL_PATTERNS <- c(
  "SCR\\.?Onset" = "SCR onset time (s, BIOPAC clock).",
  "SCR\\.?Amplitude" = "SCR amplitude (uS).",
  "^au(\\d{2})(_left|_right)?$" = "FaceReader action unit intensity (0-1); _left / _right = one side of the face.",
  "^fr_(neutral|happy|sad|angry|surprised|scared|disgusted|contempt|valence|arousal)$" = "FaceReader emotion / valence / arousal value.",
  "^time" = "Time in seconds (clock: see this file's README section).",
  "rr_interval|^rr_" = "RR interval (time between successive beats), as exported by Kubios.",
  "^onset_offset$" = "Start-end of the analysed block window (hh:mm:ss).",
  "^beats_corrected" = "Share of beats Kubios corrected as artefacts (%).",
  "^effective_data_length" = "Length of data analysed after artefact handling.",
  "^pns_index$" = "Kubios PNS (parasympathetic) index.",
  "^sns_index$" = "Kubios SNS (sympathetic) index.",
  "^stress_index$" = "Baevsky stress index (square root, as in Kubios).",
  "^mean_rr" = "Mean RR interval (ms).",
  "^sdann|^sdnni" = "SDANN / SDNNi: long-recording SDNN measures (ms; usually empty for short blocks).",
  "^sdnn" = "SDNN: standard deviation of RR intervals (ms).",
  "^mean_hr" = "Mean heart rate (beats/min).",
  "^sd_hr" = "Standard deviation of heart rate (beats/min).",
  "^min_hr" = "Minimum heart rate (beats/min).",
  "^max_hr" = "Maximum heart rate (beats/min).",
  "^rmssd" = "RMSSD: root mean square of successive RR differences (ms).",
  "^nnxx" = "NNxx: number of successive RR differences above the Kubios threshold (default 50 ms).",
  "^pnnxx" = "pNNxx: NNxx as a share of all RR intervals (%).",
  "^hrv_triangular_index$" = "HRV triangular index.",
  "^tinn" = "TINN: baseline width of the RR histogram (ms).",
  "^dc(mod)?_ms$" = "Deceleration capacity (ms; mod = modified).",
  "^ac(mod)?_ms$" = "Acceleration capacity (ms; mod = modified).",
  "peak_(fft|ar)_hz$" = "Peak frequency of the band (Hz); fft = Welch periodogram, ar = autoregressive model.",
  "pow_(fft|ar)_ms2$" = "Absolute band power (ms^2).",
  "pow_(fft|ar)_log$" = "Log band power.",
  "pow_(fft|ar)_pct$" = "Relative band power (% of total).",
  "pow_(fft|ar)_n_u$" = "Normalised band power (n.u.).",
  "^totpow" = "Total spectral power (ms^2).",
  "^lf_hf_ratio" = "LF/HF power ratio.",
  "^resp_hz$" = "Respiratory rate estimated from the ECG/beat series (Hz).",
  "^sd1|^sd2" = "Poincare plot SD1 / SD2 (ms) or their ratio.",
  "^apen$" = "Approximate entropy.",
  "^sampen$" = "Sample entropy.",
  "^d2$" = "Correlation dimension D2.",
  "^dfa[12]$" = "Detrended fluctuation analysis, short-term (1) / long-term (2) exponent.",
  "^rp_" = "Recurrence plot measure.",
  "^mse_\\d+$" = "Multiscale entropy at this scale.",
  "^number_of_beats$" = "Number of beats in the block.",
  "^mean_rrsel$" = "Mean of the selected RR intervals (Kubios ECG morphology section).",
  "wave_duration|_interval$|qrs_duration|qt_time|qtc_time|wave_amplitude" = "ECG waveform morphology from Kubios (ECG only; empty for video beats)."
)

describe_column <- function(file, col) {
  fc <- FILE_COLS[[file]]
  if (!is.null(fc) && !is.na(fc[col])) return(unname(fc[col]))
  if (!is.na(COL_ANY[col])) return(unname(COL_ANY[col]))
  hit <- names(COL_PATTERNS)[vapply(names(COL_PATTERNS), function(rx) grepl(rx, col, perl = TRUE), TRUE)]
  if (length(hit)) return(unname(COL_PATTERNS[hit[1]]))
  "NOT DESCRIBED YET"
}

# One row per column of a written data frame.
dictionary_rows <- function(d, file) {
  do.call(rbind, lapply(names(d), function(cn) {
    v <- d[[cn]]
    is_num <- is.numeric(v) && !is.logical(v)
    vals <- if (is_num && any(!is.na(v))) sprintf("%s to %s", format(min(v, na.rm = TRUE), digits = 4),
                                                     format(max(v, na.rm = TRUE), digits = 4))
            else { u <- sort(unique(as.character(v[!is.na(v)])))
                   if (cn == "participant_id") sprintf("%d codes", length(u))
                   else if (length(u) && length(u) <= 10) paste(u, collapse = "; ")
                   else if (length(u)) sprintf("%d different values", length(u)) else "" }
    data.frame(file = file, column = cn,
               type = if (is.logical(v)) "TRUE/FALSE" else if (is_num) "number" else "text",
               n_missing = sum(is.na(v) | (is.character(v) & !nzchar(v))),
               values = vals, description = describe_column(file, cn), stringsAsFactors = FALSE)
  }))
}

write_readme <- function(path, written) {
  # written: list(file = list(rows, participants, columns))
  L <- c("# Biosignals 2 - shared data files", "",
         sprintf("Generated by `08_combine_timeseries.R` on %s. Column-by-column details: `biosignals2_data_dictionary.csv`.",
                 format(Sys.Date())), "",
         README_GENERAL, "", "## Files", "")
  for (f in names(written)) {
    info <- FILE_INFO[[f]]; w <- written[[f]]
    L <- c(L, sprintf("### %s", f), "",
           if (!is.null(info)) c(sprintf("**%s.** One row per %s.", info$title, info$row), "",
                                 sprintf("- Source: %s", info$source),
                                 sprintf("- Clock: %s", info$clock),
                                 paste0("- ", info$notes))
           else "- (no description yet - add one to FILE_INFO in data_dictionary.R)",
           sprintf("- This release: %d rows, %d participants, %d columns.", w$rows, w$participants, w$columns),
           "")
  }
  writeLines(L, path, useBytes = TRUE)
}
