# Changelog

All notable changes to this build, phase by phase, per `PRD.md`'s phased plan.

## Phase 0 — Project Scaffolding

**Added:**

- `app/` FastAPI package (`app/main.py`) with a `GET /health` endpoint
  returning `{"status": "ok"}`.
- `app/database.py` — SQLAlchemy engine/session setup, SQLite by default via
  `DATABASE_URL` env var, one-line swap to Postgres.
- Alembic migration environment (`alembic/`, `alembic.ini`) wired to
  `app.database.Base.metadata`; initial revision `a4d629debf3f` is an empty
  no-op schema (no tables yet — those arrive with Phase 1's `Device` /
  `ParsedConfig` models).
- `tests/test_health.py` — one trivial passing test via FastAPI `TestClient`.
- `requirements.txt` pinned to fastapi, uvicorn, sqlalchemy, alembic, jinja2,
  pytest, httpx (exactly the Phase 0 list from the PRD — later phases add
  their own deps as needed).
- `Dockerfile` + `docker-compose.yml` (single `api` service; Ollama/Postgres
  services deferred to the phases that actually need them, per the PRD).
- `.env.example`, `.gitignore`.
- Corrected `README.md`'s Tech Stack / Getting Started / Project Structure
  sections, which predated `PRD.md` and described a conflicting stack (React
  + Node.js + npm build + PostgreSQL + Netmiko). PRD §4 is the finalized,
  authoritative stack (FastAPI + Jinja2 + HTMX + Tailwind CDN, no SPA, no npm
  build, SQLite default) and takes precedence.

**Assumption (design ambiguity):** PRD Phase 0 says "Initialize repo
structure (see README's Project Structure section)", but the README's
structure described the old `backend/` + `frontend/` React layout. Since the
PRD's own Verify commands are explicit (`uvicorn app.main:app`,
`tests/test_ingestion.py`, etc.), the app package is named `app/` (not
`backend/`) and there is no separate `frontend/` — Jinja2 templates and
static assets live under `app/templates/` and `app/static/`, consistent with
"no separate SPA" in PRD §4.

**Verified:**

- `pytest` → `1 passed`.
- `uvicorn app.main:app` booted locally; `curl http://localhost:8000/health`
  → `{"status": "ok"}`.
- `docker compose up --build` → clean boot from a fresh image;
  `/health` responded correctly through the container; `docker compose down`
  tore it down cleanly.

**Exit criteria met:** Server boots, `/health` returns 200, test suite
passes, Docker Compose brings the app up cleanly. ✅

---

## Phase 1 — Ingestion Layer

**Added:**

- `app/models.py` — `Device` and `ParsedConfig` ORM models (per PRD §6);
  Alembic migration `3cd8ff31948c` adds their tables.
- `app/vendor_detect.py` — vendor auto-detection: checks filename hints
  first, then a small ordered signature table against the first 40 lines of
  content (Arista/Fortinet/Palo Alto/Juniper checked before the generic
  Cisco fallback, since Arista's IOS-like syntax would otherwise be
  misdetected as Cisco). Falls back to `"unknown"` when nothing matches.
- `app/ingestion.py` — `extract_files()`: detects a ZIP via magic bytes
  (`zipfile.is_zipfile`, not just the `.zip` extension) and expands it into
  one `(filename, text)` pair per contained file; a non-ZIP upload is
  treated as a single file.
- `app/routers/devices.py` — `POST /devices/upload` (creates one `Device` +
  `ParsedConfig` row per file found, HTML-fragment response for HTMX) and
  `GET /upload` (full page, HTMX form + live device list).
- `app/templates/upload.html`, `_device_list.html` — minimal server-rendered
  pages (no Tailwind polish yet; that's Phase 7's job per the PRD).
