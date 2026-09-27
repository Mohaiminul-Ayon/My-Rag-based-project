# PRD: Doctor Nearby You

## 1. Product Goal

Build a Bangladeshi doctor information chatbot where a patient can describe symptoms, answer a few simple questions, and get relevant doctor or hospital suggestions from our own dataset.

This is not a diagnosis app. It is a triage and doctor-finding assistant.

## 2. MVP

The MVP must do only these things:

1. Patient writes symptoms in a big chat box: `What's your problem?`
2. Bot asks missing general questions, such as location, age group, duration, and danger signs.
3. Bot maps symptoms to a likely doctor specialty.
4. Bot searches our doctor dataset by specialty and region.
5. Bot returns doctor name, specialty, hospital, chamber address, phone, visiting time, and source.
6. Bot gives safe immediate guidance, not medicine prescriptions.
7. Frontend shows a simple patient chat page and doctor result cards.

Not in MVP:

- Google Maps hospital fallback.
- Online appointment booking.
- Payment.
- Prescription.
- Doctor rating/review.
- Video call.
- Full admin dashboard.
- Doctor signup and claim flow.

Add these only after the chatbot reliably returns useful doctors.

## 3. Users

### Patient

Wants fast help finding what type of doctor to see and where.

### Doctor

Future user. Wants to add or update their profile after the patient chatbot works.

### Admin

Future user. Approves doctor profile claims and edits.

## 4. Storyline

A patient opens the app and sees:

```text
Doctor Nearby You

[ What's your problem? ]
```

The patient writes:

```text
amar buk betha hocche
```

The bot does not immediately guess. It asks:

```text
Apnar buk betha kotokkhon dhore?
Shash nite koshto hocche?
Apni kon city/area te?
```

If emergency signs exist, the bot says:

```text
Eta emergency hote pare. Nearest emergency hospital-e jan or local emergency help call korun.
```

If not emergency, it suggests:

```text
Cardiologist or Medicine Specialist dekhano better.
Dhaka te available doctors:
1. Dr. ...
```

If the user did not give location, the bot asks location before doctor search.

## 5. MVP Tasks, Time, Subtasks, Microtasks

### Task 1: Backend Project Setup

Task time: 1 day

Subtask 1.1: Go project bootstrap

Sprint time: 2 hours

Microtasks:

- Create `go.mod`.
- Create `backend/cmd/api/main.go`.
- Create `backend/internal/config`.
- Add `.env.example`.
- Add health endpoint: `GET /health`.

Subtask 1.2: Postgres connection

Sprint time: 3 hours

Microtasks:

- Add database config.
- Open Postgres connection at startup.
- Ping database on startup.
- Add migration folder.

Subtask 1.3: Basic API structure

Sprint time: 3 hours

Microtasks:

- Create `backend/internal/http`.
- Create route registration.
- Create JSON response helper.
- Create request error helper.

Learning outcome:

You learn how a Go API starts, loads config, connects DB, and exposes routes.

### Task 2: Database Schema

Task time: 1 day

Subtask 2.1: Doctor tables

Sprint time: 4 hours

Microtasks:

- Create `doctors` table.
- Create `chambers` table.
- Create indexes on `specialty`, `region`, and `doctor_id`.
- Store `source_url` for citation.

Subtask 2.2: User and doctor claim tables

Sprint time: 4 hours

Microtasks:

- Create `users` table.
- Create `doctor_claims` table.
- Add claim status: `pending`, `approved`, `rejected`.
- Add duplicate matching fields: BMDC, name, phone, hospital.

Learning outcome:

You learn data modeling: one doctor can have many chambers, and one doctor profile can be claimed by a signed-up doctor.

### Task 3: Import Scraped Dataset

Task time: 1 day

Subtask 3.1: JSONL importer

Sprint time: 4 hours

Microtasks:

- Read `crawler/data/doctors.jsonl`.
- Insert or update doctors by `doctor_id`.
- Insert chambers for each doctor.
- Keep source URL and scraped timestamp.

Subtask 3.2: Import verification

Sprint time: 3 hours

Microtasks:

- Count imported doctors.
- Count imported chambers.
- Print duplicate BMDC/name warnings.
- Add one test with a tiny sample JSONL.

Learning outcome:

You learn ETL: scraped data becomes application database data.

### Task 4: Doctor Search API

Task time: 1 day

Subtask 4.1: Search endpoint

Sprint time: 4 hours

Endpoint:

```http
GET /api/doctors/search?specialty=cardiology&region=dhaka
```

Microtasks:

- Validate query params.
- Search doctors by specialty and region.
- Return doctor + chamber info.
- Limit result count.

