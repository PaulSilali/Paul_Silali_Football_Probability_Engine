# Restart Test with Database Pool Fix
# This script stops all Python processes and restarts the test with new pool settings

Write-Host "=== Restarting Test with Database Pool Fix ===" -ForegroundColor Cyan
Write-Host ""

# Stop all Python processes
Write-Host "Stopping all Python processes..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3

# Verify pool settings
Write-Host "`nVerifying pool settings..." -ForegroundColor Yellow
python -c "import sys; sys.path.insert(0, '.'); from app.config import settings; print(f'Pool Size: {settings.DATABASE_POOL_SIZE}'); print(f'Max Overflow: {settings.DATABASE_MAX_OVERFLOW}'); print(f'Total Connections: {settings.DATABASE_POOL_SIZE + settings.DATABASE_MAX_OVERFLOW}')" 2>&1 | Select-String -Pattern "Pool|Max|Total"

Write-Host "`nStarting test with new pool settings..." -ForegroundColor Green
$env:PYTHONUNBUFFERED="1"
python -u Test_Scripts/end_to_end_production_test.py 2>&1 | Tee-Object -FilePath "test_restarted_pool_fix.log"

Write-Host "`n[SUCCESS] Test restarted. Monitor with:" -ForegroundColor Green
Write-Host "  Get-Content test_restarted_pool_fix.log -Tail 30 -Wait" -ForegroundColor Cyan

