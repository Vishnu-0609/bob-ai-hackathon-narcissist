# ReconcileAI local open-source stack

The application is designed to keep sensitive case data on the operator's machine or private infrastructure.

## Included now

| Component | Role | License |
|---|---|---|
| Node.js | API runtime | MIT |
| IBM Granite 4 3B via Ollama | Free-text normalization | Apache-2.0 model |
| IBM Granite 3.2 Vision 2B via Ollama | Image-to-structured-observation extraction | Apache-2.0 model |
| Ollama | Local model runtime | MIT |
| Deterministic in-repository engine | Candidate scoring and evidence comparison | Project license |
| JSON repository | Local prototype persistence | Project license |
| PostgreSQL 17 | Durable Docker persistence for operational records | PostgreSQL License |

No cloud AI API is required. LLM output never determines the match score or confirms an identity.

## Native setup (recommended for the current Windows machine)

1. Install Ollama from its official Windows installer.
2. From PowerShell, run:

```powershell
.\scripts\setup-local-models.ps1
cd backend
npm start
```

Model storage requires several gigabytes. The text model is approximately 2 GB; allow additional space for the vision model and runtime cache.

## Docker setup (alternative)

```powershell
docker compose up -d
```

The `ollama-models` initialization service pulls both Granite models automatically.
PostgreSQL initializes its schema and synthetic seed records when the API first starts.

## AI endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/ai/status` | Ollama reachability and model readiness |
| POST | `/api/v1/ai/normalize-description` | Convert narrative text into the evidence schema |
| POST | `/api/v1/ai/extract-image` | Extract observable evidence from a base64 JPEG/PNG/WebP |

Example normalization body:

```json
{
  "description": "Last seen in a navy tee and black jeans, wearing a black wrist watch. Scar on the left forearm."
}
```

Example image extraction body:

```json
{
  "mimeType": "image/jpeg",
  "imageBase64": "BASE64_DATA_WITHOUT_OR_WITH_DATA_URL_PREFIX"
}
```

## Deliberately not required

- **Vector database:** the records are structured and the candidate set can be scored deterministically. Add pgvector/Qdrant only when scale requires candidate pre-filtering.
- **Face recognition:** excluded because operational DVI identification needs forensic confirmation and multimodal evidence.
- **Cloud LLM APIs:** excluded to prevent case imagery and personal data from leaving controlled infrastructure.
- **Separate OCR in the MVP:** Granite Vision can return visible text. PaddleOCR can later be added as a second evidence source if multilingual OCR accuracy needs improvement.

## Production upgrades

Add Keycloak for role-based access, use MinIO for encrypted evidence objects, and add an append-only audit log. PostgreSQL is already used by the Docker deployment; native development retains the JSON fallback.