Subtask 4.2: Search ranking

Sprint time: 3 hours

Microtasks:

- Exact region match first.
- Exact specialty match first.
- Doctors with phone/time first.
- Return source URL.

Learning outcome:

You learn basic search before adding AI. This matters because RAG is only useful if normal search works.

### Task 5: RAG Bot API

Task time: 2 days

Subtask 5.1: RAG request model

Sprint time: 3 hours

Endpoint:

```http
POST /api/chat
```

Request:

```json
{
  "message": "amar buk betha",
  "location": "Dhaka",
  "session_id": "optional"
}
```

Response:

```json
{
  "reply": "...",
  "questions": ["..."],
  "suggested_specialties": ["Cardiology", "Medicine"],
  "doctors": [],
  "safety_level": "normal|urgent|emergency"
}
```

Microtasks:

- Create chat request/response structs.
- Add input validation.
- Save chat messages.
- Return structured JSON.

Subtask 5.2: Emergency checker

Sprint time: 4 hours

Microtasks:

- Add keyword rules for emergency symptoms.
- Detect chest pain + breathing problem.
- Detect stroke-like words.
- Detect unconscious/severe bleeding.
- Return emergency response before normal doctor search.

Subtask 5.3: Specialty classifier

Sprint time: 4 hours

Microtasks:

- Start with simple keyword mapping.
- Fever/body pain -> Medicine.
- Skin rash -> Dermatology.
- Tooth pain -> Dental.
- Eye problem -> Eye.
- Pregnancy issue -> Gynecology.

Subtask 5.4: RAG answer generation

Sprint time: 5 hours

Microtasks:

- Build prompt with user message, known location, specialty, and retrieved doctors.
- Tell the LLM not to diagnose.
- Tell the LLM to cite doctor source URLs.
- If location missing, ask for location.
- If doctor missing, say dataset has no match.

Learning outcome:

You learn that RAG is not magic. The code first retrieves facts, then the LLM explains them safely.

### Task 6: Frontend MVP

Task time: 2 days

Subtask 6.1: Patient homepage

Sprint time: 4 hours

Microtasks:

- Add title: `Doctor Nearby You`.
- Add large chat input: `What's your problem?`
- Add default mode: Patient.
- Add button: `As a Doctor`.

Subtask 6.2: Chat UI

Sprint time: 1 day

Microtasks:

- Send message to `/api/chat`.
- Show bot questions.
- Show doctors as cards.
- Show urgent warning clearly.
- Show source link.

Learning outcome:

You learn how frontend talks to your Go API and displays structured AI output.

### Task 7: Testing and Safety Review

Task time: 1 day

Subtask 8.1: Backend tests

Sprint time: 4 hours

Microtasks:

- Test doctor search.
- Test emergency checker.
- Test duplicate matching.
- Test missing location response.

Subtask 8.2: Manual AI test cases

Sprint time: 4 hours

Microtasks:

- Test chest pain.
- Test fever.
- Test skin problem.
- Test child fever.
- Test missing location.
- Test no doctor found.
- Test Bangla mixed with English.

Learning outcome:

You learn evals. AI apps need test questions, not just unit tests.

## 6. Backend Design: SRP and SOLID

Keep packages small and boring.

Suggested Go structure:

```text
backend/cmd/api/main.go
backend/internal/config
backend/internal/database
backend/internal/http
backend/internal/doctor
backend/internal/chat
backend/internal/auth
backend/internal/importer
backend/internal/safety
rag
```

### SRP Rules

Each package has one reason to change:

- `doctor`: doctor search, profile, chamber logic.
- `chat`: chat session and chat API logic.
- `safety`: emergency keyword detection.
- `rag`: prompt building and LLM call.
- `importer`: JSONL to Postgres.
- `database`: DB connection only.

Bad:

```go
func ChatHandler() {
    // parse request
    // connect database
    // search doctors
    // call LLM
}
```

Good:

```go
func ChatHandler(service *chat.Service) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        // HTTP only: decode request, call service, encode response.
    }
}
```

### SOLID in this project

S: Single Responsibility

Handlers handle HTTP. Services handle business rules. Repositories handle SQL.

O: Open/Closed

Add a new specialty mapping without changing HTTP handlers.

L: Liskov

If `DoctorRepository` has an interface, a test fake should behave like the real repo.

I: Interface Segregation

Do not create one giant `Repository` interface. Use small interfaces only where tests or swapping need them.

D: Dependency Inversion

Chat service depends on interfaces like doctor search and LLM client, not directly on HTTP/OpenAI/Postgres details.

Ponytail note: Do not create interfaces everywhere. In Go, add an interface only where you actually need testing or replacement.

