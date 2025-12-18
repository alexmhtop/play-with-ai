# Multi-stage build for FastAPI app using uv (no global pip) and non-root runtime
FROM python:3.14-slim AS builder

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

# Install toolchain and uv once
# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl -Ls https://astral.sh/uv/install.sh | sh

ENV PATH="/root/.local/bin:${PATH}"
WORKDIR /app

COPY requirements.txt ./
RUN uv pip install --system -r requirements.txt

COPY src ./src
# Strip __pycache__ to shrink image (guarded for platform Python path)
RUN python - <<'PY'
import pathlib
import subprocess
import sys

root = pathlib.Path("/usr/local/lib")
version_dir = root / f"python{sys.version_info.major}.{sys.version_info.minor}"
if version_dir.exists():
    subprocess.run(
        [
            "find",
            str(version_dir),
            "-type",
            "d",
            "-name",
            "__pycache__",
            "-prune",
            "-exec",
            "rm",
            "-rf",
            "{}",
            "+",
        ],
        check=True,
    )
PY

# Runtime image stays slim and non-root
FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create non-root user
RUN addgroup --system app && adduser --system --ingroup app app \
    && mkdir -p /app \
    && chown -R app:app /app

WORKDIR /app

# Copy installed deps and binaries from builder (match runtime Python version)
COPY --from=builder /usr/local/lib/python3.14 /usr/local/lib/python3.14
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn

# Copy application code
COPY --chown=app:app src ./src

USER app
EXPOSE 8000

CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
