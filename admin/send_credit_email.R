# send_credit_email.R  (Biosignals-2 admin; data in Box 3_Data/credit_allocation)
#
# Once a week: finds everyone who has FINISHED the follow-up questionnaire, works
# out which of them signed up through SONA, and emails CREDIT_RECIPIENT the Sussex
# email addresses that need SONA credits. Nobody is sent twice (credit_email_log.csv).
#
# How a participant ID (PID) is linked to SONA:
#   1. sona_link.xlsx (this folder), filled in by hand, always wins:
#        participant_id | sona_credit (yes/no) | sona_email | notes
#   2. Otherwise: the email they typed in the baseline (Demographics) questionnaire
#      (Q51), linked by PID to their follow-up response via followup_schedule.csv, is
#      looked up in the SONA roster in the credit_allocation folder (roster_download_<date>.csv).
#      It is matched against login_id (their university email) and the SONA email
#      column. Found -> SONA participant; credits go to the login_id address.
#   3. Otherwise: not decided. Listed in credit_check.csv, NOT emailed. Add the PID
#      to sona_link.xlsx (sona_credit = yes + sona_email, or no) and it goes next week.
#   People whose SONA row already has a date_granted are skipped (already credited).
#
# Files in Box 3_Data/credit_allocation (contain contact details, never put in git):
#   sona_link.xlsx           manual PID -> SONA link (you fill in)
#   roster_download_<date>.csv  SONA roster (.xlsx/.xls also read); if several, all are read
#   credits_to_allocate.csv  this run's list: participant_id, email
#   credit_check.csv         follow-up done but not sent, with the reason
#   credit_email_log.csv     everyone already sent (credit_email_log_TEST.csv in test mode)
#   credit_email_runs.log    output of each scheduled run (admin/run_credit_email.bat)
#
# The recipient's address is set in config.R (not in git):
#   CREDIT_RECIPIENT <- "M.Casey@sussex.ac.uk"
#
# Needs: Windows + classic Outlook (same as the follow-up emails), R packages
# readr, dplyr, lubridate, readxl. Uses config.R, admin/questionniare_followup_dates.R,
# admin/outlook_send_email.ps1 and analysis/participant_status.R from the Biosignals-2 repo.

# ============================ SETTINGS ========================================

MODE      <- "draft"         # "dry_run" = list only | "draft" = Outlook Drafts | "send"
TEST_MODE <- FALSE           # TRUE = email goes to TEST_RECIPIENT instead. Set FALSE once checked.
TEST_RECIPIENT <- "c.m.daoust@sussex.ac.uk"
SEND_FROM <- "c.m.daoust@sussex.ac.uk"   # Outlook account to send from ("" = default)

SEND_IF_NOBODY <- FALSE     # TRUE = still email "no credits this week" when the list is empty
REFRESH_SCHEDULE <- TRUE    # re-run questionniare_followup_dates.R first
SKIP_STATUSES <- c("test")  # participant_status.csv statuses never credited (add "pilot" if needed)
MAX_PER_EMAIL <- 60         # stop if more than this: something is probably wrong

REPO_DIR <- "C:/Users/carme/Documents/Biosignals-2"

SUBJECT <- "SONA credits to grant ({n})"
BODY <- "
Hi Martha,

Just a quick one to let you know that the following {n} participant(s) have completed their in-person session for the Can AI Read Your Emotions? study after signing up through SONA.

Could you please arrange for their 4 course credits to be added?

{emails}

Thanks!

Best,
Carmen"

# ==============================================================================

suppressPackageStartupMessages({
  library(readr); library(dplyr); library(lubridate); library(readxl)
})
stopifnot(MODE %in% c("dry_run", "draft", "send"), is.logical(TEST_MODE))

finish <- function(msg) {
  cat(msg, "\n")
  if (interactive()) invokeRestart("abort") else quit(save = "no", status = 0)
}

admin_dir    <- file.path(REPO_DIR, "admin")
analysis_dir <- file.path(REPO_DIR, "analysis")
config_candidates <- file.path(c(analysis_dir, REPO_DIR), "config.R")
config_file <- config_candidates[file.exists(config_candidates)][1]
if (is.na(config_file)) stop("config.R not found in ", REPO_DIR)
source(config_file)
CREDIT_RECIPIENT <- trimws(get0("CREDIT_RECIPIENT", ifnotfound = ""))   # set in config.R
if (!exists("SERVER_ROOT") || !dir.exists(SERVER_ROOT)) stop("SERVER_ROOT (Box 3_Data) not found")
source(file.path(analysis_dir, "participant_status.R"), local = TRUE)

