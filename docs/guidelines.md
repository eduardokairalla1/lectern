# Code guidelines

Conventions this codebase follows. The first section is enforced by tooling;
everything after it is judgment the tools cannot check, so it is written down.

## What the tools enforce

```bash
scripts/test    # ruff check, ruff format --check, mypy, pytest
```

Configured in `pyproject.toml`:

- 80 columns, single quotes.
- One import per line, `from` imports before plain `import`, no grouping by
  origin (`no-sections`), first-party is `src`.
- Ruff rules `E, W, F, I, B, UP, SIM, C4`. `UP` targets Python 3.12, so new
  syntax is expected (`X | None`, PEP 695 generics).
- mypy with `disallow_untyped_defs`, over `src` and `tests`.

Two things the linter does *not* catch, worth knowing: blank-line rules
(E301 to E306) are preview-only in ruff, and `--enable-error-code=deprecated`
is off by default in mypy.

## File layout

Files are divided by comment markers. Three are standard:

```python
"""
One-line summary of the module.
"""

# --- IMPORTS ---
...

# --- GLOBALS ---
logger = logging.getLogger(__name__)

# --- CODE ---
...
```

Two blank lines separate every function, including methods inside a class.
This is stricter than PEP 8, which asks for one between methods, and ruff
cannot check it: the blank-line rules are preview-only.

A file may use a more specific marker when it genuinely helps
(`# --- PAYLOADS ---` and `# --- RESPONSES ---` in a schema module,
`# --- INPUT ---` / `# --- PIPELINE ---` / `# --- OUTPUT ---` in
`services/chatbot/types.py`), but the default is `# --- CODE ---`.

Module docstrings are one line. The exception is a module whose *design*
needs explaining, where a short paragraph prevents someone from "fixing" it
wrongly later: `middleware/cors.py` says why Starlette's CORSMiddleware is
not used, because that constraint is invisible from the code.

## Docstrings

Every function with arguments documents them:

```python
def _summary_key(session_id: str) -> str:
    """
    Redis key holding the conversation summary.

    :param session_id: Conversation identifier.

    :return: Redis key for the summary.
    """
```

Blank line before `:param:`, blank line before `:return:`. Use `:return:`
(the dominant form; `:returns:` also appears in older files).

Three accepted exceptions, all cases where the arguments are not the reader's
question: Pydantic validators, where the framework calls the function and the
argument is the field itself; nested closures; and test functions, covered
below.

## Comments

Lowercase, above the block, saying what happens and why:

```python
# open database connection
async with self._session() as session:

    # insert or update the session record
    stmt = pg_insert(Sessions).values(...)
```

Capitalise only when the first word is a proper noun or an acronym
(`# Redis is unavailable: log a warning and return None`, `# NOTE: ...`).

**Keep them short.** One line is the target, two is the ceiling. A comment
that needs a paragraph is usually a docstring, or a sign that the code below
wants splitting or has grown too complex.

`NOTE:` is the one exception to the ceiling. It exists precisely to record what
needs the room: a constraint, a trap, or why the obvious simplification is
wrong. Those are worth a paragraph, because the alternative is someone
"fixing" the code back into the bug.

A comment that repeats the code earns nothing. A comment that records a
decision, a constraint or a non-obvious consequence earns its place.

## Simplicity

A human reviews this code, and a human will maintain it. That is the constraint
the others answer to: code only its author or AI assistant can follow is a
defect, however correct it is.

**Prefer a data structure to a chain of `if`/`elif`.** A dictionary keyed by
whatever you are branching on, read with `.get()`, turns a decision tree into a
lookup, and a new case becomes an entry instead of another branch:

```python
_MESSAGE_RESOLVERS: dict[str, Callable[[ChatMessage], Awaitable[str]]] = {
    'text': resolve_text,
    'audio': resolve_audio,
}

resolver = _MESSAGE_RESOLVERS.get(chat_message.message_type)

# resolver is registered for the message type: raise an error
if resolver is None:
    raise UnsupportedMessageTypeError()
```

