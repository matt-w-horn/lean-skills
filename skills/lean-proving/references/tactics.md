# Tactics

The inventories below were extracted from Lean core and Mathlib source at
**`leanprover/lean4:v4.32.0`**. Tactic sets change between revisions, so treat
this as a starting point and regenerate for the pin you are on.

## Regenerating this list for your pin

Lean and Mathlib source ships with the toolchain and with `lake`, so the
authoritative answer is already on disk — no network needed:

```sh
# Lean core tactics
grep -oE '^\s*(syntax|macro|elab)\s*(\(name := [^)]*\)\s*)?"[a-zA-Z_][a-zA-Z0-9_?!'"'"']*' \
  ~/.elan/toolchains/*/src/lean/Init/Tactics.lean | grep -oE '"[a-zA-Z_][^"]*' | tr -d '"' | sort -u

# Mathlib tactics
grep -rhoE '^\s*(syntax|macro|elab)\s*(\(name := [^)]*\)\s*)?"[a-zA-Z_][a-zA-Z0-9_?!'"'"']*' \
  .lake/packages/mathlib/Mathlib/Tactic/ | grep -oE '"[a-zA-Z_][^"]*' | tr -d '"' | sort -u
```

To read what one does, grep its docstring:

```sh
grep -B 30 'elab (name := pushStx)' .lake/packages/mathlib/Mathlib/Tactic/Push.lean
```

A sharper signal is what the project already uses: a tactic with 300 hits in
the local library is known to work at this pin, and matching it keeps proofs
stylistically consistent.

```sh
grep -rhoE '\b(norm_num|linarith|nlinarith|positivity|bound|gcongr|ring|field_simp|omega|aesop)\b' \
  YourLib/*.lean | sort | uniq -c | sort -rn
```

## Reading the goal

Most failures are misread goals rather than missing lemmas. Two terms that
print identically can differ in an implicit argument, a coercion, or which
instance was selected.

```lean
set_option pp.all true          -- everything: implicits, universes, instances
set_option pp.explicit true     -- implicit arguments only
set_option pp.numericTypes true -- which type each numeral lives in
set_option pp.coercions true    -- make ↑ coercions visible
set_option pp.notation false    -- raw function applications instead of operators
```

Scope them to one declaration by putting `set_option … in` on the line above
it, so the rest of the file keeps readable output.

Inspect without proving:

```lean
#check @Nat.succ_le_of_lt   -- the @ shows every implicit argument
#print Nat.add              -- the definition
#print axioms myTheorem     -- what the proof actually depends on
example : 2 + 2 = 4 := by trace_state; norm_num
```

## Core tactics (Lean core)

Verified present at v4.32.0. Grouped by what you reach for them to do.

**Closing a goal**
`exact` · `exact?` (searches, prints a usable `exact …`) · `assumption` ·
`rfl` · `apply_rfl` · `trivial` · `decide` (decidable props, by evaluation) ·
`native_decide` (same, compiled — adds a compiler-trust axiom, so many
projects forbid it) · `omega` (linear integer/nat arithmetic) · `simp` ·
`simp_all` · `simpa` (simp then close with a term) · `contradiction` ·
`exfalso` · `nofun` · `sorry` / `admit` (leaves a hole; the build stays green
but the theorem proves nothing — see `lean-verification`)

**Moving between goal and context**
`intro` · `intros` · `revert` · `rename_i` · `clear` · `specialize` ·
`generalize` · `subst` · `subst_vars` · `replace` · `have` · `let` ·
`show` · `suffices` · `change` · `refine` (leaves `?holes`) · `refine'`

**Structure**
`constructor` · `left` · `right` · `exists` · `cases` · `rcases` ·
`induction` · `injection` · `split` (splits `if`/`match`) · `case` · `focus` ·
`next` · `·` bullets

**Rewriting**
`rw` · `rewrite` · `rwa` (rewrite then `assumption`) · `rw?` (searches for a
rewrite) · `simp only` · `dsimp` (definitional only) · `unfold` · `delta` ·
`norm_cast` · `push_cast` · `symm`

**Meta**
`try` · `repeat` · `first` · `all_goals` · `any_goals` · `skip` · `done` ·
`stop` · `sleep` · `trace_state` · `trace` · `show_term` (prints the proof
term a tactic block produced) · `classical` (adds classical instances) ·
`extract_lets` · `with_reducible`

