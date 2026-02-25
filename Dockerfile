# ----------------------------
# Base Image
# ----------------------------
FROM python:3.11-slim

# ----------------------------
# Environment
# ----------------------------
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ----------------------------
# System Dependencies
# ----------------------------
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# ----------------------------
# Install uv (Astral)
# ----------------------------
RUN curl -Ls https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# ----------------------------
# Create Non-Root User
# ----------------------------
RUN useradd -m auditor
WORKDIR /app
RUN chown -R auditor:auditor /app
USER auditor

# ----------------------------
# Copy Project Files
# ----------------------------
COPY --chown=auditor:auditor pyproject.toml uv.lock* ./
COPY --chown=auditor:auditor . .

# ----------------------------
# Install Dependencies (uv sync)
# ----------------------------
RUN uv sync --frozen

# ----------------------------
# Expose Port (if API)
# ----------------------------
EXPOSE 8000

# ----------------------------
# Default Command
# ----------------------------
CMD ["uv", "run", "main.py"]