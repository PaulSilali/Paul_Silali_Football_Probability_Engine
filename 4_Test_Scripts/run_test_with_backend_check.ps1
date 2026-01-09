# Run Test with Backend Health Check
# Checks if FastAPI backend is running, restarts if needed, then runs tests

param(
    [int]$BackendPort = 8000,
    [string]$BackendUrl = "http://localhost:8000/api/model/status"
)

Write-Host "=== Test Runner with Backend Health Check ===" -ForegroundColor Cyan
Write-Host ""

function Check-BackendRunning {
    param([string]$Url)
    try {
        $response = Invoke-WebRequest -Uri $Url -Method GET -TimeoutSec 5 -ErrorAction Stop
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Start-Backend {
    Write-Host "[BACKEND] Starting FastAPI server..." -ForegroundColor Yellow
    Set-Location "F:\[ 11 ] Football Probability Engine  [SP Soccer]\2_Backend_Football_Probability_Engine"
    
    # Start backend in background
    $backendJob = Start-Job -ScriptBlock {
        Set-Location $using:PWD
        uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    }
    
    Write-Host "[BACKEND] Waiting for server to start..." -ForegroundColor Yellow
    $maxWait = 30
    $waited = 0
    while ($waited -lt $maxWait) {
        Start-Sleep -Seconds 2
        $waited += 2
        if (Check-BackendRunning -Url $BackendUrl) {
            Write-Host "[BACKEND] Server is running!" -ForegroundColor Green
            return $true
        }
        Write-Host "." -NoNewline
    }
    Write-Host ""
    Write-Host "[BACKEND] Server may not have started properly" -ForegroundColor Yellow
    return $false
}

function Stop-AllPythonProcesses {
    Write-Host "[CLEANUP] Stopping all Python processes..." -ForegroundColor Yellow
    Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Write-Host "[CLEANUP] All processes stopped" -ForegroundColor Green
}

# Step 1: Check if backend is running
Write-Host "[1/4] Checking if backend is running..." -ForegroundColor Cyan
$backendRunning = Check-BackendRunning -Url $BackendUrl

if (-not $backendRunning) {
    Write-Host "[BACKEND] Backend is NOT running" -ForegroundColor Red
    Stop-AllPythonProcesses
    $backendStarted = Start-Backend
    if (-not $backendStarted) {
        Write-Host "[ERROR] Failed to start backend. Continuing anyway (test uses direct service calls)." -ForegroundColor Yellow
    }
} else {
    Write-Host "[BACKEND] Backend is running!" -ForegroundColor Green
}

# Step 2: Wait a moment for backend to be ready
Write-Host "`n[2/4] Waiting for backend to be ready..." -ForegroundColor Cyan
Start-Sleep -Seconds 3

# Step 3: Verify backend again
Write-Host "`n[3/4] Verifying backend status..." -ForegroundColor Cyan
$backendRunning = Check-BackendRunning -Url $BackendUrl
if ($backendRunning) {
    Write-Host "[BACKEND] Backend is ready!" -ForegroundColor Green
} else {
    Write-Host "[BACKEND] Backend check failed, but continuing (test uses direct service calls)" -ForegroundColor Yellow
}

# Step 4: Start test
Write-Host "`n[4/4] Starting end-to-end test..." -ForegroundColor Cyan
$env:PYTHONUNBUFFERED="1"
$env:MAX_LEAGUES_TO_TEST="0"
$logFile = "test_with_backend_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

Write-Host "Test log: $logFile" -ForegroundColor Yellow
Write-Host "Monitor with: Get-Content $logFile -Tail 30 -Wait`n" -ForegroundColor Cyan

python -u Test_Scripts/end_to_end_production_test.py 2>&1 | Tee-Object -FilePath $logFile

Write-Host "`n=== Test Complete ===" -ForegroundColor Green

