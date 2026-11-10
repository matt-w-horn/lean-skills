# The drift catalogue

Every entry is a way prose can diverge from the statement it describes, with
the signature that reveals it and the fix. Work through them in order when
auditing a paragraph; they are roughly ordered by how often they occur.

Contents: [Quantifier drift](#1-quantifier-drift) ·
[Missing hypothesis](#2-missing-hypothesis) ·
[Direction reversal](#3-direction-reversal) ·
[Strength inflation](#4-strength-inflation) ·
[Stale reference](#5-stale-reference) ·
[Phantom linking lemma](#6-phantom-linking-lemma) ·
[Degenerate-corner concealment](#7-degenerate-corner-concealment) ·
[Triviality concealment](#8-triviality-concealment) ·
[Numeric witness](#9-unchecked-numeric-witness) ·
[Scope creep in examples](#10-scope-creep-in-examples)

---

## 1. Quantifier drift

Prose universalizes what the statement bounds.

**Signature words**: every, all, any, always, never, however large, in general,
arbitrary.

Mathlib's own `OrderHom.lfp` shows the shape (`Mathlib/Order/FixedPoints.lean`):

<example>
**Prose** (its docstring): "Least fixed point of a monotone function"
**Context**: `variable [CompleteLattice α] (f : α →o α)`, then `def lfp : (α →o α) →o α`
**Drift**: monotonicity alone gets you nothing. The construction needs the
ambient order to be a **complete lattice** — that is where the fixed point
comes from, via Knaster–Tarski. A reader taking the docstring at face value
would expect fixed points for monotone maps on any order.
**Fix**: "Least fixed point of a monotone function on a complete lattice".
</example>

The general form: a universal in the prose ("every monotone function") whose
scope in the statement is narrowed by a typeclass binder, a `variable` line, or
a section hypothesis — all three of which sit far from the declaration and are
easy to read past.

The check: for each universal word, find the binder in the statement that
carries it. A universal with no binder is the finding.

---

## 2. Missing hypothesis

The statement's side conditions do not appear in the prose, so a reader
believes the result applies more widely than it does.

Side conditions that carry real content and get dropped most often: positivity
(`0 < x`), nonzero-ness (`x ≠ 0`), summability, measurability, nonemptiness,
finiteness, and bounds that rule out a degenerate corner.

<example>
**Prose**: "the logarithm turns products into sums"
**Statement** (`Mathlib/Analysis/SpecialFunctions/Log/Basic.lean:132`):
```lean
theorem Real.log_mul (hx : x ≠ 0) (hy : y ≠ 0) : log (x * y) = log x + log y
```
**Drift**: both nonzero-ness hypotheses are silent. `Real.log 0 = 0` by
convention, so at `x = 0` the claim reads `0 = 0 + log y`, which is false for
`y ≠ 1`. The hypotheses are the content, not bookkeeping.
**Fix**: "for nonzero arguments, the logarithm turns products into sums".
</example>

A second case where the junk convention bites in the other direction:

<example>
**Prose**: "subtracting then adding back returns the original"
**Statement** (Lean core, `Init/Data/Nat/Basic.lean:991`):
```lean
protected theorem Nat.sub_add_cancel {n m : Nat} (h : m ≤ n) : n - m + m = n
```
**Drift**: `h : m ≤ n` is essential. `Nat` subtraction truncates at zero, so
`3 - 5 + 5 = 5`, not `3`. Compare `Rat.sub_add_cancel {a b : Rat} : a - b + b = a`,
which needs no hypothesis at all — same name, different theorem, because the
type is different.
</example>

The check: list the statement's hypotheses; for each, either find it in the
prose or confirm it is genuinely immaterial to the reader's understanding.

---

## 3. Direction reversal

A one-directional theorem described as a characterization, or a necessary
condition read as sufficient.

**Signature words**: if and only if, exactly when, characterizes, precisely,
is equivalent to, diagnoses, means that.

<example>
**Prose**: "compactness is exactly closedness plus boundedness"
**Statements**:
```lean
-- holds in any Hausdorff space  (Mathlib/Topology/Separation/Hausdorff.lean:590)
theorem IsCompact.isClosed [T2Space X] {s : Set X} (hs : IsCompact s) : IsClosed s

-- the equivalence needs more   (Mathlib/Topology/MetricSpace/Bounded.lean:336)
theorem Metric.isCompact_iff_isClosed_bounded [T2Space α] [ProperSpace α] : ...
```
**Drift**: one direction is general; the equivalence holds only in a proper
space. Stated as "exactly", the prose claims Heine–Borel in settings where it
is false — an infinite-dimensional normed space has closed bounded sets that
are not compact.
**Fix**: "compact sets are closed and bounded; in a proper space the converse
holds too".
</example>

This class matters most in documents mapping theory onto real incidents, where
a one-directional theorem read as a diagnosis produces a false claim about a
real system. A row that cites a theorem must respect its direction.

---

## 4. Strength inflation

The claim is directionally right but quantitatively stronger than proved.

Signatures: a definite article where the statement gives one of several ("*the*
bound"), an equality where the statement gives an inequality, "exactly" for
"at most", a tight claim for a loose one, "optimal" for "sufficient".

<example>
**Prose**: "the threshold above which the system collapses"
**Statement**: gives a sufficient condition for collapse, with no claim that it
is the least such.
**Fix**: "a threshold above which the system collapses" — or prove tightness
and keep the definite article.
</example>

---

## 5. Stale reference

The cited name no longer exists, or exists with a different meaning.

Two failure modes, and the second is the dangerous one:

- **Deleted or renamed** — a textual check catches this.
- **Moved namespace, same last component** — `Foo.lemma_name` becomes
  `Bar.lemma_name` when a result is generalized onto a weaker structure. A
  checker matching by last name component still resolves, and reports green
  while the document cites a name that no longer exists. Mathlib does this
  routinely as results are generalized, so any project tracking Mathlib
  inherits the problem.

After any namespace change, grep the prose surfaces by hand. See
`sync-checks.md` for the normalization that makes the grep work through LaTeX
escapes.

---

## 6. Phantom linking lemma

The prose asserts an equivalence between two formal objects, and no lemma in
the library connects them.

<example>
**Prose**: "our combinatorial `weight` function is the Euler characteristic"
**Library**: `weight` is defined, and `Mathlib` has an Euler characteristic.
No lemma relates the two; the identification lives only in the author's head
and in this sentence.
**Fix**: prove the bridge (`weight_eq_eulerChar`), or downgrade the prose —
"our `weight` function, which plays the role of an Euler characteristic".
</example>

The identification is often *true*, which is what makes this class dangerous:
the author knows it, the reader believes it, and no artifact records it. When
the definitions later diverge, nothing catches it.

The check: for every "is", "equals", "amounts to", or "is the same as" joining
two named formal objects, find the lemma. If there is no lemma, there is no
claim.

---

## 7. Degenerate-corner concealment

The statement is junk-true or vacuous somewhere, and the prose does not say so.
The junk-value table lives in `lean-proving/references/statement-design.md`.

The prose fix is disclosure: "for positive rates" costs four words and prevents
a reader from applying the result at zero.

---

## 8. Triviality concealment

A named theorem whose statement reduces to a closed numeral, or whose
conclusion is one of its own hypotheses, presented as a substantive result.

<example>
**Prose**: "we establish the capacity bound for the worked configuration"
**Statement**: every parameter is a literal, so after unfolding the definitions
it evaluates to `10 ≤ 10`.
**Fix**: restate over a free variable so the theorem has content, or disclose
the immediacy — "at the worked configuration the bound holds by computation".
</example>

Concrete numeric `example`s are valuable as regression tests and should be
kept. The defect is presenting one as a general result.

The check that finds these: can you state the theorem's content without naming
its hypotheses? If not, it may be an instance rather than a theorem.

---

## 9. Unchecked numeric witness

Any number in prose is unverified text. Matrices, thresholds, worked examples,
counts, and rates all belong here.

<example>
A docstring and a paper both stated that a particular matrix contracts a
particular weight vector. The matrix was right and the derived scalar was
right; the weight vector was wrong, and multiplying it out gave a result
larger than the vector it was supposed to be below. Nothing mechanical could
catch it, and it survived several rounds of review — because every reader
checked the surrounding argument rather than doing the arithmetic.
</example>

Two fixes, in order of preference: promote the number to a Lean `example` so
the kernel carries it, or recompute it by hand and record that you did.

Counts stated in prose ("N declarations", "currently N") are the most
recurrent drift of all, because they change whenever anything is added. Script
that check — see `sync-checks.md`.

---

## 10. Scope creep in examples

A worked example or case study claims the formal machinery applies where it
was only informally suggested.

The honest form names what transfers and what does not: "the vocabulary and
the accounting identity transfer; we assert no instance of the formal
structure here, and claim none of its consequences". A case study that quietly
upgrades an analogy into an instance is the same defect as an overclaiming
docstring, at document scale — and it is harder to catch, because the reader
meets the analogy before they meet the formal claim.

---

## Reporting format

For each finding, give the four parts. Anything less is not checkable by the
person reading your report.

```
CLAIM     file.tex:LINE — "quoted prose"
STATEMENT File.lean:LINE — quoted Lean statement, hypotheses included
CLASS     one of the ten above
VERDICT   supported | overclaim | underclaim | stale | unverifiable
FIX       the specific replacement wording, or the statement change to queue
```

When the statement is what is wrong, say so and stop. Changing a statement to
match prose someone already wrote is backwards, and in a project with a review
process it is the change that most needs a human decision.
