# Syncing prose from a stream of commits

The main skill covers one resync after one change. This file covers the
recurring case: the Lean repo moves in many commits while the document
stands still, and a periodic pass has to catch the prose up. The failure
modes are different — work done twice, work done on text that no longer
exists, and a backlog too large to hold in one head — and so is the
machinery.

## The frontier

Persist which commit the prose was last synced to, and record it where
the prose lives, not where the Lean lives. A trailer on the sync commit
itself is the cleanest home:

```
Synced-To: 3f2c9d1e8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d
```

The frontier is then the newest such trailer in the document repo's log:
one fact, one home, atomic with the sync it describes, and it survives a
fresh clone with no side file. Advance it only on a completed, verified
sync — never on a failed or partial one — and every Lean commit is
synced exactly once by construction.

## Net diff, never per-commit replay

Sync the single diff from frontier to HEAD. Replaying commit-by-commit
does strictly worse on both failure modes it invites:

- **Add-then-revert.** A lemma added in one commit and deleted three
  commits later has vanished from the net diff; a per-commit replay
  writes prose for it and then deletes that prose. Both passes were
  waste.
- **Restated declarations.** A statement adjusted twice in the range
  gets prose written against the intermediate form — text that was
  stale the moment it was written.

The commit *messages* still matter: read them to group the work and to
name it in the sync commit. They inform intent; the net diff is the
work.

Where the project keeps an elaborated statement lock (see
`sync-checks.md`, check 6), the net statement-level delta is one
command — diff the lock file between the frontier and HEAD — and each
changed block is one declaration with its before and after types. That
is the exact-targets list a sync pass starts from.

## What kind of change is this? The work differs by kind

Sort the net delta before dispatching any work; each kind owes a
different pass, and treating them alike either wastes effort or misses
the defect.

**Mechanical: renames, moves, build config.** Citations dangle or go
stale. A namespace move is the trap: `Polynomial.natDegree_le` becoming
`MvPolynomial.natDegree_le` keeps any last-component name check green
while the document cites a name that no longer exists. Read the citation
sites; do not trust the checker. Build-config and CI changes usually owe
the prose nothing unless the document describes the toolchain.

**Docstring-only.** The obligation is two-sided: docstring versus
statement, and docstring versus every external prose surface that
paraphrases it. A fix landing on one side leaves the other stale — if
the document's sentence was tightened last month and the docstring still
carries the old overclaim, this stream's docstring edit is the moment to
reconcile them, and vice versa.

**Statement changes.** The full drift-catalogue re-audit
(`claim-checking.md`) over every claim citing the declaration. One
hazard deserves its own sentence: the prose that goes stale often does
not contain the declaration's name. A dropped `Monotone` hypothesis
lives in the document as the word "monotone" in a caveat beside the
citation — "(monotone kernels)", "requires monotonicity" — so search
for the *hypothesis words* near cite sites, not only for names.

**Additions.** Nothing greps to them. A new theorem falsifies prose
that scopes what the development does *not* do: the limitations
section, an omissions list, a "we prove only the weaker form"
concession, the abstract's hedges. Read those surfaces whole after any
addition; this is the category periodic syncs miss most.

**Deletions.** Dangling citations, plus the billing direction: a
deleted declaration may have been the support for a sentence that now
claims formal backing it no longer has.

**Framing discoveries.** Occasionally a commit changes what the
document should *argue* — a completeness result where only sufficiency
was claimed, a counterexample to something the narrative leaned on. A
sync pass fixes claims; it does not re-frame a document. Escalate these
to a human with the evidence quoted, and leave the framing untouched.

## Structured findings for a multi-agent pass

When the backlog is grouped and farmed out to parallel workers, make
each worker return findings in a fixed shape rather than edited files —
the aggregation step needs to see conflicts before anything is applied:

```json
{"class": "mandatory | recommended | optional | escalate",
 "surface": "which document",
 "anchor": "verbatim current text, enough to locate uniquely",
 "proposed": "exact replacement or insertion",
 "basis": {"declaration": "...", "statement_quote": "..."},
 "note": "one sentence of rationale"}
```

- **mandatory** — the document states what the library no longer
  proves: a stale claim, a dangling name, a wrong count.
- **recommended** — real drift short of falsehood, and additions the
  limitations text now contradicts.
- **optional** — enrichment: a new result worth citing, a remark worth
  tightening.
- **escalate** — framing-level, or anything requiring a change on the
  Lean side. Never auto-applied.

Quote-both-sides is a schema requirement, not a style preference: a
finding without the current text and the statement pasted in cannot be
verified by the aggregator and must not be applied. Aggregate with a
deterministic conflict rule — when two findings touch the same anchor,
the one grounded in the newer commit wins — and apply everything in one
pass, by hand, reading each target paragraph whole. Two workers editing
the same file directly, or the same anchor patched twice, is how a
grouped sync corrupts a document.

## Findings that arrive from outside

Two recurring false-positive shapes in review feedback on formal
documents, both worth checking before any edit:

- **Extraction artifacts.** A reviewer working from extracted PDF text
  reports typography that is not in the source: accent glyphs rendered
  as stray symbols, small-caps headings read as CamelCase typos,
  ligatures read as missing spaces. Verify every typo claim against the
  source file; if it is absent there, the finding is about the
  extractor.
- **The tighter-formula trap.** A reviewer proposes a sharper bound or
  a cleaner constant than the document states. Sharper may well be
  *true* — and still not what the cited declaration proves. A document
  that outclaims its library is broken in the worst way, so verify
  every strengthening against the statement, and either keep the proved
  form or mark the sharper one explicitly as unverified.
