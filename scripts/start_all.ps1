# ==============================================================================
# Taxi Demand Heatmap Generation - Single-Command Startup Script
# Run from Windows PowerShell in the project root:
#   .\scripts\start_all.ps1
# ==============================================================================

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " STARTING TAXI DEMAND HEATMAP BIG DATA PLATFORM" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Check Python Virtual Environment
if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "  [NOTICE] Python virtual environment not found. Creating .venv..." -ForegroundColor Yellow
    python -m venv .venv
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
}

# 2. Check if Datasets Exist
if (-not (Test-Path ".\data\sample\yellow_tripdata_sample_100k.csv") -or -not (Test-Path ".\data\geo\nyc_taxi_zones.geojson")) {
    Write-Host "`n[Step 1/5] Acquiring NYC TLC datasets and GeoJSON geometries..." -ForegroundColor Yellow
    .\.venv\Scripts\python.exe scripts\02_download_and_sample_data.py
} else {
    Write-Host "`n[Step 1/5] Verified datasets and GeoJSON boundaries are present." -ForegroundColor Green
}

# 3. Check if Historical MapReduce Baseline Exists
if (-not (Test-Path ".\data\processed\historical_baseline.csv")) {
    Write-Host "`n[Step 2/5] Running Hadoop MapReduce Historical Aggregation..." -ForegroundColor Yellow
    .\.venv\Scripts\python.exe mapreduce\run_mapreduce_local.py
    .\.venv\Scripts\python.exe mapreduce\verify_baseline.py
} else {
    Write-Host "`n[Step 2/5] MapReduce historical hourly baseline is verified." -ForegroundColor Green
}

# 4. Optional: Start Docker Kafka if Docker is running
$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if ($dockerCmd) {
    Write-Host "`n[Step 3/5] Docker detected. Checking Kafka container..." -ForegroundColor Yellow
    docker compose -f docker\docker-compose.yml up -d kafka 2>$null
    Start-Sleep -Seconds 3
} else {
    Write-Host "`n[Step 3/5] Docker not in PATH. Streaming will run in standalone simulation mode." -ForegroundColor Gray
}

# 5. Run Live Streaming Producer & Consumer
Write-Host "`n[Step 4/5] Ingesting streaming trip-starts and updating rolling window..." -ForegroundColor Yellow
.\.venv\Scripts\python.exe streaming\kafka_producer.py --max-events 500 --delay 0.002
.\.venv\Scripts\python.exe streaming\kafka_consumer.py --max-events 500 --window 15

# 6. Compute Demand Surge Synthesis
Write-Host "`n[Step 5/5] Synthesizing MapReduce baseline with streaming counts..." -ForegroundColor Yellow
.\.venv\Scripts\python.exe analytics\surge_calculator.py

# 7. Launch Dashboard
Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host " LAUNCHING DASHBOARD SERVER" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  -> Dashboard URL: http://127.0.0.1:8050" -ForegroundColor Green
Write-Host "  -> Auto-Refresh:  Every 10 minutes (600,000 ms)" -ForegroundColor White
Write-Host "`nOpening your browser... Press Ctrl+C in this window to stop.`n" -ForegroundColor Yellow

# Launch browser automatically
Start-Process "http://127.0.0.1:8050" -ErrorAction SilentlyContinue

# Run Dash application
.\.venv\Scripts\python.exe dashboard\app.py