## 7. API Endpoints

### Health

```http
GET /health
```

### Doctor Search

```http
GET /api/doctors/search?specialty=medicine&region=dhaka
```

### Chatbot

```http
POST /api/chat
```

## 8. Postgres Tables

Minimum schema:

```sql
doctors(
  id uuid primary key,
  source_doctor_id text unique,
  name text not null,
  specialty text,
  qualifications text,
  designation text,
  workplace text,
  bmdc_reg_no text,
  region text,
  source_url text,
  status text not null default 'published',
  created_at timestamptz not null,
  updated_at timestamptz not null
)

chambers(
  id uuid primary key,
  doctor_id uuid references doctors(id),
  hospital text,
  address text,
  phone text,
  visiting_hours text,
  created_at timestamptz not null
)

chat_sessions(
  id uuid primary key,
  user_location text,
  created_at timestamptz not null
)

chat_messages(
  id uuid primary key,
  session_id uuid references chat_sessions(id),
  role text not null,
  content text not null,
  created_at timestamptz not null
)
```

## 9. Code Comment Rules

Comments must teach why code exists, not repeat what the line says.

Bad:

```go
// Create user
CreateUser()
```

Good:

```go
// Doctor profiles from scraping are public data, but profile edits need review
// because a random user must not overwrite a real doctor's chamber details.
```

Every important package should start with a short package comment:

```go
// Package safety catches obvious emergency cases before the LLM runs.
// This keeps urgent warnings deterministic instead of depending on model output.
package safety
```

## 10. LEARN: What Happens in the Codebase

When a patient sends a message:

1. Frontend sends `POST /api/chat`.
2. HTTP handler decodes JSON.
3. Chat service checks if location is missing.
4. Safety service checks emergency symptoms.
5. Specialty classifier maps symptom to possible specialty.
6. Doctor service searches Postgres.
7. RAG service builds prompt with retrieved doctors.
8. LLM writes a safe answer.
9. Handler returns JSON to frontend.
10. Frontend shows answer, questions, and doctor cards.

When scraped data is imported:

1. Importer reads JSONL.
2. Each doctor becomes one `doctors` row.
3. Each chamber becomes one `chambers` row.
4. Existing doctors update by `source_doctor_id`.
5. Search API can now use Postgres.

## 11. Safety Requirements

The bot must not:

- diagnose disease.
- prescribe medicine.
- guarantee doctor availability.
- say scraped data is verified.
- hide emergency warnings.

The bot must:

- ask location if missing.
- show source URL when suggesting doctors.
- say when no match is found.
- recommend emergency care for danger signs.
- keep answers simple Bangla/Banglish friendly.

Emergency examples:

- chest pain with breathing difficulty.
- stroke signs.
- unconscious.
- severe bleeding.
- severe allergic reaction.
- pregnancy emergency.
- newborn emergency.
- self-harm mention.

## 12. Criticism

This project can fail in these ways:

1. Dataset quality may be weak.

Scraped data can be outdated, duplicate, or wrong. Do not present it as verified truth.

2. Symptom-to-specialty mapping is risky.

Many symptoms map to multiple specialties. The bot should say `possible specialist`, not `you need exactly this doctor`.

3. Google Maps fallback is not MVP.

Maps sounds useful, but it adds API keys, billing, rate limits, and location privacy. Add it after basic RAG works.

4. Doctor signup can create fake profiles.

Without verification, anyone can claim a doctor. MVP must keep claims pending.

5. LLM can hallucinate medical advice.

Keep emergency checker and doctor retrieval deterministic. LLM should explain retrieved facts, not invent doctors.

6. Too much SOLID can hurt learning.

Do not create interfaces and factories everywhere. SRP matters. Fake enterprise architecture does not.

7. Bangla medical language is messy.

Users may write Bangla, English, Banglish, spelling mistakes, or local terms. Start with common examples and improve from real test questions.

## 13. Future Work

Add only after MVP works:

- Google Maps nearest hospital fallback.
- Admin dashboard.
- Doctor signup and profile claim.
- Doctor profile verification documents.
- Appointment booking.
- Better multilingual symptom classifier.
- Vector database with pgvector.
- Analytics: most searched symptom, no-result regions.
- WhatsApp/Messenger bot.

## 14. Definition of Done

MVP is done when:

- A patient can chat with symptoms.
- Bot asks missing location.
- Bot detects obvious emergency cases.
- Bot suggests specialty.
- Bot returns doctors from Postgres.
- Bot shows source URL.
- Frontend can send chat messages and show doctor cards.
- Tests cover search, safety, and missing location.
