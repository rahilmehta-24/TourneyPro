# TourneyPro Load Testing Guide & Performance Optimization Manual

This document provides a comprehensive operational guide for load testing the **TourneyPro** backend using **Grafana k6**, along with baseline benchmark results, bottleneck analysis, interactive web dashboard instructions, and production optimization strategies.

---

## 1. Architecture of the Load Testing Suite

The testing suite resides in the [`load_tests/`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/load_tests) directory and is structured modularly:

```text
load_tests/
├── config.js                      # Base URLs, ports, SLO thresholds, and HTTP headers
├── helpers/
│   └── auth.js                    # JWT authentication & session token manager
├── scenarios/
│   ├── smoke.js                   # Minimal verification test (1 VU, ~10s)
│   ├── public-browse.js           # Read-only public browse load test (up to 50 VUs)
│   ├── authenticated-user.js      # Authenticated user session test (up to 40 VUs)
│   ├── combined-load.js           # Realistic 70/30 mix of public visitors & logged-in players
│   └── stress-spike.js            # Sudden spike test simulating registration opening (up to 100 VUs)
├── run.sh                         # Automated CLI runner script
└── README.md                      # Quick-reference instructions
```

### Key Design Principles:
1. **Rate-Limit Resilience**: The TourneyPro API enforces an IP-level rate limiter on `/api/v1/auth/login` (10 requests/minute). To prevent artificial 429 throttling during load tests, credentials are authenticated once during the `setup()` lifecycle hook of k6 and distributed to Virtual Users (VUs) via Bearer JWT tokens.
2. **Realistic User Journeys**: Separates read-heavy traffic (browsing tournaments, categories, match schedules, and leaderboards) from write/authenticated traffic (checking user notifications, profiles, and registrations).
3. **Automated Verification**: Every response validates HTTP 200/201 status codes and JSON payload integrity.

---

## 2. Baseline Benchmark Results (Initial Run)

The test was executed using `load_tests/scenarios/combined-load.js` against the TourneyPro application powered by Gunicorn (`-w 4`) connected to remote Supabase PostgreSQL.

### Execution Metrics:
* **Total HTTP Requests Handled**: **1,201 requests**
* **Check Pass Rate**: **100.00%** (1,202 / 1,202 assertions passed)
* **HTTP Failure Rate**: **0.00%** (0 errors / 0 dropped connections)
* **Peak Concurrency**: **70 Virtual Users (VUs)** (50 public visitors + 20 authenticated players)
* **Test Duration**: **2 minutes 3.6 seconds**

```
  █ TOTAL RESULTS 

    checks_total.......: 1202    9.721115/s
    checks_succeeded...: 100.00% 1202 out of 1202
    checks_failed......: 0.00%   0 out of 1202

    ✓ login status is 200
    ✓ login returned access_token
    ✓ tournaments status 200
    ✓ users/me status 200
    ✓ notifications status 200
    ✓ leaderboard status 200
    ✓ academies status 200
    ✓ my-registrations status 200

    HTTP
    http_req_duration..............: avg=3.00s  min=296.69ms med=3.03s max=5.93s p(90)=5.02s p(95)=5.29s
    http_req_failed................: 0.00%      0 out of 1201
    http_reqs......................: 1201       9.71/s
```

---

## 3. Bottleneck & Root-Cause Analysis

### Key Takeaway:
* **Stability**: **Rock solid.** The backend did not crash, throw 500s, or drop connections under heavy concurrency.
* **Latency Profile**: While individual queries take ~300ms, latency under full 70-VU load rose to a median of **3.03s** and p95 of **5.29s**.

### Why did requests queue up?
1. **Synchronous Worker Limitation**:
   With 4 standard Gunicorn sync workers (`-w 4`), only **4 requests can be processed concurrently** at any millisecond.
2. **WAN Network Latency to Supabase**:
   Because the database is hosted remotely on AWS `ap-southeast-1` (Singapore), each database round-trip incurs ~150–300ms of network latency.
