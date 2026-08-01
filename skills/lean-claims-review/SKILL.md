---
name: lean-claims-review
description: Run blinded docstring-vs-statement reviews over a Lean library. Use when a project keeps a claims ledger (verdicts that each docstring claims exactly what its statement proves) and asks to review pairs — bootstrapping a full sweep, re-reviewing declarations a gate reports stale, or calibrating referee configurations. Dispatches one blinded referee subagent per declaration; the referee sees the statement, the docstring, and verified dependency docstrings, never the source tree. Also use for the design questions: which effort level referees need, how to order a sweep, when a mismatch indicts the statement instead of the prose.
---

# Blinded claims review

A docstring is a claim about what the kernel checked, and the kernel does
not read prose. A claims review compares each docstring against its
declaration's elaborated statement and records a verdict; a project-side
gate then fails the build when a verdicted pair changes. This skill is the
review half: it dispatches referees, enforces their blinding, and routes
their findings. The gate, the ledger, and the probe are the project's; this
skill assumes they exist and their paths are recorded in the project's
CLAUDE.md.

## The blinding invariant

> A referee's prompt contains exactly one piece of unverified prose: the
> docstring under judgment. Everything else it sees is formal (the printed
> statement, probe output) or previously verified (direct dependencies'
> docstrings, already ledger-passed).

A referee that reads the source file inherits the author's framing — the
module docstring restates the claim three ways and the referee nods along.
Blinding is enforced by tooling, not instruction: referees run as an agent
type whose only tools are the project's probe command (a `lake env lean
--stdin` wrapper) and web search. No Read, no Grep, no general shell. The
project's manuscripts and READMEs are excluded for the same reason at any
effort level: papers narrate significance, and a referee steeped in
significance passes significance-flavored docstrings — a false `supported`,
the silent failure direction.

## What the project must supply

- **Pairs**: a machine-readable manifest with, per declaration: name, kind,
  the pretty-printed elaborated statement, the docstring, content hashes,
  and direct-dependency edges. (A build artifact, not something this skill
  extracts.)
- **A probe**: one whitelisted command elaborating Lean source from stdin
  against the built library, exit code distinguishing success.
- **A ledger and its writer**: verdicts are recorded only through the
  project's ledger tool; this skill never writes the ledger file directly.
- **Calibration pairs**: constructed defective pairs with an answer key.
  No referee configuration produces accepted verdicts until it has flagged
  every constructed defect and answered the ambiguous pair
  `intent-unclear` — a detector is calibrated before its verdict counts.

## Invocation

Invoked bare, the skill reviews and routes: prose findings go to a
full-context session, statement findings stop at the maintainer. Invoked
with the **`--fix`** argument, the run is fully autonomous — the flag is
the maintainer's standing authorization to repair whatever a finding
indicts, prose or Lean: docstring rewrites, statement restatements,
proof repairs, deletions of duplicates, whichever the dispatching
session judges worthwhile on the referee's evidence (decision guidance
in `references/dispatch.md`, "Disposing statement findings"; Lean
authoring follows the proving skill's craft, applied between waves).
Everything else is unchanged: findings are still logged, every
statement-level act still gets its process-record entry at the time it
is made, and reverting a bad call re-enters the declaration on the next
run.

## Workflow

1. Diff the manifest against the ledger: the unverdicted and stale set.
2. Order it into waves by dependency depth, dependencies first, so each
   referee's dependency docstrings arrive already verified.
3. Dispatch a wave's referees back-to-back (one shared cached prefix; see
   `references/dispatch.md` for cache, effort, budget, and model policy).
4. Record `supported` verdicts through the ledger tool. Route findings:
   prose fixes go to a full-context session; statement indictments and
   ambiguities go to the maintainer, or are disposed by the dispatching
   session itself when the maintainer has authorized autonomous
   disposition (`references/dispatch.md`, "Disposing statement findings").
   Referees author nothing either way.
5. On a flag, skip the declaration's consumer cone and keep sweeping; the
   fixed declaration re-enters on the next run — or between waves, when
   the maintainer authorizes fixing inline (`references/dispatch.md`,
   "Fixing between waves").
6. Stop cleanly when the token budget is spent — the ledger is the resume
   state.

## The dual disposition

A mismatch has two repairs: fix the prose, or the docstring recorded the
intent and the statement fails to carry it — fix the Lean. The referee
does not choose by judgment; it chooses by probe (satisfiability,
triviality, strengthening — `references/referee-protocol.md`). All probes
quiet means prose conforms to the statement: the kernel-checked statement
is the artifact of record, and changing it is the maintainer's deliberate
act, never a review side effect.

## References

| File | Read it when |
|---|---|
| `references/referee-protocol.md` | Dispatching referees: the verbatim protocol prompt, verdict schema, probe battery |
| `references/dispatch.md` | Planning a sweep: waves, cache structure, effort/model/budget policy, calibration procedure |

Sibling skills: `lean-latex-sync` owns prose-truthfulness craft and the
drift taxonomy the verdict axes come from; `lean-verification` audits
whether a proof establishes its claim (a statement-side question);
`lean-proving` for acting on `statement-suspect` findings.
