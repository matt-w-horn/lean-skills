# Does the statement mean what it claims?

This is the pass the kernel cannot do for you, and it is where the real defects
live. A proof is checked against its statement; nobody checks the statement
against the intent. Everything below survives a fully green build.

Scope the pass to what changed since the last verified state. Auditing an
unchanged library repeatedly finds nothing and costs the same as finding
something.

## Junk values from total definitions

Lean's functions are total, so operations outside their mathematical domain
return a convention value rather than failing. Every one of these has produced
a real defect.

**Division.** `x / 0 = 0`, by a deliberate totality convention the FAQ states
outright, so `a / b = c` is *provable* at `b = 0` for reasons unrelated to the
mathematics. Is there a hypothesis forcing the denominator nonzero, or does the
statement quietly include the junk case?

**Truncated `Nat` subtraction.** `a - b = 0` when `b ≥ a`. Every `Nat`
subtraction in a statement needs either a bound hypothesis or an explicit
decision that the floor is intended. `a - b + b = a` is false in general, and
reads true.

**`tsum` and infinite sums.** `∑' i, f i` evaluates to `0` when `f` is not
`Summable`. An identity about a `tsum` with no `Summable` hypothesis may be an
identity about zero. Check whether any consumer reads it as a real sum.

**`sInf` / `sSup`.** Junk at the empty set and when unbounded, `0` on `ℝ`.
Nonemptiness and boundedness are content, not bookkeeping. This includes
fixed-point machinery built over infima.

**`Nat.findGreatest` and search functions.** Return `0` when nothing satisfies
the predicate, indistinguishable from "0 satisfies it". Ask whether any
consumer distinguishes those cases, because the statement does not.

**`rpow`, `log`, and friends.** `Real.log x` for `x ≤ 0`, and `rpow` at
negative bases, follow junk conventions. Positivity hypotheses are load-bearing.

Beyond the named cases, instantiate at the corners: rates and capacities at 0,
counts at 0 and 1, probabilities at exactly 0 and exactly 1, singleton and
empty collections. At each, does the statement still say something, and does
the docstring disclose the behavior?

Two smaller shapes worth the same attention. A hypothesis the proof never uses
narrows the theorem for nothing and misleads about what is required, which is
what `unusedArguments` catches. And an orientation flip between `≤` and `<`, or
`≥` and `>`, reads as a typo and changes the theorem, so check both against
what the docstring's gloss says.

## Vacuity

A hypothesis bundle nothing satisfies proves everything, and nothing mechanical
detects it. The check is a witness: concrete values satisfying every hypothesis
simultaneously, ideally as a Lean `example` so the kernel carries it.

```lean
example : ∃ p : ℝ, 0 < p ∧ p < 1 ∧ SomeCondition p :=
  ⟨1/2, by norm_num, by norm_num, by ...⟩
```

Hypothesis bundles accumulated over several edits are the ones to check first,
because each addition was locally reasonable and nobody re-checked the
conjunction.

When a witness already exists, verify it is coherent in the units the field
docstrings state. A witness that satisfies the types but not the intended
semantics passes the kernel and misleads every reader.

## Does the statement say anything?

Three shapes that look like theorems and are not:

**Reduces to a closed numeral.** After unfolding the definitions the statement
evaluates to something like `10 ≤ 10`. It is true, it is checked, and it
generalizes nothing. `norm_num` or `decide` closing a goal where generality was
meant is the usual symptom. Fix: restate over a free variable, or disclose that
it is an instance.

**Conclusion is a hypothesis.** Sometimes after several layers of definitional
unfolding, which is what makes it hard to see. `synTaut` catches only the
syntactic case.

**Definitionally immediate.** The proof is `rfl`, and the "theorem" restates a
definition. Legitimate as a named bridge lemma; misleading when presented as a
result.

The test that finds all three: state the theorem's content in one sentence
without naming its hypotheses. If you cannot, look harder at what it proves.

## Prose versus statement

Every English surface describing a declaration is a claim: the docstring, the
README row, any document citing it. The **`lean-latex-sync`** skill owns this
pass and carries the full drift catalogue. The short form is to check each
claim on five axes: quantifier, hypothesis, direction, strength, existence.

## Does the proof prove the theorem, or an easier one?

Read the statement as written, not as intended. Common substitutions:

- A quantifier that was meant to be universal is bound at a fixed value.
- An `↔` was weakened to `→` at some point and the name kept its `_iff`.
- A hypothesis was added to get the proof through, narrowing the theorem
  without anyone deciding to.
- The result is stated for a special case (a concrete instance, a fixed
  dimension) while the surrounding prose describes the general one.

The last one is the most common in practice, because it happens gradually: each
narrowing was a reasonable step to get something green, and no single step
looked like a retreat.

## Recording findings

A statement defect is queued for deliberate review, not fixed in passing.
Changing a statement changes what everything downstream means, and in a project
with a freeze process the queue entry *is* the deliverable.

```
MyLib/Rates.lean:88  ratio_eq
  STATEMENT  theorem ratio_eq (h : 0 ≤ d) : n / d = r
  DEFECT     junk-true at d = 0 (Lean's `x / 0 = 0`); `0 ≤ d` admits that case
  CLAIMED    docstring: "holds for any divisor"
  IMPACT     three consumers read this as a real ratio; two worked examples cite it
  PROPOSED   strengthen to `0 < d`  — statement change, needs sign-off
```

Check findings against the project's own decision record before proposing
fixes. Some of what looks like a defect is a decision already taken
deliberately, and a review that reads only the code cannot see that.
