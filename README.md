# lean-skills

[![ci](https://github.com/matt-w-horn/lean-skills/actions/workflows/ci.yml/badge.svg)](https://github.com/matt-w-horn/lean-skills/actions/workflows/ci.yml)
![license: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)

Claude Code skills for working in [Lean 4](https://lean-lang.org/) and
[Mathlib](https://github.com/leanprover-community/mathlib4).

Seven skills, split by what you are doing rather than by topic. Topic-shaped
skills fail in a specific way: a "tactics" skill and a "Mathlib" skill would
both match every Lean task, so both would load, and neither would tell the
agent what to do next. A task-shaped skill fires when its task comes up, and carries the
workflow for it.

| Skill | Fires when | Covers |
|---|---|---|
| `lean-proving` | You are changing Lean source, or asking whether something is provable | Feasibility, prior art, statement design, tactics, decoding errors, Mathlib naming |
| `lean-refactoring` | You are simplifying or golfing existing proofs | The frozen-statements contract, proof-vs-statement changes, the slice loop, a working elaborated-statement lock |
| `lean-latex-sync` | Prose describes Lean code: a paper, README, or docstring | Claim-versus-statement auditing, drift classes, resyncing prose after a stream of Lean commits, `\lean{}` citation checks, listings/minted setup |
| `lean-verification` | You are asking whether work is actually correct or complete | Build and axiom evidence, junk values and vacuity, prior-art searches, acceptance criteria |
| `lean-claims-review` | A project keeps a claims ledger and pairs need verdicts | Blinded referee dispatch, verdict schema, probe battery, wave ordering, calibration |
| `lake` | The build, the toolchain, or a new project's setup is the problem | `lake build`, Mathlib cache, toolchains, dependencies, `lake test`/`lake lint` drivers, module-system migration, troubleshooting |
| `loogle` | You need a lemma that probably already exists | Shape-based and conclusion-based search over Mathlib |

## The idea

Two things go wrong in Lean work, and they fail independently.

The kernel catches the first: a proof that does not establish its statement
will not compile. Nothing catches the second: a statement that does not mean
what its author intended compiles perfectly and can sit in a library for years.
`x / 0 = 0` in Lean, so a theorem about a ratio is provable at a zero
denominator for reasons that have nothing to do with the mathematics. These
skills spend most of their length on that second failure, because it is the one
you get no help with.

The other bias throughout is toward verification against the toolchain on disk
rather than recall. Mathlib renames things continuously: `push_neg` logs a
deprecation warning at v4.32.0, and `div_add_div_same` is gone. A remembered
lemma name costs a full rebuild to disprove. The full Mathlib source sits in
`.lake/packages/mathlib/` at the revision you pinned. A grep of that source is
faster and more reliable than memory. The skills say so repeatedly, and give
the commands.

## Installing

Symlink whichever skills you want into `~/.claude/skills/`:

```sh
git clone https://github.com/matt-w-horn/lean-skills.git
cd lean-skills
for s in skills/*/; do
  ln -s "$PWD/$s" ~/.claude/skills/"$(basename "$s")"
done
```

Or add the repository as a plugin marketplace:
`/plugin marketplace add matt-w-horn/lean-skills`.

The `loogle` skill documents how to install the
[loogle](https://github.com/nomeata/loogle) binary. That install is optional:
a hosted instance at <https://loogle.lean-lang.org/> needs no install. Nothing
else here has dependencies. The skills are Markdown. The only code is two
standard-library Python tools, each with its tests: the validator in `tools/`
and the sweep renderer in the claims-review skill. CI runs the validator and
both test suites.

## Layout

```
skills/<name>/
├── SKILL.md        # the workflow, loaded when the skill fires
├── references/     # detail, loaded only when SKILL.md points at it
└── scripts/        # bundled tooling, where a skill has any
```

Only `SKILL.md` is required. `lake` and `loogle` are a single file each, and
`lean-claims-review` is the one skill that bundles code.

The split is deliberate. The frontmatter is always in context, the body loads
when the skill triggers, and reference files load only when `SKILL.md` points
at them. Version-pinned inventories go to `references/` for that reason: the
tactic inventories, the error strings, and the linter list are long, and none of
them should cost context on a task that never reaches for them. The validator
enforces the other half of the bargain, failing CI on any file under
`references/` that no chain of mentions from `SKILL.md` reaches.

## Sources

Written against Lean 4 and Mathlib at `v4.32.0`, with later additions checked
at `v4.32.1`. Tactic inventories, linter names, and error strings were
extracted from those toolchains rather than recalled. Version-specific claims
are marked, and the reference files that carry version-pinned inventories say
how to regenerate them for a different pin.

Background reading drawn on: [Theorem Proving in Lean
4](https://lean-lang.org/theorem_proving_in_lean4/), [The Hitchhiker's Guide to
Logical Verification](https://github.com/lean-forward/logical_verification_2025),
[Logic and Proof](https://leanprover-community.github.io/logic_and_proof/), the
[Lean FAQ](https://lean-lang.org/faq/), [Mathlib's naming
conventions](https://leanprover-community.github.io/contribute/naming.html), and
the [100 theorems](https://leanprover-community.github.io/100.html) tracking
pages.

## Related work

[leanprover/skills](https://github.com/leanprover/skills) is the Lean FRO's own
skill set, aimed at contributing to Lean and Mathlib upstream: proof writing,
MWE minimization, bisection, and PR conventions.
[cameronfreer/lean4-skills](https://github.com/cameronfreer/lean4-skills) is a
proving workflow pack with review and golf commands. This repository sits
downstream of both. It is about building and auditing your own formalization,
and most of its length goes to the checks nothing upstream covers: whether a
statement means what it claims, and whether the prose citing it is still true.

Two sibling repositories put these skills to work.
[lean-self-audit-template](https://github.com/matt-w-horn/lean-self-audit-template)
is a fork-ready Lean 4 + Mathlib template whose claims ledger is the kind of
project `lean-claims-review` referees.
[Overload](https://github.com/matt-w-horn/overload) is the formalization these
skills were developed against, with every gate live.

## Contributing

Corrections are welcome, particularly where a version-specific claim went
stale. That is the failure mode this repository is most exposed to. `python3
tools/validate_skills.py` checks structure and cross-references, and runs in
CI.

## License

Apache-2.0. See `LICENSE` and `NOTICE`.