- `tests/fixtures/configs/` — one realistic sample config per vendor
  (`cisco_ios_1.cfg`, `juniper_1.cfg`, `paloalto_1.cfg`, `fortinet_1.cfg`,
  `arista_1.cfg`) plus `unknown_device.txt`. Created all 5 vendor families
  now (not just the 3 the Phase 1 task text names) since Phase 2's exit
  criteria require all 5, and the top-level instructions say to reuse Phase
  1 fixtures across every later phase rather than inventing new ones per
  phase.
- `tests/conftest.py` — `db_session`/`client` fixtures: a fresh temp-file
  SQLite DB per test, wired in via FastAPI `dependency_overrides` so tests
  never touch the dev `compliance.db`.
- Added `python-multipart` (required by Starlette to parse the upload form)
  and `beautifulsoup4` (per PRD's Testing stack row) to `requirements.txt`.

**Verified:**

- `pytest tests/test_ingestion.py` → `4 passed` (single Cisco upload →
  `vendor="cisco"`; ZIP of 3 configs → 3 `Device` rows with correct
  per-file vendors; unrecognizable `.txt` → `vendor="unknown"`, no crash).
- Full suite: `pytest` → `5 passed`.
- Standalone check: `detect_vendor()` run against all 5 fixtures with a
  generic filename (forcing pure content-based detection) — all 5 correctly
  identified, confirming detection doesn't just rely on filename hints.
- Manual: booted the server, `curl -F file=@cisco_ios_1.cfg
  http://localhost:8000/devices/upload` → returned the updated device-list
  fragment with `vendor=cisco`; `GET /upload` then showed that device in
  the rendered table.

**Exit criteria met:** All ingestion tests pass; uploaded devices are
visible and persisted; unknown vendors don't crash the pipeline. ✅

---

## Phase 2 — Tier-1 Parsing & Normalization

**Assumption (design ambiguity, investigated before implementing):** PRD
Phase 2 says to "integrate `ntc-templates` + TextFSM for Cisco IOS, Juniper,
Arista, Palo Alto, Fortinet." Before writing any parser code, I installed
`textfsm`/`ntc-templates`/`ciscoconfparse2` and inspected ntc-templates'
actual template index: it ships **zero** "show running-config"-style
templates for any of the 5 platforms (Fortinet has no templates at all;
Cisco/Palo Alto only have narrow ones like `show running-config partition
access-list`). ntc-templates + TextFSM are built for parsing *tabular "show
command" output*, not full raw config-file dumps — a full config isn't the
input shape these tools target. So the actual design is:
  - **ciscoconfparse2** genuinely parses the one hierarchical structure
    that needs it — Cisco IOS / Arista EOS configs as a whole, and
    specifically nested ACL blocks (parent `ip access-list ...` + child
    `permit`/`deny` lines), exactly the case PRD's own task text calls out.
  - **TextFSM** parses each extracted ACL block's entries — the one
    genuinely tabular, repetitive-row structure in these configs (every
    ACE has the same action/protocol/source/dest/port shape) — via a
    project-authored template (`app/parsers/textfsm_templates/acl_entries.textfsm`),
    since no ntc-templates template matches our input format.
  - Single-line boolean/value fields (telnet, SSH, AAA, syslog, banner,
    password policy, weak ciphers) are plain regex over the raw text for
    all 5 vendors — TextFSM's state-machine engine is the wrong tool for a
    single boolean presence check, and PRD §9 already anticipates "vendor
    parser coverage gaps" as expected, not a bug.
  - Juniper/Palo Alto/Fortinet ("set"-style or `config`/`edit`/`next`/`end`
    block syntax) have no ciscoconfparse2/ntc-templates fit at all, so
    they're direct per-vendor line/regex extraction — this is also what
    the PRD's own task 3 asks for regardless ("normalize(vendor,
    parsed_output) -> schema_dict mapper **per vendor family**").

