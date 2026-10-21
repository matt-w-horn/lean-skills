# Lake: building Lean projects, toolchains, and modules

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
TOML is the default. `lake init` does the same in the current directory. For
formalization work, prefer `math` over `math-lax`: the linting configuration it
brings is the one Mathlib holds itself to, and adding it later means fixing a
backlog.

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

The driver's kind decides what `lake test` means:

- **A `lean_lib` driver** is a compile-only suite, Mathlib's pattern. Every
  file that elaborates passes; a failed proof or `#guard` fails the build.
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

## Dependencies, manifests, and toolchains

`lake-manifest.json` records the exact resolved commit of every dependency and
belongs in version control. Set `autoImplicit = false` and
`relaxedAutoImplicit = false` in `leanOptions` so typo'd identifiers do not
silently become universe-polymorphic variables.

`lake update` is not a routine command: it changes pinned revisions, can move
`lean-toolchain` under you, and typically invalidates the Mathlib cache. Keep
`lean-toolchain` and the Mathlib revision in lockstep (`v4.32.0` matches
`leanprover/lean4:v4.32.0`).

## Migrating a project to the module system

Mathlib and Batteries are on Lean's module system (`module` header + `public
import` + `@[expose] public section`), and `lake shake` requires it:

```lean
module

public import Mathlib
public import MyProject.Foundations

/-! # Module docstring -/

@[expose] public section
```

Four things that bite, in the order you hit them:

1. **Migration is bottom-up, and the compiler enforces it.** A `module` file
   cannot import a pre-module one (`cannot import non-module X from module`),
   though a pre-module file can import a `module` file. Migrate leaves first.
2. **`@[expose]` is about definition *bodies*, not visibility.** Plain
   `public section` exports a definition's signature while leaving its body
   opaque downstream, so nothing can unfold it. Use `@[expose] public section`
   whenever downstream proofs unfold definitions.
3. **Metaprogramming moves to the meta phase.** A file registering linters or
   defining `elab` commands needs `public meta import` for what it elaborates
   against, and its declarations inside a `meta section`.
4. **`public section` lifts nested proofs into named constants, so printed types
   change.** A proof written inline in a *type* (`g 3 (by omega)`) is an
   anonymous term in a pre-module file and prints elided (`g 3 ⋯ = 3`), whereas
   under `public section` it becomes a public auxiliary (`g 3 t._proof_2 = 3`),
   which moves any statement lock that records pretty-printed types.

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
