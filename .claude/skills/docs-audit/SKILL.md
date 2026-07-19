---
name: docs-audit
description: >-
  Full sweep of context docs (docs/, HANDOFF.md, STATUS.md, CONTEXT.md, root docs) for staleness,
  broken links, misplaced files, and duplication. Auto-fixes mechanical issues, flags judgment-call
  issues. Use when asked to audit/review the docs system, or periodically after a batch of doc edits
  to catch drift.
---

# Docs Audit

Conventions enforced: [.claude/rules/docs-management.md](../../rules/docs-management.md).

1. **Inventory**: list `docs/**/*.md`, `HANDOFF.md`, `STATUS.md`, `CONTEXT.md`, `README.md`, `CLAUDE.md`.
2. **Staleness**: for each doc with a "Last updated" or dated header (e.g. `docs/DECISIONS.md`
   entries), compare against its own body content and cross-linked docs (does it reference a
   decision or spec change dated later than its own header?). Auto-fix: bump the date.
3. **ADR vs `DECISIONS.md` placement**: scan `docs/DECISIONS.md` entries for language describing an
   algorithm, architecture, or module-boundary change (the two-tier criterion in
   `docs-management.md`) that was recorded inline instead of split into its own `docs/adr/NNNN-*.md`.
   Flag — do not auto-split; report the entry and recommend extraction.
4. **Duplicate/overlapping registries or content**: grep for docs covering the same ground (e.g.
   two decision logs, two task trackers). Flag — do not auto-merge; report the overlap and
   recommend which is canonical per `docs-management.md`.
5. **`docs/plans/` lifecycle**: any plan whose open questions are fully resolved (check against
   `docs/DECISIONS.md` and `docs/adr/` for a matching dated entry) should be deleted after
   confirming its content made it into one of those. Flag if unclear.
6. **`docs/specs/` vs `docs/plans/` drift**: flag any file in `docs/plans/` that reads as a durable
   build spec (referenced by code/build order, not just open questions) — recommend moving to
   `docs/specs/`. Flag the inverse too: a `docs/specs/` file that's actually still an open-question
   plan.
7. **Archive pattern conformance**: confirm archived material lives under a per-directory `archive/`
   subfolder, not a top-level `docs/archive/`. Flag deviations.
8. **Single-registry conformance**: confirm no second registry has appeared outside its canonical
   home (e.g. an experiment tracker under `.claude/` instead of `docs/experiments/README.md`).
9. **Dead links**: check relative links/paths in edited docs resolve to real files. Auto-fix
   obvious renames (e.g. a doc moved but old links weren't updated); flag ambiguous cases.
10. **Report**: summarize what was auto-fixed vs. what needs a human decision, in that order.
