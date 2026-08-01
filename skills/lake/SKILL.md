---
name: lake
description: Build, configure, and troubleshoot Lean 4 projects with Lake, Lean's build tool and package manager. Use whenever a Lean build, toolchain, or editor setup is involved — `lake build` fails, hangs, or starts recompiling Mathlib from source; the Mathlib cache will not download; a project needs setting up from scratch; dependencies or `lake-manifest.json` need updating; `lean-toolchain` needs changing; errors appear deep inside Mathlib after bumping its revision, which almost always means a version mismatch rather than a real error; or a Lean project will not load in the editor and the language server hangs or spins. Also use for elan toolchain management, trimming imports, and "how do I start a Lean project with Mathlib".
---

# Lake: building Lean projects

Lake is Lean's build tool and package manager. It reads `lakefile.toml` (or
`lakefile.lean`), resolves dependencies into `.lake/packages/`, and builds
`.olean` files into `.lake/build/`.

Everything below was checked against Lake 5.0.0 with Lean 4.32.0, where
`lake --version` prints `Lake version 5.0.0-src (Lean version 4.32.0)`. Lake's
surface changes across major Lean releases, so `lake <cmd> --help` is the
authority when something here does not match.

## The one thing that goes wrong most

**A Mathlib project that builds Mathlib from source is misconfigured, not
slow.** Mathlib takes hours to compile and minutes to download. If `lake build`
starts elaborating `Mathlib.Analysis.…`, stop it and fetch the cache:

```sh
lake exe cache get
```

Two similarly-named commands exist and they are not the same thing:

| Command | What it is |
|---|---|
| `lake exe cache get` | **Mathlib's own** cache tool, declared as `lean_exe cache` in Mathlib's lakefile. Downloads prebuilt `.olean`s from Mathlib's server. This is the one you want for Mathlib. |
| `lake cache get` | **Lake's** built-in cache subcommand (Lake 5+), for configured remote cache services generally. |

`lake exe cache get` requires that the dependency has been *materialized*
first: `lake update` or an initial `lake build` has to have cloned Mathlib into
`.lake/packages/`. Running it in a fresh clone with no manifest fails with an
unknown-executable error, which reads like a broken install and is not.

The cache is keyed by the exact Mathlib commit. A project pinned to a revision
nobody built produces a cache miss and a source build, which is why the pin
wants to be a Mathlib release tag matching your `lean-toolchain`.

## Starting a project

```sh
lake +leanprover/lean4:v4.32.0 new myproject math
cd myproject
lake exe cache get
lake build
```

Templates, from `lake new --help`:

| Template | Contents |
|---|---|
| `std` | Library and executable (default) |
| `exe` | Executable only |
| `lib` | Library only |
| `math-lax` | Library with a Mathlib dependency |
| `math` | Library with a Mathlib dependency, plus Mathlib's linting and CI workflows |

Suffix with `.toml` or `.lean` to choose the config language (`math.lean`);
TOML is the default. `lake init` does the same in the current directory. The
`+<version>` prefix works when Lake is running under elan, which is the normal
setup, and pins the new project's toolchain in one step.

For formalization work, prefer `math` over `math-lax`: the linting
configuration it brings is the one Mathlib holds itself to, and adding it later
means fixing a backlog.

## Everyday commands

```sh
lake build                     # build default targets
lake build MyLib.Foo           # one module
lake build --wfail             # treat warnings as failure, good for CI
lake build -v                  # show the actual command invocations
lake clean                     # delete build outputs
lake test                      # run the configured test driver
lake lint                      # run the configured lint driver
lake env <cmd>                 # run a command with LEAN_PATH set from this project
lake exe <name> <args>         # build an executable target and run it
lake serve                     # start the language server
lake shake                     # report and trim unnecessary imports
```

`lake env` is how any external tool (search tools, REPLs, custom scripts) finds
the project's `.olean` files, and it has to run from inside the project
directory: it reads the *current directory's* lakefile to compute `LEAN_PATH`.

```sh
lake env lean MyLib/Foo.lean   # elaborate one file with the project's imports
lake env printenv LEAN_PATH
```

## Wiring `lake test` and `lake lint`

