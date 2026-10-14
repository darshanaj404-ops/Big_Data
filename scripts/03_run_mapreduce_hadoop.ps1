# ==============================================================================
# Phase 3: Hadoop HDFS & MapReduce Streaming Execution Script
# Runs either directly against the Hadoop Docker container or via local streaming runner
# ==============================================================================

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " PHASE 3: HADOOP HDFS & MAPREDUCE AGGREGATION PIPELINE" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$hadoopContainer = "hadoop-single-node"
$dockerRunning = $false

# 1. Check if Docker is running and container is active
$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if ($dockerCmd) {
    $containerStatus = docker ps --filter "name=$hadoopContainer" --format "{{.Status}}" 2>&1
    if ($containerStatus -like "*Up*") {
        $dockerRunning = $true
        Write-Host "  [OK] Hadoop container '$hadoopContainer' is active." -ForegroundColor Green
    }
}

if ($dockerRunning) {
    Write-Host "`n[Step 1/3] Copying sample dataset into Hadoop HDFS..." -ForegroundColor Yellow
    docker exec $hadoopContainer hdfs dfs -mkdir -p /taxi/historical/raw
    docker exec $hadoopContainer hdfs dfs -mkdir -p /taxi/historical/baseline
    docker cp .\data\sample\yellow_tripdata_sample_100k.csv ${hadoopContainer}:/tmp/yellow_tripdata_sample_100k.csv
    docker exec $hadoopContainer hdfs dfs -put -f /tmp/yellow_tripdata_sample_100k.csv /taxi/historical/raw/
    Write-Host "  -> Dataset successfully stored in HDFS at /taxi/historical/raw/." -ForegroundColor Green

    Write-Host "`n[Step 2/3] Submitting Hadoop Streaming MapReduce Job to YARN..." -ForegroundColor Yellow
    docker cp .\mapreduce\mapper.py ${hadoopContainer}:/tmp/mapper.py
    docker cp .\mapreduce\reducer.py ${hadoopContainer}:/tmp/reducer.py
    docker exec $hadoopContainer hdfs dfs -rm -r -f /taxi/historical/baseline/output

    docker exec $hadoopContainer hadoop jar /opt/hadoop/share/hadoop/tools/lib/hadoop-streaming-3.3.6.jar `
        -input /taxi/historical/raw/yellow_tripdata_sample_100k.csv `
        -output /taxi/historical/baseline/output `
        -mapper "python3 /tmp/mapper.py" `
        -reducer "python3 /tmp/reducer.py"

    Write-Host "`n[Step 3/3] Exporting MapReduce output from HDFS to local storage..." -ForegroundColor Yellow
    docker exec $hadoopContainer hdfs dfs -get -f /taxi/historical/baseline/output/part-00000 /tmp/baseline_output.tsv
    docker cp ${hadoopContainer}:/tmp/baseline_output.tsv .\data\processed\historical_baseline_raw.tsv
    Write-Host "  -> HDFS output retrieved successfully." -ForegroundColor Green
} else {
    Write-Host "`n[NOTICE] Hadoop Docker container is not currently running." -ForegroundColor Yellow
    Write-Host "         Executing standard MapReduce streaming pipeline locally (mapper | sort | reducer)..." -ForegroundColor White
    .\.venv\Scripts\python.exe mapreduce\run_mapreduce_local.py
}

Write-Host "`n[Verification] Validating output mathematical accuracy..." -ForegroundColor Yellow
.\.venv\Scripts\python.exe mapreduce\verify_baseline.py

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host " MAPREDUCE HISTORICAL AGGREGATION COMPLETE" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
