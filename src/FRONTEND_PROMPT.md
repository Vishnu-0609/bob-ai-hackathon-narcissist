# ReconcileAI Frontend Build Prompt

Build a polished, responsive frontend for **ReconcileAI**, an explainable disaster-victim-identification (DVI) candidate-reconciliation system. This is an operational workspace for authorized response teams—not a marketing website. The interface must help operators register missing-person information, upload post-mortem evidence images, review AI-extracted observable characteristics, and inspect transparently scored candidate matches.

## Product principles

- Treat this as sensitive operational software with a calm, precise, trustworthy tone.
- Never describe a match score as an identity probability or identity confirmation.
- Display this message prominently wherever candidates are reviewed: **“Candidate match only — requires forensic confirmation.”**
- AI only extracts and normalizes observations. Deterministic backend logic calculates candidate scores.
- Extracted image characteristics always require human review before being treated as verified evidence.
- Do not infer or display ethnicity, gender, exact age, cause of death, identity, or other sensitive attributes from an image.
- Raw images remain local and are not retained by the current backend.

## Technology

Use React with TypeScript and a clean component architecture. Use the existing project stack if one is already present; otherwise use Vite. Keep dependencies minimal. Use semantic HTML, accessible forms, keyboard-friendly interactions, and responsive layouts.

Read the backend base URL from an environment variable:

```text
VITE_API_URL=http://127.0.0.1:4000
```

Do not hard-code production credentials or secrets in frontend code.

## Visual direction

Create a dense but readable operational dashboard rather than a generic admin template.

- Use a deep navy/slate background with cool blue surfaces and teal as the primary action/accent color.
- Use amber for pending review, red only for contradictions or errors, and green/teal for available services or concordant evidence.
- Use restrained borders, compact cards, excellent spacing, and high-contrast typography.
- Avoid gradients everywhere, oversized hero sections, glassmorphism, decorative stock imagery, and playful animations.
- Use a left navigation rail on desktop and an accessible drawer on mobile.
- Minimum body text should be 16px; common labels should generally be at least 14px.
- Support desktop, tablet, and mobile without horizontal page scrolling. Data tables may scroll inside their own containers.

## Main navigation

Provide these primary views:

1. **Overview**
2. **Missing persons**
3. **Unidentified records**
4. **Image intake**
5. **Candidate review**
6. **System status**

The header should show the current view title, backend connection state, Ollama/model readiness, a refresh action, and a context-appropriate primary action.

## 1. Overview

Open directly on a useful operational dashboard. Do not show a landing-page hero.

Display summary cards for:

- Missing-person records
- Unidentified-person records
- Pending reviews
- Externally reconciled records

Show a priority queue of unidentified records requiring candidate review and a recent-activity list. Each queue item should show its record ID, incident reference, extraction status, and an action that opens Candidate Review.

Use:

```text
GET /api/v1/dashboard
```

## 2. Missing-person registry

Create a searchable registry using:

```text
GET /api/v1/ante-mortem
POST /api/v1/ante-mortem
```

The table should show:

- Record ID
- Full name
- Age
- Height
- Upper and lower clothing
- Visible marks
- Accessories
- Status
- Last updated timestamp

Provide an “Add missing person” dialog or side panel with these fields:

- `fullName` — required
- `age` — optional, 0–130
- `heightCm` — optional, 30–250
- `upperType`
- `upperColor`
- `lowerType`
- `lowerColor`
- `visibleMarks`
- `accessories`
- `dentalNotes`
- `otherDescription`

Show field-level validation errors returned by the API. After successful creation, close the form, show a success notification, refresh the registry, and focus the newly created record.

## 3. Unidentified-person registry

Create a searchable registry using:

```text
GET /api/v1/post-mortem
POST /api/v1/post-mortem
```

Show:

- Record ID
- Incident reference
- Estimated height
- Observed clothing
- Visible marks
- Accessories
- Dental observations
- Extraction status
- Record status
- Last updated timestamp

Each record must have an action to open its candidate matches. Provide a manual-entry form for records that do not have an image.

## 4. Image intake and automatic characteristic extraction

This is a primary workflow. Design it as a focused, guided workspace—not as a small file input hidden inside a generic form.

### Step A: Case details

Collect:

- `incidentRef` — required
- `estimatedHeightCm` — optional
- `dentalNotes` — optional and manually entered; do not infer dental details from the image unless directly supported by the backend contract

### Step B: Select image

Accept JPEG, PNG, and WebP. Provide drag-and-drop and a normal file picker. Show:

- A local preview
- Filename
- MIME type
- File size
- A clear remove/replace action

Reject unsupported files before submission. Warn when the selected file is too large for the backend request limit. Do not upload automatically; require an explicit “Analyze image” action.

Convert the image to base64 in the browser and send:

```text
POST /api/v1/post-mortem/from-image
Content-Type: application/json
```

Request body:

```json
{
  "incidentRef": "INC-2026-101",
  "estimatedHeightCm": 172,
  "dentalNotes": "manual observation if available",
  "mimeType": "image/jpeg",
  "imageBase64": "BASE64_DATA_WITHOUT_OR_WITH_DATA_URL_PREFIX"
}
```

