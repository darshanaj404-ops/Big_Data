# ==============================================================================
# Phase 1: Environment & System Diagnostic Verification Script
# Run this from Windows PowerShell in the project root:
#   .\scripts\verify_environment.ps1
# ==============================================================================

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " TAXI DEMAND HEATMAP - ENVIRONMENT DIAGNOSTIC CHECK" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Hardware Memory Check (8 GB RAM Budget Verification)
Write-Host "`n[1/6] Checking System Memory (RAM)..." -ForegroundColor Yellow
try {
    $ramInfo = Get-CimInstance Win32_ComputerSystem
    $totalRamGB = [math]::Round($ramInfo.TotalPhysicalMemory / 1GB, 2)
    Write-Host "  -> Total Physical RAM Detected: $totalRamGB GB" -ForegroundColor White
    if ($totalRamGB -lt 7.0) {
        Write-Host "  [WARNING] Less than 8 GB RAM detected. Strict container memory bounds are critical." -ForegroundColor Red
    } else {
        Write-Host "  [OK] 8 GB RAM target verified. Low-memory container profiles enabled." -ForegroundColor Green
    }
} catch {
    Write-Host "  [INFO] Could not query CIM memory info." -ForegroundColor Gray
}

# 2. Python Verification
Write-Host "`n[2/6] Checking Python on Windows Host..." -ForegroundColor Yellow
$pythonInstalled = Get-Command python -ErrorAction SilentlyContinue
if ($pythonInstalled) {
    $pyVersion = python --version 2>&1
    Write-Host "  -> Found: $pyVersion" -ForegroundColor White
    Write-Host "  -> Path: $($pythonInstalled.Source)" -ForegroundColor Gray
    Write-Host "  [OK] Python is available." -ForegroundColor Green
} else {
    Write-Host "  [ERROR] Python is not found on Windows PATH." -ForegroundColor Red
}

# 3. Virtual Environment Check
Write-Host "`n[3/6] Checking Python Virtual Environment (.venv)..." -ForegroundColor Yellow
if (Test-Path ".\.venv\Scripts\python.exe") {
    $venvPy = & ".\.venv\Scripts\python.exe" --version 2>&1
    Write-Host "  -> Virtual environment exists: .\.venv ($venvPy)" -ForegroundColor White
    Write-Host "  [OK] Virtualenv verified." -ForegroundColor Green
} else {
    Write-Host "  [NOTICE] .venv does not exist yet. Run: python -m venv .venv" -ForegroundColor Yellow
}

# 4. Java Runtime Check (Host)
Write-Host "`n[4/6] Checking Java on Windows Host..." -ForegroundColor Yellow
$javaInstalled = Get-Command java -ErrorAction SilentlyContinue
if ($javaInstalled) {
    $javaVer = java -version 2>&1 | Select-Object -First 1
    Write-Host "  -> Host Java: $javaVer" -ForegroundColor White
} else {
    Write-Host "  [INFO] Java is NOT installed on Windows host." -ForegroundColor Gray
    Write-Host "         (This is expected and fine: Hadoop runs containerized with its own OpenJDK)" -ForegroundColor Green
}

# 5. Docker & WSL2 Check
Write-Host "`n[5/6] Checking Docker and WSL2..." -ForegroundColor Yellow
$dockerInstalled = Get-Command docker -ErrorAction SilentlyContinue
if ($dockerInstalled) {
    $dockerVer = docker --version 2>&1
    Write-Host "  -> Host Docker: $dockerVer" -ForegroundColor Green
} else {
    Write-Host "  [NOTICE] 'docker' command is not recognized in Windows PATH." -ForegroundColor Yellow
    # Check WSL2 status
    $wslInstalled = Get-Command wsl -ErrorAction SilentlyContinue
    if ($wslInstalled) {
        Write-Host "  -> WSL2 is present. Testing distributions..." -ForegroundColor White
        wsl -l -v
    }
}

# 6. Project Skeleton & Configuration Validation
Write-Host "`n[6/6] Verifying Project Skeleton and Configuration..." -ForegroundColor Yellow
$requiredDirs = @("configs", "docker", "data/raw", "data/sample", "data/geo", "data/processed", "mapreduce", "streaming", "analytics", "dashboard", "scripts", "tests")
$allDirsExist = $true
foreach ($dir in $requiredDirs) {
    if (-not (Test-Path $dir)) {
        Write-Host "  [MISSING] $dir" -ForegroundColor Red
        $allDirsExist = $false
    }
}

if (Test-Path "configs\app_config.yaml") {
    Write-Host "  -> configs\app_config.yaml verified." -ForegroundColor White
} else {
    Write-Host "  [MISSING] configs\app_config.yaml" -ForegroundColor Red
    $allDirsExist = $false
}

if ($allDirsExist) {
    Write-Host "  [OK] Project directory skeleton is 100% complete." -ForegroundColor Green
} else {
    Write-Host "  [WARNING] Some directories are missing." -ForegroundColor Red
}

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host " DIAGNOSTIC COMPLETE" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
