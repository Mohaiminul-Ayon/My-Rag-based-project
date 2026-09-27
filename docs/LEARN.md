# Learn the current app: request to doctor results

This note describes what the code does today. The current app is a small Go
search chatbot; it does not call an LLM and it is not RAG yet.

## First: what is running?

Start the backend from the project folder:

```powershell
go run ./backend/cmd/api
```

Keep that terminal open. Then open `http://127.0.0.1:8080/`. The page and API
come from the same Go process, so the browser sends `/api/chat` to that process.
If the process is stopped, the browser cannot get a reply.

## What happens when you click Ask?

```text
frontend/index.html
  -> POST /api/chat (JSON: message + location)
  -> backend/cmd/api/main.go decodes the JSON
  -> backend/internal/chat/chat.go checks safety and picks specialty keywords
  -> backend/internal/doctor/doctor.go scans the doctors loaded from JSONL
  -> Go returns JSON
  -> frontend/index.html renders the reply and doctor cards
```

For example, `pet betha` currently does not match the English/Bangla stomach
pain rules, so it falls through to the default specialty, `Medicine`. The
current classifier is only a small keyword switch, not a language model.

## What data is searched?

At server startup, `backend/cmd/api/main.go` calls `doctor.LoadJSONL` on
`crawler/data/doctors.jsonl`. `backend/internal/doctor/doctor.go` reads one JSON doctor per line
into Go memory. For each chat, `Store.Search` loops through those doctor records,
adds simple points for matching specialty, region, phone, and visiting hours,
sorts by score, and returns up to five.

This is ordinary text/field matching. There is no vector database, no embedding
model, and no vector data being created or stored anywhere. PostgreSQL is also
not connected yet; `db/migrations/001_init.sql` is just a schema draft.

## RAG in plain language

RAG means Retrieval-Augmented Generation. It has two distinct parts:

1. **Retrieve:** find relevant doctor records from the data store.
2. **Generate:** send the patient's question and those retrieved records to an
   LLM, which writes a grounded response using only that context.

Embeddings turn text into number arrays (vectors) that roughly represent
meaning. A vector search compares the question's vector to stored doctor-text
vectors and finds nearby meanings. Those vectors must first be created by an
embedding model and saved in a vector index, for example PostgreSQL with
`pgvector`. The current app does none of these steps.

## What is the next learning step?

First improve and test ordinary search with the real dataset: verify names,
specialties, regions, and chamber details. Then add one embedding model, create
one searchable text record per doctor, store embeddings in `pgvector`, and
compare vector results against the current keyword search. Only after retrieval
looks correct should an LLM receive those results to draft a cited answer.

In this app, the eventual flow should be:

```text
patient message -> safety check -> retrieve doctor records -> check evidence
                -> LLM drafts a cautious answer -> API response -> UI
```

Keep emergency handling deterministic and do not ask an LLM to invent doctor
details or diagnose the patient.
