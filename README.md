# 🛡️ Self-Healing Cloud Infrastructure

A production-grade self-healing system that **automatically detects and recovers failing containers** — no manual intervention required.

Built with Docker, Python, and Prometheus. Deploys locally in under 2 minutes.

![CI](https://github.com/YOUR_USERNAME/self-healing-cloud-infra/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)
![License](https://img.shields.io/badge/License-MIT-green)

---

## How It Works

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Host                          │
│                                                         │
│  ┌──────────────┐   GET /health   ┌─────────────────┐  │
│  │    Healer    │ ──────────────► │   sample-app    │  │
│  │  (Python)    │                 │   (Flask :8080) │  │
│  │              │ ◄── 200 / 503 ─ │                 │  │
│  │  3 failures? │                 └─────────────────┘  │
│  │  → restart   │                                       │
│  │  → Slack 🔔  │   scrape        ┌─────────────────┐  │
│  └──────────────┘ ──────────────► │   Prometheus    │  │
│                                   │    (:9090)      │  │
│                                   └─────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

1. The **Healer** polls every monitored container's `/health` endpoint every 15 seconds
2. If a container fails **3 consecutive checks**, the Healer restarts it via the Docker API
3. A **Slack alert** fires on every restart (optional — configure via webhook)
4. **Prometheus** scrapes metrics from all services for observability

---

## Project Structure

```
self-healing-cloud-infra/
├── healer/
│   ├── health_monitor.py   # Core polling and restart logic
│   ├── slack_alert.py      # Slack webhook notifications
│   ├── Dockerfile          # Multi-stage build for the healer
│   └── requirements.txt
├── sample-app/
│   ├── app.py              # Flask app with /health, /break, /fix endpoints
│   └── Dockerfile
├── prometheus/
│   └── prometheus.yml      # Scrape configuration
├── scripts/
│   └── simulate_failure.sh # Demo script — break and watch recovery
├── .github/workflows/
│   └── ci.yml              # GitHub Actions: lint, test, docker build
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose)
- Git

### 1. Clone and configure

```bash
git clone https://github.com/YOUR_USERNAME/self-healing-cloud-infra.git
cd self-healing-cloud-infra

# Optional: configure Slack alerts
cp .env.example .env
# Edit .env and add your SLACK_WEBHOOK_URL
```

### 2. Start all services

```bash
docker compose up --build
```

You should see three containers start:

| Container    | URL                          | Purpose                   |
|-------------|------------------------------|---------------------------|
| `sample-app` | http://localhost:8080/health | The monitored application |
| `prometheus` | http://localhost:9090        | Metrics dashboard         |
| `healer`     | (background service)         | Health monitor            |

### 3. Run the self-healing demo

Open a new terminal and run:

```bash
chmod +x scripts/simulate_failure.sh
./scripts/simulate_failure.sh
```

This will:
1. Confirm the app is healthy
2. Force it into an unhealthy state
3. Stream the healer's logs live
4. Confirm automatic recovery (~45 seconds)

**Expected output:**

```
[INFO]  === Self-Healing Demo ===
[ OK ]  App is currently healthy (HTTP 200)
[INFO]  Sending /break signal to sample-app...
[WARN]  App is now returning HTTP 503 on /health
[INFO]  Streaming healer logs...
         ⚠️  sample-app unhealthy (1/3)
         ⚠️  sample-app unhealthy (2/3)
         ⚠️  sample-app unhealthy (3/3)
         ⚠️  Restarting container: sample-app
         ✅  sample-app restarted successfully
[ OK ]  ✅  Recovery confirmed — app is healthy again (HTTP 200)
```

---

## Configuration

All healer settings are configurable via environment variables in `docker-compose.yml` or your `.env` file:

| Variable            | Default  | Description                                         |
|---------------------|----------|-----------------------------------------------------|
| `CHECK_INTERVAL`    | `15`     | Seconds between health polls                        |
| `FAILURE_THRESHOLD` | `3`      | Consecutive failures before a restart is triggered  |
| `REQUEST_TIMEOUT`   | `5`      | Per-request timeout in seconds                      |
| `HEALTH_PATH`       | `/health`| HTTP path polled on each monitored container        |
| `SLACK_WEBHOOK_URL` | *(empty)*| Slack Incoming Webhook URL — leave blank to disable |

### Marking a container as monitored

Add the label `monitored=true` to any container you want the healer to watch:

```yaml
# docker-compose.yml
services:
  your-app:
    image: your-image
    labels:
      monitored: "true"
```

---

## Slack Alerts

When configured, the healer sends formatted Slack alerts for every recovery event:

```
✅ Self-Healing Alert — sample-app
Container `sample-app` failed 3 health checks and was automatically restarted.
```

To enable:
1. Create a Slack app and add an Incoming Webhook: https://api.slack.com/messaging/webhooks
2. Add the webhook URL to your `.env` file:
   ```
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
   ```

---

## Prometheus Metrics

Visit **http://localhost:9090** to explore collected metrics.

Useful queries to try:

```promql
# Check if sample-app is up
up{job="sample-app"}

# HTTP request rate
rate(flask_http_request_total[1m])

# Process memory usage
process_resident_memory_bytes{job="sample-app"}
```

---

## Running Tests

```bash
cd healer
pip install -r requirements.txt pytest flake8

# Lint
flake8 . --max-line-length=100

# Unit tests
pytest ../tests/ -v
```

---

## Tech Stack

| Layer              | Technology                  |
|--------------------|-----------------------------|
| Containerisation   | Docker, Docker Compose      |
| Health monitoring  | Python 3.11, `docker` SDK   |
| Metrics collection | Prometheus 2.52             |
| Alerting           | Slack Incoming Webhooks     |
| CI/CD              | GitHub Actions              |
| Sample application | Flask 3.0                   |

---

## License

MIT — see [LICENSE](LICENSE) for details.
