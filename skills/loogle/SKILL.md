---
name: loogle
description: Search Lean 4 and Mathlib for an existing lemma or definition by name, by subexpression shape, or by what the statement concludes. Use whenever working on a Lean proof and about to prove something from scratch, guess a Mathlib lemma name from memory, or ask "is there already a lemma for this?" — loogle answers in seconds where grepping Mathlib source or guessing names takes minutes and often fails. Works against any local Lean/Lake project whose toolchain matches loogle's build, and there is a hosted instance needing no install at all.
---

# loogle: searching Lean and Mathlib

Mathlib carries on the order of 200,000 declarations with frequently
unguessable names: is it `tsum_mul_left` or `ENNReal.tsum_mul_left`? Each wrong
guess costs a rebuild.

loogle indexes a project's entire import graph, Mathlib included, and searches
by name, by the shape of a statement, or by what a lemma concludes. Shape
search answers "there must be a lemma like this" without knowing any of the
lemma's words.

## Two ways to run it

### Hosted, no install

<https://loogle.lean-lang.org/> runs the same query language against a recent
Mathlib. Use it when there is no local build, or for a second opinion on which
Mathlib revision carries a lemma. The hosted index tracks Mathlib's master
rather than your project, so confirm any hit against your own pin with
`#check`.

### Locally, against your own project

A local build searches *your* import graph at *your* pin, so anything it finds
will actually compile where you need it.

```sh
git clone https://github.com/nomeata/loogle.git ~/.local/share/loogle
cd ~/.local/share/loogle
cp /path/to/your-project/lean-toolchain .    # match the project you will search
lake build
```

Run it from **inside** the Lean project you want to search:

```sh
cd /path/to/your-project
lake env ~/.local/share/loogle/.lake/build/bin/loogle '<query>'
```

`lake env` reads the *current directory's* lakefile to compute `LEAN_PATH`,
which is how loogle finds built `.olean` files. Run it outside a Lean project,
or inside one Lake has not built, and it fails with a toolchain or "no such
file" error rather than returning nothing: that error is about where you are,
not about the query.

A wrapper on `PATH` saves the typing:

```sh
cat > ~/.local/bin/loogle <<'EOF'
#!/bin/sh
exec lake env "$HOME/.local/share/loogle/.lake/build/bin/loogle" "$@"
EOF
chmod +x ~/.local/bin/loogle
```

**The first query against a project takes several minutes.** That is index
construction, not a hang: loogle writes a search index next to Mathlib's
`.olean`s (`Mathlib.loogle-index`) the first time it searches a module, and
every later query reuses it and returns in seconds. The message `no index file
at …; rebuilding` is that one-time cost announcing itself.

## Query syntax

One query string, up to five filter forms, comma-separated. Comma means AND.
Metavariables written `?a` are independent per filter.

| Form | Example | Finds |
|---|---|---|
| By constant | `Real.sin` | lemmas whose statement mentions `Real.sin` |
| By name substring | `"differ"` | lemmas with `differ` in their **name** |
| By subexpression | `_ * (_ ^ _)` | statements containing that shape anywhere |
| Non-linear subexpression | `Real.sqrt ?a * Real.sqrt ?a` | the same metavariable in both positions |
| By conclusion | `\|- tsum _ = _ * tsum _` | the **conclusion** (right of all `→`/`∀`) has this shape |
| Conclusion plus hypothesis | `\|- _ < _ → tsum _ < tsum _` | that conclusion, with such a hypothesis anywhere |
| Data versus proofs | `⊢ (_ : Type _)` / `⊢ (_ : Prop)` | data-producing defs versus theorems |

Combined, these narrow fast:

```sh
loogle 'Real.sin, "two", _ * _, |- _ < _ → _'
```

finds lemmas mentioning `Real.sin`, with `two` in the name, containing a
product, and carrying a `_ < _` hypothesis, all at once.

Queries containing `(`, `)`, or `|-` need shell quoting:

```sh
loogle '(List.replicate (_ + _) _ = _)'
loogle '|- Monotone _ → Monotone _'
```

## Useful flags

- `--module Mathlib` (the default) searches all of Mathlib; `--module YourLib`
  restricts to your project's own root library and its imports.
- `--json` / `-j` for machine-readable output (`hits[].name`, `.module`,
  `.type`).
- `--max-results n` (default 200).
- `--interactive` / `-i` reads one query per line from stdin, avoiding the
  `lake env` startup cost on each of several searches.
- `--index-mode write` forces a fresh index.
- `--help` lists everything.

## Writing a query that finds things

Describe the shape you want to end up with, not the concept's name.

| You want | Query |
|---|---|
| Something concluding `a * b ≤ c * d` | `\|- _ * _ ≤ _ * _` |
| A lemma turning `log (x*y)` into a sum | `Real.log (_ * _)` |
| Anything about `√a * √a` | `Real.sqrt ?a * Real.sqrt ?a` |
| A monotonicity transfer lemma | `\|- Monotone _ → Monotone _` |
| Cancellation for truncated subtraction | `\|- _ - _ + _ = _, "sub"` |

Start broad, then add filters. A query returning 200 hits is more useful than
one returning zero, because one more name filter narrows it and a zero result
tells you nothing about where you went wrong.

## Troubleshooting

- **Toolchain mismatch** (`no default toolchain configured`, or a load failure
  on a different project): loogle binaries are pinned to whatever
  `lean-toolchain` was present when they were built. A project on a different
  toolchain needs its own build:

  ```sh
  cd ~/.local/share/loogle
  cp /path/to/other-project/lean-toolchain .
  lake build
  ```

  This overwrites the current pin, and only one can be active at a time. For
  projects on different toolchains, keep a second checkout rather than
  rebuilding back and forth: each rebuild is slow and leaves the binary's
  current pin unclear.
- **Stale results** after updating Mathlib or editing your library: rerun with
  `--index-mode write` rather than trusting the cache.
- **Updating loogle**: `cd ~/.local/share/loogle && git pull && lake build`.

## When loogle is the wrong tool

- **The goal is in front of you** and you want something that closes it now:
  `exact?`, `apply?`, and `rw?` search the environment with your hypotheses in
  scope, which loogle cannot see.
- **You know the concept but not Lean's vocabulary for it**: natural-language
  search (<https://leansearch.net/>, <https://www.leanexplore.com/>) bridges
  that gap better than shape search does.
- **You want to read the surrounding theory**: grep
  `.lake/packages/mathlib/Mathlib/` directly, which is also the authoritative
  answer at your exact pin and needs no index.

Source and full documentation: <https://github.com/nomeata/loogle>.
