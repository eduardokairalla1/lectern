<p align="center">
  <img src="assets/lectern-banner.png"
       alt="Lectern — Declare who speaks. Ingest what they know. Deploy."
       width="100%">
</p>

![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-DB-lightblue)
![Redis](https://img.shields.io/badge/Redis-Cache%20%2B%20Memory-red)
![Qdrant](https://img.shields.io/badge/Qdrant-Vector%20Store-purple)
![Celery](https://img.shields.io/badge/Celery-Worker-37814A)
![OpenAI](https://img.shields.io/badge/OpenAI-LLM%20%2B%20Embeddings-412991)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)
![License](https://img.shields.io/badge/License-Apache%202.0-D22128)

## Description

**Lectern** is a self-hostable, headless backend that turns a declared identity
and a set of documents into a grounded conversational API.

The system offers:
- Retrieval-augmented answers, as a single JSON document or streamed over SSE
- Text or audio questions, transcribed server-side
- Per-session memory (rolling summary plus recent interactions)
- Analytics on every exchange: retrieved documents and scores, token usage per
  model call, and visitor feedback

> The subject can be a person, a company or a product. It is whoever the deployment's identity file declares.

### Zero pipeline configuration. All subject configuration.

You do not choose *how* it thinks. The pipeline ships assembled and wired,
`load_memory → rewrite → retrieve → answer`, with grounding, memory, cache and
analytics already in place. You declare *what it speaks about*, and it does not
stray from that: it never states a fact that is not in your corpus, and it
records every time it could not answer.

---

## Documentation

- [Architecture](docs/architecture.md) — layers, request flows, and the
  reasoning behind the notable decisions.
- [Code guidelines](docs/guidelines.md) — conventions the codebase follows.
- [Domain concepts](docs/concepts.md) — what an exchange, an execution, the
  memory and the cache actually are.

---

## Configuration

**`identity.yaml`** — the subject: the profile served by `/api/whoami` and the
persona the assistant speaks in. `identity.example.yaml` documents every field.
Unknown keys under `persona` are rejected rather than ignored, so a typo fails
at startup instead of quietly changing behaviour.

**`.env`** — infrastructure: database URLs, API keys, model names, limits.
See `.env.example` for the settings a deployment normally sets.

Two settings worth knowing:

- `API_PREFIX` (default `/api`) — every route lives under it, and the reverse
  proxy is expected to forward it as-is, not strip it.
- `CORS_ORIGINS` — comma-separated. `/api/whoami` is open to any origin
  regardless; everything else is restricted to this list.

---

## Architecture

How a request travels, and which layer owns what. The full walkthrough, with
the streaming and non-streaming flows, is in
[docs/architecture.md](docs/architecture.md).

```mermaid
graph TD
    Client[Client / browser / agent]
    Router["routers/ — HTTP boundary<br/>(auth, request/response shape)"]
    Identity["identity.yaml — the subject<br/>(profile + persona)"]
    Orchestrator["services/chatbot/respond.py<br/>services/chatbot/respond_stream.py"]
    Pipeline["services/chatbot/pipeline.py<br/>+ steps/ (load_memory, rewrite, retriever, answer)"]
    Repo["databases/relational/repositories/"]
    DB[(Postgres)]
    Redis[(Redis — memory + cache)]
    Qdrant[(Qdrant — RAG)]
    Worker["tasks/chatbot/ — Celery worker<br/>(fire-and-forget persistence)"]

    Client --> Router --> Orchestrator --> Pipeline
    Identity -.-> Router
    Identity -.-> Pipeline
    Pipeline --> Redis
    Pipeline --> Qdrant
    Orchestrator -- "schedule_persistence (async)" --> Worker
    Worker --> Repo --> DB
```

---

## Tech Stack

| Layer                | Technology                                      |
|----------------------|-------------------------------------------------|
| **Language**         | Python 3.12                                     |
| **Framework**        | FastAPI + Uvicorn                               |
| **Database**         | PostgreSQL                                      |
| **ORM**              | SQLAlchemy (async) + psycopg                    |
| **Migrations**       | Alembic                                         |
| **Vector store**     | Qdrant                                          |
| **Cache and memory** | Redis                                           |
| **Background jobs**  | Celery                                          |
| **LLM**              | LangChain + OpenAI (chat, embeddings, Whisper)  |
| **Validation**       | Pydantic + pydantic-settings                    |
| **Identity config**  | YAML                                            |
| **Audio**            | ffprobe (duration) + filetype (format sniffing) |
| **Tooling**          | uv, Ruff, mypy, pytest                          |
| **Containerization** | Docker                                          |

---

## Dev Setup

### Requirements

- [Python 3.12+](https://docs.python.org/3.12/) — runtime
- [uv](https://docs.astral.sh/uv/) — dependencies and virtual environment
- [PostgreSQL](https://www.postgresql.org/docs/) — exchanges, executions and feedback
- [Redis](https://redis.io/docs/latest/) — response cache and conversation memory
- [Qdrant](https://qdrant.tech/documentation/) — vector store for the indexed documents
- [ffmpeg](https://ffmpeg.org/ffprobe.html) — provides `ffprobe`, which reads the duration of uploaded audio
- [OpenAI API key](https://platform.openai.com/docs/api-reference) — chat, embeddings and transcription

### Running it

```bash
# 1. install dependencies
uv sync

# 2. declare who this instance speaks for
cp identity.example.yaml identity.yaml && $EDITOR identity.yaml

# 3. configure infrastructure
cp .env.example .env && $EDITOR .env

# 4. create the database schema
uv run alembic upgrade head

# 5. run it
scripts/dev
```

The server listens on `http://localhost:8000`, with docs at
`/api/docs`.

Before committing, run `scripts/test` — it lints, checks formatting and
types, and runs the unit tests.

The background worker persists analytics (sessions, exchanges, token usage and
feedback), refreshes conversation summaries and writes the response cache.
Answers work without it, tasks queue up in Redis until a worker consumes them,
so it is optional in development, with two caveats: nothing reaches PostgreSQL,
and no answer is ever cached.

Run the worker in the other process:

```bash
scripts/dev --worker
```

---

## License

[Apache-2.0](LICENSE). No usage restrictions, no source-available clause: you
can run it, modify it and deploy it commercially. The patent grant and the
trademark reservation in sections 3 and 6 are the reason for choosing it over
MIT.
