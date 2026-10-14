# NYC Taxi Demand Heatmap Generation
**College Big Data Analytics Project**  
**Architecture:** Hybrid Lambda (Hadoop HDFS/MapReduce + Apache Kafka + Plotly Dash)  
**Developer Profile:** Windows 11 / 10 | 8 GB RAM Laptop Budget  

---

## 1. Problem Statement & Project Objective

### Problem Statement
Taxi fleet operators cannot effectively match driver supply to passenger demand across dynamic urban taxi zones. In peak hours, this leads to long passenger wait times in underserved zones and excessive fuel consumption or idle drivers in oversupplied zones.

### Project Objective
1. **Historical Baseline Aggregation:** Ingest official NYC Yellow Taxi Trip Records into Hadoop HDFS and execute Python Hadoop Streaming MapReduce (`mapper.py` and `reducer.py`) to calculate baseline pickup averages per zone and hour.
2. **Real-Time Event Streaming:** Stream simulated real-time trip-start events through Apache Kafka into a rolling 15-minute sliding micro-aggregation window.
3. **Surge Synthesis Engine:** Synthesize historical MapReduce hourly baselines with real-time Kafka window counts to compute a transparent **Estimated Pickup Surge Ratio** across all 265 NYC taxi zones.
4. **Interactive Geospatial Dashboard:** Visualize real-time demand using a Plotly Dash Mapbox choropleth heatmap and a ranked Top 10 High-Demand Leaderboard.
5. **Automated 10-Minute Refresh:** Refresh dashboard figures automatically every 10 minutes (`600,000 ms`) without application restarts.
6. **Domain & Data Integrity:** Explicitly distinguish observed pickup demand surges from actual unmet passenger demand, acknowledging that NYC TLC records capture completed trip starts rather than passenger search attempts or driver telematics.

---

## 2. Architecture & Data Flow

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   HISTORICAL BATCH LAYER (HADOOP)                      │
│  NYC TLC Trip Data  ──►  HDFS Storage  ──►  Hadoop MapReduce Job       │
│  (100k Sample CSV)       (/taxi/raw/)       (mapper.py & reducer.py)   │
│                                                       │                │
│                                                       ▼                │
│                                             historical_baseline.csv    │
└───────────────────────────────────────────────────────┬────────────────┘
                                                        │
┌───────────────────────────────────────────────────────┼────────────────┐
│                   SPEED STREAMING LAYER (KAFKA)       │                │
│  Trip-Start Producer ──►  Kafka Topic  ──►  Window Consumer            │
│  (Rate-limited JSON)      (trip-starts)     (15-min Sliding Window)    │
│                                                       │                │
│                                                       ▼                │
│                                             live_window_pickups.json   │
└───────────────────────────────────────────────────────┬────────────────┘
                                                        │
                                                        ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   SERVING & VISUALIZATION LAYER                        │
│                     analytics/surge_calculator.py                      │
│                                   │                                    │
│                                   ▼                                    │
│                         Plotly Dash Dashboard                          │
│               Mapbox Heatmap  •  Top 10 Chart  •  KPI Cards            │
│                 Auto-Refreshed Every 10 Minutes (600,000 ms)           │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Hardware Budgeting (8 GB RAM Developer Laptop)

Running Hadoop and Kafka on an 8 GB machine requires strict memory limits:

| Component | Runtime Context | Allocated RAM | Memory Protection Strategy |
| :--- | :--- | :--- | :--- |
| **Apache Kafka (KRaft)** | Docker Container | **512 MB** | KRaft mode eliminates ZooKeeper entirely, saving ~350 MB RAM. |
| **Hadoop (HDFS + YARN)** | Single-Node Container | **1,792 MB** | NameNode, DataNode, and MapReduce tasks are capped at `-Xmx192m` to `-Xmx256m`. |
| **Python Services & Dash** | Windows Host (`.venv`) | **~500 MB** | Runs directly on Windows host; avoids heavy containerized Python runtimes. |
| **Windows OS & Editor** | Host System | **~4.5 GB** | Leaves ample RAM for Windows 11 and VS Code without swap thrashing. |

---

## 4. Quick Start (Single-Command Execution)

