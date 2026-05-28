$hermesPath = "$env:LOCALAPPDATA\hermes\hermes-agent\.venv\Scripts\hermes.exe"

Write-Host ""
Write-Host "  ===================================" -ForegroundColor Cyan
Write-Host "   Hermes Agent Gateway - SignalForge" -ForegroundColor Cyan
Write-Host "  ===================================" -ForegroundColor Cyan
Write-Host ""

# Kill any old bot.py processes to avoid Telegram token conflicts
$oldBots = Get-Process -Name "python" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match "bot\.py" }
if ($oldBots) {
    $oldBots | Stop-Process -Force
    Write-Host "[cleanup] Stopped old bot.py processes" -ForegroundColor Yellow
}

# Check hermes exists
if (-not (Test-Path $hermesPath)) {
    Write-Host "ERROR: hermes.exe not found at $hermesPath" -ForegroundColor Red
    Write-Host "Install Hermes Agent first." -ForegroundColor Red
    pause
    exit 1
}

Write-Host "[start] Launching Hermes Gateway..." -ForegroundColor Green
& $hermesPath gateway run
