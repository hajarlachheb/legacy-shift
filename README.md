# LegacyShift

**AI-powered legacy code migration tool** — explains, tests, and rewrites old code safely.

Banks and insurers run on millions of lines of legacy Java (and COBOL). Nobody wants to touch it because if it breaks, the business loses money. LegacyShift gives engineers an AI-assisted pipeline that **prioritises test-driven safety** over speed: it generates a comprehensive test suite *before* attempting translation, then uses a feedback loop to iteratively fix failures until the tests pass.

---

## Demo

The web UI lets you paste Java code, **parse** its structure, **explain** it in plain English, **generate tests**, and **translate** to Python — all in one place.

Run the app with `uvicorn legacy_shift.api:app --host 0.0.0.0 --port 8000` and open **http://localhost:8000**.

### Parse — structural summary (no LLM)

Parse Java to see classes, methods, imports, and a structural summary.

![Parse demo](docs/screenshots/demo-parse.png)

### Explain — plain-English breakdown

Get a plain-English explanation of what the code does and how it behaves.

![Explain demo](docs/screenshots/demo-explain.png)

### Tests — generated pytest suite

Generate a pytest suite before translation; the pipeline retries until tests pass or max iterations.

![Tests demo](docs/screenshots/demo-tests.png)

### Translated — Java → Python

Java is translated to Python with dataclasses, type hints, and preserved business logic.

![Translated demo](docs/screenshots/demo-translated.png)

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     LegacyShift Pipeline                     │
│                                                              │
│  ┌─────────┐   ┌─────────┐   ┌───────────┐   ┌──────────┐  │
│  │  Parse   │──▶│ Explain │──▶│  Generate  │──▶│Translate │  │
│  │(Tree-    │   │  (LLM)  │   │   Tests    │   │  (LLM)   │  │
│  │ sitter)  │   │         │   │   (LLM)    │   │          │  │
│  └─────────┘   └─────────┘   └───────────┘   └────┬─────┘  │
│                                                     │        │
│                              ┌───────────┐   ┌─────▼─────┐  │
│                              │  Retry w/  │◀──│   Run     │  │
│                              │  Feedback  │   │  Tests    │  │
│                              │  (LLM)     │──▶│  (pytest) │  │
│                              └───────────┘   └───────────┘  │
│                                                              │
│  Observability: LangSmith / Phoenix    Vector DB: pgvector   │
│  LLM Routing:  LiteLLM                API: FastAPI           │
└──────────────────────────────────────────────────────────────┘
```

### Key design decisions

| Concern | Choice | Why |
|---------|--------|-----|
| **AST parsing** | Tree-sitter (Java grammar) | Structural context helps the LLM understand the code beyond raw text |
| **Prompt chain** | LangGraph state machine | Deterministic flow with conditional retry edges |
| **Test-first safety** | Tests generated *before* translation | The tests define correctness; the translator must satisfy them |
| **Feedback loop** | pytest stdout fed back into translation prompt | Self-healing: the LLM sees its own failures and fixes them |
| **LLM routing** | LiteLLM / `init_chat_model` | Swap providers (OpenAI, Anthropic, Azure) without code changes |
| **Pattern memory** | pgvector | Store successful translations as few-shot examples for future runs |
| **Observability** | LangSmith + Arize Phoenix | Full trace of every LLM call for evaluation and debugging |
| **Packaging** | Docker Compose | One command to spin up app + Postgres + Phoenix |

---

## Quick Start

### 1. Clone and configure

```bash
git clone <repo-url> && cd legacy-shift
cp .env.example .env
# Edit .env — set OPENAI_API_KEY (or Azure) for paid APIs, or use the free option below
```

**Free local model (no API key):** To use a free model with no quota or billing, use [Ollama](https://ollama.com). Install Ollama, then in a terminal run:

```bash
ollama run llama3.2
```

Leave `OPENAI_API_KEY` and Azure keys empty in `.env`. The app will use `ollama/llama3.2` automatically. You can also set `DEFAULT_MODEL=ollama/llama3.2` and `OLLAMA_BASE_URL=http://localhost:11434` explicitly.

### 2a. Run with Docker (recommended)

```bash
docker compose up --build
```

This starts:
- **App** on `http://localhost:8000` (FastAPI)
- **Postgres + pgvector** on port 5432
- **Phoenix** on `http://localhost:6006` (trace UI)

