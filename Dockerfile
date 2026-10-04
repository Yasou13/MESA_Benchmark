# Build from standalone repository root:
# docker build -t mesa-benchmark .
FROM python:3.14.7-slim-bookworm@sha256:82bc3c539b8813ada9d68c63b40158fa002f7f33de9bf3312a3dfdc0620dff56

COPY --from=ghcr.io/astral-sh/uv:0.9.6@sha256:4b96ee9429583983fd172c33a02ecac5242d63fb46bc27804748e38c1cc9ad0d /uv /uvx /bin/

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/opt/mesa-model-cache \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

# The digest makes the starting filesystem reproducible, while Debian's
# security repository supplies fixed packages published after that digest.
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends build-essential gcc \
    && rm -rf /var/lib/apt/lists/*

# The pinned Python base ships vulnerable setuptools vendored utilities.  Keep
# the runtime tooling fixed independently of the application lockfile.
RUN python -m pip install --no-cache-dir setuptools==83.0.0

COPY pyproject.toml uv.lock MANIFEST.in README.md USAGE_GUIDE.md /app/
COPY mesa_benchmark /app/mesa_benchmark
COPY datasets /app/datasets
COPY scripts /app/scripts
RUN uv sync --frozen --no-dev --extra benchmarks
RUN uv pip install --python /app/.venv/bin/python setuptools==83.0.0
RUN HF_HUB_OFFLINE=0 TRANSFORMERS_OFFLINE=0 /app/.venv/bin/python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# Optionally install pinned MESA wheel when provided
ARG MESA_WHEEL=""
COPY ${MESA_WHEEL:-pyproject.toml} /tmp/mesa_wheel/
RUN if ls /tmp/mesa_wheel/*.whl 1> /dev/null 2>&1; then uv pip install --python /app/.venv/bin/python /tmp/mesa_wheel/*.whl; fi

RUN groupadd --gid 10001 mesa \
    && useradd --uid 10001 --gid mesa --create-home --shell /usr/sbin/nologin mesa \
    && install --directory --owner mesa --group mesa /app/results /opt/mesa-model-cache \
    && chown -R mesa:mesa /app

USER mesa:mesa
ENTRYPOINT ["/app/.venv/bin/mesa-benchmark", "run"]
CMD ["--config", "resource://configs/legacy/default.yaml"]
