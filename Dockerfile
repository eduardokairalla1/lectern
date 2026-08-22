# --- Build ---
FROM python:3.12.13-slim-bookworm AS build

# install build dependencies
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    libpq-dev \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# install uv
COPY --from=ghcr.io/astral-sh/uv:0.11.24 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

# copy lock files first for better layer caching
COPY pyproject.toml uv.lock ./

# install dependencies without the project
RUN uv sync --frozen --no-dev --no-install-project

# copy application code
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./
COPY scripts/init-api scripts/init-worker ./

# install the project itself
RUN uv sync --frozen --no-dev


# --- Production base ---
FROM python:3.12.13-slim-bookworm AS base

# locale and timezone
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV TZ=UTC
ENV PATH="/app/.venv/bin:$PATH"

# install runtime dependencies
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# install ffprobe from mwader/static-ffmpeg
COPY --from=mwader/static-ffmpeg:7.1 /ffprobe /usr/local/bin/ffprobe

# create a non-root user to run the application
RUN groupadd --gid 10001 app \
 && useradd --uid 10001 --gid app --create-home app

# set the working directory
WORKDIR /app

# copy built application from build stage
COPY --from=build --chown=app:app /app /app

# switch to the non-root user
USER app

# expose the port that the application will run on
EXPOSE 8000


# --- Worker ---
FROM base AS worker
CMD ["/app/init-worker"]

# --- API ---
FROM base AS api
CMD ["/app/init-api"]
