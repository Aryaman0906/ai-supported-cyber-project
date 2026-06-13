@echo off
cd /d D:\cyberproject\ai-supported-cyber-project

if not exist reports\generated mkdir reports\generated

echo =============================== > reports\generated\task-log.txt
echo Task started >> reports\generated\task-log.txt
echo Current directory: %cd% >> reports\generated\task-log.txt
echo. >> reports\generated\task-log.txt

D:\cyberproject\ai-supported-cyber-project\.venv\Scripts\python.exe -m api.gmail_poll_worker --once --limit 20 >> reports\generated\task-log.txt 2>&1

echo. >> reports\generated\task-log.txt
echo Exit code: %ERRORLEVEL% >> reports\generated\task-log.txt
echo Task finished >> reports\generated\task-log.txt
echo =============================== >> reports\generated\task-log.txt