# TourneyPro Grafana k6 Load Testing Suite

A modular load testing framework for the TourneyPro Flask & REST API backend using **Grafana k6**.

---

## 📁 Directory Structure

```text
load_tests/
├── config.js                      # Base URLs, ports, thresholds, and headers
├── helpers/
│   └── auth.js                    # JWT login helper & auth header generator
├── scenarios/
│   ├── smoke.js                   # Minimal verification test (1 VU)
│   ├── public-browse.js           # Read-only public browse load test (up to 50 VUs)
│   ├── authenticated-user.js      # Authenticated user session test (up to 40 VUs)
│   ├── combined-load.js           # Realistic 70/30 mix of public & authenticated users
│   └── stress-spike.js            # Rapid spike test (up to 100 VUs)
├── run.sh                         # Convenient test runner script (with --dashboard support)
└── README.md                      # Documentation & usage guide
```

---

## ⚡ Quick Start

### 1. Start the Local Server
```bash
# Standard dev server (port 5001)
python run.py

# OR multi-worker Gunicorn server (recommended for >20 VUs)
./venv/bin/gunicorn -w 4 -b 0.0.0.0:5001 run:app
```

---

### 2. Run Test Scenarios

```bash
# Smoke test (checks endpoint reachability and credentials)
./load_tests/run.sh smoke

# Public browsing test (read-heavy, ramps up to 50 VUs)
./load_tests/run.sh browse

# Authenticated user test (JWT-authenticated profile and registrations)
./load_tests/run.sh auth

# Combined realistic load test (70% public visitors, 30% authenticated players)
./load_tests/run.sh combined

# Spike / registration rush test (rapid jump to 100 VUs)
./load_tests/run.sh spike
```

---

## 📊 Live Web Dashboard & HTML Reports

Grafana k6 provides a built-in real-time web interface:

### 1. Run with live browser dashboard
```bash
# Automatically opens http://127.0.0.1:5665 in your browser:
K6_WEB_DASHBOARD=true K6_WEB_DASHBOARD_OPEN=true k6 run load_tests/scenarios/combined-load.js

# Or using the runner script:
./load_tests/run.sh combined 5001 --dashboard
```

### 2. Export a standalone interactive HTML report
```bash
K6_WEB_DASHBOARD=true K6_WEB_DASHBOARD_EXPORT=report.html k6 run load_tests/scenarios/combined-load.js
```

---

## ⚙️ Dashboard Environment Variables

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `K6_WEB_DASHBOARD` | `false` | Enables embedded web dashboard server |
| `K6_WEB_DASHBOARD_OPEN` | `false` | Auto-opens default web browser on start (`true`/`false`) |
| `K6_WEB_DASHBOARD_PORT` | `5665` | Local port for dashboard (default `5665`) |
| `K6_WEB_DASHBOARD_EXPORT` | — | Path to export self-contained static HTML report |
| `K6_WEB_DASHBOARD_PERIOD` | `1s` | Metrics polling and chart refresh period |
