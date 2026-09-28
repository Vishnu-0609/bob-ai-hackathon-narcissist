# ReconcileAI backend

Node.js REST API for the ReconcileAI hackathon prototype, using PostgreSQL in
Docker and a lightweight JSON fallback for native development.

## IBM Bob

Open the repository root in IBM Bob IDE. Bob automatically reads the root
`AGENTS.md` for project architecture, commands, and domain safeguards, plus the
mode-specific guidance under `.bob/`. Run `/init` in Bob after major structural
changes if you want Bob to regenerate or refresh its discovered project context.

## Run

```powershell
cd backend
npm start
```

The API starts at `http://127.0.0.1:4000`. Development mode uses Node's watch mode:

```powershell
npm run dev
```

For the complete PostgreSQL + Ollama stack, run from the repository root:

```powershell
docker compose up -d --build
```

The one-shot `ollama-models` service downloads the required Granite models on
first startup. Model files and PostgreSQL data are retained in Docker volumes.

## Test

```powershell
npm test
```

## Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/api/v1/dashboard` | Dashboard totals and recent activity |
| GET | `/api/v1/ai/status` | Local Ollama and model readiness |
| POST | `/api/v1/ai/normalize-description` | Normalize narrative evidence with local Granite |
| POST | `/api/v1/ai/extract-image` | Extract observable image evidence with local Granite Vision |
| GET | `/api/v1/ante-mortem` | List missing-person records |
| POST | `/api/v1/ante-mortem` | Create a missing-person record |
| GET | `/api/v1/post-mortem` | List unidentified-person records |
| POST | `/api/v1/post-mortem` | Create an unidentified-person record |
| POST | `/api/v1/post-mortem/from-image` | Extract image characteristics and create a review-required record |
| GET | `/api/v1/post-mortem/:id/matches?limit=3` | Rank candidates with an evidence breakdown |

## Design boundaries

- Scores are transparent, configurable match scores—not identity probabilities.
- Missing evidence is excluded from the denominator instead of treated as a mismatch.
- Every result is labeled as requiring forensic confirmation.
- Current records are synthetic and persisted to `data/records.json`.
- Docker uses PostgreSQL 17. Native development falls back to `data/records.json` when `DATABASE_URL` is unset.
- A future extraction service can call Granite Vision, OCR, and image-processing workers without changing the record or matching contracts.
- The included local-AI service calls Ollama only at the configured local endpoint. See `../OPEN_SOURCE_STACK.md` for setup.

## Image ingestion

Send a base64 JPEG, PNG, or WebP together with the incident reference:

```json
{
  "incidentRef": "INC-2026-101",
  "mimeType": "image/jpeg",
  "imageBase64": "BASE64_DATA"
}
```

The Granite Vision result is normalized into a post-mortem record with
`extractionStatus: "ai-extracted-pending-review"`. The raw image is not stored,
and all extracted characteristics require human review.
