# The statement freeze

A freeze makes "no statement moved" checkable. The strong form reads the
**elaborated environment**; the weak form digests source text. Build the strong
one when you can; the code below is complete and was compiled and exercised at
`leanprover/lean4:v4.32.1`.

## Why elaborated types

Source-level digests have three holes, each observed in practice:

1. **`variable` binders.** A statement's source line can be byte-identical
   while a shared `variable` above it changed what it means. The elaborated
   type has the binders resolved in place, so the change is visible.
2. **Truncation.** Header-scanning digests cap the lines they read; a long
   statement's tail is silently unfrozen.
3. **Additions.** A digest that only diffs known keys never reports a new
   declaration, and new statements are as much part of the library's meaning as
   old ones.

Elaborated pretty-printing is deterministic for a pinned toolchain, so a lock
file generated from it can be **tracked in git**: the freeze survives clones,
and a statement edit shows up as an ordinary reviewable diff of human-readable
types.

## The lock, working code

Three pieces: a library to freeze (here `Demo`), an executable, and the lakefile
wiring. The exe **imports the library in its source**, which is what makes Lake
rebuild the library before the exe runs; without it the exe reads whatever stale
`.olean`s happen to be on disk, and a config-only dependency
(`extraDepTargets`) did not force the build at this pin.

```toml
# lakefile.toml
name = "demo"
defaultTargets = ["Demo"]
testDriver = "lock"          # optional: makes `lake test` run the check

[[lean_lib]]
name = "Demo"

[[lean_exe]]
name = "lock"
root = "Lock"
supportInterpreter = true
```

```lean
-- Lock.lean
import Lean
import Demo   -- forces the library build; see above

open Lean

def kindOf : ConstantInfo → String
  | .thmInfo _ => "theorem"
  | .defnInfo _ => "def"
  | _ => "other"

unsafe def main (args : List String) : IO UInt32 := do
  initSearchPath (← findSysroot)
  enableInitializersExecution
  let env ← importModules #[{module := `Demo}] {} (trustLevel := 1024) (loadExts := true)
  let ctx : Core.Context := { fileName := "<lock>", fileMap := default }
  let blocks ← Prod.fst <$> (Core.CoreM.toIO · ctx { env }) do
    let names := env.constants.toList.filterMap fun (n, _) =>
      if n.getRoot == `Demo && !n.isInternal then some n else none
    let mut out : Array String := #[]
    for n in names.toArray.qsort (·.toString < ·.toString) do
      let some ci := env.find? n | continue
      let type ← Meta.MetaM.run' do
        return (← Meta.ppExpr ci.type).pretty (width := 100)
      let value ← match ci with
        | .defnInfo d => Meta.MetaM.run' do
            return s!"\n  := {(← Meta.ppExpr d.value).pretty (width := 100)}"
        | _ => pure ""
      out := out.push s!"#### {n} : {kindOf ci}\n  {type}{value}"
    return out
  let lock := String.intercalate "\n" blocks.toList ++ "\n"
  let file : System.FilePath := "statements.lock"
  if args.contains "--update" then
    IO.FS.writeFile file lock
    IO.println s!"lock: wrote {blocks.size} blocks"
    return 0
  let old ← IO.FS.readFile file
  if old == lock then
    IO.println s!"lock: {blocks.size} statements unchanged"
    return 0
  IO.FS.writeFile "statements.lock.new" lock
  IO.println "lock: statements changed — diff statements.lock statements.lock.new"
  return 1
```

`lake exe lock --update` writes `statements.lock` (track it); `lake exe lock`,
or `lake test` with the `testDriver` line, fails on any drift and writes
`statements.lock.new` so `diff` shows exactly which statements moved. For a
theorem the lock holds the printed type only; for a `def` it also holds the
printed value, because a definition's body is its statement. Theorem proof
bodies are exactly the freedom being protected.

Changing `variable {α : Type}` to `{α : Type 1}` above an untouched theorem
produces

```
-   ∀ {α : Type} (a : α), a = a
+   ∀ {α : Type 1} (a : α), a = a
```

which is precisely the change no source digest reports.

An empty diff says the walked declarations' elaborated types, and `def` values,
are identical to the locked ones under this toolchain pin. It says nothing about
declarations outside the walked root, about auxiliaries the walk filters out, or
about whether the statements were right in the first place: a freeze is a
no-drift check, not a correctness check.

Notes for real libraries:

- **Scope the walk by namespace root** (`n.getRoot`), as above. Filter out
  compiler-generated companions if they show up in your environment (equation
  lemmas `*.eq_1`, `casesOn`-family, `mk`, `*.congr_simp`, `match_*`/`proof_*`
  auxiliaries): they are realized on demand, so their presence varies with which
  proofs forced them, and they churn the lock without carrying independent
  meaning.
- **Hash long values if size matters.** Printed proof-free `def` bodies are
  usually small; if one is not, store a hash of the printed value and keep the
  full text in a generated artifact.
- For a Mathlib-based project the exe is identical; `importModules` loads
  whatever the library imports, and only the walked namespace changes.

## Prove the freeze works before trusting it

A check that inspects nothing still passes. Watch the lock fail once per failure
mode before relying on it: edit a `variable` binder or a hypothesis and see the
diff; comment out a declaration and see the removal reported; add a throwaway
theorem and see the addition reported, which is the case weak freezes silently
pass. A fixture file the check must reject keeps that demonstration cheap to
re-run.

## The weak form, when the toolchain is out of reach

The source-text digest (hash `theorem`/`lemma` headers up to `:=`, hash whole
bodies for definition kinds, key by fully qualified name) is described in
`lean-latex-sync/references/sync-checks.md`. It needs no build and no
metaprogramming, and it carries all three holes at the top of this file. Using
it means stating those holes wherever its output is read, and treating "no drift
reported" as covering exactly what it digests rather than the library's meaning.