While processing, show explicit stages such as:

- Preparing image
- Waiting for local Granite Vision
- Extracting observable characteristics
- Creating review-required record

Do not use fake percentage progress.

### Step C: Review extracted characteristics

The response `data` is the created post-mortem record. The response `meta.extraction` contains the model extraction, including possible warnings. Present the extracted fields in an editable review surface:

- Upper garment type and color
- Lower garment type and color
- Visible distinguishing marks
- Accessories
- Visible text on clothing
- Other directly observable details
- Model warnings or image limitations

Clearly label the record status as **AI extracted — pending human review**. Visually distinguish empty or unavailable observations from confirmed values. Show that the raw image was not stored using `meta.rawImageStored`.

After review, provide an action to open Candidate Review for the newly created record. Do not add a “Confirm identity” button.

## 5. Candidate review

Load matches using:

```text
GET /api/v1/post-mortem/:id/matches?limit=3
```

The left side should summarize the selected post-mortem record. The main panel should show ranked candidate tabs or cards.

For each candidate display:

- Rank
- Candidate name and ante-mortem ID
- Score out of 100
- Classification: high, moderate, or low agreement
- Evidence coverage percentage
- Backend rationale
- Required forensic-confirmation disclaimer

Render an evidence comparison table with one row per category:

- Dental observations
- Distinguishing marks
- Clothing
- Accessories
- Height
- Other description

Each row should show:

- Ante-mortem value
- Post-mortem value
- Weight
- Result: concordant, partial, contradictory, or unknown

Use teal for concordant, amber for partial, red for contradictory, and neutral gray for unknown. Explain that unknown evidence did not contribute to the denominator. Do not hide contradictions behind a collapsed section.

## 6. System status

Use:

```text
GET /health
GET /api/v1/ai/status
```

Show:

- API availability
- Local Ollama reachability
- Text model name and installation state
- Vision model name and installation state
- Local-only processing indicator

If the vision model is unavailable, disable image analysis and provide a specific, actionable message while keeping manual record entry available.

## API error handling

The API error format is:

```json
{
  "error": {
    "code": "VALIDATION_FAILED",
    "message": "Record validation failed.",
    "details": []
  }
}
```

Handle at least:

- Offline backend
- Validation errors
- Unsupported image type
- Payload too large
- Ollama unavailable
- Vision model not installed
- Model timeout
- Invalid model response
- Record not found
- Unexpected server error

Preserve form contents after recoverable errors. Use inline errors for fields and a concise notification for request-level failures. Include retry actions where retrying is meaningful.

## Loading and empty states

- Use skeletons for initial dashboard and table loading.
- Use a small inline spinner for button-level actions.
- Empty registries should explain what is missing and provide the relevant creation action.
- Candidate review should explain when no post-mortem record is selected.
- Never display fabricated matches or silently fall back to demo data in the production application.

## Accessibility

- All inputs need visible labels and described validation messages.
- Dialogs and drawers must trap focus and restore it on close.
- Every action must be keyboard accessible.
- Status and error messages should use appropriate live regions.
- Do not encode evidence results using color alone; always include text and/or an icon.
- Image previews require descriptive alternative text such as “Locally selected evidence preview.”
- Respect reduced-motion preferences.

## Component structure

Use a maintainable structure similar to:

```text
src/
  api/
    client.ts
    types.ts
  components/
    AppShell.tsx
    ConnectionStatus.tsx
    DataTable.tsx
    EvidenceComparison.tsx
    RecordForm.tsx
    ImageDropzone.tsx
    ExtractionReview.tsx
    StatusBadge.tsx
  pages/
    OverviewPage.tsx
    AnteMortemPage.tsx
    PostMortemPage.tsx
    ImageIntakePage.tsx
    CandidateReviewPage.tsx
    SystemStatusPage.tsx
  hooks/
  styles/
```

Define TypeScript interfaces that match the API instead of using `any`. Keep API calls in a single typed client module. Use an error boundary for unexpected rendering failures.

## Acceptance criteria

The frontend is complete when:

1. It loads dashboard and registry data from the real backend.
2. Operators can create ante-mortem and manual post-mortem records.
3. Operators can select an image, preview it locally, submit it for Granite Vision analysis, and see the extracted characteristics and warnings.
4. The image workflow creates a post-mortem record marked as pending review.
5. Operators can open ranked matches and inspect every evidence category, weight, result, rationale, coverage value, and disclaimer.
6. API, model, validation, timeout, and offline states are handled clearly.
7. The interface is usable at desktop and mobile widths and supports keyboard navigation.
8. No screen implies that AI or a score confirms identity.
9. No raw image, secret, or sensitive case payload is persisted in browser storage.
10. The production build completes without TypeScript or linting errors, and the primary flows are tested.

Before finishing, run the frontend locally against `http://127.0.0.1:4000`, exercise the image intake and candidate-review flows, verify responsive behavior, and document the exact development and build commands in the frontend README.