When order matters the table still wins. `_STREAM_ERROR_TABLE` in
`services/chatbot/events.py` is an ordered tuple of (exception types, result)
resolved by a single `next(...)`, and the rule that decides the order lives in
a comment beside the data instead of being implied by the shape of a ladder.

**Watch the branch count.** A function carrying many nested conditions is
usually several functions, or one function plus a table. Guard clauses that
return early beat nested `if`s, and a flat sequence of steps beats a tree.

**About generated code.** AI assistants tend to produce dense, heavily branched
code that reads as correct and is expensive for a person to verify. Volume is
not the goal. If a change cannot be explained in a sentence to the person
reviewing it, simplify it before proposing it.

## Naming

- Route input schemas end in `Payload`, route output schemas in `Response`
  (`ChatbotPayload`, `ChatbotResponse`), and live in
  `schemas/endpoints/<route>.py`, one module per route.
- Objects that a route merely serialises but that live longer than a request
  are not schemas. `Health` and `Info` are application state and live in
  `src/system.py`.
- Type placement follows one rule: `src/types/` is for shapes more than one
  layer speaks; `services/chatbot/types.py` is for the pipeline's own
  vocabulary.

## Errors

Every failure answers with `{"error": <slug>, "message": <text>}`. To add a
failure mode, declare a class; do not build a response by hand:

```python
class PayloadTooLargeError(BackendError):
    MESSAGE = 'Payload Too Large!'
    STATUS_CODE = 413
```

The slug is derived from the class name, and one handler covers every
subclass. Document it on the route with `error_responses(...)`, which reads
those same attributes, so the OpenAPI document cannot drift from behaviour.

**Do not re-type an error you cannot classify.** Wrapping a provider error
into a generic one costs the layers above the type they classify on: a rate
limit wrapped as `ProcessingError` reaches the stream as `unavailable`
instead of `rate_limit`. Log and re-raise instead:

```python
except Exception:
    logger.error('[Step: answer] failed. Session: %s', session_id,
                 exc_info=True)
    raise
```

**Keep `try` blocks around what can legitimately fail**, not around whole
functions. A `try` that spans a step's entire body turns a bug in your own
code into the same warning as a provider timeout, and hides it.

## Closed vocabularies are `Literal`

A set of allowed strings is a type, not a convention:

```python
ExecutionType = Literal['chatbot_answer', 'query_rewrite',
                        'metadata_extraction']
```

This is not decoration. A tag that the database `CHECK` constraint rejected
shipped once because it was a bare `str`. `StreamEventType` and
`StreamErrorCode` follow the same pattern.

## Configuration

Three homes, by nature of the value:

- **`.env`** (`src/config.py`): infrastructure, per deployment. URLs, keys,
  model names, limits.
- **`identity.yaml`**: the subject. Profile and persona. Unknown keys under
  `persona` are rejected, so a typo fails at startup instead of silently
  falling back to a default.
- **`ClassVar` in `Config`**: values shared across modules that are *not*
  deployment-tunable, such as the audio formats the transcription API
  accepts. They need a neutral home, not an environment variable.

## Migrations

A migration is a snapshot of a moment. It must not import a value that can
change, or replaying it later produces a different schema. When a constant is
mirrored in a migration (the `execution_type` pattern is), that is a
deliberate, commented duplication, and changing the constant means writing a
new revision.

## Tests

`tests/unit/t_*.py`, mirroring the surface under test rather than the module
tree. They target contracts: status codes, response shape, which events an
SSE stream emits, which persistence was scheduled.

**The test name is the documentation.** Name it as a sentence
(`test_response_invalid_session_id_returns_400`) and add a docstring only when
the reason is not in the name:

```python
def test_framework_errors_use_the_json_error_envelope(...) -> None:
    """404/405 come from Starlette's router, not from our code, and must
    still answer with {'error', 'message'} like every other failure."""
```

Fixtures are injected by pytest and never passed by hand, so they carry no
`:param:`. A docstring that restates the test name repeats the code and earns
nothing.

When a fix depends on a seam (a monkeypatched function, a registered
handler), add the test that fails without it. Verify that it does fail:
a test that passes for the wrong reason is worse than no test.