## Mathlib automation

The tactics worth knowing before writing anything by hand. All verified
present at Mathlib v4.32.0.

| Tactic | Solves |
|---|---|
| `linarith` | Linear arithmetic over ordered fields, from hypotheses. Linear means no variable-by-variable products. |
| `nlinarith` | `linarith` plus heuristic products of hypotheses; try when `linarith` just fails |
| `polyrith` | Polynomial identities via Gröbner bases (needs network) |
| `positivity` | Goals of the form `0 < e`, `0 ≤ e`, `e ≠ 0`, structurally |
| `bound` | Bounds on compound expressions by structural recursion |
| `gcongr` | Congruence for inequalities: reduce `f a ≤ f b` to `a ≤ b` |
| `ring` / `ring_nf` | Commutative (semi)ring identities |
| `field_simp` | Clears denominators, given nonzero side conditions |
| `norm_num` | Numeric goals on concrete literals; extensible |
| `omega` | Linear `Nat`/`Int` arithmetic including divisibility and mod |
| `decide` | Any decidable proposition, by evaluating the decision procedure |
| `aesop` | General-purpose search over a rule set; good at logical plumbing |
| `tauto` | Propositional tautologies |
| `push_cast` / `norm_cast` / `zify` / `qify` / `rify` | Move coercions around, or change the ambient numeric type |
| `push` | Push a head symbol inward — `push Not` is the modern `push_neg` |
| `contrapose` / `contrapose!` | Swap to the contrapositive |
| `by_contra` | Classical proof by contradiction |
| `wlog` | Without loss of generality, with the reduction as a side goal |
| `interval_cases` | Case-split a variable with finite known bounds |
| `fin_cases` | Case-split over a `Fin n` or finite type |
| `choose` | Turn `∀ x, ∃ y, P x y` into a function plus its property |
| `set` | Name a subterm and abstract it everywhere |
| `convert` | Close a goal up to subgoals for the mismatching parts |
| `congr` | Reduce `f a = f b` to argument equalities |
| `ext` / `funext` | Prove equality of functions or sets pointwise |
| `filter_upwards` | Eventually-true goals in filter arguments |
| `measurability` / `continuity` / `fun_prop` | Discharge side conditions of that kind |
| `monotonicity` / `mono` | Monotonicity side goals |
| `linear_combination` | Prove an equality as a stated linear combination of hypotheses |
| `hint` | Runs a panel of tactics and reports which ones make progress |

`hint`, `exact?`, `apply?`, and `rw?` are the search tactics: slow, so they suit
a stuck moment rather than a loop, but authoritative, because they search the
environment you actually have.

## Combinators

```lean
tac1 <;> tac2          -- run tac2 on every goal tac1 produced
first | tac1 | tac2    -- try in order, take the first that succeeds
try tac                -- run tac, succeed regardless
repeat tac             -- run until it fails
all_goals tac          -- tac on each goal; every one must succeed
any_goals tac          -- tac on each goal; at least one must succeed
solve | tac1 | tac2    -- like first, but each branch must fully close the goal
done                   -- fail unless zero goals remain
```

`<;>` is the workhorse: `constructor <;> norm_num` handles a conjunction whose
halves are both numeric. `solve` is worth preferring over `first` when you
mean "one of these finishes it", because `first` will happily take a branch
that succeeds partially and leave you with worse goals.

## `conv`: surgical rewriting

Use `conv` when `rw` rewrites the wrong occurrence, or when you need to get
inside a binder where `rw` cannot reach.

```lean
example (a b c : Nat) : a * b * c = a * (b * c) := by
  conv => lhs; rw [Nat.mul_assoc]

example (f : Nat → Nat) (h : ∀ x, f x = x) : (fun y => f y) = fun y => y := by
  conv => lhs; ext y; rw [h]
```

Navigation inside `conv`: `lhs` · `rhs` · `arg i` (the i-th explicit argument)
· `congr` · `intro x` / `ext x` (enter a binder) · `enter [1, x, 2]` (a path
combining `arg` and `intro`) · `conv in pat => …` (jump to the first subterm
matching a pattern, `_` wildcards allowed).

