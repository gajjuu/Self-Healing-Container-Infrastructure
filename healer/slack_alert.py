"""
slack_alert.py
--------------
Sends formatted Slack notifications via an Incoming Webhook URL.
Set the SLACK_WEBHOOK_URL environment variable to enable alerts.
If the variable is not set, alerts are logged locally and skipped.
"""

import os
import json
import logging
import requests

log = logging.getLogger(__name__)

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

# Colour codes for Slack message attachments
COLOURS = {
    "recovered": "#2ecc71",  # green
    "error":     "#e74c3c",  # red
    "warning":   "#f39c12",  # orange
}

ICONS = {
    "recovered": "✅",
    "error":     "❌",
    "warning":   "⚠️",
}


def send_slack_alert(status: str, container_name: str, message: str) -> None:
    """
    Post a Slack message for a self-healing event.

    Args:
        status:         One of 'recovered', 'error', 'warning'
        container_name: The Docker container name that was affected
        message:        Human-readable description of what happened
    """
    icon = ICONS.get(status, "ℹ️")
    colour = COLOURS.get(status, "#95a5a6")
    title = f"{icon} Self-Healing Alert — {container_name}"

    payload = {
        "attachments": [
            {
                "color":    colour,
                "title":    title,
                "text":     message,
                "footer":   "Self-Healing Infrastructure Monitor",
                "ts":       int(__import__("time").time()),
            }
        ]
    }

    if not SLACK_WEBHOOK_URL:
        log.info("[SLACK SKIPPED — no webhook configured] %s: %s", title, message)
        return

    try:
        resp = requests.post(
            SLACK_WEBHOOK_URL,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=5,
        )
        if resp.status_code != 200:
            log.warning("Slack webhook returned %d: %s", resp.status_code, resp.text)
        else:
            log.info("Slack alert sent for %s (%s)", container_name, status)
    except requests.exceptions.RequestException as exc:
        log.error("Failed to send Slack alert: %s", exc)
