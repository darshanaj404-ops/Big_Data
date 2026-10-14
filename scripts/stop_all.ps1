# ==============================================================================
# Taxi Demand Heatmap Generation - Single-Command Shutdown Script
# Gracefully stops all project services, containers, and frees RAM
# ==============================================================================

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " SHUTTING DOWN TAXI DEMAND HEATMAP SERVICES" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Stop Python Dashboard Processes
Write-Host "`n[1/2] Stopping Dash application and streaming processes..." -ForegroundColor Yellow
$pyProcs = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -like "*dashboard\app.py*" -or $_.CommandLine -like "*streaming\kafka_*"
}

if ($pyProcs) {
    foreach ($p in $pyProcs) {
        Write-Host "  -> Terminating process $($p.ProcessId) ($($p.Name))..." -ForegroundColor Gray
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Write-Host "  [OK] Dashboard processes stopped." -ForegroundColor Green
} else {
    Write-Host "  [INFO] No active background dashboard processes found." -ForegroundColor Gray
}

# 2. Stop Docker Containers (if Docker is running)
Write-Host "`n[2/2] Checking Docker containers..." -ForegroundColor Yellow
$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if ($dockerCmd) {
    Write-Host "  -> Stopping Docker containers (Kafka & Hadoop)..." -ForegroundColor Gray
    docker compose -f docker\docker-compose.yml down --remove-orphans 2>$null
    Write-Host "  [OK] Docker containers stopped and memory released." -ForegroundColor Green
} else {
    Write-Host "  [INFO] Docker is not active. No containers to stop." -ForegroundColor Gray
}

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host " SHUTDOWN COMPLETE - ALL MEMORY FREED" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
