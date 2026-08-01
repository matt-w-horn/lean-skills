# Finding what already exists

Mathlib carries on the order of 200,000 declarations. Two consequences shape
how to work: almost any general-purpose fact you need is already there, and
you will almost never guess its name. Searching is not a fallback for when
you are stuck — it is the first step of proving.

## The search ladder

Ordered by speed. Stop as soon as one answers.

### 1. Grep the source on disk

Mathlib is vendored into the project at the exact pin, so this is both the
fastest option and the only one guaranteed to match what will compile:

```sh
grep -rn "theorem add_le_add" .lake/packages/mathlib/Mathlib/ | head
grep -rn "Nat.findGreatest" .lake/packages/mathlib/Mathlib/ | head
```

Grep the *statement shape* when the name is unknown but the form is not:

```sh
grep -rnE "theorem.*: *Monotone .* → Monotone" .lake/packages/mathlib/Mathlib/Order/ | head
```

Useful directory intuition: `Mathlib/Order/` for lattices and monotonicity,
`Mathlib/Analysis/` for limits and normed spaces, `Mathlib/Topology/` for
filters and continuity, `Mathlib/Algebra/Order/` for ordered-field arithmetic,
`Mathlib/Data/` for concrete types, `Mathlib/Probability/` for measure and PMF.

### 2. Search by shape with the `loogle` skill

When you know what the statement *looks like* but not what it is called,
loogle searches by subexpression and by conclusion rather than by name. Invoke
the **`loogle`** skill for query syntax and setup; the short version is that
`|- _ * _ ≤ _ * _` finds lemmas concluding in that shape, and comma-separated
filters combine with AND.

Reach for it before writing anything longer than three lines by hand.

### 3. Ask Lean, in the file

Authoritative, because it searches the environment you actually have with your
hypotheses in scope. Slow enough to suit a stuck moment, not a loop.

```lean
example (a b : ℝ) (h : a ≤ b) : a + 1 ≤ b + 1 := by exact?
-- Try this: exact add_le_add_right h 1

example (s : Set ℕ) (h : s.Finite) : s.Nonempty ∨ s = ∅ := by apply?
example (n : ℕ) : n + 0 = n := by rw?
example (x : ℝ) (hx : 0 < x) : 0 < x ^ 2 := by hint
```

`exact?` looks for a single lemma closing the goal. `apply?` allows leftover
subgoals. `rw?` lists rewrites that apply. `hint` runs a panel of tactics and
reports which make progress — a good "I have no idea where to start" move.

Add `says` or read the suggestion and paste it; leaving `exact?` in committed
source makes every future build pay for the search.

### 4. Natural-language search

When you know the mathematical concept but not its Mathlib vocabulary — the
gap is "what do they call this?" rather than "what is the name?".

- **LeanSearch** — <https://leansearch.net/> — natural-language queries over
  Mathlib statements
- **LeanExplore** — <https://www.leanexplore.com/> — natural-language search
  over Lean declarations
- **Loogle web** — <https://loogle.lean-lang.org/> — the hosted form of the
  same shape search
- **Mathlib API docs** — <https://leanprover-community.github.io/mathlib4_docs/>
  — browsable, with the module hierarchy visible

These reach the network and search *some* Mathlib revision, not necessarily
yours. Treat a hit as a name to confirm against your pin with `#check`.

## Has anyone formalized this theorem at all?

A different question from "is there a lemma": whether a named classical result
exists in Lean anywhere. The 100-theorems tracking pages, the search order,
and the reporting format live in the `lean-verification` skill:
`lean-verification/references/prior-art.md` owns that check, counts included.
From the proving side its answer settles a narrower question: whether the
ambient theory you need is already built out.

## When nothing exists

Genuinely novel results are the normal case in a research formalization. You
have searched enough once you can state precisely what you looked for and why
the near-misses do not apply.

Before writing from scratch, check whether your statement is a corollary of
something that does exist. Specializing a general Mathlib theorem is shorter
to write, shorter to maintain, and makes the dependency legible to a reader.
