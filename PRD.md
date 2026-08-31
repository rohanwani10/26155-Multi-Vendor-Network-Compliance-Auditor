# PRD — Multi-Vendor Network Compliance Auditor

**Problem Statement:** NTRO #26155 **Document type:** Agent-executable Product
Requirements Document (phased build plan) **Audience:** Autonomous coding agent
(e.g. Claude Code) executing this build end-to-end, phase by phase, with a
test/verify gate before advancing.

---

## 1. Purpose

Build a vendor-agnostic tool that ingests network device configuration files
(any vendor), normalizes them into a common schema, checks that schema against a
chosen security framework (CIS / NIST / STIG / ISO), reports pass/fail findings
with severity and remediation, and — when it meets an unrecognized config format
— lets a human teach it once via a UI, after which it never needs to ask again
for that pattern.

## 2. Goals

- G1: Parse configs from 5+ vendor families out of the box (Cisco IOS, Juniper,
  Palo Alto, Fortinet, Arista, at minimum).
- G2: Evaluate against at least CIS as the primary framework, with NIST/STIG/ISO
  as additional rule packs (same evaluator, different YAML).
- G3: Handle an unrecognized config line via embedding-similarity match → local
  LLM classification → human-in-the-loop training, in that order.
- G4: Generate a PDF report per device with pass/fail, severity, and exact
  remediation CLI.
- G5: Ship a working, demoable end-to-end flow, not just isolated modules.

## 3. Non-Goals (explicitly out of scope for this build)

- Pushing/deploying configs to live devices (read-only auditing only).
- Live SSH polling of devices (file upload only, for this version).
- Multi-tenant auth / RBAC (single-admin assumption for now).
- The network-monitoring / multi-WAN failover module — tracked separately as a
  bonus/Phase 9, not required for core completion.

## 4. Tech Stack (finalized)

Frontend need is intentionally minimal, so **the backend renders the frontend
directly** — no separate SPA, no npm build step, no client/server API contract
to maintain in two places.

| Layer           | Choice                                                                                                                            | Why                                                                                                     |
| --------------- | --------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| Web framework   | **FastAPI**                                                                                                                       | Async, auto OpenAPI docs, one language across the whole backend                                         |
| Frontend        | **Server-rendered HTML via Jinja2**, styled with **Tailwind CDN**, interactivity via **HTMX**                                     | No build step; HTMX gives modal/table interactivity (needed for the Training UI) without a JS framework |
| Tier-1 Parsing  | **TextFSM + `ntc-templates`**, **`ciscoconfparse2`** for hierarchical Cisco-style configs                                         | Reuses a mature, community-maintained template library instead of hand-writing per-vendor parsers       |
| Tier-2 fallback | **`sentence-transformers`** (embeddings) → **Chroma** (local vector store) → **Ollama** (local LLM: `phi3:mini` or `llama3.1:8b`) | Fully on-prem / air-gap-friendly, no external API calls on sensitive config data                        |
| Rule engine     | Custom Python evaluator reading **YAML rule packs**                                                                               | Trivial to add a new framework/control with zero code change                                            |
| Database        | **SQLite** by default (zero setup, fine for demo); swappable to **PostgreSQL** via one env var (SQLAlchemy)                       | Keeps local dev/test friction near zero while staying production-upgradable                             |
| PDF Reporting   | **WeasyPrint** rendering the _same_ Jinja2 templates used for the web view                                                        | One template, two outputs (HTML page + PDF) — avoids duplicating report layout logic                    |
| Testing         | **pytest**, **httpx** (API/integration tests), **BeautifulSoup** (assert rendered HTML content)                                   | Lightweight, no browser automation needed since there's no client-side JS logic to test                 |
| Deployment      | **Docker Compose** (api + ollama + optional postgres)                                                                             | One command spins up the whole air-gapped stack                                                         |

---

## 5. System Architecture (recap)

```
[Upload UI] → Ingestion → Tier-1 Parser ─┬─(known)──────────────► Vendor-Neutral Schema (JSON)
                                          └─(unknown)→ Tier-2 LLM ─┬─(confident)─────► Schema
                                                                    └─(unsure)→ Training UI
                                                                                  → Learned Rules Store
                                                                                  (feeds back into Tier-1)

Schema → Compliance Evaluator (CIS/NIST/STIG/ISO YAML rule packs) → Findings
Findings → HTML Dashboard + PDF Report (same Jinja2 templates)
```

---

## 6. Data Model (minimum viable schema)