### 2b. Run locally

```bash
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

### 3. Use the CLI

```bash
# Full migration pipeline (explain → test → translate → verify)
legacy-shift migrate examples/BankAccount.java -o output/

# Just explain the code
legacy-shift explain examples/BankAccount.java

# Just generate tests (no translation)
legacy-shift generate-tests examples/BankAccount.java -o output/
```

### 4. Use the API

```bash
# Parse only (no LLM, instant)
curl -X POST http://localhost:8000/parse \
  -H "Content-Type: application/json" \
  -d '{"source_code": "public class Foo { public int bar() { return 42; } }"}'

# Full migration
curl -X POST http://localhost:8000/migrate \
  -H "Content-Type: application/json" \
  -d @- <<'EOF'
{
  "source_code": "... your Java code ...",
  "max_retries": 3
}
EOF
```

Interactive API docs (OpenAPI) are at **http://localhost:8000/docs** when the server is running.

---

## Limitations

- **Source language:** Parser and prompts target Java 8. Multi-file or multi-class projects need to be migrated one class/file at a time.
- **Human review:** Output is AI-generated. “Partial” status means tests did not all pass; always review and test translated code before production use.
- **Scope:** Very large files may hit timeouts or token limits; consider splitting or setting `MIGRATION_TIMEOUT_SECONDS` and `MAX_SOURCE_CODE_CHARS` in `.env`.
- **Pattern store:** Few-shot learning and pattern storage require Postgres + pgvector and (for embeddings) `OPENAI_API_KEY`. Without them, translations still run but do not improve from past runs.

---

## Project Structure

```
legacy-shift/
├── legacy_shift/
│   ├── cli.py              # Click CLI (migrate, explain, generate-tests)
│   ├── api.py              # FastAPI REST server
│   ├── config.py           # Pydantic Settings (.env loading)
│   ├── graph/
│   │   ├── state.py        # MigrationState TypedDict
│   │   ├── nodes.py        # LangGraph node functions (explain, test_gen, translate)
│   │   └── workflow.py     # LangGraph compile (entry → explain → test_gen → translate → run_tests ↻)
│   ├── parser/
│   │   └── ast_parser.py   # Tree-sitter Java parser → structured ClassInfo/MethodInfo
│   ├── vector/
│   │   └── store.py        # pgvector pattern store (successful translations as few-shot)
│   ├── feedback/
│   │   └── loop.py         # Run pytest in tmpdir, capture pass/fail, return errors
│   ├── tracing/
│   │   └── observability.py # LiteLLM init + LangSmith + Phoenix OTEL setup
│   └── prompts/
│       ├── explain.py       # Explain prompt template
│       ├── test_gen.py      # Test generation prompt template
│       └── translate.py     # Translation prompt template (with feedback variant)
├── tests/                   # pytest suite for the tool itself
├── examples/                # Sample Java 8 files (BankAccount, InsurancePolicy)
├── Dockerfile
├── docker-compose.yml       # app + postgres/pgvector + phoenix
├── pyproject.toml
└── .env.example
```

---

## Running Tests

```bash
pip install -e ".[dev]"
python -m pytest -v
```

On Windows, use `python -m pytest -v` so the venv’s pytest is used (the `pytest` script may not be on PATH).

The test suite covers:
- **Parser tests** — verify Tree-sitter extracts classes, methods, fields, imports
- **Graph tests** — verify the LangGraph compiles and has expected nodes
- **API tests** — verify FastAPI /parse and /health endpoints
- **Feedback tests** — verify the test-runner correctly detects pass/fail

---

## Extending

### Add a new source language

1. Install the Tree-sitter grammar (`tree-sitter-cobol`, etc.)
2. Create a new parser class in `legacy_shift/parser/`
3. Add language-specific prompt templates in `legacy_shift/prompts/`

### Add a new target language

1. Add a translation prompt variant in `legacy_shift/prompts/translate.py`
2. Update `run_tests_node` in `legacy_shift/feedback/loop.py` to run the target language's test runner

### Improve accuracy over time

After each successful migration, store the (source, translation) pair in pgvector via `PatternStore.add_pattern()`. Future runs can retrieve similar patterns as few-shot examples.

---

## License

MIT
