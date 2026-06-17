@echo off
setlocal

REM Local no-billing Gmail polling task runner.
REM This file writes only clean scan/report summaries and never prints secrets.
cd /d "%~dp0"

REM Optional local configuration for Drive uploads.
REM Set DRIVE_REPORT_FOLDER as a Windows environment variable, or create an ignored
REM .env.local file in the project root with this line:
REM DRIVE_REPORT_FOLDER=https://drive.google.com/drive/folders/YOUR_FOLDER_ID
if exist ".env.local" (
    for /f "usebackq tokens=1,* delims==" %%A in (".env.local") do (
        if /i "%%A"=="DRIVE_REPORT_FOLDER" set "DRIVE_REPORT_FOLDER=%%B"
    )
)

if not exist "reports\generated" mkdir "reports\generated"

echo ================================================== >> "reports\generated\task-log.txt"
echo Gmail polling task started: %DATE% %TIME% >> "reports\generated\task-log.txt"
echo. >> "reports\generated\task-log.txt"

python -m api.gmail_poll_worker --once --limit 20 >> "reports\generated\task-log.txt" 2>&1
set SCAN_EXIT_CODE=%ERRORLEVEL%

echo. >> "reports\generated\task-log.txt"
if "%DRIVE_REPORT_FOLDER%"=="" (
    echo DRIVE_REPORT_FOLDER is not configured. Generating local report only. >> "reports\generated\task-log.txt"
    python -m api.gmail_poll_worker --report-today >> "reports\generated\task-log.txt" 2>&1
) else (
    echo DRIVE_REPORT_FOLDER is configured. Generating report and uploading to Drive. >> "reports\generated\task-log.txt"
    python -m api.gmail_poll_worker --report-today --upload-drive --drive-folder "%DRIVE_REPORT_FOLDER%" >> "reports\generated\task-log.txt" 2>&1
)
set REPORT_EXIT_CODE=%ERRORLEVEL%

echo. >> "reports\generated\task-log.txt"
echo Scan exit code: %SCAN_EXIT_CODE% >> "reports\generated\task-log.txt"
echo Report exit code: %REPORT_EXIT_CODE% >> "reports\generated\task-log.txt"
echo Gmail polling task finished: %DATE% %TIME% >> "reports\generated\task-log.txt"
echo ================================================== >> "reports\generated\task-log.txt"

if not "%SCAN_EXIT_CODE%"=="0" exit /b %SCAN_EXIT_CODE%
exit /b %REPORT_EXIT_CODE%
