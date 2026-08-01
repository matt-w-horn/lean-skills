---
name: lean-verification
description: Check whether Lean work actually establishes what it claims. Use whenever the question is "does this really prove X?", "does this build?", "is this sorry-free?", "is my theorem vacuous or junk-true?", "does anything actually satisfy these hypotheses?", "has anyone already formalized this?", or "does this meet my acceptance criteria" — and whenever working through a list of release requirements, auditing a library before tagging it, or reviewing a proof someone else wrote. Use it even when the check looks simple enough to answer directly, because a wrong formalization produces exactly the same green `lake build` and the same plausible-looking statement as a right one. For auditing prose, docstrings, or LaTeX against the code, use lean-latex-sync instead.
---

# Verifying Lean work

A green build establishes exactly one thing: every proof in the library
typechecks against its own statement. It does not establish that the statements
say what anyone intended, that a theorem is non-vacuous, that a `sorry` is
absent, or that the result matches its description. Those fail independently,
and each needs its own check.

The stance that finds defects is "what would have to be true for this to be
wrong, and can I show it isn't?", not "does this look right?". Claims here need
the output that backs them, because the failure is silent: a wrong "verified"
reads exactly like a right one, and gets believed.

## The ladder

Each rung is cheap relative to the one above, and a failure below makes
everything above it meaningless.

| Rung | Question | Where |
|---|---|---|
| 1 | Does it build? | `references/evidence-ladder.md` |
| 2 | Is it `sorry`-free and axiom-clean? | `references/evidence-ladder.md` |
| 3 | Do the linters and the project's own gates pass? | `references/evidence-ladder.md` |
| 4 | Does each statement mean what it claims? | `references/soundness-audit.md` |
| 5 | Is it non-vacuous: does anything satisfy the hypotheses? | `references/soundness-audit.md` |
| 6 | Does the prose match? | the **`lean-latex-sync`** skill |
| 7 | Has it been formalized before? | `references/prior-art.md` |
| 8 | Does it meet the stated criteria? | `references/acceptance-criteria.md` |

A project that already has a verify script (`.claude/verify/`, a
`scripts/verify.sh`, a Makefile target, a repo-local skill) has encoded which
surfaces count, and that list is hard-won. Run it, then do the semantic rungs it
cannot.

## Rungs 1 to 3, in four commands

```sh
lake build
grep -rn "\bsorry\b\|\bstop\b\|\badmit\b" --include="*.lean" YourLib/
lake exe runLinter YourLib        # if Batteries is a dependency
```

```lean
#print axioms myTheorem
-- expect: 'myTheorem' depends on axioms: [propext, Classical.choice, Quot.sound]
```

`#print axioms` is the sharpest single check available, because it reports what
a proof *actually* depends on transitively. A `sorry` anywhere in the dependency
chain surfaces as `sorryAx`, however deep it is buried. Anything else in the
list is either a declared project axiom or a hole.

## Three ways a green build still proves nothing

Worth holding in mind before reading any "verified" claim, including your own:

- **`sorry` in an `example`.** Lean never adds an `example` to the environment,
  so an environment sweep cannot see one, and a `sorry` inside it leaves any
  declaration count unchanged. Only a source-level scan catches these. Treat
  inline `example`s as regressions, not as audited declarations.
- **Junk-true statements.** `a / b = c` is provable at `b = 0` because division
  by zero returns `0`. The theorem is true and says nothing. See
  `references/soundness-audit.md`.
- **Vacuous hypotheses.** A hypothesis bundle nothing satisfies makes every
  conclusion provable. Nothing in the build detects this; only a witness does.

## Reporting

State the rung reached, the command, and the output. A finding quotes both
sides, the claim and the source it is checked against, because a finding the
reader cannot check is one they have to take on trust.

```
CHECKED   lake build            → exit 0, 0 errors, 0 warnings
CHECKED   sorry scan            → 0 hits across 34 files
CHECKED   #print axioms main_thm → propext, Classical.choice, Quot.sound
FINDING   MyLib/Rates.lean:88 — `ratio_eq` is junk-true at `d = 0` (division
          convention); the docstring claims it holds "for any divisor"
NOT RUN   runLinter — Batteries not in this project's dependencies
```

`NOT RUN` is a real and useful line. Omitting a check silently is how a
verification report becomes misleading without containing a false sentence.

Sibling skills: **`lean-proving`** to fix what this finds, **`lean-latex-sync`**
for the prose-versus-statement rung, and **`lake`** when the build itself is
the problem.
