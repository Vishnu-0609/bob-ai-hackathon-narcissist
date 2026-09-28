# ReconcileAI Project Guide

## Purpose

ReconcileAI is an explainable disaster-victim-identification (DVI) candidate-reconciliation prototype. It records ante-mortem and post-mortem observations, ranks possible matches using deterministic evidence scoring, and uses local IBM Granite models only to structure narrative or image observations.

This software produces candidates for trained human review. It must never claim or imply that a score confirms an identity.

## Repository layout

- `backend/`: dependency-free Node.js REST API.
- `backend/src/domain/scoring.js`: deterministic evidence comparison and candidate ranking.
- `backend/src/services/local-ai.js`: Ollama client for Granite text and vision models.
- `backend/src/data/`: JSON repository and synthetic seed records.
- `backend/test/`: Node test-runner suites.
- `docker-compose.yml`: API and Ollama services with persistent volumes.
- `scripts/setup-local-models.ps1`: native Windows Ollama model setup.
- `OPEN_SOURCE_STACK.md`: architecture, setup, and model documentation.

## Runtime and commands

- Node.js 20 or newer is required; the container currently uses Node 24 Alpine.
- Run locally: `cd backend && npm start`.
- Run in watch mode: `cd backend && npm run dev`.
- Test: `cd backend && npm test`.
- Run the container stack: `docker compose up -d --build`.
- Required Ollama models: `granite4:3b` and `granite3.2-vision:2b`.
- Native Ollama defaults to `http://127.0.0.1:11434`; the Compose API uses `http://ollama:11434`.

## Engineering conventions

- Use ECMAScript modules and the Node.js standard library. Do not add a dependency unless it materially simplifies a requirement and the tradeoff is documented.
- Keep routing thin. Put record workflows in services, comparisons in `domain`, validation in `lib`, and persistence behind the repository interface.
- Return JSON envelopes as `{ "data": ... }` on success and `{ "error": { "code", "message", "details" } }` on failure.
- Validate all external input and use `ApiError` for expected client or upstream failures.
- Preserve atomic JSON persistence and serialized writes in `JsonRepository`.
- Add or update tests for scoring, validation, routing, or Ollama behavior whenever those areas change.
- Keep generated runtime data out of source changes unless a fixture is intentionally required.

## Safety and domain invariants

- LLM output may normalize or extract evidence, but must never determine match scores or identity.
- Scores are transparent candidate-ranking scores, not probabilities.
- Missing evidence is excluded from the denominator; it is not a mismatch.
- Candidate results must retain the forensic-confirmation disclaimer.
- Image extraction must not infer identity, name, ethnicity, gender, exact age, cause of death, or exact height.
- Keep case data local. Do not introduce cloud AI calls or telemetry that sends record data off-device.
- Treat included names and records as synthetic demo data.

## Change checklist

1. Read the relevant service, validation, and tests before editing.
2. Make the smallest coherent change while preserving API compatibility.
3. Run `npm test` from `backend/`.
4. For runtime changes, verify `/health`; for AI changes, also verify `/api/v1/ai/status`.
5. Update `backend/README.md` or `OPEN_SOURCE_STACK.md` when setup, endpoints, models, or architectural boundaries change.