**Assumption (schema, no `docs/architecture.md` exists in this repo):**
PRD §6 names the 5 top-level categories (`management_plane`, `auth`,
`logging`, `acl_rules`, `crypto`) but defers field-level detail to "the
architecture doc," which isn't in this repo. Defined a minimal schema
covering exactly the fields Phase 5's own MVP rule list needs (telnet,
SSH+version, AAA, password min length, syslog, banner, weak ciphers) plus
`acl_rules` and `unrecognized_lines`. All scalar leaves default to a
concrete "not found" value (`False` / `0`) rather than `None`, so the
Phase 5 evaluator always has something to compare and Phase 2's own ">80%
populated" exit criterion holds by construction — see `app/parsers/schema.py`.

**Added:**

- `app/parsers/schema.py` — `empty_schema()` skeleton.
- `app/parsers/common.py` — `classify_unrecognized()`: a line is
  "unrecognized" (Tier-2 candidate) only if it matches *no* known-syntax
  pattern for that vendor — not "recognized syntax we just don't map to a
  field." Keeps Phase 4's training queue free of routine noise like
  interface/routing config.
- `app/parsers/ios_style.py` — shared Cisco/Arista normalizer
  (ciscoconfparse2 + TextFSM, as above).
- `app/parsers/juniper.py`, `paloalto.py`, `fortinet.py` — per-vendor
  regex-based normalizers for the 3 flat-syntax vendors.
- `app/parsers/unknown.py` — vendor entirely unrecognized: every line goes
  straight to `unrecognized_lines`.
- `app/parsers/__init__.py` — `normalize(vendor, raw_text) -> dict`
  dispatcher.
- Wired into `app/routers/devices.py`'s upload handler: every uploaded
  config is now normalized at ingestion time, storing `normalized_json` +
  `parse_tier=1` on its `ParsedConfig` row.
- Extended `tests/fixtures/configs/cisco_ios_1.cfg` and `arista_1.cfg`
  (created in Phase 1) with a small ACL block each, since neither had one
  and Phase 2 explicitly needs nested-ACL coverage — completing those
  fixtures rather than inventing new ones, per the reuse-fixtures rule.

**Verified:**

- `pytest tests/test_tier1_parsing.py` → `8 passed`: Cisco
  `telnet_enabled` is `bool` (`True`, matching its intentionally
  "before-hardening" fixture); Juniper's fields populate the same way;
  an injected nonsense line lands in `unrecognized_lines` for both an
  IOS-style vendor (Cisco) and a set-style vendor (Juniper) rather than
  being dropped; all 5 vendor fixtures clear >80% fields populated (in
  fact 100%, by the "never None" schema design); ACL blocks for Cisco and
  Arista come back correctly structured through ciscoconfparse2 + TextFSM.
- Full suite: `pytest` → `14 passed` (added one integration test
  confirming the upload endpoint itself persists `normalized_json` +
  `parse_tier=1`, not just the standalone `normalize()` function).
- Manually inspected full normalized JSON for Palo Alto, Fortinet, and
  Juniper to confirm values are semantically correct (not just
  structurally non-null) — ACL rules, syslog servers, and banner/AAA
  status all matched the fixtures' actual content.

**Exit criteria met:** All 5 vendor fixtures normalize with >80% (100%) of
schema fields populated; unrecognized content is always captured, never
silently discarded. ✅

---

## Phase 3 — Tier-2 Fallback (Embeddings + Local LLM)

