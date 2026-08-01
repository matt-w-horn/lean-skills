---
name: lean-proving
description: Write and plan Lean 4 proofs and definitions. Use whenever a task adds or changes Lean source — proving a new theorem, stating a definition, fixing a broken proof, closing a `sorry` — and equally for the design questions that come first: "could we prove X?", "how would I show Y?", "is this feasible in Lean?", "how should I phrase this statement?", "where do the quantifiers go?", "do I actually need this hypothesis?". Use it for any question about how a statement should be written, even before a line of Lean exists. Also use when a proof is stuck, a tactic fails, an error message is opaque, or a remembered Mathlib lemma name turns out not to exist.
---

# Writing Lean

Lean gives you a kernel that cannot be fooled and an error surface that is
frequently opaque. The work divides into two halves that fail in different
ways: getting the **statement** right, which the kernel cannot help you with,
and getting the **proof** through, which it can. Most wasted effort in a Lean
session comes from proving a statement that did not say what the author meant,
or from guessing lemma names instead of looking them up.

Repo conventions override everything here, so read the project's `CLAUDE.md`
and any repo-local build or verify skill first. Every lemma name and tactic
below is true only relative to a version, so establish the pin:

```sh
cat lean-toolchain           # e.g. leanprover/lean4:v4.32.0
cat lakefile.toml            # or lakefile.lean, for the Mathlib rev
```

Design the statement before writing any tactic
(`references/statement-design.md`); a statement that is junk-true at a
degenerate corner passes the kernel and proves nothing. Search before proving,
because Mathlib has ~200k declarations and the odds of guessing a name are low
(`references/finding-lemmas.md`). Then end green: `lake build` plus whatever
the project adds on top, such as a linter, an axiom audit, or negative tests.

## Never cite a lemma or tactic you have not confirmed at this pin

Mathlib renames and deprecates continuously. At v4.32.0, `push_neg` still
elaborates but logs `"push_neg" has been deprecated. Prefer using "push Not"
instead`, and `div_add_div_same` is gone. A remembered name is a hypothesis
until confirmed, and the feedback loop for a wrong guess is a full rebuild.

Three ways to confirm, fastest first:

```sh
# 1. Grep the Mathlib source that is already on disk at your exact pin
grep -rn "theorem mul_le_mul_left" .lake/packages/mathlib/Mathlib/ | head

# 2. Ask loogle by shape rather than by name (see the `loogle` skill)
loogle '|- _ * _ ≤ _ * _'
```

```lean
-- 3. Ask Lean itself, in the file, where the context is exact
#check @mul_le_mul_left
example (a b : ℝ) (h : a ≤ b) : a + 1 ≤ b + 1 := by exact?
```

`exact?` and `apply?` search the loaded environment and print an `exact …` you
can paste; `rw?` does the same for rewrites. Slow, but authoritative.

## When a proof will not go through

After a tactic path fails twice, the problem is usually the statement or the
lemma choice rather than the tactic. Permuting `simp` sets is cheap to *try*
and expensive to *finish*, so it feels productive while consuming the session.

Print the goal with `set_option pp.all true` or `pp.explicit true` before the
failing tactic: goals that look identical often differ in an implicit argument,
a coercion, or an instance. Check the claim is true at all by instantiating at
concrete numbers with `norm_num`, or by looking for the degenerate corner; a
surprising number of stuck proofs are stuck because the claim is false as
written. Localize the difficulty with `have h : ⟨smaller claim⟩ := by sorry`
and see whether the rest closes. If the ambient theory is in Mathlib there is
usually a named road in, findable by searching on conclusion shape rather than
concept name.

## Adding a declaration

Name it by Mathlib convention (`references/naming.md`) so that readers can
guess it and search finds it. Give it a docstring that claims exactly what the
statement proves, no more: docstring honesty is the review boundary the kernel
cannot check. Prefer a corollary of existing machinery to a fresh proof, and
resist factoring out a helper used once, since every named declaration widens
the surface that later changes have to preserve.

## References

| File | Read it when |
|---|---|
| `references/tactics.md` | Choosing a tactic; needing the verified inventory at a pin |
| `references/finding-lemmas.md` | Looking for an existing lemma, definition, or idiom |
| `references/statement-design.md` | Writing a statement or definition; worried it is junk-true |
| `references/errors.md` | An error message or elaboration failure is opaque |
| `references/naming.md` | Naming a declaration Mathlib-style |

Sibling skills: **`lean-refactoring`** for golfing, simplifying, or
restructuring existing proofs while every statement stays frozen;
**`lean-verification`** for checking that a finished proof
proves what it claims; **`lean-latex-sync`** for the prose or LaTeX that has to
change alongside the Lean; **`lake`** for builds, toolchains, and dependencies;
**`loogle`** for shape-based lemma search.
