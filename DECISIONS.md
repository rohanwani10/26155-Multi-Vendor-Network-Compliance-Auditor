# Decisions

Running log of what changed and why, per the SIH PS 26155 compliance work
order. Appended after every numbered item — raw material for
`docs/architecture.md` (item 12), not a substitute for it.

---

## Item 1 — Observation wrapper + tri-state verdicts (Correction 1)

**What:** Every schema leaf now carries provenance instead of a bare
`False`/`0` default: `{value, derivation, evidence, confidence}`.
`derivation="absent_unknown"` means no adapter found any signal for the
field at all; only `"explicit"` (a real line matched, regex or Tier-2 AI
classification) or `"vendor_default"` (a documented platform fact, e.g.
Junos SSH is always v2 once enabled) may back a Pass/Fail verdict.
Everything else evaluates to `manual_review` instead of guessing.

**Why:** The audit found confident Pass/Fail verdicts issued on data no
adapter ever examined — e.g. the Juniper fixture reported PASS on telnet
and weak-ciphers purely because `empty_schema()`'s concrete-falsy defaults
are indistinguishable from an affirmatively-confirmed-absent finding.

**Decided against:** Modeling `vendor_default` beyond the two cases that
already existed in the code (Junos/PAN-OS/FortiOS SSH-is-v2-only-once-
enabled). Every other absent field is conservatively `absent_unknown`
rather than guessing at platform behavior not fully verified — "never
guess" was the explicit instruction, and asserting a vendor default I'm
not certain of would just be guessing with extra steps.

**Deferred:** Precise per-adapter coverage measurement — that's item 2.

**Tests:** 39 → 42 passed (3 new, 0 regressions, 0 deleted). Required test
(`tests/test_observation_tristate.py`) written and confirmed failing
against pre-fix code before implementing, per instruction.

---

## Item 2 — Coverage matrix (Correction 3)

**What:** Each vendor adapter now declares which fields it has real
extraction logic for (`app/parsers/*.py`, `DECLARED_COVERAGE` — the same 8
fields the CIS pack's 8 controls read). `app/evaluator/coverage.py`
computes, from a normalized schema, how many of those fields the adapter
actually backed with a real Observation for a given file. One computation,
wired into all four deliverables the correction asked for:

1. **Enforcement test** (`tests/test_coverage_matrix.py`,
   `test_declared_coverage_never_exceeds_actual_coverage`) — fails if an
   adapter's own canonical fixture doesn't actually demonstrate every field
   it declares. Written first; it failed against the pre-enrichment
   fixtures exactly as expected (Cisco/Arista missing password-length
   evidence; Juniper/PaloAlto missing aaa+password; Fortinet missing
   aaa+password+banner).
2. **UI indicator** — `/api/devices/{id}/report` now returns
   `manual_review_count` and `coverage: {evaluable_count, total_controls}`;
   the report page shows "N of M controls evaluable... X require
   configuration data this adapter did not extract" and a 4th summary card
   when manual-review findings exist.
3. **PDF section** — coverage line plus a "Manual Review Required" list in
   `_render_pdf_fpdf`, feeding item 8's fuller provenance appendix later.
4. **Slide-ready data** — the coverage matrix itself (declared vs. actual,
   per vendor) is the artifact item 12 will pull directly into a slide;
   no separate slide file created yet, that's item 12's assembly step.

**Fixture enrichment (not fixture replacement — the hard constraint):**
added real aaa/password-length/banner lines to `cisco_ios_1.cfg`,
`arista_1.cfg`, `juniper_1.cfg`, `paloalto_1.cfg`, `fortinet_1.cfg` so every
declared field is actually proven achievable, not just claimed. This is
also what the enforcement test is *for* — a declared-but-unproven field is
exactly the class of bug it exists to catch.

**Collateral fix:** item 1's two pinned Juniper regression tests
(aaa/password-length → manual_review) were pointed at the shared
`juniper_1.cfg` fixture, which item 2 deliberately closed that exact gap
in. Re-pinned them to a minimal inline config kept local to the test file,
so the tri-state regression case stays isolated from a fixture that
legitimately keeps evolving for other reasons.

**Tests:** 42 → 45 passed (3 new, 0 regressions, 0 deleted).

---