```
Device
  id, filename, vendor, model, os_version, serial, uploaded_at

ParsedConfig
  id, device_id (FK), raw_text, normalized_json, parse_tier (1|2), confidence_score

LearnedRule
  id, vendor, raw_pattern (regex/snippet), category, field, created_by, created_at

RulePack
  id, framework (CIS|NIST|STIG|ISO), version

Rule
  id, rulepack_id (FK), rule_id (e.g. "CIS-1.2.1"), category, field,
  expected_value, severity, remediation_template (per-vendor dict)

Finding
  id, device_id (FK), rule_id (FK), status (pass|fail), severity, remediation_text
```

---

## 7. Phased Build Plan

**Instructions for the executing agent:** Complete phases strictly in order. At
the end of each phase, run the listed verification steps. Do not begin the next
phase until all exit criteria for the current phase pass. If a phase's tests
fail, fix within that phase before advancing — do not carry broken functionality
forward.

---

### Phase 0 — Project Scaffolding

**Objective:** Set up a runnable skeleton with no real logic yet, but a working
health-check endpoint and test harness.

**Tasks:**

- [ ] Initialize repo structure (see README's `Project Structure` section).
- [ ] Set up FastAPI app with a `/health` endpoint.
- [ ] Set up SQLAlchemy + SQLite, with an Alembic migration for an empty schema.
- [ ] Set up `pytest` with one trivial passing test.
- [ ] Add `docker-compose.yml` with an `api` service (Ollama/Postgres added in
      later phases as needed).
- [ ] Add `requirements.txt` pinned for: fastapi, uvicorn, sqlalchemy, alembic,
      jinja2, pytest, httpx.

**Verify:**

```bash
uvicorn app.main:app --reload &
curl http://localhost:8000/health   # expect {"status": "ok"}
pytest                              # expect 1 passed
```

**Exit criteria:** Server boots, `/health` returns 200, test suite passes,
Docker Compose brings the app up cleanly.

---

### Phase 1 — Ingestion Layer

**Objective:** Accept a config file (single or ZIP), store it, and detect the
vendor.

**Tasks:**

- [ ] `POST /devices/upload` — accepts a single file or a ZIP; unzips and
      creates one `Device` row per file found.
- [ ] Vendor auto-detection: check filename patterns + first N lines of the
      config (e.g. `!Cisco`, `## Last commit`, `set` syntax) against a small
      lookup table; fall back to `"unknown"`.
- [ ] Persist raw config text against the `Device`/`ParsedConfig` rows (schema
      from §6).
- [ ] Minimal HTML page (`/upload`) — an HTMX form posting to the upload
      endpoint, listing uploaded devices below it.

**Test data:** Include 3–5 small sample configs (Cisco, Juniper, Palo Alto) in
`tests/fixtures/configs/` for use throughout all phases.

**Verify:**

```bash
pytest tests/test_ingestion.py
# - uploads a single Cisco config -> Device row created, vendor="cisco"
# - uploads a ZIP of 3 configs -> 3 Device rows created
# - uploads an unrecognizable text file -> vendor="unknown", no crash
```

Manual: visit `/upload`, upload a sample file, confirm it appears in the device
list.

**Exit criteria:** All ingestion tests pass; uploaded devices are visible and
persisted; unknown vendors don't crash the pipeline.

---

### Phase 2 — Tier-1 Parsing & Normalization

**Objective:** Convert recognized vendor configs into the vendor-neutral JSON
schema.

**Tasks:**

- [ ] Integrate `ntc-templates` + TextFSM for Cisco IOS, Juniper, Arista, Palo
      Alto, Fortinet.
- [ ] Use `ciscoconfparse2` for hierarchical extraction where TextFSM templates
      fall short (e.g. nested ACL blocks).
- [ ] Write a `normalize(vendor, parsed_output) -> schema_dict` mapper per
      vendor family, covering the fields in the "Vendor-Neutral Schema"
      (management_plane, auth, logging, acl_rules, crypto — see architecture
      doc).
- [ ] Store `normalized_json` + `parse_tier=1` on `ParsedConfig`.
- [ ] Any line/section that doesn't map to a known field is collected into an
      `unrecognized_lines` list (input to Phase 3).

**Verify:**

```bash
pytest tests/test_tier1_parsing.py
# - Cisco fixture -> normalized_json.management_plane.telnet_enabled is bool, not None
# - Juniper fixture -> same fields populated
# - a config with an injected nonsense line -> that line appears in unrecognized_lines, not silently dropped
```

**Exit criteria:** All 5 vendor fixtures normalize with >80% of schema fields
populated (not null); unrecognized content is captured, never silently
discarded.

---

### Phase 3 — Tier-2 Fallback (Embeddings + Local LLM)

**Objective:** Classify unrecognized lines automatically where possible, before
asking a human.

**Tasks:**

- [ ] Stand up Chroma (local, persisted to disk) as the vector store.
- [ ] Embed each unrecognized line with `sentence-transformers`
      (`all-MiniLM-L6-v2`) and check for a close match against previously
      _learned_ patterns (empty initially — populated starting Phase 4).
- [ ] If no close match: send the line to a local Ollama model (`phi3:mini` to
      start) with a few-shot prompt classifying it into one of the schema's
      categories, returning a structured `{category, field, value, confidence}`.
- [ ] If `confidence >= threshold` (configurable, default 0.75): apply it to the
      schema, `parse_tier=2`.
- [ ] If `confidence < threshold`: leave it queued for Phase 4's Training UI.

**Verify:**

```bash
pytest tests/test_tier2_fallback.py
# - a clearly-classifiable unseen line (e.g. a made-up "set mgmt-timeout 300" style line)
#   -> gets a category/field/confidence back, no exception
# - confidence below threshold -> item appears in the "pending training" queue, not silently applied
```

Manual: confirm Ollama is reachable (`ollama list` shows the pulled model)
before running.

**Exit criteria:** Fallback pipeline runs end-to-end without external network
calls; low-confidence items correctly queue for training rather than being
guessed into the schema.

---

### Phase 4 — Training & Feedback Layer

**Objective:** Let a human resolve queued/unrecognized lines, and make that
resolution permanent.

**Tasks:**

- [ ] `/training` HTML page (HTMX): table of pending unrecognized lines, each
      with dropdowns for `category` and `field`, and a submit button.
- [ ] `POST /training/resolve` — saves the mapping as a `LearnedRule` (vendor,
      raw_pattern, category, field).
- [ ] On save: re-embed the pattern and add it to Chroma so future
      identical/similar lines resolve via Phase 3's embedding-match step without
      hitting the LLM again.
- [ ] Re-run normalization for the affected `ParsedConfig` so the schema updates
      immediately (visible in the UI without a manual re-upload).

**Verify:**

```bash
pytest tests/test_training_loop.py
# - queue an unrecognized line -> resolve it via the training endpoint
# - re-submit the SAME line on a different device -> resolved via embedding match (not LLM), confirm via a mock/spy that Ollama was NOT called the second time
```

Manual: run the full loop live — upload an unknown-format config, see it queue,
train it via `/training`, re-upload a similar config, confirm it now
auto-resolves.

**Exit criteria:** A trained pattern is reused automatically on the next
matching config, with no code change and no repeat LLM call. This is the core
"learning loop" — it must work convincingly, since it's the flagship demo
moment.

---

### Phase 5 — Compliance Evaluation Engine

**Objective:** Evaluate a normalized schema against rule packs and produce
findings.

**Tasks:**

- [ ] Define the YAML rule pack format (see architecture doc example: `id`,
      `framework`, `category`, `field`, `expected`, `severity`, `remediation`
      per vendor + `default`).
- [ ] Ship an initial **CIS** rule pack covering at least: Telnet disabled,
      SSHv2 enforced, password minimum length, AAA enabled, syslog configured,
      banner configured, weak ciphers absent (8–10 rules is enough for MVP).
- [ ] Evaluator: for each `Rule` in the active `RulePack`, compare the schema's
      field to `expected`; write a `Finding` (pass/fail, severity, remediation
      pulled from the device's vendor, falling back to `remediation.default`).
- [ ] `POST /evaluate/{device_id}?framework=CIS` — triggers evaluation, returns
      findings.

**Verify:**

```bash
pytest tests/test_compliance_engine.py
# - a schema with telnet_enabled=true -> a FAIL finding for the telnet rule, correct severity
# - a schema with telnet_enabled=false -> a PASS finding
# - adding a brand-new rule via a new YAML entry (no code change) is picked up on next evaluation run
```

**Exit criteria:** Findings are correct against known-good/known-bad fixture
configs; adding a new YAML rule requires zero code changes (test this
explicitly).

---

### Phase 6 — Reporting (HTML + PDF)

**Objective:** Turn findings into a human-readable report, in both a web view
and a downloadable PDF.

**Tasks:**

- [ ] Jinja2 template `report.html` — device metadata header, findings table
      (pass/fail, severity, remediation), grouped by category.
- [ ] `GET /devices/{id}/report` — renders `report.html` in-browser.
- [ ] `GET /devices/{id}/report.pdf` — renders the _same_ template through
      WeasyPrint to produce a PDF.
- [ ] `/dashboard` — aggregated view across all devices (counts by severity,
      worst offenders first).

**Verify:**

```bash
pytest tests/test_reporting.py
# - report.html contains the device's findings (assert via BeautifulSoup)
# - report.pdf endpoint returns a valid PDF (check magic bytes %PDF)
```

Manual: open a generated PDF, confirm it's legible and includes remediation
commands.

**Exit criteria:** Both HTML and PDF reports render correctly from the same
template with no duplicated layout logic.

---

### Phase 7 — Frontend Polish (still backend-rendered)

**Objective:** Make the existing server-rendered pages presentable for a demo,
without introducing a separate frontend app.

**Tasks:**

- [ ] Apply Tailwind (via CDN, no build step) consistently across `/upload`,
      `/training`, `/dashboard`, `report.html`.
- [ ] Add HTMX-driven polish: upload progress indicator, inline success/error
      messages on training submission, live-updating findings table after
      training resolves an item.
- [ ] Add severity color-coding (red/orange/yellow) consistent across dashboard
      and reports.
- [ ] Basic nav bar linking all pages.

**Verify:** Manual walkthrough of the full flow in a browser: upload → (if
needed) train → evaluate → view dashboard → download PDF. No console errors, no
broken links.

**Exit criteria:** A first-time viewer can complete the full flow without
instructions.

---

### Phase 8 — End-to-End Integration Test & Demo Readiness

**Objective:** Confirm the whole pipeline works as one story, back to back.

**Tasks:**

- [ ] Write one integration test that runs the full path: upload a known-vendor
      config → evaluate → assert findings exist → generate PDF.
- [ ] Write one integration test for the "unknown vendor" path: upload an
      unrecognized format → confirm it queues for training → resolve it →
      confirm it now evaluates correctly.
- [ ] `docker-compose up` from a clean clone completes with no manual steps
      beyond `.env` setup.
- [ ] Record the demo flow once everything is green (this maps to the required
      2-minute demo video deliverable).

**Verify:**

```bash
pytest tests/test_e2e.py -v
docker-compose down -v && docker-compose up --build   # clean-slate boot check
```

**Exit criteria:** Both end-to-end paths pass; a clean-machine
`docker-compose up` works without hidden manual fixes.

---

### Phase 9 — (Bonus, optional, do not start before Phase 8 is green)

**Objective:** Network Health Monitoring & Link Advisory module (air-gapped
local LLM), as previously scoped — kept separate so it never blocks or dilutes
the core deliverable.

**Tasks:** (only if time remains after Phase 8)

- [ ] Telemetry collector stub (SNMP/NetFlow ingestion).
- [ ] Congestion/spike detector using the same local Ollama instance.
- [ ] Multi-WAN link comparator.
- [ ] Surface alerts on the same `/dashboard` page, clearly labeled as a
      separate module.

**Exit criteria:** Clearly does not modify or risk the Phase 0–8 deliverable;
presented as an add-on in the demo, not the headline.

---

## 8. Deliverable Mapping

| Required Deliverable                  | Produced By                                                                                      |
| ------------------------------------- | ------------------------------------------------------------------------------------------------ |
| Source Code                           | Phases 0–8 (Phase 9 optional)                                                                    |
| README with setup instructions        | Already generated (`README.md`)                                                                  |
| Architecture Document (max 2 pages)   | Derived from §5 + the Excalidraw diagram                                                         |
| Demo Video (max 2 minutes)            | Recorded at end of Phase 8, following the two integration-test scripts as the demo script        |
| Technical Presentation (max 5 slides) | Summarize §4 (stack), §5 (architecture), and the Phase 4 training-loop moment as the centerpiece |

## 9. Risks & Mitigations

| Risk                                                 | Mitigation                                                                                                                                     |
| ---------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| LLM misclassifies a security-relevant field silently | Confidence threshold + mandatory human review below it (Phase 3/4); never auto-apply low-confidence results                                    |
| Local LLM too slow/large for demo hardware           | Default to `phi3:mini`; document the swap to `llama3.1:8b` as a config change, not a code change                                               |
| Scope creep into Phase 9 before core is solid        | Hard gate: Phase 9 cannot start until Phase 8 exit criteria are met                                                                            |
| Vendor parser coverage gaps                          | `ntc-templates` covers most common vendors; anything missing is exactly what the training loop exists to handle — treat as expected, not a bug |

---

## 10. Definition of Done (whole project)

- All Phase 0–8 exit criteria met and passing in CI (or local `pytest` run).
- A user can upload an unfamiliar config, train the system live, and see it
  parse correctly on a subsequent upload — with the whole loop taking under two
  minutes, suitable for the demo video.
- `docker-compose up` on a clean machine produces a fully working system with no
  manual patching.