Both commands run whatever driver the package configures, and nothing happens
without one. Verified at Lake 5.0.0 / Lean v4.32.1:

```toml
# lakefile.toml
testDriver = "MyTests"                  # a lean_lib or lean_exe of this package
lintDriver = "batteries/runLinter"      # cross-package drivers work: pkg/target
lintDriverArgs = ["MyLib"]
```

```lean
-- lakefile.lean equivalent
package myProject where
  testDriver := "MyTests"
  lintDriver := "batteries/runLinter"
  lintDriverArgs := #["MyLib"]
```

The driver's kind decides what `lake test` means:

- **A `lean_lib` driver** is a compile-only suite, Mathlib's pattern. Every
  file that elaborates passes; a failed proof or `#guard` fails the build. A
  glob saves registering each new test file:

  ```toml
  [[lean_lib]]
  name = "MyTests"
  globs = ["MyTests.+"]        # every module under MyTests/
  ```

- **A `lean_exe` driver** is built *and then run*, for suites with runtime
  stages a compile cannot express: fixtures that must **fail** to build,
  lock-file comparisons, spawning external checkers. Set
  `supportInterpreter = true` if the exe loads the environment at runtime
  (`importModules`), and make its root module `import` the library it
  inspects: that import is what forces Lake to rebuild the library before the
  exe runs, and without it the exe reads stale `.olean`s.

`lake lint` is the same mechanism under a different key; pointing it at
Batteries' `runLinter` with your library as the argument replaces the
`lake exe runLinter MyLib` invocation.

## Dependencies and the manifest

`lake-manifest.json` records the exact resolved commit of every dependency.
It belongs in version control: it is what makes a build reproducible.

```toml
# lakefile.toml
name = "MyProject"
defaultTargets = ["MyProject"]
leanOptions = { autoImplicit = false, relaxedAutoImplicit = false }

[[require]]
name = "mathlib"
git = "https://github.com/leanprover-community/mathlib4"
rev = "v4.32.0"

[[lean_lib]]
name = "MyProject"
```

```sh
lake update                # update every dependency, rewrite the manifest
lake update mathlib        # update one
lake update --keep-toolchain   # do not let the update change lean-toolchain
```

`lake update` is not a routine command. It changes pinned revisions, can move
`lean-toolchain` under you, and typically invalidates the Mathlib cache,
turning a two-minute setup into an hours-long source build. Run it when you
mean to move, then immediately `lake exe cache get` and `lake build`.

Setting `autoImplicit = false` is worth doing in any serious project: auto-bound
implicits silently turn a typo'd identifier into a new universe-polymorphic
variable, producing a theorem that typechecks and means nothing.

## Toolchains

`lean-toolchain` holds one line naming the Lean version. elan reads it and
switches automatically when you `cd` into the project.

```sh
elan toolchain list
elan toolchain install leanprover/lean4:v4.32.0
elan default leanprover/lean4:v4.32.0
elan self update
```

**Keep the toolchain and the Mathlib revision in lockstep.** Mathlib release
tags match Lean versions (`v4.32.0` ↔ `leanprover/lean4:v4.32.0`). A mismatch
produces errors deep inside Mathlib that look like Mathlib bugs. Bump both, in
the same commit.

elan switches `lean` and `lake` per directory, but a separately-installed
binary does not follow: tools built against one toolchain fail in confusing
ways under another. Across projects on different toolchains, keep a separate
checkout of such a tool per toolchain rather than rebuilding one back and
forth, which is slow and leaves the binary's current pin unclear.

## Reading the layout

```
.lake/
├── packages/          # dependency sources: Mathlib's source lives here
│   └── mathlib/Mathlib/...
└── build/
    ├── lib/           # your .olean, .ilean, .trace files
    └── bin/           # executables
```

`.lake/` is generated and belongs in `.gitignore`. It is also the most useful
directory in the project: the full Mathlib source at your exact pin sits in
`.lake/packages/mathlib/`, so grepping it is the fastest and most authoritative
way to confirm a lemma name, a tactic, or a deprecation, with no network
involved.

## Migrating a project to the module system

