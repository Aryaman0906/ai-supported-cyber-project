$ErrorActionPreference = "Continue"

Write-Host "== Git history exposure review =="
Write-Host "Repository:" (Get-Location)
Write-Host ""

function Show-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "-- $Title --"
}

Show-Section "Tracked runtime/private files"
git ls-files | Select-String -Pattern "credentials\.json|token\.json|\.env$|\.env\.local|reports/generated|task-log|\.local|\.joblib|runtime/scan\.lock"

Show-Section "Ignored local runtime/private files"
foreach ($path in @("credentials.json", "token.json", ".env", ".env.local", ".local\gmail_poll_storage.json", "reports\generated\task-log.txt", "runtime\scan.lock")) {
    git check-ignore -v $path 2>$null
}

Show-Section "Current tracked files containing Drive folder URLs"
git grep -n -I "drive.google.com/drive/folders"

Show-Section "Git history paths for runtime/private files"
foreach ($path in @("credentials.json", "token.json", ".env", ".env.local", "reports/generated", "task-log.txt")) {
    Write-Host "### $path"
    git log --all --full-history -- $path
}

Show-Section "Git history files containing Drive folder URLs"
git rev-list --all | ForEach-Object {
    git grep -l -I "drive.google.com/drive/folders" $_ 2>$null
} | Sort-Object -Unique

Write-Host ""
Write-Host "Review complete. If a real Drive folder URL or private runtime file appears in history, rotate or recreate the exposed resource and keep the new value only in ignored local config."
