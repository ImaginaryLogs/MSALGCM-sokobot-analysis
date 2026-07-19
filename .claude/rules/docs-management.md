# Context Docs Management

Conventions for `docs/`, `HANDOFF.md`, `STATUS.md`, root docs. Full sweep + auto-fix: `docs-audit` skill.

- **Two-tier decision record.** `docs/adr/NNNN-title.md` for decisions that change algorithm,
  architecture, or module boundaries (e.g. "Weighted A* not IDA*", the HP engine choice).
  Everything else — schema tweaks, terminology fixes, scope trims, task splits — is a dated bullet
  in `docs/DECISIONS.md`. When in doubt, it's a `DECISIONS.md` bullet, not an ADR.
- **`docs/DECISIONS.md` is append-only**: single source of truth for resolved decisions, dated
  entries. `HANDOFF.md`, `STATUS.md`, and `docs/plans/*.md` link to it instead of repeating content.
- **`docs/specs/<name>.md` is durable**: a build spec meant to be referenced through and past
  implementation (e.g. `sokoban-port-plan.md`). Not deleted once decisions land — unlike a plan.
- **`docs/plans/<name>.md` is active-only**: exists only while it has open questions. When fully
  resolved, merge the resolution into `docs/DECISIONS.md` (or a new ADR, per the two-tier rule
  above) and delete the plan file. Git history is the record — don't keep resolved plans as archives.
- **Single canonical registry per concern**: e.g. `docs/experiments/README.md` tracks every
  experiment run. Do not create a second registry elsewhere (e.g. under `.claude/`) — it will
  drift and duplicate.
- **Archive pattern = per-directory `archive/` subfolder** (e.g. `docs/experiments/archive/`), not
  a top-level `docs/archive/`. Archived content stays next to its live counterpart.
- **`HANDOFF.md` is next-agent orientation only** — what to build, build order, do-nots, blocked-on.
  Not a history dump; locked decisions and rationale live in `docs/DECISIONS.md` / `docs/adr/`,
  linked not repeated.
- **`STATUS.md` is the live tracker** — owners, phases, due dates, checkboxes. Not a decision
  record; when a task's outcome becomes a decision, move it to `docs/DECISIONS.md` and leave the
  checkbox in `STATUS.md` pointing there.
- **`docs/reference/`** holds standalone background material (proposal, spec brief, wiki notes,
  format docs) that doesn't fit the other categories and isn't itself part of the project's
  decision trail.
- **`docs/papers/`** holds lit-review source PDFs. **`docs/kg/`** is the Obsidian knowledge-graph
  vault (llm-wiki pattern) — both established categories, not stray files.
- **When editing any doc with a "Last updated" header, update the date to the current session date.**
