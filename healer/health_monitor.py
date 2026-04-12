"""
health_monitor.py
-----------------
Core self-healing loop. Every CHECK_INTERVAL seconds it:
  1. Lists all running containers labelled `monitored=true`
  2. Hits each container's /health endpoint
  3. If a container fails FAILURE_THRESHOLD consecutive checks → restarts it
  4. Fires a Slack alert on every restart action
"""

import os
import time
import logging
import requests
import docker
from slack_alert import send_slack_alert

# ── Configuration ────────────────────────────────────────────────────────────
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 15))       # seconds between polls
FAILURE_THRESHOLD = int(os.getenv("FAILURE_THRESHOLD", 3))  # consecutive failures before restart
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 5))      # per-request timeout in seconds
HEALTH_PATH = os.getenv("HEALTH_PATH", "/health")           # path to poll on each container

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Docker client ─────────────────────────────────────────────────────────────
client = docker.from_env()

# ── State: tracks consecutive failure counts per container name ───────────────
failure_counts: dict[str, int] = {}


def get_monitored_containers() -> list:
    """Return all running containers with the label monitored=true."""
    return client.containers.list(filters={"label": "monitored=true", "status": "running"})


def get_container_url(container) -> str | None:
    """
    Derive the health-check URL from the container's port bindings.
    Looks for the first host-mapped TCP port and builds http://localhost:<port>/health.
    Returns None if no port mapping is found.
    """
    ports = container.ports  # e.g. {'8080/tcp': [{'HostIp': '0.0.0.0', 'HostPort': '8080'}]}
    for _proto, bindings in ports.items():
        if bindings:
            host_port = bindings[0]["HostPort"]
            return f"http://localhost:{host_port}{HEALTH_PATH}"
    return None


def check_health(container) -> bool:
    """
    Returns True if the container's /health endpoint responds with HTTP 200.
    Returns False on any error (connection refused, timeout, non-200 status).
    """
    url = get_container_url(container)
    if not url:
        log.warning("No port mapping found for %s — skipping health check", container.name)
        return True  # don't penalise containers we can't reach by port

    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        return resp.status_code == 200
    except requests.exceptions.ConnectionError:
        log.debug("Connection refused for %s at %s", container.name, url)
        return False
    except requests.exceptions.Timeout:
        log.debug("Timeout hitting %s at %s", container.name, url)
        return False
    except requests.exceptions.RequestException as exc:
        log.debug("Request error for %s: %s", container.name, exc)
        return False


def restart_container(container) -> None:
    """
    Restart a failing container and notify Slack.
    Reloads the container object after restart so we have fresh state.
    """
    name = container.name
    log.warning(
        "⚠️  Restarting container: %s (failed %d consecutive checks)", name, FAILURE_THRESHOLD
    )

    try:
        container.restart(timeout=10)
        failure_counts[name] = 0  # reset counter after successful restart
        log.info("✅  %s restarted successfully", name)
        send_slack_alert(
            status="recovered",
            container_name=name,
            message=(
                f"Container `{name}` failed {FAILURE_THRESHOLD} health checks"
                " and was automatically restarted."
            ),
        )
    except docker.errors.APIError as exc:
        log.error("❌  Failed to restart %s: %s", name, exc)
        send_slack_alert(
            status="error",
            container_name=name,
            message=f"Tried to restart `{name}` but got a Docker API error: {exc}",
        )


def run_monitor_loop() -> None:
    """Main polling loop — runs forever until interrupted."""
    log.info(
        "🚀  Health monitor started (interval=%ds, threshold=%d)",
        CHECK_INTERVAL, FAILURE_THRESHOLD
    )

    while True:
        try:
            containers = get_monitored_containers()

            if not containers:
                log.info("No monitored containers found. Waiting...")
            else:
                for container in containers:
                    name = container.name
                    healthy = check_health(container)

                    if healthy:
                        if failure_counts.get(name, 0) > 0:
                            log.info("✅  %s recovered (resetting failure count)", name)
                        failure_counts[name] = 0
                        log.debug("OK  %s", name)
                    else:
                        failure_counts[name] = failure_counts.get(name, 0) + 1
                        count = failure_counts[name]
                        log.warning("🔴  %s unhealthy (%d/%d)", name, count, FAILURE_THRESHOLD)

                        if count >= FAILURE_THRESHOLD:
                            restart_container(container)

        except docker.errors.DockerException as exc:
            log.error("Docker error in monitor loop: %s", exc)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    run_monitor_loop()