### Startup
Open Windows PowerShell in the project root:
```powershell
.\scripts\start_all.ps1
```
This script will:
1. Verify the Python virtual environment (`.venv`).
2. Verify datasets and GeoJSON polygon boundaries.
3. Verify the Hadoop MapReduce historical baseline.
4. Stream trip-start events and compute the 15-minute rolling window snapshot.
5. Compute the demand surge synthesis across all 265 zones.
6. Launch the Dash web application and open **`http://127.0.0.1:8050`** in your browser.

### Shutdown
To stop all services cleanly and release all system RAM:
```powershell
.\scripts\stop_all.ps1
```

---

## 5. Step-by-Step Manual Execution & Verification

### Step 1: Environment Diagnostic Verification
```powershell
.\.venv\Scripts\Activate.ps1
powershell.exe -ExecutionPolicy Bypass -File .\scripts\verify_environment.ps1
pytest -v tests\test_environment.py
```

### Step 2: Dataset Acquisition & Sample Preprocessing
```powershell
python scripts\02_download_and_sample_data.py
pytest -v tests\test_dataset_sampling.py
```

### Step 3: Hadoop MapReduce Historical Aggregation
```powershell
# Runs MapReduce streaming locally (mapper | sort | reducer)
python mapreduce\run_mapreduce_local.py

# Independent mathematical ground-truth verification
python mapreduce\verify_baseline.py
pytest -v tests\test_mapreduce_pipeline.py
```

### Step 4: Kafka Real-Time Event Streaming
```powershell
# Produces trip-start events and consumes them into a 15-minute rolling window
powershell.exe -ExecutionPolicy Bypass -File .\scripts\04_start_streaming.ps1
pytest -v tests\test_kafka_streaming.py
```

### Step 5: Demand Surge Analytics & Top 10 Ranking
```powershell
powershell.exe -ExecutionPolicy Bypass -File .\scripts\05_run_surge_analytics.ps1
pytest -v tests\test_surge_analytics.py
```

### Step 6: Interactive Plotly Dash Web Application
```powershell
powershell.exe -ExecutionPolicy Bypass -File .\scripts\06_launch_dashboard.ps1
pytest -v tests\test_dashboard_components.py
```

### Step 7: Run Full Automated Test Suite (23 Passing Tests)
```powershell
pytest -v
```

---

## 6. Mathematical Formulation & Domain Transparency

### Historical Baseline ($B_{i, h}^{\text{window}}$)
For each zone $i$ and hour $h$, MapReduce computes the total historical pickups. Because the live streaming window is 15 minutes, expected pickups are scaled:
$$B_{i, h}^{\text{window}} = B_{i, h} \times \frac{15}{60}$$

### Estimated Pickup Surge Ratio
$$\text{Surge Ratio}_i = \frac{L_i}{B_{i, h}^{\text{window}} + \epsilon}$$
* $L_i$: Live pickup count observed in the streaming window.
* $\epsilon = 1.0$: Smoothing factor to prevent division-by-zero or false alarms in low-volume zones.

### Domain Integrity Distinction
* **Measured:** Observed trip-start velocity relative to historical hourly pickup patterns.
* **Unmeasured:** Passenger wait times, unmet hailing demand, and idle driver counts (because NYC TLC trip records only capture served/started trips without real-time vehicle telematics).

---

## 7. College Viva & Examination Q&A Cheat Sheet

**Q1: Why did you use Hadoop MapReduce instead of a simple database query?**  
*Answer:* In real-world enterprise architectures, historical datasets span hundreds of millions of trip records over years (terabytes of data). Hadoop MapReduce allows distributed batch processing across HDFS nodes, scaling horizontally without memory bottlenecks.

**Q2: What is the purpose of Kafka in this architecture?**  
*Answer:* Apache Kafka acts as a distributed, fault-tolerant message broker decoupling high-velocity event producers (taxi meters/apps) from consumers. It allows real-time rolling-window micro-aggregations without polling relational databases.

**Q3: Why is Kafka KRaft mode significant?**  
*Answer:* In Kafka 3.3+, KRaft (Kafka Raft Metadata mode) replaces ZooKeeper. This eliminates an entire distributed daemon, dramatically simplifying deployment and saving ~350 MB of RAM on developer machines.

**Q4: How does the dashboard refresh without restarting the server?**  
*Answer:* The dashboard uses Dash Core Component `dcc.Interval(id="interval-component", interval=600000)`. Every 10 minutes (600,000 ms), the browser triggers a client-side callback that re-executes the data query and updates the Plotly figures reactively in-place without reloading the page or restarting the server.