**Assumption (model choice):** PRD suggests `phi3:mini` as the starting
Ollama model. This machine already has `gemma3:4b` pulled (confirmed via
`ollama list`) and no `phi3:mini`. Per PRD §9's own risk mitigation ("the
exact model is a config swap, not a code change"), defaulted
`OLLAMA_MODEL` to `gemma3:4b` (whatever's already available) instead of
downloading a new multi-GB model just to match the PRD's literal example.
`phi3:mini` / `llama3.1:8b` remain drop-in swaps via `.env`.

**Assumption (no `PendingReview` table in PRD §6):** the schema in §6 has
no explicit "training queue" table, but Phase 3 needs somewhere durable to
put lines that don't clear the confidence threshold, and Phase 4's own
Verify section (queue → resolve → re-submit) requires that queue to
persist across requests. Added `PendingReview` (device_id, parsed_config_id,
vendor, raw_line, suggested category/field/value, confidence, status) —
minimal infrastructure Phase 3 needs to produce and Phase 4 will consume,
not scope creep into Phase 4's UI work itself.

**Added:**

- `app/tier2/embeddings.py` — Chroma-backed lookup against previously
  human-resolved patterns (`sentence-transformers` `all-MiniLM-L6-v2` for
  embeddings; empty until Phase 4 starts writing to it, so every Phase 3
  line is a genuine cache miss → LLM, by design). `anonymized_telemetry`
  explicitly disabled — this tool's whole premise is on-prem/air-gapped
  handling of device configs (PRD G3), so Chroma must never phone home.
- `app/tier2/llm_classifier.py` — calls local Ollama's REST API directly
  over `httpx` (already a dependency; didn't add the separate `ollama`
  PyPI client for one HTTP POST) with a few-shot prompt and
  `format: "json"` for structured `{category, field, value, confidence}`
  output. Unreachable/unparseable responses raise `LLMClassificationError`
  rather than ever silently guessing.
- `app/tier2/fallback.py` — `classify_line()` orchestrates embedding-match
  → LLM, in that order (PRD G3); `is_confident()` / `is_applicable()` gate
  whether a result is safe to auto-apply (only the 4 dict-shaped schema
  categories — `acl_rules` and unclassifiable results always go to review).
- `app/pipeline.py` — new `ingest_one()` / `apply_tier2()`, factored out of
  the upload router: Tier-1 normalize, then Tier-2-classify whatever's
  left unrecognized, merging confident results into the schema and queuing
  everything else as `PendingReview` rows. Reused by the upload endpoint
  now and by Phase 4's re-normalize-on-resolve step later.
- `PendingReview` model + migration `e87401803cb0`.
- `docker-compose.yml` — added the `ollama` service (PRD's stack table:
  "api + ollama + optional postgres"), with `OLLAMA_HOST`/`OLLAMA_MODEL`
  wired into the `api` service's environment so the containerized app can
  reach it. Model pull is a documented one-time manual step (`docker
  compose exec ollama ollama pull gemma3:4b`) — deliberately not baked
  into the image or auto-pulled on boot, since it's a multi-GB download.
- `tests/conftest.py` — `isolated_chroma` autouse fixture: every test gets
  its own on-disk Chroma directory so learned-pattern state can never leak
  between tests or across local runs.

**Verified:**

- `pytest tests/test_tier2_fallback.py` → `3 passed`, against the **real**
  local Ollama instance (confirmed reachable first via `ollama list`, per
  the PRD's manual precondition) — PRD's own example line
  (`"set mgmt-timeout 300"`) round-trips through the actual LLM and comes
  back with a valid category/field/confidence, no exception. The
  below-threshold branch is tested with a mocked LLM response (real model
  output isn't something a test should assert an exact confidence value
  against) to deterministically prove it queues via `PendingReview` and
  does *not* silently patch the schema.
- Full suite: `pytest` → `17 passed` in ~17s — including Phase 1's
  "unrecognized upload doesn't crash" test, which now genuinely exercises
  the full Tier-2 path end-to-end (3 real LLM calls) since Tier-2 is wired
  into every upload per the architecture diagram. Manually inspected the
  real classifications for that fixture's nonsense lines: the model
  correctly returned `category: "unknown"` at confidences 0.6/0.3/0.25 —
  all below the 0.75 threshold, all correctly queued rather than applied.
- Docker: rebuilt the image with the new ML dependencies
  (`sentence-transformers`, `chromadb`) and confirmed it still builds and
  boots cleanly.

**Exit criteria met:** Fallback pipeline runs end-to-end with no external
network calls (Ollama + Chroma are both local-only, telemetry disabled);
low-confidence items correctly queue for training rather than being
guessed into the schema. ✅