Acting inside: `rw` · `simp` · `change` · `rfl` · `whnf` · `tactic => …` to
drop back to ordinary tactic mode. `conv at h => …` targets a hypothesis.

## `calc`: chained reasoning

`calc` chains transitive steps and is the most readable way to present a
computation. Operators need not match, but must be compatible — `=`, `<`, `≤`
compose; `<` and `>` do not.

```lean
theorem two_mul_example (m n : ℕ) : 2 * m + n = m + n + m :=
  calc 2 * m + n = m + m + n := by rw [Nat.two_mul]
    _            = m + n + m := by ac_rfl
```

The `_` is part of the syntax and stands for the previous line's right-hand
side. The same proof written with `have`s has to name every intermediate and
invoke `Eq.trans` by hand, so `calc` wins for anything longer than two steps.

## `simp` versus `rw`

Both replace equals with equals, left to right. They differ in scope and in
how they fail, and choosing wrong is a common source of stuck proofs.

- `rw [h]` finds the **first** subterm matching `h`'s left-hand side, then
  rewrites **all** occurrences of that particular subterm. It then tries `rfl`.
  It fails loudly if nothing matches — which is useful, because the failure
  tells you your mental model of the goal is wrong.
- `simp` rewrites **exhaustively** with the whole `@[simp]` set until nothing
  applies. It is far more powerful and far less predictable; a proof that
  depends on bare `simp` can break when Mathlib adds a simp lemma.

```lean
rw [h]                -- once, first match
rw [← h]              -- right-to-left
rw [h₁, h₂]           -- in sequence
rw [h] at h'          -- rewrite a hypothesis
rw [h] at *           -- everywhere
rw [show a = b from p]-- rewrite by an inline proof

simp                  -- exhaustive, default simp set
simp [h]              -- default set plus h
simp only [h₁, h₂]    -- exactly these, nothing else
simp [-bad_lemma]     -- default set minus one
simp [*] at *         -- use every hypothesis, rewrite everything
simp_all              -- simp hypotheses and goal against each other, to fixpoint
dsimp                 -- definitional unfolding only, no propositional rewriting
```

For proofs meant to last, prefer `simp only [explicit, list]` over bare `simp`:
it states what the step depends on, survives simp-set churn, and reads as an
argument rather than as a search. Bare `simp` is excellent while exploring.

When `simp` closes a goal, `simp?` prints the `simp only [...]` that reproduces
it; `exact?` and `rw?` behave similarly. Converting an exploratory `simp` into
the `simp only` it printed is usually the last step before committing a proof.

## Induction pitfalls

`induction h` fails with `Invalid target: Index in target's type is not a
variable` when the inductive predicate's argument is a compound term rather
than a variable. A self-contained toy (Mathlib's `Even` is an existential
`def`, not an inductive, so it cannot show this):

```lean
inductive Ev : Nat → Prop
  | zero : Ev 0
  | add_two : ∀ n, Ev n → Ev (n + 2)

-- hev : Ev (2 * n + 1) ⊢ False     -- induction hev fails here
```

The fix has two parts. Generalize the compound term to a variable carrying an
equation, and then `generalizing` any variable the induction hypothesis needs
to be instantiated at a *different* value:

```lean
theorem not_ev_two_mul_add_one (m n : ℕ) (hm : m = 2 * n + 1) : ¬ Ev m := by
  intro h
  induction h generalizing n with
  | zero => omega
  | add_two k hk ih => ...
```

Without `generalizing n`, the induction hypothesis fixes `n`, and the step
case needs it at `n - 1` — so the goal is unprovable even though the theorem
is true. Whenever an induction hypothesis looks too weak, `generalizing` is
the first thing to try.

`cases h` performs the same case analysis without producing induction
hypotheses; reach for it when you need the case split but not recursion.

## Deprecations move under you

Mathlib deprecates continuously, and the warning appears only when you
compile. Two confirmed at v4.32.0:

- `push_neg` elaborates but logs *"`push_neg` has been deprecated. Prefer
  using `push Not` instead."*
- `div_add_div_same` is gone; `ring` covers the cases that used it.

When a remembered name fails, check whether it was renamed rather than
removed. Mathlib leaves deprecation aliases with the replacement in the
message, so the compiler error usually names its own fix:

```sh
grep -rn "deprecated.*old_name" .lake/packages/mathlib/Mathlib/ | head
```
