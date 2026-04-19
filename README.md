# ShopWave Autonomous Support Resolution Agent

ShopWave processes 20 simulated support tickets with a concurrent ReAct-style loop that:

- ingests tickets from JSON
- gathers customer, order, product, and policy context
- classifies and triages through the planner state
- resolves when it is safe to do so
- escalates with a structured summary when policy or confidence requires it
- logs every tool call, retry, validation failure, reasoning step, and final outcome

## Stack

| Layer | Choice |
|---|---|
| Backend | Python, FastAPI, asyncio, Pydantic |
| Agent loop | Custom ReAct orchestration |
| LLM | Gemini-assisted planning and confidence scoring with deterministic fallback |
| Frontend | Next.js 16, React 19 |
| Design system | Storybook 10 |
| Packaging | Docker + docker-compose |

## What is implemented

- Concurrent processing with `asyncio.gather`
- Minimum 3 tool calls per reasoning chain
- Real tool-using agent loop
- Gemini-assisted planner and confidence scorer when `GEMINI_API_KEY` is present
- Deterministic fallback planning if the model is unavailable
- Deterministic failure injection:
  - timeout on one `get_customer` call
  - malformed `get_order` response on one call
  - partial `search_knowledge_base` response on one call
- Retry budgets with exponential backoff
- Schema validation before agent actions
- Dead-letter queue persistence
- Confidence scoring with automatic escalation below `0.6`
- Structured audit log for all 20 tickets
- Responsive frontend dashboard with analytics and ticket drill-down
- Storybook component coverage

## Project structure

```text
backend/
  agent/                  # planner, evaluator, loop, executor
  api/                    # FastAPI routes
  core/                   # logger, retries, validator, state manager, DLQ, LLM client
  data/                   # customers, orders, products, tickets, KB
  tools/                  # read and write tool implementations
  audit_log.json
  dead_letter_queue.json
frontend/
  src/app/                # dashboard, analytics, ticket detail
  src/components/         # Storybook-backed UI pieces
  src/stories/            # component documentation
architecture.png
failure_modes.md
docker-compose.yml
```

## Run locally

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

## Gemini setup

Create `backend/.env`:

```text
GEMINI_API_KEY=your_key_here
```

Important:

- `backend/.env` is ignored by `.gitignore`
- never commit real API keys to the public repo

If the key is missing or Gemini fails, the agent still runs using deterministic fallback logic.

## Storybook

```bash
cd frontend
npm run storybook
```

## Docker

```bash
docker-compose up --build
```

Frontend runs on `http://localhost:3000` and backend on `http://localhost:8000`.

## Demo run

### UI flow

1. Start backend and frontend, or run Docker.
2. Open `http://localhost:3000`.
3. Click `Run Agent`.
4. In `Ticket Queue`, click the customer name to open customer details and all queries related to that customer.
5. Review ticket outcomes and analytics.

### API flow

Start processing:

```bash
curl -X POST http://localhost:8000/api/run
```

Inspect status:

```bash
curl http://localhost:8000/api/status
```

Inspect full audit log:

```bash
curl http://localhost:8000/api/audit-log
```

## API

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/run` | POST | Start processing all tickets |
| `/api/status` | GET | Job status and ticket states |
| `/api/tickets` | GET | Ticket summaries |
| `/api/tickets/{ticket_id}` | GET | Full audit trail |
| `/api/customers` | GET | Customer directory (name/email/tier) |
| `/api/customers/{customer_email}` | GET | Customer profile + all related queries |
| `/api/analytics` | GET | Aggregate metrics |
| `/api/audit-log` | GET | Full audit log |
| `/api/dead-letters` | GET | DLQ contents |

Note: `customer_email` in `/api/customers/{customer_email}` should be URL encoded.
Example: `alice.turner@email.com` -> `alice.turner%40email.com`.

## Deliverables included

- `README.md`
- `architecture.png`
- `failure_modes.md`
- `backend/audit_log.json`
- `backend/dead_letter_queue.json`
- Storybook stories in `frontend/src/stories`

## Submission instructions

1. Push the full project to a public GitHub repository named `hackathon2026-pranika`.
2. Confirm these files are present before submission:
   - `README.md`
   - `architecture.png` or `architecture.pdf`
   - `failure_modes.md`
   - `backend/audit_log.json` or `audit_log.txt`
   - recorded demo
3. Make sure no secrets are committed:
   - keep `backend/.env` local only
   - check GitHub history for any accidental API key commits
4. Make sure the audit log covers all 20 tickets.
5. Make sure the app can be started with a single documented workflow:
   - local backend + frontend commands, or
   - `docker-compose up --build`

## Final pre-submit checklist (all done!)

- Backend starts successfully
- Frontend starts successfully
- `Run Agent` processes all 20 tickets
- Audit log is regenerated from a fresh run
- Architecture document and failure analysis are present
- Recorded demo is prepared
