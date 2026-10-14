# ==============================================================================
# Phase 5: Demand Surge Analytics & Synthesis Pipeline Script
# Merges historical MapReduce baseline with live Kafka stream counts
# ==============================================================================

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " PHASE 5: DEMAND SURGE ANALYTICS & SYNTHESIS PIPELINE" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Execute Surge Synthesis Engine
Write-Host "`n[Step 1/2] Computing zone-by-zone surge metrics and rankings..." -ForegroundColor Yellow
.\.venv\Scripts\python.exe analytics\surge_calculator.py

# 2. Display Top 10 Ranked Surge Zones
Write-Host "`n[Step 2/2] Top 10 High-Demand Taxi Zones Leaderboard:" -ForegroundColor Yellow
$top10Csv = "data\processed\top_10_demand_zones.csv"

if (Test-Path $top10Csv) {
    $rows = Import-Csv $top10Csv
    Write-Host ("`n{0,-6} {1,-30} {2,-15} {3,-10} {4,-12} {5,-15}" -f "Rank", "Zone Name", "Borough", "Live", "Expected", "Surge Ratio") -ForegroundColor White
    Write-Host ("-" * 90) -ForegroundColor Gray

    foreach ($r in $rows) {
        $color = "Green"
        if ([double]$r.surge_ratio -ge 1.5) { $color = "Red" }
        elseif ([double]$r.surge_ratio -ge 1.2) { $color = "Yellow" }

        Write-Host ("{0,-6} {1,-30} {2,-15} {3,-10} {4,-12} {5,-15}" -f $r.surge_rank, $r.Zone, $r.Borough, $r.live_window_pickups, $r.expected_window_pickups, $r.surge_ratio) -ForegroundColor $color
    }

    $summaryJson = "data\processed\surge_analytics_summary.json"
    if (Test-Path $summaryJson) {
        $summary = Get-Content $summaryJson -Raw | ConvertFrom-Json
        Write-Host "`n--- Summary Metrics ---" -ForegroundColor Cyan
        Write-Host "  Target Hour:                 $($summary.target_hour):00" -ForegroundColor White
        Write-Host "  Total Zones Analyzed:        $($summary.total_official_zones)" -ForegroundColor White
        Write-Host "  Active Streaming Zones:      $($summary.zones_with_live_pickups)" -ForegroundColor White
        Write-Host "  High Surge Zones:            $($summary.high_surge_zones_count)" -ForegroundColor Red
        Write-Host "  Moderate Surge Zones:        $($summary.moderate_surge_zones_count)" -ForegroundColor Yellow
        Write-Host "  Peak Demand Zone:            $($summary.top_surge_zone.Zone) ($($summary.top_surge_zone.Borough)) - Ratio: $($summary.top_surge_zone.surge_ratio)" -ForegroundColor Green
    }
} else {
    Write-Host "  [ERROR] top_10_demand_zones.csv was not generated!" -ForegroundColor Red
}

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host " DEMAND SURGE ANALYTICS COMPLETE" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
