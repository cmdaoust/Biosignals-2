@echo off
rem run_credit_email.bat - started weekly (Friday 10:00) by Windows Task Scheduler.
rem Runs send_credit_email.R and appends its output to credit_email_runs.log.

set "SCRIPT=C:\Users\carme\Documents\Biosignals-2\admin\send_credit_email.R"
set "RUNLOG=C:\Users\carme\Box\Project_Biosignals_study_2\3_Data\credit_allocation\credit_email_runs.log"

set "RSCRIPT="
for /f "delims=" %%i in ('where Rscript 2^>nul') do if not defined RSCRIPT set "RSCRIPT=%%i"
if not defined RSCRIPT for /d %%d in ("C:\Program Files\R\R-*") do set "RSCRIPT=%%d\bin\Rscript.exe"
if not defined RSCRIPT (
  echo %date% %time% ERROR: Rscript not found >> "%RUNLOG%"
  exit /b 1
)

echo ==================== %date% %time% ==================== >> "%RUNLOG%"
"%RSCRIPT%" "%SCRIPT%" >> "%RUNLOG%" 2>&1
echo exit code %errorlevel% >> "%RUNLOG%"
