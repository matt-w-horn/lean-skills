# Designing statements

The kernel checks that your proof proves your statement. Nothing checks that
your statement means what you intended. Every serious error in a formalization
lives in that gap, and it survives a green build indefinitely. A proof of the
wrong statement is worse than no proof, because it looks like progress.

## Junk values: the dominant failure mode

Lean's functions are total. Operations with no sensible answer return a
designated value instead of failing, and a theorem quantified over that case
becomes true for a reason having nothing to do with mathematics. Lean's FAQ
states the design directly: division is extended to a total function returning
`0` for a zero denominator, because totality is "most convenient" and is
standard practice in theorem provers.

Junk conventions worth memorizing, because they generate silent vacuity:

| Expression | Junk value | Trap |
|---|---|---|
| `x / 0` | `0` | `a / b = c` is provable at `b = 0` for the wrong reason |
| `Nat` subtraction `a - b` when `b > a` | `0` | `a - b + b = a` is false; every `Nat` subtraction needs a bound |
| `Real.log x` for `x ≤ 0` | `0` | Positivity hypotheses are load-bearing, not decoration |
| `x ^ (r : ℝ)` for `x < 0` | convention-dependent | Check `Real.rpow` at your pin before relying on a sign |
| `sInf ∅` / `sSup ∅` | `0` on `ℝ` | Nonemptiness and boundedness must be hypotheses |
| `Nat.findGreatest P n` when nothing satisfies `P` | `0` | A consumer reading "0 means none fit" versus "0 fits" differ |
| `∑' i, f i` when not `Summable` | `0` | A `tsum` identity with no `Summable` hypothesis may say nothing |
| `Classical.choice` on an empty type | unreachable | Fine, but marks the definition `noncomputable` |

The test to run on every new statement: **instantiate it at each degenerate
corner and ask whether it is still saying something.** `n = 0`, the empty set,
a singleton, an empty index, probability exactly 0 or 1. If the
statement goes vacuously or junk-true at a corner and the docstring does not
disclose that, either add the hypothesis or say so in the docstring.

## Vacuity

A hypothesis set that nothing satisfies makes every conclusion provable. This
is easy to produce by accident when hypotheses are added defensively one at a
time: say, `0 < p`, `p < 1`, and separately `2 ≤ p`.

The durable fix is a **witness**, a concrete instance satisfying the whole
hypothesis bundle, proved as an `example` or a named lemma. That converts
"probably not vacuous" into something the kernel carries.

```lean
/-- Non-vacuity witness for the hypothesis bundle of `main_theorem`. -/
example : ∃ p : ℝ, 0 < p ∧ p < 1 ∧ SomeCondition p :=
  ⟨1/2, by norm_num, by norm_num, by ...⟩
```

## Shape conventions that prevent misreading

**Existentials conjoin, not imply.** `∃ x, P x ∧ Q x` says something; `∃ x, P x → Q x`
is satisfied by any `x` failing `P`, which is almost never the intent and reads
almost identically.

**Definitions total, partiality in hypotheses.** Rather than a definition
guarded by a proof obligation, define it everywhere and let theorems carry the
side conditions. This keeps the definition usable in `simp` and keeps
statements readable.

**Design division out of definitions.** Where a quantity is naturally a
quotient, defining it by the equivalent product or sum and proving the
quotient form as a lemma removes a whole class of junk-value questions from
every downstream statement.

**Drop hypotheses the proof does not use.** An unused hypothesis narrows the
theorem for no gain and misleads readers about what is required. If Lean's
linter reports one as unused, remove it rather than silencing the warning,
unless the hypothesis is there deliberately for statement uniformity, in which
case say so in the docstring.

**Direction is content.** `A → B` and `B → A` are different theorems, and an
`↔` claim needs both. When prose says "characterizes", "exactly when", or "iff",
the statement owes an `↔` or a pair of named lemmas.

## Docstrings that do not overclaim

The docstring is the only place a reader learns what the theorem means, and
nothing mechanical checks it against the statement. Recurring overclaim
signatures, each with a specific fix:

| Signature | Fix |
|---|---|
| A universal the statement does not quantify — "every", "always", "however fast" | Quantify it, or scope the prose to what is bound |
| An equivalence claim with no linking lemma | Prove the bridge, or downgrade the prose to the direction proved |
| A named theorem whose statement reduces to a closed numeral | Restate over a free variable, or disclose the immediacy |
| A theorem whose conclusion is its own hypothesis | Same — state the general form or say it is definitional |
| Prose that hides junk-value or degenerate-corner behavior | Disclose the corner in the docstring |
| A necessary condition described as sufficient (or vice versa) | Name the direction explicitly |

The check is mechanical: read the docstring, read the statement, and for each
claim in the prose point at the part of the statement carrying it. A claim you
cannot point at is the finding.

## Numeric witnesses in prose have no type checker

A number stated in a docstring, README, or paper is unchecked text. Recompute
every one, or promote it to a Lean `example` so the kernel carries it:

```lean
/-- Regression: the worked numbers in the module docstring. -/
example : (2.5 : ℝ) * 4 = 10 := by norm_num
```

Numeric `example`s double as regression tests when definitions change.