credit_dir    <- file.path(SERVER_ROOT, "credit_allocation")
link_file     <- file.path(credit_dir, "sona_link.xlsx")
out_file      <- file.path(credit_dir, "credits_to_allocate.csv")
check_file    <- file.path(credit_dir, "credit_check.csv")
log_file      <- file.path(credit_dir, if (TEST_MODE) "credit_email_log_TEST.csv" else "credit_email_log.csv")
schedule_file <- file.path(SERVER_ROOT, "followup_schedule.csv")
ps_script     <- file.path(admin_dir, "outlook_send_email.ps1")
today_uk      <- today(tzone = "Europe/London")

if (!dir.exists(credit_dir)) stop("Folder not found: ", credit_dir)
if (MODE == "send" && !TEST_MODE && !nzchar(CREDIT_RECIPIENT))
  stop("Set CREDIT_RECIPIENT in config.R before sending for real.")
if (MODE != "dry_run" && !file.exists(ps_script)) stop("Missing ", ps_script)

cat("=== SONA credit email:", format(today_uk), "| MODE =", MODE,
    if (TEST_MODE) paste("| TEST MODE: goes to", TEST_RECIPIENT) else paste("| LIVE: goes to", CREDIT_RECIPIENT),
    "===\n\n")

# as.character(): ifelse() on 0 rows returns logical, which breaks the joins when a file is empty
norm_id    <- function(x) { x <- toupper(trimws(as.character(x))); as.character(ifelse(is.na(x) | x == "", NA_character_, x)) }
norm_email <- function(x) { x <- tolower(trimws(as.character(x))); as.character(ifelse(is.na(x) | x == "" | !grepl("@", x), NA_character_, x)) }

# ---- 1. Who finished the follow-up -------------------------------------------

if (REFRESH_SCHEDULE) {
  cat("Updating the follow-up schedule...\n")
  invisible(capture.output(source(file.path(admin_dir, "questionniare_followup_dates.R"), local = new.env())))
}
schedule <- read_csv(schedule_file, col_types = cols(.default = col_character()), show_col_types = FALSE)
done <- schedule |>
  filter(followup_completed == "yes", !is.na(id), id != "") |>
  transmute(participant_id = norm_id(id), quest_email = norm_email(email),
            followup_completed_date) |>
  distinct(participant_id, .keep_all = TRUE)
done$pstatus <- participant_status_of(done$participant_id)
cat("Follow-up completed:", nrow(done), "participant(s)\n")

# ---- 2. SONA rosters ------------------------------------------------------------
# roster_download_<date>.csv: first_name, last_name, login_id, survey_id, email, ...,
# date_granted, ..., comments. login_id = university email (if SONA ever gives just the
# username, @sussex.ac.uk is added). A title row above the header ("Participants") is fine:
# the header row is found by looking for first_name + login_id/email.

read_sona <- function(path) {
  raw <- if (grepl("\\.xlsx?$", path, ignore.case = TRUE)) {
    as.data.frame(read_excel(path, col_names = FALSE, col_types = "text", .name_repair = "minimal"))
  } else {
    read.csv(path, header = FALSE, colClasses = "character", check.names = FALSE,
             fill = TRUE, na.strings = "", fileEncoding = "UTF-8-BOM",
             col.names = paste0("V", 1:30))
  }
  low <- as.matrix(as.data.frame(lapply(raw, function(v) tolower(trimws(as.character(v))))))
  hdr <- which(apply(low, 1, function(r) "first_name" %in% r && any(c("login_id", "email") %in% r)))[1]
  if (is.na(hdr)) { warning("No SONA header row (first_name + login_id/email) in ", basename(path), " - skipped", call. = FALSE); return(NULL) }
  nm <- low[hdr, ]; keep <- !is.na(nm) & nzchar(nm)
  d <- raw[-seq_len(hdr), keep, drop = FALSE]; names(d) <- nm[keep]
  d <- d[!apply(is.na(d) | d == "", 1, all), , drop = FALSE]
  for (cn in c("date_granted", "login_id", "email")) if (!cn %in% names(d)) d[[cn]] <- NA_character_
  login <- tolower(trimws(as.character(d$login_id)))
  login <- ifelse(!is.na(login) & nzchar(login) & !grepl("@", login), paste0(login, "@sussex.ac.uk"), login)
  data.frame(sussex_email = coalesce(norm_email(login), norm_email(d$email)),   # where credits go
             sona_email   = norm_email(d$email),
             date_granted = trimws(as.character(d$date_granted)),
             source = basename(path), stringsAsFactors = FALSE)
}

