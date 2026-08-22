# Development

How to run the development environment. See [architecture.md](architecture.md)
for what the pieces are, and [guidelines.md](guidelines.md) for how the code is
written.

## Setup

Everything runs in Docker. You need nothing else installed.

```bash
# 1. declare who this instance speaks for
cp identity.example.yaml identity.yaml && $EDITOR identity.yaml

# 2. your keys and settings
cp .env.example .env && $EDITOR .env

# 3. start the datastores and the development container
docker compose -f deploy/docker-compose.yaml -f deploy/docker-compose-dev.yaml up -d
```

## Working

```bash
ssh dev@localhost -p 2222          # no password, lands in the repository
```

The repository is mounted, so you edit on your machine and it runs in the
container. Nothing to rebuild while you work.

## Scripts and commands

The project has two scripts to help with development.

`scripts/dev` runs the application and the worker in the development
container.

> The worker is a second process you need to start in another terminal
> session.

```bash
scripts/dev
```

```bash
scripts/dev --worker
```

Without the worker, answers still work: tasks queue in Redis until a worker
takes them.

`scripts/test` runs the test suite and the linting.
IMPORTANT: you need to run this before committing any changes.

```bash
scripts/test
```

Command to run the database migrations:

```bash
uv run alembic upgrade head
```

## Running on your machine instead

If you would rather have the toolchain locally, install Python 3.12, uv and
ffmpeg, keep the three URLs in `.env` on `localhost`, and use the same
datastores:

```bash
uv sync
uv run alembic upgrade head
scripts/dev
```