3. **Queueing Mechanics**:
   When 70 VUs issue requests simultaneously, 4 requests occupy the 4 workers, while the remaining 66 requests wait in Gunicorn's listen backlog. Each queued request waits:
   $$\text{Queue Time} \approx \frac{\text{Concurrent Requests}}{\text{Number of Workers}} \times \text{Average Request Latency}$$
   $$\text{Queue Time} \approx \frac{66}{4} \times 300\text{ms} \approx 4.95\text{ seconds}$$
   This exactly matches our observed p90/p95 of ~5.0–5.2 seconds.

---

## 4. Real-Time Web Dashboard & HTML Reports

Grafana k6 comes with an embedded, zero-dependency real-time **Web Dashboard**. It spins up a local HTTP server that streams live metrics via WebSockets directly to your web browser.

### How to Use `K6_WEB_DASHBOARD=true`

#### Command Syntax:
```bash
K6_WEB_DASHBOARD=true k6 run load_tests/scenarios/combined-load.js
```

When you execute this command:
1. k6 starts a local web service at **`http://127.0.0.1:5665`**.
2. Open **`http://127.0.0.1:5665`** in your browser to watch the live dashboard.
3. You will see real-time streaming charts for:
   * **Active Virtual Users (VUs)** timeline.
   * **Requests Per Second (RPS)** and total throughput.
   * **Response Time Percentiles** (p50, p90, p95, min, max, average).
   * **Check Assertions** pass/fail status in real-time.
   * **Per-Endpoint Latency Breakdown** for every route (`/api/v1/tournaments`, `/api/v1/users/me`, etc.).

---

### Dashboard Environment Options & Flags

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `K6_WEB_DASHBOARD` | `false` | Set to `true` to turn on the embedded web server. |
| `K6_WEB_DASHBOARD_OPEN` | `false` | Automatically opens your default web browser on test launch when set to `true`. |
| `K6_WEB_DASHBOARD_PORT` | `5665` | Custom port for the web dashboard if port 5665 is already in use. |
| `K6_WEB_DASHBOARD_EXPORT` | — | Path to save an interactive, self-contained **standalone HTML report** when the test finishes. |
| `K6_WEB_DASHBOARD_PERIOD` | `1s` | Chart refresh and aggregation interval (e.g. `500ms`, `1s`, `2s`). |

---

### Useful Command Recipes

#### 1. Auto-open the dashboard in your browser:
```bash
K6_WEB_DASHBOARD=true K6_WEB_DASHBOARD_OPEN=true k6 run load_tests/scenarios/combined-load.js
```

#### 2. Generate a persistent standalone HTML report to share or save:
```bash
K6_WEB_DASHBOARD=true K6_WEB_DASHBOARD_EXPORT=load_tests/test-report.html k6 run load_tests/scenarios/combined-load.js
```
*(The generated HTML file is fully self-contained with interactive charts — open it anytime in any browser without needing k6 running).*

#### 3. Using the `run.sh` Helper Script:
You can pass the `--dashboard` flag or set `DASHBOARD=true`:
```bash
# Using the CLI flag:
./load_tests/run.sh combined 5001 --dashboard

# Or via environment variable:
DASHBOARD=true ./load_tests/run.sh combined

# Export HTML report automatically:
EXPORT_HTML=report.html ./load_tests/run.sh combined
```

---

## 5. Optimization Strategies & Commands

To achieve **sub-500ms response times under 100+ concurrent VUs**, apply the following optimizations:

### Strategy 1: Enable Gunicorn Multi-Threading (Recommended First Step)
By adding worker threads, each Gunicorn worker process can handle multiple requests concurrently while waiting for database I/O, without requiring async code changes.

```bash
# Run with 4 worker processes and 4 threads each (16 concurrent request slots):
./venv/bin/gunicorn --workers 4 --threads 4 --bind 0.0.0.0:5001 run:app
```
* **Expected Result**: Cuts queue waiting time by ~75% ($16$ slots instead of $4$).

---

