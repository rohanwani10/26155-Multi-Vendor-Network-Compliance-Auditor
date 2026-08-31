# Multi-Vendor Network Compliance Auditor

> An AI-powered, vendor-agnostic compliance auditing platform for heterogeneous
> enterprise networks.

Audits network device configurations from **any vendor** (Cisco, Palo Alto,
Juniper, Fortinet, Arista, MikroTik, SONiC/white-box, and more) against industry
security frameworks — **CIS Benchmarks, NIST SP 800-53, DISA STIGs, and ISO/IEC
27001** — and generates actionable, per-device PDF reports with severity-scored
findings and CLI-level remediation steps.

Built for **Smart India Hackathon — Problem Statement 26155**, National
Technical Research Organisation (NTRO).

---

## Table of Contents

- [Problem Statement](#problem-statement)
- [Key Features](#key-features)
- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Supported Frameworks & Vendors](#supported-frameworks--vendors)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

---

## Problem Statement

Enterprise networks run devices from dozens of vendors, each with proprietary
CLI syntax. Security frameworks demand consistent hardening (disabling Telnet,
enforcing SSHv2, strong password policies, granular ACLs, centralized logging,
etc.), but today organizations rely on either manual checklist audits or
expensive vendor-locked management suites that break down in heterogeneous,
multi-vendor environments.

This project solves that with an **AI-augmented compliance engine** that:

1. Normalizes any vendor's config into one vendor-neutral schema.
2. Evaluates that schema against a chosen compliance framework.
3. **Learns unseen vendor formats on the fly** via a human-in-the-loop training
   interface — no code redeployment required.
4. Produces a clear, audit-ready PDF report per device.

---

## Key Features

- 🔌 **Unified Ingestion** — single or bulk (ZIP/batch) config upload, with
  automatic vendor fingerprinting.
- 🧠 **Hybrid Parsing Engine** — deterministic rule-based parsers for known
  vendors, with an LLM fallback classifier for anything unrecognized.
- 🎓 **Self-Learning Training Loop** — admins map unrecognized config lines to
  compliance categories through a simple GUI; the system remembers the mapping
  permanently.
- 📋 **Multi-Framework Compliance** — evaluate against CIS, NIST SP 800-53, DISA
  STIGs, or ISO/IEC 27001, defined as declarative, editable rule packs (no
  hard-coded logic).
- 🩹 **Actionable Remediation** — every failed check ships with the exact,
  vendor-specific CLI commands to fix it.
- 📄 **Automated PDF Reporting** — device identification, pass/fail results,
  severity ratings, and remediation steps in one report.
- 🧩 **Vendor-Agnostic & Scalable** — add a new vendor, OS version, or framework
  without touching the codebase.

---

## Architecture Overview

```
Config File(s) ──▶ Ingestion Layer ──▶ Parsing & Normalization Layer ──▶ Vendor-Neutral Schema (JSON)
                                              │
                                    (unrecognized pattern?)
                                              │
                                              ▼
                                  Training & Feedback Layer
                            (human maps line → category, saved as a rule,
                             fed back into the parser for all future configs)

Vendor-Neutral Schema ──▶ Compliance Evaluation Engine (CIS/NIST/STIG/ISO rule packs)
                                              │
                                              ▼
                              Reporting & Remediation Layer ──▶ Per-Device PDF Report
```

Full system diagram (with decision logic, feedback loop, and data flow) is in
[`/docs/architecture.md`](docs/architecture.md).

---

## Tech Stack

Frontend need is intentionally minimal, so the backend renders the frontend
directly — no separate SPA, no npm build step.

| Layer                       | Technology                                                                |
| ---------------------------- | -------------------------------------------------------------------------- |
| Backend & Frontend           | Python (FastAPI), server-rendered HTML via Jinja2, Tailwind CDN, HTMX      |
| Config Collection            | File upload (single file or ZIP); no live SSH polling in this version     |
| Parsing (Tier 1)             | TextFSM + `ntc-templates`, `ciscoconfparse2` for hierarchical configs      |
| Parsing (Tier 2 — fallback)  | `sentence-transformers` embeddings → Chroma (local vector store) → local Ollama LLM |
| Compliance Rule Packs        | YAML                                                                       |
| Reporting                    | WeasyPrint, rendering the same Jinja2 templates as the web view           |
| Database                     | SQLite by default; swappable to PostgreSQL via one env var (SQLAlchemy)   |
| Deployment                   | Docker / Docker Compose (api + ollama + optional postgres)                |

---

## Getting Started

### Prerequisites

- Python 3.10+
- Docker & Docker Compose (recommended) — brings up an `ollama` service
  alongside the app; after first boot, pull a model into it once with
  `docker compose exec ollama ollama pull gemma3:4b` (only needed for the
  Tier-2 LLM fallback path; swapping models is a config change — see
  `.env.example` — not a code change)
- Running without Docker instead: install [Ollama](https://ollama.com)
  locally and `ollama pull gemma3:4b`

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/<your-username>/multi-vendor-compliance-auditor.git
   cd multi-vendor-compliance-auditor
   ```

2. **Set up environment variables**

   ```bash
   cp .env.example .env
   # edit .env if you want to point DATABASE_URL at Postgres instead of SQLite
   ```

3. **Run with Docker (recommended)**

   ```bash
   docker-compose up --build
   ```

   The app (UI + API, server-rendered) is available at `http://localhost:8000`.

4. **Manual setup (without Docker)**

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   alembic upgrade head
   uvicorn app.main:app --reload
   ```

---

## Usage

1. Open the dashboard and upload a device config file (or a ZIP of multiple
   configs).
2. Select the compliance framework(s) to evaluate against.
3. Review the auto-generated report:
   - If the vendor/format is recognized → results appear immediately.
   - If unrecognized → you'll be prompted to use the **Training Interface** to
     map the unfamiliar lines once.
4. Download the per-device PDF report, or view the aggregated dashboard summary
   across all audited devices.

---

## Project Structure

```
.
├── app/
│   ├── main.py              # FastAPI app, routes
│   ├── database.py          # SQLAlchemy engine/session setup
│   ├── models.py            # ORM models (Device, ParsedConfig, RulePack, ...)
│   ├── parsers/              # Tier 1 rule-based vendor parsers
│   ├── llm_fallback/         # Tier 2 embedding + LLM classification module
│   ├── rulepacks/            # CIS / NIST / STIG / ISO YAML rule packs
│   ├── training/             # Human-in-the-loop training module & learned rules store
│   ├── reporting/            # HTML + PDF report generation
│   ├── templates/            # Jinja2 templates (shared by HTML views and PDF export)
│   └── static/
├── alembic/                  # DB migrations
├── tests/
│   └── fixtures/configs/     # Sample vendor configs used across all test phases
├── docs/
│   ├── architecture.md       # 2-page architecture document
│   └── diagram.png
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
├── CHANGELOG.md
└── README.md
```

---

## Supported Frameworks & Vendors

**Frameworks:** CIS Benchmarks · NIST SP 800-53 · DISA STIGs · ISO/IEC 27001
_(extensible via YAML rule packs)_

**Vendors tested out-of-the-box:** Cisco (IOS/Catalyst/Nexus) · Juniper
(SRX/EX/MX) · Palo Alto · Fortinet · Arista EOS · MikroTik Any additional vendor
is supported through the **Training Interface** without code changes.

---

## Roadmap

- [ ] Live device polling via SSH/API (in addition to file upload)
- [ ] Role-based access control for multi-admin teams
- [ ] Historical compliance trend tracking per device
- [ ] _(Bonus/exploratory)_ Air-gapped network health monitoring module — local
      LLM-based congestion/anomaly detection with multi-WAN failover advisory,
      surfaced in the same dashboard

---

## Contributing

Contributions are welcome. Please open an issue to discuss significant changes
before submitting a pull request.

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes
4. Push and open a PR

---

## License

This project is licensed under the MIT License — see [`LICENSE`](LICENSE) for
details.

---

## Contact

For queries related to the problem statement, refer to NCIIPC:
[nciipc.gov.in](https://nciipc.gov.in) · `helpdesk1@nciipc.gov.in`

For project-specific questions, open an issue on this repository.
