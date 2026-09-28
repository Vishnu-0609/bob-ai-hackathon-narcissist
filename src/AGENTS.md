# DVI-Bridge System Architecture & Agent Guide

## Purpose

DVI-Bridge is an explainable disaster-victim-identification (DVI) candidate-reconciliation platform. It records ante-mortem and post-mortem observations, ranks possible matches using deterministic forensic evidence scoring, and uses IBM Bob + Google Gemini 2.5 Flash multimodal cloud vision for observable extraction subject to human review.

This software produces candidate matches for trained forensic coordinators. LLM output never determines match scores or confirms identities.

## Repository Layout

- `src/backend/`: FastAPI backend with SQLAlchemy and deterministic scoring engine.
- `src/backend/app/services/matching_engine.py`: Forensic candidate scoring (DNA, dental, physical traits, tattoos, scars, clothing, jewellery).
- `src/backend/app/services/vision/`: Google Gemini 2.5 Flash Cloud multimodal image extraction and verification service.
- `src/backend/app/services/bob_copilot.py`: IBM Bob DVI Coordinator Copilot with natural language forensic query capabilities.
- `src/frontend/`: Modern React TypeScript interface with Tailwind/CSS styling, multimodal comparison matrices, and case inspection modal.

## Safety and Domain Invariants

- AI models extract and structure observations; they never determine match scores or confirm identities.
- Scores are transparent candidate-ranking metrics (0-100), not biometric identity confirmations.
- Missing evidence is never scored as a contradiction.
- All extracted image observations require human-in-the-loop verification before database persistence.

