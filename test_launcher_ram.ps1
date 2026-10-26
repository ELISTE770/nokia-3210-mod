# ====================================================================
# test_launcher_ram.ps1 - Test Smart Launcher in RAM over USB (0 Risk)
# ====================================================================

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Nokia 3210 4G - Smart Launcher RAM Test (No Flash / 0 Risk)" -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Instructions:" -ForegroundColor White
Write-Host "1. Power off your Nokia 3210 4G." -ForegroundColor Gray
Write-Host "2. Hold down the Boot button (usually Up or Center key)." -ForegroundColor Gray
Write-Host "3. Plug in the USB cable to your PC." -ForegroundColor Gray
Write-Host "4. spd_dump will detect the phone in BROM mode and load launcher.bin into RAM." -ForegroundColor Gray
Write-Host ""

$binDir = Join-Path $PSScriptRoot "bin"
$spdDump = Join-Path $binDir "spd_dump.exe"
$fdl1 = Join-Path $binDir "t117_fdl1.bin"
$launcher = Join-Path $PSScriptRoot "release_sd\nokia\launcher.bin"

if (-not (Test-Path $launcher)) {
    Write-Host "[ERROR] launcher.bin not found at: $launcher" -ForegroundColor Red
    exit 1
}

Write-Host "Launching spd_dump... Waiting for device on USB..." -ForegroundColor Green
& $spdDump fdl $fdl1 0x6200 fdl $launcher 0x801M
