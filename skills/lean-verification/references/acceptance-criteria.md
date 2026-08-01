# Working a criteria list

A long list of acceptance criteria fails in a characteristic way: the early
items get real checks, the middle gets skimmed, and the tail gets a summary
sentence covering everything at once. The result reads as thorough and is not.
What prevents it is one criterion, one verdict, one piece of evidence, with the
evidence gathered before the verdict is written.

Enumerate the criteria before running anything, splitting the compound ones.
"Builds cleanly and is sorry-free with all theorems documented" is three
criteria that fail independently, and collapsing them lets one failure hide two
passes.

## What kind of criterion is it?

| Kind | How it resolves | Example |
|---|---|---|
| **Mechanical** | A command, with output | "`lake build` passes" |
| **Semantic** | Reading statements against intent | "the main theorem covers the unbounded case" |
| **Comparative** | Diffing two artifacts | "the paper's claims match the library" |
| **Absence** | Proving a negative | "no `sorry` anywhere" |
| **Underspecified** | Nothing; ask | "the proof is elegant" |

Flag the underspecified ones early, while there is still time to resolve them.
An underspecified criterion silently interpreted is how a review concludes
"met" on something the author would have failed.

Each criterion gets its own evidence, even when running the check looks
redundant. Inferring one from another ("it builds, so it must be `sorry`-free")
is exactly wrong here, because `sorry` is a warning and a library full of them
builds green. Absence criteria need the search scope reported alongside the
result: a search that inspects nothing returns the same number as a search that
finds nothing.

## Verdicts

| Verdict | Means |
|---|---|
| `MET` | Evidence gathered and quoted |
| `NOT MET` | Evidence gathered, criterion fails; state the gap |
| `PARTIAL` | Some sub-part met; state precisely which and which not |
| `NOT CHECKED` | No evidence gathered; state why |
| `UNDERSPECIFIED` | Cannot be resolved as written; state the question |

`NOT CHECKED` is a legitimate outcome. Its absence from a report is what makes
the report misleading, because a criterion silently marked met is
indistinguishable from one that was actually verified.

```
AC-1  Library builds with no errors or warnings
      MET — `lake build` exit 0; build.log: "Build completed successfully."
            0 lines matching warning|error.

AC-2  No `sorry`, `admit`, or `native_decide`
      MET — grep across 34 files / 8,412 lines: 0 hits.
            `#print axioms` on all 12 root theorems: propext, Classical.choice,
            Quot.sound only.

AC-3  Every public theorem carries a docstring
      NOT MET — 51 named results have none. `docBlameThm` is disabled by
            default so `runLinter` does not catch this; counted with:
            [command]. List attached.

AC-4  The main theorem covers the unbounded case
      PARTIAL — `main_thm` assumes `hB : Bounded S` (File.lean:203). The
            unbounded case is stated as `main_thm_unbounded` but proved only
            for finite index sets.

AC-5  Proof style is idiomatic
      UNDERSPECIFIED — no stated standard. Proposing: terminal `simp only`
            rather than bare `simp`, and no `native_decide`. Confirm?

AC-6  Performance regression under 5%
      NOT CHECKED — no baseline timing exists in the repo. Needs a prior
            measurement to compare against.
```

## What makes a criteria review wrong

Four failures, in rough order of frequency:

**Inferring rather than checking.** One command's output used to answer three
criteria.

**Reading the summary rather than the artifact.** A build log's last line, a
docstring instead of the statement, a README claim instead of the code. The
artifact is the evidence; a description of it is a claim.

**Charitable interpretation of a vague criterion.** Reading it as whatever the
work happens to satisfy. Flag it as underspecified instead: that is the
finding.

**A green mechanical check standing in for a semantic one.** "Does this prove
X" is not answered by "it compiles". The build establishes that the proofs match
their statements, and the criterion is almost always about what the statements
mean.