sona_files <- list.files(credit_dir, pattern = "^roster_download.*\\.(csv|xlsx|xls)$",
                         full.names = TRUE, ignore.case = TRUE)
sona_files <- sona_files[!startsWith(basename(sona_files), "~$")]   # Excel lock files
sona <- bind_rows(lapply(sona_files, read_sona))
if (nrow(sona) == 0) {
  cat("WARNING: no roster_download_*.csv read from", credit_dir, "- only sona_link.xlsx is used.\n")
  sona <- data.frame(sussex_email = character(), sona_email = character(),
                     date_granted = character(), source = character())
}
sona <- sona |> filter(!is.na(sussex_email)) |>
  mutate(granted = !is.na(date_granted) & date_granted != "" & !tolower(date_granted) %in% c("na", "n/a")) |>
  group_by(sussex_email) |>
  summarise(granted = any(granted), sona_email = first(na.omit(sona_email)), .groups = "drop")
# Lookup: a questionnaire email can match login_id OR the SONA email column.
sona_keys <- bind_rows(
  transmute(sona, key = sussex_email, sussex_email, granted),
  transmute(filter(sona, !is.na(sona_email)), key = sona_email, sussex_email, granted)
) |> distinct(key, .keep_all = TRUE)
cat("SONA sign-ups:", nrow(sona), "unique email(s) from", length(sona_files), "file(s)\n")

# ---- 3. Manual link sheet ------------------------------------------------------

link <- if (file.exists(link_file)) {
  read_excel(link_file, sheet = 1, col_types = "text")
} else {
  cat("WARNING: no", basename(link_file), "- only email matching is used.\n")
  data.frame(participant_id = character(), sona_credit = character(), sona_email = character())
}
names(link) <- tolower(trimws(names(link)))
miss <- setdiff(c("participant_id", "sona_credit", "sona_email"), names(link))
if (length(miss)) stop(basename(link_file), " is missing column(s): ", paste(miss, collapse = ", "))
link <- link |>
  transmute(participant_id = norm_id(participant_id),
            link_credit = tolower(trimws(sona_credit)),
            link_email = norm_email(sona_email)) |>
  filter(!is.na(participant_id))
dup <- unique(link$participant_id[duplicated(link$participant_id)])
if (length(dup)) stop(basename(link_file), ": PID listed twice: ", paste(dup, collapse = ", "))
bad <- link |> filter(!is.na(link_credit), !link_credit %in% c("yes", "no"))
if (nrow(bad)) stop(basename(link_file), ": sona_credit must be yes or no (", paste(bad$participant_id, collapse = ", "), ")")

# ---- 4. Decide for each completer ---------------------------------------------

read_log <- function(path) if (file.exists(path))
  read_csv(path, col_types = cols(.default = col_character()), show_col_types = FALSE) else
  tibble(participant_id = character(), result = character())
already <- read_log(log_file) |> filter(result %in% c("sent", "drafted")) |> pull(participant_id)
if (TEST_MODE) already <- c(already, read_log(file.path(credit_dir, "credit_email_log.csv")) |>
                              filter(result %in% c("sent", "drafted")) |> pull(participant_id))

d <- done |>
  left_join(link, by = "participant_id") |>
  left_join(rename(sona_keys, quest_sussex = sussex_email, quest_in_sona = granted), by = c("quest_email" = "key")) |>
  left_join(rename(sona_keys, link_sussex = sussex_email, link_granted = granted), by = c("link_email" = "key")) |>
  mutate(
    email = case_when(link_credit == "yes" ~ coalesce(link_sussex, link_email),
                      is.na(link_credit) & !is.na(quest_in_sona) ~ quest_sussex),
    granted = coalesce(case_when(link_credit %in% "yes" ~ link_granted,
                                 is.na(link_credit) ~ quest_in_sona), FALSE),
    decision = case_when(
      pstatus %in% SKIP_STATUSES                        ~ paste("skip: participant_status", pstatus),
      participant_id %in% already                       ~ "already sent",
      link_credit == "no"                               ~ "not SONA (sona_link.xlsx)",
      link_credit == "yes" & is.na(link_email)          ~ "CHECK: sona_credit yes but no sona_email in sona_link.xlsx",
      !is.na(email) & granted                           ~ "already granted in SONA",
      !is.na(email) & !grepl("@sussex\\.ac\\.uk$", email) ~ "CHECK: email is not @sussex.ac.uk",
      !is.na(email)                                     ~ "SEND",
      TRUE ~ "CHECK: not in sona_link.xlsx and questionnaire email not in SONA roster"
    )
  )

