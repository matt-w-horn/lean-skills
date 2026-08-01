---
name: lean-refactoring
description: Simplify, golf, shorten, deduplicate, or restructure existing Lean 4 proofs without changing what is proved. Use for simplification and cleanup passes, "make this proof shorter", reducing line count, collapsing tactic blocks, converting tactic proofs to term proofs, and merging duplicated proof work — and for the guard question every such pass owes an answer, "did this refactor change any statement?". The contract is that statements stay frozen while proof bodies change freely. For writing a new proof, fixing a broken one, or designing a statement, use lean-proving instead.
---

# Refactoring proofs without changing what is proved

In a proof library the statements are the test assertions and the proof bodies
are the implementation. The kernel guarantees that whatever proof you write
establishes the statement above it, so a refactor preserves meaning exactly
when two things hold: the build is green, and no statement moved. The first is
free. The second is the discipline of this skill, because nothing in a green
build reports that a statement changed while you were shortening its proof.

That makes the acceptance test mechanical: green build plus an empty
statement-freeze diff means meaning preserved, with no human re-reading of the
proofs.

## Freeze before you touch

Find the project's statement freeze before editing anything. It is usually a
tracked lock file of statements (often `tests/*.lock`) with commands to check
and to regenerate it, or a statement-digest check inside a verify script
(`lean-latex-sync/references/sync-checks.md` describes that form). If the
project has neither, snapshot the statements yourself first, from the
elaborated environment, and diff against the snapshot after every slice.
`references/statement-freeze.md` has a working ~50-line lock that drops into
any project, and explains why elaborated types are the right thing to freeze:
source-level digests miss `variable` binders.

## What counts as a statement change

Several edits feel like proof cleanup and are statement changes. Each belongs
in a separate, deliberately reviewed change, never inside a golf slice:

- **Dropping a hypothesis the proof no longer uses.** The theorem got stronger.
  Often desirable, still a statement change.
- **Binder edits**: implicit versus explicit, reordering, instance-implicit
  changes, and edits to a shared `variable` line, which alter every declaration
  elaborating under it.
- **Renames and namespace moves**, including "just" qualifying a name.
- **Body edits to `def`, `abbrev`, `structure`, `class`, `instance`,
  `inductive`, `opaque`.** For these kinds the body is the statement; only
  `theorem`/`lemma` proofs are free.
- **Deleting a declaration**, helper lemmas included. The freeze reports it as
  a removal, and the project's dead-code policy governs it.
- **Changing a numeric literal** in a concrete regression theorem. The old
  number was the assertion.

An unintended non-empty freeze diff means revert the slice. An intended one
means the change is not a refactor: split it out, follow the project's
statement-change process, and regenerate the lock there.

## Slices

Work in slices small enough to revert independently: one proof, one file, one
repeated pattern. Rebuild, lint, and run the freeze check on each, and commit
per slice, because a refactor batched into one commit cannot be unwound when a
later slice turns out to have been wrong.

Watch the linter as closely as the build. Shortening a proof strands `have`s
nothing consumes and arguments nothing uses, and `unusedHavesSuffices` and
`unusedArguments` are the cheap way to notice.

## Golfing moves

Roughly in the order worth trying (`lean-proving/references/tactics.md` has the
verified tactic detail):

- **Squeeze exploratory tactics into explicit forms.** `simp?` prints the `simp
  only [...]` that reproduces a closing `simp`; `exact?`/`rw?` print the term or
  the rewrite. The explicit form names which lemmas did the work and survives
  simp-set churn.
- **Collapse `have` chains** whose intermediate names are used once, either by
  inlining or by turning the chain into a `calc`.
- **Term-mode one-liners.** A tactic block that is `intro`s plus one `exact` is
  a lambda.
- **Deduplicate repeated subproofs onto an existing named lemma** when two or
  more proofs derive the same fact inline. Prefer discharging through a lemma
  that already exists; resist minting a new single-use helper, since every named
  declaration widens the frozen surface later changes must preserve.
- **Delete dead weight**: unused `have`s, redundant `show`s, hypotheses restated
  verbatim. (An unused hypothesis in the *statement* is the trap above, not a
  golf.)

## When a shorter proof will not go through

A proof that only works after weakening the statement, adding a hypothesis, or
nudging a definition is a statement change wearing a golf's clothes. Report it
and stop; the assertion does not move to fit the implementation. A freeze diff
you cannot explain is a finding too, not noise to regenerate away.

## Related

`references/statement-freeze.md` covers setting up or evaluating a freeze, with
the working elaborated-type lock. Sibling skills: **`lean-proving`** for writing
or fixing proofs and for statement design; **`lean-verification`** for whether
the refactored library still meets its gates; **`lean-latex-sync`** when a
statement change does happen and prose must move with it; **`lake`** for wiring
the freeze into `lake test`.
