@echo off
rem run_combine_questionnaires.bat - started each weekday morning (07:00) by Windows Task Scheduler,
rem after the 06:00 Qualtrics SFTP exports land and before the 09:00 follow-up emails.
rem Runs combine_qualtrics_exports.R (stacks all Demographics_* and Follow-up_* exports into
rem raw_questionnaire\combined\) and appends its output to a run log on Box.

set "SCRIPT=C:\Users\carme\Documents\Biosignals-2\analysis\combine_qualtrics_exports.R"
set "RUNLOG=C:\Users\carme\Box\Project_Biosignals_study_2\3_Data\combine_questionnaires_runs.log"

rem Find Rscript: on PATH, else the newest R under Program Files.
set "RSCRIPT="
for /f "delims=" %%i in ('where Rscript 2^>nul') do if not defined RSCRIPT set "RSCRIPT=%%i"
if not defined RSCRIPT for /d %%d in ("C:\Program Files\R\R-*") do set "RSCRIPT=%%d\bin\Rscript.exe"
if not defined RSCRIPT (
  echo %date% %time% ERROR: Rscript not found >> "%RUNLOG%"
  exit /b 1
)

cd /d "C:\Users\carme\Documents\Biosignals-2\analysis"
echo ==================== %date% %time% ==================== >> "%RUNLOG%"
"%RSCRIPT%" "%SCRIPT%" >> "%RUNLOG%" 2>&1
set "RC=%errorlevel%"
echo exit code %RC% >> "%RUNLOG%"
exit /b %RC%
