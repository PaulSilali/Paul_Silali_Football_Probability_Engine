# Force Restart All Processes with New Pool Settings
# This script forcefully stops ALL Python processes and restarts the test

Write-Host "=== Force Restart All Processes ===" -ForegroundColor Red
Write-Host ""

# Step 1: Stop ALL Python processes (including FastAPI server)
Write-Host "[1/5] Stopping ALL Python processes..." -ForegroundColor Yellow
$procs = Get-Process python -ErrorAction SilentlyContinue
if ($procs) {
    Write-Host "  Found $($procs.Count) process(es) - stopping..." -ForegroundColor Yellow
    $procs | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
    Write-Host "  All processes stopped" -ForegroundColor Green
} else {
    Write-Host "  No processes found" -ForegroundColor Green
}

# Step 2: Wait for processes to fully terminate
Write-Host "`n[2/5] Waiting for processes to terminate..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Step 3: Verify config settings
Write-Host "`n[3/5] Verifying pool configuration..." -ForegroundColor Yellow
python -c "import sys; sys.path.insert(0, '.'); from app.config import settings; print(f'Pool Size: {settings.DATABASE_POOL_SIZE}'); print(f'Max Overflow: {settings.DATABASE_MAX_OVERFLOW}'); print(f'Total: {settings.DATABASE_POOL_SIZE + settings.DATABASE_MAX_OVERFLOW}')" 2>&1 | Select-String -Pattern "Pool|Max|Total"

# Step 4: Verify no processes are running
Write-Host "`n[4/5] Verifying no processes are running..." -ForegroundColor Yellow
$remaining = Get-Process python -ErrorAction SilentlyContinue
if ($remaining) {
    Write-Host "  WARNING: $($remaining.Count) process(es) still running!" -ForegroundColor Red
    $remaining | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
} else {
    Write-Host "  ✓ No processes running" -ForegroundColor Green
}

# Step 5: Start test with new settings
Write-Host "`n[5/5] Starting test with new pool settings..." -ForegroundColor Green
$env:PYTHONUNBUFFERED="1"
$env:MAX_LEAGUES_TO_TEST="0"
$logFile = "test_force_restart_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
python -u Test_Scripts/end_to_end_production_test.py 2>&1 | Tee-Object -FilePath $logFile

Write-Host "`n=== Restart Complete ===" -ForegroundColor Green
Write-Host "Test log: $logFile" -ForegroundColor Cyan
Write-Host "Monitor with: Get-Content $logFile -Tail 30 -Wait" -ForegroundColor Cyan

