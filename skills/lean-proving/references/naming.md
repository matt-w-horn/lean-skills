# Mathlib naming conventions

Following the convention is what makes a declaration findable — by a reader
guessing, and by `loogle`'s name filter. The rules below are Mathlib's, and
apply to any project that wants to read like Mathlib.

## Capitalization

1. `snake_case` — theorem names and proofs
2. `UpperCamelCase` — types, structures, classes, inductives
3. `lowerCamelCase` — all other terms, including functions and defs
4. A function is named after its return type where that reads naturally
5. An `UpperCamelCase` concept appearing inside a `snake_case` theorem name is
   written `lowerCamelCase`
6. Acronyms are treated as one group: `LE`, `HPow`, `HAdd`

```lean
structure OneHom (M : Type*) (N : Type*) [One M] [One N] where
  toFun : M → N                         -- structure: UpperCamelCase, field: lowerCamelCase

theorem lt_of_le_of_lt : ...            -- theorem: snake_case
def OrderHom.lfp : (α →o α) →o α := ... -- def: lowerCamelCase
```

## The symbol dictionary

A theorem name describes its statement by naming the symbols in order.

**Logic** — `∨` `or` · `∧` `and` · `→` `of` or `imp` · `↔` `iff` · `¬` `not` ·
`∃` `exists` (or `bex` for bounded) · `∀` `forall` (or `ball`) · `=` `eq` ·
`≠` `ne`

**Order and lattice** — `≤` `le` · `<` `lt` · `≥` `ge` · `>` `gt` ·
`⊔` `sup` · `⊓` `inf` · `⨆` `iSup` · `⨅` `iInf`

**Algebra** — `0` `zero` · `+` `add` · `-` `neg` (unary) or `sub` (binary) ·
`1` `one` · `*` `mul` · `^` `pow` · `/` `div` · `•` `smul` · `⁻¹` `inv` ·
`∣` `dvd` · `∑` `sum` · `∏` `prod`

**Sets** — `∈` `mem` · `∉` `notMem` · `∪` `union` · `∩` `inter` ·
`⋃` `iUnion` · `⋂` `iInter` · `⋃₀` `sUnion` · `⋂₀` `sInter` · `\` `sdiff` ·
`ᶜ` `compl`

## Structure: conclusion first, hypotheses after `_of_`

`A → B → C` is named `C_of_A_of_B`. The conclusion leads because that is what
a searcher knows they want.

```lean
theorem lt_of_le_of_lt  : a ≤ b → b < c → a < c
theorem ne_of_gt        : a > b → a ≠ b
theorem add_pos_of_pos_of_nonneg : 0 < a → 0 ≤ b → 0 < a + b
```

Names read left to right as the statement reads: `add_le_add_left` is
`add`ition, `le` conclusion, on the `left`.

## Standard suffixes and dot-notation members

| Component | Means |
|---|---|
| `.symm` | The symmetric form (`Eq.symm`, `Iff.symm`) |
| `.trans` | Transitivity |
| `.mp` / `.mpr` | Forward / reverse direction of an `↔` |
| `.le` / `.lt` | Weakening between order relations |
| `_left` / `_right` | Which operand the statement acts on |
| `_iff` | The bidirectional form of a one-directional lemma |
| `_inj` | `f x = f y ↔ x = y` |
| `_injective` / `_surjective` | The predicate form, as a suffix |
| `_monotone` / `_antitone` | Same |
| `.ext` / `.ext_iff` | Extensionality |
| `'` (prime) | A variant of a nearby lemma, usually different hypotheses |

Axiomatic-property names are used bare: `refl`, `irrefl`, `symm`, `trans`,
`antisymm`, `asymm`, `congr`, `comm`, `assoc`, `inj`, `def`.

Induction and recursion principles: `T.induction_on`, `T.recOn`, `T.induction`,
`T.rec`.

## Namespaces and dot notation

Dots separate namespaces, and also mark automatically generated names —
recursors, eliminators, structure projections.

```lean
And.intro    Eq.symm    Or.resolve_left    Nat.succ_le_of_lt
```

Putting a lemma in the namespace of its subject buys dot notation at the call
site, which is the main readability win available:

```lean
theorem IsCompact.exists_isMaxOn (hs : IsCompact s) (ne_s : s.Nonempty)
    (hf : ContinuousOn f s) : ∃ x ∈ s, IsMaxOn f s x
-- call site: hs.exists_isMaxOn ne_s hf
--    rather than: IsCompact.exists_isMaxOn hs ne_s hf
```

When a namespaced definition is mentioned inside a lemma name from outside its
namespace, drop the namespace — or use `lowerCamelCase` if dropping it would
be ambiguous.

## Checking a name before committing to it

A name that collides, or that shadows a Mathlib lemma, produces confusing
errors later. Both checks are one line:

```lean
#check @my_intended_name    -- errors if unused, which is what you want
open Mathlib in #check @add_le_add_left
```

```sh
grep -rn "theorem my_intended_name\b" .lake/packages/mathlib/Mathlib/ YourLib/
```

A project may add rules on top, such as reserved substrings a build-time audit
rejects or a freeze on renaming declarations cited elsewhere. Those are
invisible in the code and surface at build time or at review, so check the
project's `CLAUDE.md` too.