to_send <- d |> filter(decision == "SEND")
dup_email <- unique(to_send$email[duplicated(to_send$email)])
if (length(dup_email)) {
  to_send <- to_send |> filter(!email %in% dup_email)
  d$decision[d$decision == "SEND" & d$email %in% dup_email] <- "CHECK: same SONA email for two PIDs"
}

checks <- d |> filter(startsWith(decision, "CHECK"))
write_csv(select(checks, participant_id, followup_completed_date, questionnaire_email = quest_email,
                 sona_email = email, reason = decision), check_file, na = "")
write_csv(select(to_send, participant_id, email), out_file, na = "")

cat("\nDecisions:\n"); print(as.data.frame(count(d, decision)), row.names = FALSE); cat("\n")
if (nrow(checks)) {
  cat("Need a look (", nrow(checks), ", in credit_check.csv), NOT sent:\n", sep = "")
  print(as.data.frame(select(checks, participant_id, decision)), row.names = FALSE); cat("\n")
}
cat("To credit this run (", nrow(to_send), "), saved to credits_to_allocate.csv\n", sep = "")

if (nrow(to_send) > MAX_PER_EMAIL) stop(nrow(to_send), " people is more than MAX_PER_EMAIL - check before sending.")
if (nrow(to_send) == 0 && !SEND_IF_NOBODY) finish("Nobody new to credit. No email sent.")
if (MODE == "dry_run") {
  print(as.data.frame(select(to_send, participant_id, email)), row.names = FALSE)
  finish("Dry run: nothing sent.")
}

# ---- 5. One email, then log everyone in it -------------------------------------

n <- nrow(to_send)
emails <- if (n) paste(to_send$email, collapse = "\n") else "(nobody this week)"
subject <- gsub("{n}", n, SUBJECT, fixed = TRUE)
body <- gsub("{emails}", emails, gsub("{n}", n, BODY, fixed = TRUE), fixed = TRUE)
recipient <- if (TEST_MODE) TEST_RECIPIENT else CREDIT_RECIPIENT
if (TEST_MODE) subject <- paste("[TEST]", subject)

msg_dir <- tempfile("credit_msg_"); dir.create(msg_dir)
writeLines(recipient, file.path(msg_dir, "to.txt"), useBytes = TRUE)
writeLines(enc2utf8(subject), file.path(msg_dir, "subject.txt"), useBytes = TRUE)
writeLines(enc2utf8(body), file.path(msg_dir, "body.txt"), useBytes = TRUE)
if (nzchar(SEND_FROM)) writeLines(SEND_FROM, file.path(msg_dir, "from.txt"), useBytes = TRUE)
out <- suppressWarnings(system2("powershell",
  c("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", shQuote(ps_script),
    "-MsgDir", shQuote(msg_dir), "-Mode", MODE), stdout = TRUE, stderr = TRUE))
unlink(msg_dir, recursive = TRUE)

ok <- any(trimws(out) == "OK")
result <- if (ok) (if (MODE == "send") "sent" else "drafted") else "failed"
if (n) write_csv(tibble(
  logged_at = format(now(tzone = "Europe/London"), "%Y-%m-%d %H:%M:%S"),
  participant_id = to_send$participant_id, email = to_send$email,
  followup_completed_date = to_send$followup_completed_date,
  recipient = recipient, mode = MODE, test = TEST_MODE, result = result,
  detail = if (ok) "" else paste(trimws(out), collapse = " | ")
), log_file, append = file.exists(log_file), na = "")

if (!ok) stop("Email NOT sent: ", paste(trimws(out), collapse = " | "))
cat("Done:", result, "to", recipient, "with", n, "email address(es). Log:", log_file, "\n")
