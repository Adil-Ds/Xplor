# Xplor Backend Starter
# Kills any stale Python/uvicorn process on port 8000 then starts fresh

Write-Host "Checking port 8000..." -ForegroundColor Cyan

$conn = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($conn) {
    $pid = $conn.OwningProcess
    Write-Host "Killing stale process on port 8000 (PID $pid)..." -ForegroundColor Yellow
    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

Write-Host "Port 8000 free. Starting Xplor backend..." -ForegroundColor Green

Set-Location "$PSScriptRoot\backend"
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
