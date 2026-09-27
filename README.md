# My-Rag-based-project — Doctor Nearby You

A learning project for a conversational doctor-finder for Bangladesh.

## Project structure

```text
crawler/       Python scraper, scraper tests, and exported doctor data
backend/       Go HTTP API and business logic
rag/           Small Gemini embedding and similarity experiment
db/            PostgreSQL schema and migrations
frontend/      Patient chat page
docs/          PRD and step-by-step learning notes
go.mod         Shared Go module for backend and RAG experiments
```

The current backend is still a keyword-based prototype: it loads
`crawler/data/doctors.jsonl` into memory and searches doctor fields. The
standalone program in `rag/` calls Gemini to create sample embeddings and
compares two vectors. The app does not yet use embeddings, PostgreSQL, pgvector,
or an LLM to write its chat replies.

## Run the Go app

From the project root:

```powershell
go run ./backend/cmd/api
```

Open `http://127.0.0.1:8080/`. The API reads the JSONL dataset and serves the
page from `frontend/index.html`.

Endpoints:

- `GET /health`
- `GET /api/doctors/search?specialty=Medicine&region=Dhaka&limit=10`
- `POST /api/chat` with `{"message":"amar jor","location":"Dhaka"}`

## Run the Gemini RAG learning experiment

Set `GEMINI_API_KEY` as a Windows user environment variable, open a new
PowerShell terminal, then run from the project root:

```powershell
go run ./rag
```

This makes two embedding API calls for sample text and calculates cosine
similarity. Keep the API key out of source files, screenshots, and GitHub. Use
fictional test queries; do not send real patient health information to the free
API tier.

## Scraper and dataset

The crawler keeps its source code and data together:

- `crawler/crawler.py`: fetches, parses, and exports doctor profiles.
- `crawler/data/doctors.jsonl`: one doctor JSON object per line.
- `crawler/data/doctors.xlsx`: flat Excel export for review.
- `crawler/data/doctors_fixed.xlsx`: earlier repaired workbook, retained for reference.
- `crawler/data/crawl.sqlite3`: local crawl queue and cached HTML, ignored by Git because it is over GitHub's 100 MB per-file limit.

Set up Python and run a small batch:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r crawler\requirements.txt
.\.venv\Scripts\python.exe crawler\crawler.py --limit 10
```

Continue with another batch; completed pages are skipped:

```powershell
.\.venv\Scripts\python.exe crawler\crawler.py --limit 100
```

Other useful commands:

```powershell
# Process every remaining URL; this can take hours.
.\.venv\Scripts\python.exe crawler\crawler.py --limit 0
# Re-discover sitemap URLs, then process up to 100.
.\.venv\Scripts\python.exe crawler\crawler.py --rediscover --limit 100
# Rebuild JSONL and Excel from the local SQLite cache without fetching pages.
.\.venv\Scripts\python.exe crawler\crawler.py --export-only
# Re-parse saved HTML after parser changes.
.\.venv\Scripts\python.exe crawler\crawler.py --reparse
```

`--limit` counts attempted pages, not successful doctor profiles. Requests run
sequentially with a delay. `Ctrl+C` saves completed pages and exports the current
dataset; rerunning resumes from pending or failed pages. Do not run two crawlers
against the same data folder simultaneously.

## Database

The initial schema is in `db/migrations/001_init.sql`. PostgreSQL is not wired
into the Go backend yet. The next RAG phase will enable pgvector, create a
768-dimensional embedding column, import a small sample, and verify retrieval
before processing the full dataset.

## Learning notes

Start with [`docs/LEARN.md`](docs/LEARN.md) for the current code path and RAG
concepts. [`docs/PRD.md`](docs/PRD.md) records the product scope and planned
implementation tasks.
