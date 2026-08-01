# Has this been formalized already?

Two different questions get asked in these words. "Is there a lemma for this?",
meaning a general-purpose fact you need as a step, is a proving activity: see
the **`lean-proving`** skill's
`lean-proving/references/finding-lemmas.md`, with the **`loogle`** skill as the
tool. This page is the other one, whether a named result exists in Lean
anywhere, which bears on novelty claims and on whether to build or reuse.

## Named classical theorems

**Freek Wiedijk's 100 theorems** is the standard benchmark for comparing proof
assistants, and the Lean community tracks its status:

- <https://leanprover-community.github.io/100.html> — formalized, with author
  and the mathlib declaration name for each. At last check, **84 of 100** were
  formalized in Lean, with 0 statement-only entries.
- <https://leanprover-community.github.io/100-missing.html> — the remaining
  **16**.

Entries give the declaration name directly, so the page doubles as a lookup:

| # | Theorem | Declaration |
|---|---|---|
| 1 | Irrationality of √2 | `irrational_sqrt_two` |
| 2 | Fundamental Theorem of Algebra | `Complex.exists_root` |
| 4 | Pythagorean Theorem | `EuclideanGeometry.dist_sq_eq_dist_sq_add_dist_sq_iff_angle_eq_pi_div_two` |
| 11 | Infinitude of Primes | `Nat.exists_infinite_primes` |
| 49 | Cayley–Hamilton | `Matrix.aeval_self_charpoly` |

Not yet formalized as of the last crawl, with their numbers on Wiedijk's list:
#8 trisecting the angle and doubling the cube, #12 independence of the parallel
postulate, #13 the polyhedron formula, #21 Green's theorem, #28 Pascal's
hexagon theorem, #29 Feuerbach's theorem, #32 the four colour problem, #33
Fermat's Last Theorem, #41 Puiseux's theorem, #43 the isoperimetric theorem,
#50 the number of Platonic solids, #53 transcendence of π, #56
Hermite–Lindemann, #84 Morley's theorem, #87 Desargues's theorem, #92 Pick's
theorem.

Both counts move as the community formalizes more, so check the page rather
than quoting these numbers back.

## Searching Mathlib itself

For results that are not on anybody's list, which is the usual case:

```sh
# grep the vendored source at your exact pin
grep -rn "Pick\|latticePoint\|Polygon.*area" .lake/packages/mathlib/Mathlib/ | head
```

Search by *statement shape* when the name is unguessable, via the **`loogle`**
skill:

```
|- Monotone _ → Monotone _
_ * _ ≤ _ * _, "mul"
```

Natural-language search when you know the concept but not Mathlib's vocabulary
for it:

- **LeanSearch** — <https://leansearch.net/>
- **LeanExplore** — <https://www.leanexplore.com/>
- **Mathlib docs** — <https://leanprover-community.github.io/mathlib4_docs/>

These search a Mathlib revision that may not be yours, so confirm any hit
against your pin with `#check` before relying on it.

## Beyond Mathlib

A result absent from Mathlib may still be formalized somewhere:

- **The Archive of Formal Proofs** (`isa-afp.org`) — Isabelle, but a formalized
  result there tells you the mathematics has been mechanized and often how.
- **Rocq** (formerly Coq) — `coq-community`, and the standard library.
- **Lean community projects** — the Mathlib repository's `Archive/` and
  `Counterexamples/` directories, plus standalone repositories.
- **The Zulip archive** — <https://leanprover.zulipchat.com/> — the fastest way
  to learn that something was attempted and abandoned, and why.

For a formalization paper, "not in Mathlib" and "not formalized anywhere" are
different claims. Only make the second one if you looked in the second place.

## Reporting a novelty check

State what you searched and how, so a reader can judge the coverage. A bare
"not found" hides whether you searched one name or twenty, and a novelty claim
resting on an unstated search scope is the kind that gets corrected in public.

Worked on Pick's theorem, which the community list records as unformalized:

```
SEARCHED  Mathlib v4.32.0 source, grep: "Pick", "latticePoint", "Polygon.*area" → 0
SEARCHED  loogle: |- _ = _ + _ / 2  with "lattice"/"polygon" name filters       → 0
SEARCHED  100 theorems list  → #92, listed on 100-missing.html as not formalized
SEARCHED  LeanSearch: "area of lattice polygon", "Pick's theorem"  → nearest hits
          are convex-body results that do not state it
NOT       Rocq, Zulip archive
CONCLUDE  no Lean formalization found — but Pick's theorem IS formalized in
          Isabelle's AFP (entry `Picks_Theorem`, Binder & Kosaian, 2024), so
          "not formalized anywhere" would have been false. Checking one more
          source turned a wrong claim into a right one.
```

That last line is the point of the exercise. "Not in Mathlib" was true and
"nobody has done this" was not, and the two are one search apart.
