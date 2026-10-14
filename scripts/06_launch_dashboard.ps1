# ==============================================================================
# Phase 6: Plotly Dash Web Application Launch Script
# Starts the interactive NYC Taxi Demand Heatmap & Surge Monitor Dashboard
# ==============================================================================

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " LAUNCHING TAXI DEMAND HEATMAP DASHBOARD" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Ensure Virtual Environment is Active
if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "  [ERROR] Virtual environment .venv not found!" -ForegroundColor Red
    exit 1
}

Write-Host "  -> Dashboard URL:              http://127.0.0.1:8050" -ForegroundColor Green
Write-Host "  -> Background Refresh Timer:   Every 10 minutes (600,000 ms)" -ForegroundColor White
Write-Host "  -> Data Sources:               Hadoop MapReduce Baseline + Kafka Stream" -ForegroundColor White
Write-Host "`nOpening dashboard server... Press Ctrl+C in this terminal to stop.`n" -ForegroundColor Yellow

.\.venv\Scripts\python.exe dashboard\app.py
