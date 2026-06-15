@echo off
setlocal

REM Local no-billing Gmail polling task runner.
REM This file writes only clean scan/report summaries and never prints secrets.
cd /d "%~dp0"

if not exist "reports\generated" mkdir "reports\generated"

echo ================================================== >> "reports\generated\task-log.txt"
echo Gmail polling task started: %DATE% %TIME% >> "reports\generated\task-log.txt"
echo. >> "reports\generated\task-log.txt"

python -m api.gmail_poll_worker --once --limit 20 >> "reports\generated\task-log.txt" 2>&1
set SCAN_EXIT_CODE=%ERRORLEVEL%

echo. >> "reports\generated\task-log.txt"
python -m api.gmail_poll_worker --report-today >> "reports\generated\task-log.txt" 2>&1
set REPORT_EXIT_CODE=%ERRORLEVEL%

echo. >> "reports\generated\task-log.txt"
echo Scan exit code: %SCAN_EXIT_CODE% >> "reports\generated\task-log.txt"
echo Report exit code: %REPORT_EXIT_CODE% >> "reports\generated\task-log.txt"
echo Gmail polling task finished: %DATE% %TIME% >> "reports\generated\task-log.txt"
echo ================================================== >> "reports\generated\task-log.txt"

if not "%SCAN_EXIT_CODE%"=="0" exit /b %SCAN_EXIT_CODE%
exit /b %REPORT_EXIT_CODE%
