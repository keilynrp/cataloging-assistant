# Cataloging Assistant

Human-in-the-loop cataloging assistance with evidence traceability and read-only integration with DSpace.

## Overview

Cataloging Assistant is an experimental platform for assisting technical cataloging workflows while preserving human review as the final decision point.

The current MVP combines a DSpace 7.6.6 read-only integration, normalized local metadata, deterministic diagnostics, controlled-vocabulary validation, auditable human review, local draft preparation, operational monitoring, and a conversational assistant built on internal read-only tools.

The system is designed to support catalogers without silently modifying source records or treating generated suggestions as authoritative cataloging decisions.

## Core principles

- **Human-in-the-loop:** cataloging decisions remain under human review.
- **DSpace as source of truth:** the current scope does not write back to DSpace.
- **Evidence traceability:** findings and suggestions should expose their source, validation context, and relevant provenance.
- **Deterministic behavior where applicable:** diagnostics and operational classifications should be reproducible from the same inputs and approved vocabularies.
- **Explicit separation of states:** extraction, validation, suggestion, selection, review, and persistence are treated as distinct concerns.
- **No silent normalization or semantic overwrite:** blocked, stale, or uncertain values remain visible for review.
- **Auditable local operations:** human review and draft revisions are recorded locally without changing the source repository.

## Current scope

The MVP currently includes:

- read-only synchronization and enumeration from DSpace 7.6.6;
- normalized repeatable metadata stored in PostgreSQL;
- paginated, idempotent, resumable synchronization;
- FastAPI endpoints for search, filters, item detail, diagnostics, and operational state;
- a Next.js interface for catalog exploration and review;
- deterministic cataloging diagnostics;
- structured similar-record comparison;
- collection-level coverage and relationship profiling;
- an operational work queue;
- append-only human review of findings;
- local linguistic metadata drafts with source-staleness detection;
- versioned approved controlled vocabularies and literal validation;
- notification and operational monitoring flows;
- a conversational assistant restricted to internal read-only tools;
- UX experimentation for evidence-centered cataloging workflows.

The current scope intentionally excludes direct metadata writes to DSpace.

## Architecture

At a high level, the project is composed of:

```text
DSpace 7.6.6
    │
    │ read-only synchronization
    ▼
FastAPI services
    │
    ├── synchronization
    ├── diagnostics
    ├── validation
    ├── review and local drafts
    ├── notifications
    └── conversational assistant tools
    │
    ▼
PostgreSQL
    │
    ▼
Next.js web interface
```

Detailed architectural decisions and implementation constraints are documented under [`docs/adr`](docs/adr) and [`docs/specs`](docs/specs).

## Technology stack

- **Backend:** FastAPI / Python
- **Frontend:** Next.js / TypeScript
- **Database:** PostgreSQL
- **Containerization:** Docker Compose
- **Source system:** DSpace 7.6.6
- **Testing:** local fixtures and PostgreSQL-backed test flows

Additional libraries and services should be treated as implementation details and are documented alongside the relevant specifications or ADRs.

## Getting started

### Requirements

A local development environment should provide:

- Docker and Docker Compose;
- Git;
- access to the required environment configuration described in `.env.example`.

WSL2 or a Linux-compatible development environment is recommended for local development.

### Clone and configure

```bash
git clone <repository-url>
cd cataloging-assistant
cp .env.example .env
```

Review `.env` before starting the services. Do not commit secrets, provider credentials, tokens, or machine-specific paths.

### Start the application

```bash
docker compose up -d postgres api web
```

Run the initial synchronization and diagnostics when required:

```bash
docker compose run --rm api python -m cataloging_api.sync.cli
docker compose run --rm api python -m cataloging_api.diagnostics.cli
```

Default local services:

- Web interface: `http://localhost:3000`
- API documentation: `http://localhost:8000/docs`
- Health endpoint: `http://localhost:8000/health`

The application does not require real DSpace access for the complete test suite; fixtures are available for local verification.

## Verification

Run the standard project checks with:

```bash
make test
make lint
docker compose build web
```

The expected development baseline is a passing test suite, lint checks, and a successful web build before merging changes that affect runtime behavior.

## Project structure

```text
.
├── cataloging_api/     # backend services and domain logic
├── docs/
│   ├── adr/            # architecture decision records
│   ├── evaluation/     # evaluation and validation artifacts
│   ├── specs/          # technical and functional specifications
│   └── ux/             # UX governance, prompts, evidence, and reviews
├── web/                # web application when applicable to the current layout
├── docker-compose.yml  # local service orchestration
└── README.md
```

The repository may evolve as the MVP grows. Specifications and ADRs are the preferred source for implementation-level detail.

## Documentation

Project documentation is organized by purpose:

- [`docs/adr`](docs/adr) — architecture decisions and design constraints;
- [`docs/specs`](docs/specs) — functional and technical specifications;
- [`docs/evaluation`](docs/evaluation) — evaluation methodology and evidence;
- [`docs/ux`](docs/ux) — UX governance, prototypes, prompt history, and audit evidence.

The README intentionally avoids duplicating detailed specifications, operational internals, endpoint catalogs, security implementation details, or UX audit records.

## Data handling and security

The project follows these baseline rules:

- DSpace access is read-only within the current MVP scope;
- secrets and credentials must not be committed to the repository;
- review tokens and provider credentials belong in configuration or protected storage, not in client-side code;
- local review and draft data are separate from normalized source metadata;
- generated or inferred content must not be treated as source evidence without explicit provenance and review;
- machine-specific paths, usernames, personal identifiers, and private environment details must not be documented in the repository README.

Security-sensitive implementation details belong in the corresponding ADR or specification rather than in this public-facing project overview.

## Development status

This repository represents an evolving MVP. Some capabilities are production-oriented experiments, while others remain explicitly constrained to local or presentation-only behavior.

Before promoting a capability beyond the MVP, verify its specification, runtime classification, persistence model, evidence semantics, and DSpace interaction contract.

For UX work, the current governance and audit trail are maintained under [`docs/ux`](docs/ux).

## Contributing

Keep changes scoped and auditable:

1. create a focused branch;
2. document architectural or semantic changes when required;
3. avoid mixing unrelated refactors with functional changes;
4. run the relevant tests and checks;
5. preserve read-only DSpace behavior unless an approved specification explicitly changes that contract;
6. update documentation when a change affects public behavior, architecture, or cataloging semantics.

## License

This project is licensed under the Apache License 2.0. See [`LICENSE`](LICENSE) for details.
