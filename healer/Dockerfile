# ── Stage 1: dependency install ───────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install dependencies into a separate directory so the final image stays lean
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: runtime image ────────────────────────────────────────────────────
FROM python:3.11-slim

LABEL maintainer="gajendra"
LABEL description="Self-healing health monitor for Docker containers"

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /install /usr/local

# Copy application source
COPY health_monitor.py slack_alert.py ./

# The healer needs access to the Docker socket (mounted at runtime)
# Never run as root in production — create a non-root user
RUN useradd --no-create-home --shell /bin/false healer
USER healer

# No ports exposed — this is a background service, not a server
CMD ["python", "-u", "health_monitor.py"]
