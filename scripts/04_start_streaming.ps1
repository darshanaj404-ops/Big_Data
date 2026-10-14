# ==============================================================================
# Phase 4: Kafka Trip-Start Streaming Pipeline Execution Script
# Simulates live event streaming and rolling-window consumption
# ==============================================================================

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " PHASE 4: KAFKA TRIP-START STREAMING PIPELINE" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Check Kafka Broker Connectivity
Write-Host "`n[Step 1/3] Checking Apache Kafka connectivity..." -ForegroundColor Yellow
.\.venv\Scripts\python.exe streaming\kafka_manager.py

# 2. Produce 500 Streaming Trip-Start Events
Write-Host "`n[Step 2/3] Producing streaming trip-start events..." -ForegroundColor Yellow
.\.venv\Scripts\python.exe streaming\kafka_producer.py --max-events 500 --delay 0.005

# 3. Consume Streaming Events and Update Rolling Window
Write-Host "`n[Step 3/3] Consuming events and computing rolling window pickup velocity..." -ForegroundColor Yellow
.\.venv\Scripts\python.exe streaming\kafka_consumer.py --max-events 500 --window 15

# 4. Display Window Snapshot Status
Write-Host "`n[Verification] Checking generated rolling window snapshot..." -ForegroundColor Yellow
$snapshotPath = "data\processed\live_window_pickups.json"
if (Test-Path $snapshotPath) {
    Write-Host "  -> Snapshot verified at: $snapshotPath" -ForegroundColor Green
    $content = Get-Content $snapshotPath -Raw | ConvertFrom-Json
    Write-Host "  -> Total Window Events:  $($content.total_window_events)" -ForegroundColor White
    Write-Host "  -> Active Zones Count:    $($content.active_zones_count)" -ForegroundColor White
    Write-Host "  -> Data Freshness Status: $($content.data_freshness)" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] Snapshot file was not created!" -ForegroundColor Red
}

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host " STREAMING PIPELINE EXECUTION COMPLETE" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
