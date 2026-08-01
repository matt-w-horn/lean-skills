# Decoding Lean errors

Lean's errors are precise but rarely phrased as advice. The wording below was
read from Lean core source at **v4.32.0**; messages get rephrased between
releases, so match on the shape rather than character-for-character.

A worked example of that drift: the 2025 edition of *The Hitchhiker's Guide to
Logical Verification* quotes the failing-induction error as `index in target's
type is not a variable`. At v4.32.0 the same condition reads `major premise
type index … is not a variable`. Same cause, different words — which is why
grepping your own toolchain beats recalling a message.

```sh
# Find the source of any error you are looking at
grep -rn "the distinctive part of the message" ~/.elan/toolchains/*/src/lean/
```

---

## Rewriting

### `Did not find an occurrence of the pattern … in the target expression`

`rw [h]` could not match `h`'s left-hand side anywhere. Nearly always the goal
differs from your mental model in a way the pretty-printer hides, so
`set_option pp.all true in` before the declaration and re-read it. Common
culprits: an invisible coercion (`↑n` versus `n`), a different but defeq form,
or a numeral at a different type.

`rw` also matches up to *reducible* unfolding only, so two sides equal only by
`def`-unfolding need `simp only [myDef]` or a `show` of the reduced form first.
Under a binder `rw` cannot reach the subterm at all; use `conv` or `simp only`.

### `motive is not type correct`

Emitted by `rw` when the term being rewritten appears in the *type* of
something else in the goal, so abstracting it would break type-checking. This
is the characteristic dependent-type failure.

- `subst h` instead, when `h : a = b` and one side is a local variable.
- `simp only [h]` sometimes succeeds where `rw` cannot, because it rewrites
  differently.
- `congr` or `convert` to reduce to the equalities you actually need.
- Restructure so the dependency is not there: generalize the dependent term
  before rewriting.

### `Invalid rewrite argument: The pattern to be substituted is a metavariable`

The lemma's left-hand side is a bare variable, so it would match everything.
Instantiate the lemma's arguments explicitly: `rw [h (x := 3)]` or
`rw [show a = b from h]`.

---

## Elaboration and types

### `type mismatch`

Read the two types printed, with `set_option pp.all true` if they look
identical — they are not, or you would not be reading this. Frequent causes:

- **Coercion placement.** `(↑(a + b) : ℝ)` versus `↑a + ↑b` are propositionally
  but not definitionally equal. `push_cast` and `norm_cast` move coercions to a
  normal form; `exact_mod_cast h` closes a goal that differs from `h` only in
  casts.
- **Numeral type.** `2` elaborates at whatever type is expected; if that is
  `ℕ`, subtraction truncates. Annotate: `(2 : ℝ)`.
- **Implicit argument inferred differently** than intended. Supply it by name:
  `f (α := ℝ) x`.

### `failed to synthesize` / `failed to synthesize instance`

Type class resolution found no instance. Ask what is actually missing before
adding hypotheses:

```lean
set_option trace.Meta.synthInstance true in
example : ... := by ...
#synth AddCommGroup MyType
```

Usual causes: a missing `[Instance α]` binder on the declaration; a structure
that should have been an instance but was declared as a `def`; an instance
that exists for a defeq-but-not-syntactically-equal type; or a missing import.

### `don't know how to synthesize placeholder`

An `_` that Lean cannot determine from context. Give it explicitly, or
reorder so unification sees the constraint first. In `refine`, name the hole
(`?h`) so it becomes a goal instead of an error.

### `unknown identifier` / `unknown constant`

The name does not exist in the environment as spelled. In order: check the
import, check the namespace (`open Foo` or fully qualify), check for a rename
in your Mathlib pin.

```sh
grep -rn "theorem the_name\b\|lemma the_name\b\|def the_name\b" .lake/packages/mathlib/Mathlib/
grep -rn "deprecated.*the_name" .lake/packages/mathlib/Mathlib/
```

Mathlib usually leaves a deprecation alias naming its replacement, so the
compiler warning contains its own fix.

### `function expected`

Too many arguments, or an implicit-argument mismatch making Lean read a term
as saturated. `#check` the head symbol and count.

---

## Tactic-level

### `unsolved goals`

The tactic block ended with goals open. The message prints them. When it
appears after a `simp` you expected to close everything, the remaining goal is
usually a side condition (`x ≠ 0`, `0 < n`, a `Summable`), which is a hint that
the statement needs that as a hypothesis.

### `major premise type index … is not a variable`

`induction h` where the inductive predicate's argument is a compound term
rather than a variable. Generalize the term to a variable carrying an equation,
and add `generalizing` for any variable the induction hypothesis must be
instantiated at a different value. Worked example in `tactics.md`.

The message suggests `cases` as an alternative; that works when you need the
case split without induction hypotheses.

### `simp made no progress`

`simp` found nothing to rewrite. Either the goal is already in normal form, or
the lemma you expected to fire is not a simp lemma and needs passing
explicitly: `simp [my_lemma]`.

### `maximum recursion depth has been reached`

Usually a looping `simp` set — two lemmas rewriting each other — or an
unfolding definition with no base case. Narrow to `simp only [specific, list]`
to find the pair. Raising `set_option maxRecDepth 4000` is a diagnostic, not a
fix: it confirms depth rather than looping.

### `(deterministic) timeout at whnf`

Elaboration hit `maxHeartbeats` (200000 by default). Something is being
evaluated that should not be — often `decide` on a large computation, a
`norm_num` on a huge numeral, or unfolding a definition that should stay
opaque.

```lean
set_option maxHeartbeats 400000 in   -- confirms it is size, not a loop
```

The real fixes are to prove the fact rather than decide it, to state the
reduced form with `show` first, or to mark heavy definitions `irreducible`.

---

## Definitions

### `failed to prove termination` / structural recursion errors

Lean cannot see that a recursive definition terminates.

- Add `termination_by` naming the decreasing measure, and `decreasing_by` with
  the proof.
- Restructure to structural recursion on an inductive argument, which needs no
  proof.
- For a genuinely partial function, `partial def` — but that produces an opaque
  constant you cannot reason about, so it suits tooling rather than
  mathematics.

### `noncomputable` required

The definition depends on `Classical.choice`, which produces data from a mere
existence proof and so has no computational content. Marking it
`noncomputable` is the normal outcome for real-analysis definitions and is not
a problem unless you needed to `#eval` it.

### `declaration uses sorry`

A warning, not an error, and the most important one in the file: the build is
green and the theorem is unproved. See the `lean-verification` skill for
finding these across a project.

---

## Diagnosing anything else

```lean
set_option trace.Meta.synthInstance true in   -- instance search
set_option trace.Meta.isDefEq true in         -- why two terms failed to unify
set_option trace.Elab.step true in            -- elaboration, verbose
set_option trace.profiler true in             -- where the time goes
```

`#print axioms myThm` after a proof lands tells you what it actually depends
on — the fastest way to notice an accidental `sorry` deep in a chain.
