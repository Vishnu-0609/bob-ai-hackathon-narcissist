# DVI-Bridge — IBM Bob-Powered Disaster Victim Identification Coordination Platform

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com)
[![React 19](https://img.shields.io/badge/React-19-61dafb.svg)](https://react.dev)
[![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-v4-38bdf8.svg)](https://tailwindcss.com)
[![IBM Bob](https://img.shields.io/badge/IBM%20Bob-AI%20Agent-indigo.svg)](https://www.ibm.com)
[![Audit Chain](https://img.shields.io/badge/Audit%20Chain-SHA--256%20Verified-emerald.svg)](https://github.com)

**DVI-Bridge** is an emergency-response and forensic coordination platform engineered for mass-casualty incidents (such as the 2023 Balasore train collision). It bridges Ante-Mortem (AM) missing person records and Post-Mortem (PM) mortuary observations through **deterministic forensic candidate scoring**, **contradiction detection**, **IBM Bob AI-powered structured extraction & explainability**, and **tamper-evident cryptographic audit chaining**.

---

## ⚠️ Core Forensic Mandate

> **CRITICAL FORENSIC PRINCIPLE:** DVI-Bridge is an intelligent decision-support and reconciliation tool. The platform **NEVER** claims that an AI model autonomously identifies a deceased person. Authoritative candidate ranking is computed **deterministically (0–100 Match Score)**, while final reconciliation is an authorized **human forensic decision**.

---

## 🌟 Key Features

1. **Deterministic Forensic Matching Engine**:
   - Scores 12 weighted biological, odontological, anatomical, and personal property attributes (Sex 10, Age 10, Height 8, Blood Group 7, Scars 15, Birthmarks 10, Tattoos 8, Clothing 5, Jewellery 5, Dental 12, Medical 5, Location 5).
   - Distinguishes `MATCH`, `MISMATCH`, `UNKNOWN`, and `NOT_AVAILABLE`.
   - **Missing evidence is never penalized as contradictory**.

2. **Forensic Contradiction Detection Engine**:
   - Automatically detects biological sex conflicts, serological incompatibilities, and stature discrepancies (>15 cm).

3. **Google Gemini 2.5 Flash Cloud Vision Evidence Extraction**:
   - Cloud-based multimodal visual evidence extraction for Ante-Mortem (AM) and Post-Mortem (PM) intake photographs.
   - Extracts observable clothing, jewellery, tattoos, scars/marks, physical attributes, and image quality metrics.
   - **Strict Forensic Compliance**: Gemini NEVER performs facial recognition or final identification—it only extracts structured visual observations (`OBSERVED`, `INFERRED`, `UNKNOWN`).
   - **Human-in-the-Loop Review**: All Gemini-extracted observations require explicit human review (`ACCEPT ALL`, `EDIT`, `REJECT`) before merging into authoritative case evidence and the deterministic matching engine.
   - **Cryptographic Provenance**: Calculates SHA-256 checksums, enforces private UUID-based storage, and retains complete data lineage.

4. **IBM Bob AI Agent Suite**:
   - **AM Extraction Agent**: Parses free-text family narratives and voice transcripts into structured JSON.
   - **PM Extraction Agent**: Converts mortuary examiner notes into structured observations.
   - **Rationale Agent**: Explains factual concordance without inventing evidence.
   - **Evidence Gap Agent**: Identifies missing investigations (dental, DNA, fingerprints) and recommends verification protocols.
   - **DVI Coordinator Copilot**: Conversational assistant executing controlled, parameterized FastAPI tools (zero raw SQL).

5. **Human-in-the-Loop Reconciliation**:
   - Flagship side-by-side comparison screen with integrated photographic evidence comparison and lightbox viewer.
   - Formal forensic decisions (`CONFIRMED_BY_FORENSIC_TEAM`, `REJECTED`, `NEEDS_REVIEW`) requiring mandatory coordinator comments.

6. **Tamper-Evident SHA-256 Audit Trail**:
   - Every login, image upload, analysis, record update, match calculation, and reconciliation decision is cryptographically chained:
     $$\text{event\_hash} = \text{SHA256}(\text{canonical\_payload} + \text{previous\_event\_hash})$$
   - Real-time cryptographic chain integrity verification via `GET /api/audit/verify`.

7. **Automated ReportLab PDF Dossier Generation**:
   - Generates official DVI Reconciliation Reports with field matrices, IBM Bob rationales, forensic sign-off lines, and legal disclaimers.

8. **Synthetic Balasore Benchmark Dataset**:
   - 100+ AM records, 100+ PM records, and ground truth benchmark mappings (zero real victim PII).

---

## 🏛️ System Architecture

```
                         ┌──────────────────────────┐
                         │       DVI Coordinator    │
                         │        Web Browser       │
                         └────────────┬─────────────┘
                                      │
                                      │ HTTPS
                                      ▼
                         ┌──────────────────────────┐
                         │       React Frontend     │
                         │ (Vite + TS + Tailwind)   │
                         │ Command Dashboard        │
                         │ AM / PM Intake           │
                         │ Candidate Reconciliation │
                         │ Evidence Graph           │
                         │ Bob Copilot              │
                         │ Reports & Audit          │
                         └────────────┬─────────────┘
                                      │
                                      │ REST API (Bearer JWT)
                                      ▼
                    ┌────────────────────────────────────┐
                    │             FastAPI Backend         │
                    │                                    │
                    │ Auth / Strict RBAC                 │
                    │ AM / PM Record Services            │
                    │ Deterministic Matching Engine      │
                    │ Contradiction Detection Engine     │
                    │ Evidence Provenance Service        │
                    │ Human Reconciliation Service       │
                    │ ReportLab PDF Report Generator     │
                    │ SHA-256 Hash Chain Audit Service   │
                    │ IBM Bob AI Client                  │
                    └──────────────┬──────────────┬──────┘
                                   │              │
                         ┌─────────┘              └─────────┐
                         ▼                                  ▼
              ┌─────────────────────┐             ┌────────────────────┐
              │  Relational Database│             │    IBM Bob API     │
              │ (SQLite / Postgres) │             │                    │
              │ AM / PM Records     │             │ AM / PM Extraction │
              │ Matches & Versions  │             │ Rationale Agent    │
              │ Evidence Provenance │             │ Evidence Gap Agent │
              │ Audit Hash Trail    │             │ DVI Copilot        │
              └─────────────────────┘             └────────────────────┘
```

---

## 🚀 Quick Start (Docker Compose)

```bash
# 1. Clone the repository and configure environment
cp .env.example .env

# 2. Build and launch all services with Docker Compose
docker-compose up --build
```

Access the services:
- **Command Dashboard UI**: [http://localhost:3000](http://localhost:3000)
- **FastAPI Interactive API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 💻 Local Development Setup (Without Docker)

### 1. Backend (Python 3.12+)

```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

### 2. Frontend (Node.js 20+)

```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
```

---

## 🔑 Default User Roles & Credentials

| Role | Username | Password | Access Scope |
| :--- | :--- | :--- | :--- |
| **Lead DVI Coordinator** | `coordinator` | `coordpassword123` | Full reconciliation, candidate ranking, Bob Copilot, report exports |
| **Chief Forensic Pathologist** | `reviewer` | `reviewpassword123` | Forensic evidence verification and sign-off |
| **System Administrator** | `admin` | `adminpassword123` | User administration, incident operations, audit oversight |
| **NDRF Field Operator** | `field_team` | `fieldpassword123` | AM/PM intake, voice/text extraction staging |
| **Oversight Auditor** | `auditor` | `auditpassword123` | Cryptographic audit chain verification |

---

## 🎯 Flagship Demonstration Walkthrough

1. **Sign In**: Log in as `coordinator` / `coordpassword123` (or use the 1-click demo switcher).
2. **Dashboard Overview**: View incident metrics, score distribution histograms, and intake statistics for the Odisha train collision.
3. **Open Flagship Case**: Click **"Flagship Case: Reconcile PM-017"**.
4. **Top-3 Candidate Ranking**:
   - Candidate #1: **AM-042 (Arjun Mohanty)** — **Match Score: 88–92 / 100** (High Evidence Quality).
   - Candidate #2: **AM-013 (Anil Pradhan)** — Match Score: 68 / 100.
   - Candidate #3: **AM-081 (Alok Nayak)** — Match Score: 60 / 100.
5. **Inspect Field Evidence**: Review side-by-side matching of surgical forearm scar, bird shoulder tattoo, stature, clothing, and serology.
6. **Examine Evidence Graph**: Click **"Interactive Graph"** to inspect data lineage and provenance.
7. **Consult Bob Copilot**: Ask *"Why is AM-042 ranked first for PM-017?"* or *"What evidence is missing?"*.
8. **Forensic Reconciliation**: Select **[CONFIRM RECONCILIATION]** and enter coordinator notes.
9. **Export PDF Dossier**: Click **"Export Reconciliation PDF Report"** to download the official ReportLab PDF.
10. **Audit Chain Verification**: Navigate to **Audit Hash Trail** and verify the live SHA-256 hash continuity.

---

## 🧪 Automated Test Suite

Run the full automated pytest suite:

```bash
cd backend
python -m pytest
```

---

## 📄 License & Attribution

Built for the IBM Bob Hackathon 2026 by **Team Narcissist** (Vishnu Mandlesara, Tanuj Kashyap, Utsav Nagar, Kunshal Dhawan).
