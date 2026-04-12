"""
app.py — Sample monitored application
--------------------------------------
A minimal Flask service that exposes:
  GET /         → "Hello" response
  GET /health   → health check endpoint (returns 200 or 503)
  POST /break   → forces the app into an unhealthy state (for demo)
  POST /fix     → restores the app to healthy (for demo)

The self-healing monitor watches /health. Use /break to simulate a failure
and watch the monitor detect it and restart the container automatically.
"""

import os
from flask import Flask, jsonify

app = Flask(__name__)
_healthy = True  # mutable state flag


@app.route("/")
def index():
    return jsonify({"service": "sample-app", "status": "running"})


@app.route("/health")
def health():
    if _healthy:
        return jsonify({"status": "ok"}), 200
    return jsonify({"status": "unhealthy", "reason": "manually broken for demo"}), 503


@app.route("/break", methods=["POST"])
def break_app():
    global _healthy
    _healthy = False
    return jsonify({"message": "App is now unhealthy. Monitor will detect and restart shortly."}), 200


@app.route("/fix", methods=["POST"])
def fix_app():
    global _healthy
    _healthy = True
    return jsonify({"message": "App is now healthy again."}), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