### Strategy 2: Use Asynchronous Event-Loop Workers (Gevent / Greenlet)
For I/O-bound web apps that spend most time waiting on database/network responses, Gevent allows each worker process to handle hundreds of concurrent requests using non-blocking greenlets.

#### Step 1: Install gevent
```bash
./venv/bin/pip install gevent
```

#### Step 2: Start Gunicorn with the Gevent worker class
```bash
./venv/bin/gunicorn \
  --workers 4 \
  --worker-class gevent \
  --worker-connections 1000 \
  --bind 0.0.0.0:5001 \
  run:app
```
* **Expected Result**: Eliminates backlog queueing almost entirely under 100 VUs.

---

### Strategy 3: Tune SQLAlchemy Connection Pool
When running high concurrency, ensure the SQLAlchemy engine connection pool matches or exceeds your worker concurrency.

In [`config.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/config.py), add pool configurations:
```python
if db_url and db_url.startswith('postgresql'):
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 20,           # Persistent connections kept open
        'max_overflow': 30,        # Additional burst connections allowed
        'pool_timeout': 30,        # Seconds to wait before giving up
        'pool_recycle': 1800,      # Recycle connections every 30 minutes
        'pool_pre_ping': True,     # Test connection liveness before executing
        'connect_args': {
            'prepare_threshold': None
        }
    }
```

---

### Strategy 4: Cache Public Read Endpoints (Flask-Caching / Redis)
Public endpoints like `/api/v1/tournaments` and `/api/v1/leaderboard` rarely change from second to second during peak traffic. Caching their responses for 10–30 seconds avoids hitting the database altogether.

```python
from flask_caching import Cache

cache = Cache(config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 15})
# or for production: CACHE_TYPE='RedisCache', CACHE_REDIS_URL='redis://...'

@api_bp.route('/tournaments', methods=['GET'])
@cache.cached(timeout=15, query_string=True)
def get_tournaments():
    ...
```
* **Expected Result**: Response time drops from 300ms to **< 5ms** for 90% of requests, enabling thousands of requests per second.

---

### Strategy 5: Test Against Local Database vs Remote Supabase
To isolate database network latency from application CPU load, run the server pointing to a local SQLite or PostgreSQL instance:

```bash
# Run server with local SQLite database (zero WAN network latency)
DATABASE_URL="" ./venv/bin/gunicorn --workers 4 --threads 4 --bind 0.0.0.0:5001 run:app
```

---

## 6. Execution Commands Cheat Sheet

### Running via Runner Script
```bash
# 1. Quick Smoke Test (1 VU, ~10s)
./load_tests/run.sh smoke

# 2. Public Read-Only Browsing (up to 50 VUs)
./load_tests/run.sh browse

# 3. Authenticated User Flows (up to 40 VUs)
./load_tests/run.sh auth

# 4. Realistic Combined Load Test (70% public, 30% authenticated)
./load_tests/run.sh combined

# 5. Combined Load Test with Live Web Dashboard
./load_tests/run.sh combined 5001 --dashboard

# 6. Spike / Registration Rush Test (rapid jump to 100 VUs)
./load_tests/run.sh spike
```

### Running Directly via k6 CLI
```bash
# Target custom port or environment
k6 run -e BASE_URL="http://localhost:5001" load_tests/scenarios/combined-load.js

# Custom credentials
k6 run \
  -e BASE_URL="http://localhost:5001" \
  -e AUTH_USERNAME="superadmin" \
  -e AUTH_PASSWORD="adminpassword" \
  load_tests/scenarios/authenticated-user.js

# Real-time Web Dashboard in Browser (http://127.0.0.1:5665)
K6_WEB_DASHBOARD=true K6_WEB_DASHBOARD_OPEN=true k6 run load_tests/scenarios/combined-load.js

# Export self-contained HTML report
K6_WEB_DASHBOARD=true K6_WEB_DASHBOARD_EXPORT=report.html k6 run load_tests/scenarios/combined-load.js

# Export raw metrics to JSON for custom reporting
k6 run --out json=results.json load_tests/scenarios/combined-load.js
```