Mathlib and Batteries are fully on Lean's module system — at the v4.32.1 pin,
every one of Mathlib's 8264 files and Batteries' 187 carries a `module` header.
A project that predates it still builds, so this is an upgrade on your own
schedule rather than a forced migration, but `lake shake` refuses to run
until you take it:

```
error: `lake shake` only works with `module`s currently
```

The porting idiom, from the migrated files, is a header and one line:

```lean
module

public import Mathlib
public import MyProject.Foundations

/-! # Module docstring -/

@[expose] public section

-- everything below unchanged; the section is not closed
```

Declarations stay bare — Mathlib has ~119000 plain `theorem` and no
`public theorem`, because the section does the work. About 60% of its files use
`@[expose] public section` and the rest plain `public section`.

**Four things that bite, in the order you hit them.**

**Migration is bottom-up, and the compiler enforces it.** A `module` file cannot
import a pre-module one:

```
cannot import non-`module` X from `module`
```

The reverse is fine, so a pre-module root can keep importing migrated leaves
while you work up the DAG. Do the leaves first.

**`@[expose]` is about definition *bodies*, not visibility.** Plain
`public section` exports a definition's signature while leaving its body opaque
downstream, so nothing can unfold it. Any project whose proofs rely on
unfolding — `change` reducing a structure projection, `norm_num` on a concrete
instance, `rfl` at a definition, `abbrev` chosen so reduction still fires —
needs `@[expose]` or a large fraction of it stops compiling. Reach for plain
`public section` only where you mean the body to be opaque.

**Metaprogramming moves to the meta phase.** A file registering linters or
defining `elab` commands needs `public meta import` for what it elaborates
against, and its declarations inside a `meta section`. The error names the fix:

```
Cannot add attribute `[env_linter]`: Declaration `X` must be marked as `meta`
```

An import that exists only for its elaboration side effect stays a plain
`public import` — it is not referenced by anything the registrations mention.

**`public section` lifts nested proofs into named constants, so printed types
change.** A proof written inline in a *type* — `g 3 (by omega)` — is an
anonymous term in a pre-module file and prints elided:

```
t : g 3 ⋯ = 3
```

Under `public section` it becomes a public auxiliary and prints by name:

```
t : g 3 t._proof_2 = 3
```

`module` alone does not do this and `@[expose]` is not the cause; making the
declaration public is. No pretty-printer option reverses it, because
`Lean.PrettyPrinter.Delaborator.shouldOmitProof` returns early on atomic
expressions — an inline proof term is non-atomic and elides, a named constant is
atomic and never does. It only affects theorems carrying an inline proof *in
their type*, which is rare, but it will move any digest or freeze file that
records pretty-printed types. Naming the proof as its own lemma renders stably
if you want the type readable.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `cannot import non-module X from module` | A migrated file imports a pre-module one | Migrate bottom-up; the reverse direction is legal |
| Source edit has no effect on a `lake env lean` run | `lake env lean` loads the compiled `.olean`, not your edit | `lake build <Module>` first, then re-run |
| Building Mathlib from source | No cache fetched, or a revision nobody built | `lake exe cache get`; pin to a release tag |
| `unknown executable cache` | Mathlib not materialized yet | `lake update` (or an initial `lake build`), then retry |
| Errors deep inside Mathlib | Toolchain / Mathlib revision mismatch | Align `lean-toolchain` with the Mathlib tag |
| `no default toolchain configured` | Run outside a Lean project, or elan not set up | `cd` into the project, or `elan default <version>` |
| Editor shows stale errors | Language server holding old `.olean`s | Restart the server; `lake build` first |
| Rebuilds everything after a trivial edit | A widely-imported module changed | Expected; `lake build --old` limits to modified modules |
| Build succeeds, imports are wrong | Nothing enforces import hygiene | `lake shake` |
| Config change not taking effect | Lake reusing the elaborated config | `lake build -R` (`--reconfigure`) |
| Disk filling up | `.lake/` grows with every dependency version | `lake clean`, or delete `.lake/` and re-fetch |

`lake build -v` shows the actual `lean` invocations, and `lake build --no-cache`
distinguishes a corrupt cache from a real error.

## Related

**`lean-proving`** for what to do once the build works, **`lean-verification`**
for build-based evidence gathering, and **`loogle`** for searching the Mathlib
that Lake put on your disk.
