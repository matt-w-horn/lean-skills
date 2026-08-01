# The mechanical checks

The Lean community's own checklist for "did you actually prove it?" is five
items: the code lives in a real Lean repository rather than loose files, it
builds with `lake build`, the file holding the theorem is genuinely *imported*
into that build, `#print axioms` returns only `[propext, Classical.choice,
Quot.sound]` or a subset, and the statement faithfully says what it claims. See
<https://leanprover-community.github.io/did_you_prove_it.html>. Rungs 1 to 3
here mechanize the first four; rungs 4 and 5 are the fifth, which no command
can do for you.

## Rung 1: does it build?

```sh
lake build 2>&1 | tee build.log; echo "exit: $?"
grep -i "warning\|error\|sorry" build.log
```

Lean reports `warning: declaration uses 'sorry'` as a **warning**, so the exit
code is 0 and the theorem is unproved. Read the output, not just the status.

For a slow or first build, see the **`lake`** skill: a Mathlib project that
rebuilds Mathlib from source is misconfigured, not slow.

## Rung 2: `sorry`-free and axiom-clean

### Source-level scan

This is the scan that catches everything, because it reaches every declaration
kind including `example`s that never enter the environment:

```sh
grep -rn "\bsorry\b\|\badmit\b\|\bstop\b\|sorryAx" --include="*.lean" YourLib/
```

Two refinements, both learned from scanners that failed. Strip comments before
scanning, or a `sorry` mentioned in a docstring reads as a hit; handle string
literals when you do, because a scanner that treated `--` inside a string as a
comment opener discarded the rest of the line and hid everything after it. And
scan `example`s, since they are the case an environment sweep cannot see.

### Environment-level check

```lean
#print axioms myTheorem
-- 'myTheorem' depends on axioms: [propext, Classical.choice, Quot.sound]
```

Those three are Lean's standard axioms, and their presence is normal:

| Axiom | What it adds | Blocks kernel reduction | Blocks compilation |
|---|---|---|---|
| `propext` | Equivalent propositions are equal | yes | no |
| `Quot.sound` | Quotient identification; `funext` derives from it | yes | no |
| `Classical.choice` | Choice: produces data from an existence proof | yes | **yes** |

Anything else in that list is a finding. In particular:

- **`sorryAx`** — a `sorry` somewhere in the dependency chain, however deep.
  This is the check that catches an incomplete proof imported from three
  modules away.
- **A project-defined axiom** — legitimate if declared and documented, a hole
  if not. Grep for `axiom ` in the library to see what exists.
- **`Lean.ofReduceBool` / `Lean.trustCompiler`** — introduced by
  `native_decide`, which trusts the compiler rather than the kernel. Many
  projects forbid it for exactly that reason.

To sweep a whole namespace, projects commonly define a custom command that
walks every declaration under it at build time and fails the build on an
unexpected axiom. A project's own sweep is authoritative, with one caveat that
has bitten real libraries: **it only sees modules that the file it runs in
actually imports.** A separate audit root needs every module imported there as
well as in the build root, or coverage silently shrinks as modules are added.

```sh
# does every module reach the audit root?
diff <(ls YourLib/*.lean | xargs -n1 basename | sed 's/.lean//' | sort) \
     <(grep -oE 'import YourLib\.[A-Za-z.]+' YourLib/AxiomAudit.lean | sed 's/.*\.//' | sort)
```

Writing one is a few lines of metaprogramming over `Lean.Environment` and
`CollectAxioms`; the Lean 4 metaprogramming documentation covers the pattern.

## Rung 3: linters

```sh
lake exe runLinter YourLib
```

Available when Batteries is a dependency. Verified present at Batteries for
Lean v4.32.0:

| Linter | Catches | Default |
|---|---|---|
| `unusedArguments` | Hypotheses and binders the declaration never uses | on |
| `docBlame` | Missing docstrings on **defs and instances** | on |
| `docBlameThm` | Missing docstrings on **theorems** | **off** |
| `checkType` | Declarations whose type is malformed | on |
| `synTaut` | Statements that are syntactic tautologies | on |
| `unusedHavesSuffices` | `have`/`suffices` steps nothing consumes | on |
| `simpNF` | `@[simp]` lemmas not in simp normal form | on |
| `simpComm` | Commutativity simp lemmas that loop | on |
| `explicitVarsOfIff` | Iff statements with implicit variables | off |

The gap worth naming in any audit: **`docBlameThm` is disabled by default**, so
a library can pass `runLinter` with every theorem undocumented. Docstring
coverage on theorems is unenforced unless a project turns it on, and docstring
*honesty* is unenforced by anything at all. That is the boundary the semantic
pass exists to cover.

`synTaut` is the closest mechanical check to "this theorem says nothing", and
it only catches syntactic cases. A theorem that reduces to a closed numeral
after unfolding passes it.

## Rung 3b: project-specific gates

These encode constraints nothing generic knows about. The lakefile is the first
place to look: a package with `testDriver`/`lintDriver` keys means `lake test`
and `lake lint` *are* the gates, and running only build plus linter
under-verifies it.

```sh
grep -i "driver" lakefile.toml lakefile.lean 2>/dev/null
lake test && lake lint
ls .claude/verify/ scripts/ Makefile tests/ 2>/dev/null
cat .pre-commit-config.yaml 2>/dev/null
```

Negative tests, fixtures that must *fail* to compile, deserve particular
attention: they are how a project proves its own gates work, and a gate nobody
has watched fail is a gate nobody has tested. The same rule governs *adding* a
gate, so demonstrate the new check failing on a constructed bad input and
passing on the real tree before wiring it in. The recurring failure shape is
the check that inspects nothing, a scanner pointed at files that state nothing
or a digest whose corpus is empty, which reports zero findings in the same
voice as a real pass.

## Rung 3c: coverage, for a proof library

Line coverage is meaningless for proofs and no tool measures it (none exists
for Lean as of this pin). The metric that does mean something is
per-declaration **verification class**: is each declaration *consumed* by
another declaration's type or proof, *witnessed* (in the dependency cone of a
concrete instance), *pinned* (by a closed-statement regression), or a justified
*terminal* deliverable. Anything that is none of these is compiled-only, which
a gate can reject.

All of it is computable from the environment. `Expr.getUsedConstants` over each
declaration's type and value yields the consumption graph as the kernel sees
it, so dot-notation and every other surface spelling that defeats textual
matching are irrelevant. Two facts make the classes cheap: a theorem whose
statement quantifies over nothing is its own kernel-checked regression (the
kernel accepted a closed fact, and that *is* the test), and reachability from
concrete witnesses is one graph traversal. The implementation is the same
few-lines-of-metaprogramming shape as the axiom sweep above, and carries the
same caveat that the environment only holds what the running file imports.

## What to record

```
lake build                 → exit 0; 0 errors, 0 warnings          [quote the tail]
sorry scan                 → 0 hits across 34 files, 8,412 lines
#print axioms main_theorem → propext, Classical.choice, Quot.sound
runLinter                  → 0 findings  [or: N findings, listed below]
negative fixtures          → 5/5 failed to elaborate as required
```

Counts of what was inspected, not just counts of what was found. "0 problems"
and "0 files looked at" produce the same number, and only one of them is good
news.
