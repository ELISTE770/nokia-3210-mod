# ====================================================================
# flash_clean_nokia.ps1 - One-Click Clean PAC Firmware Flash
# ====================================================================

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Nokia 3210 4G - Clean Custom Firmware Flasher" -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This script flashes the custom clean firmware package:" -ForegroundColor White
Write-Host " - PAC File: 3210_custom_launcher.pac" -ForegroundColor Green
Write-Host " - Removed: All demo bloatware games & dead WAP browser" -ForegroundColor Green
Write-Host " - Added: Balanced 18-app clean menu with Extras/Launcher" -ForegroundColor Green
Write-Host " - VoLTE Calls & SMS: 100% Preserved" -ForegroundColor Green
Write-Host ""

$pacFile = Join-Path $PSScriptRoot "3210_custom_launcher.pac"
$toolPath = Join-Path $PSScriptRoot "spd_research_tool_r23.19.3301\ResearchDownload.exe"
if (-not (Test-Path $toolPath)) {
    $toolPath = Join-Path $PSScriptRoot "_DownloadFiles64E0_A641E99_0\UpgradeDownload.exe"
}

if (-not (Test-Path $pacFile)) {
    Write-Host "[ERROR] 3210_custom_launcher.pac not found!" -ForegroundColor Red
    exit 1
}

Write-Host "[1] Checking Firmware Package Integrity..." -ForegroundColor Cyan
python (Join-Path $PSScriptRoot "tools\nokia_pac.py") verify $pacFile

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Firmware CRC verification failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[2] Flashing Instructions via Official Unisoc ResearchDownload:" -ForegroundColor Yellow
Write-Host "1. Opening ResearchDownload tool automatically..." -ForegroundColor White
Write-Host "2. Click the 'Load Packet' icon (single gear) on top-left." -ForegroundColor White
Write-Host "3. Select the file: $pacFile" -ForegroundColor Cyan
Write-Host "4. Click the 'Start Downloading' play button." -ForegroundColor White
Write-Host "5. Turn off phone, hold Boot key, and plug in USB cable." -ForegroundColor White
Write-Host "6. Once flashing finishes (Passed / Green), unplug and turn on!" -ForegroundColor White
Write-Host ""

if (Test-Path $toolPath) {
    Start-Process $toolPath
} else {
    Write-Host "ResearchDownload executable located in spd_research_tool_r23.19.3301" -ForegroundColor Yellow
}
