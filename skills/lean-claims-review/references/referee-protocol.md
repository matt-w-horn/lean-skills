# The referee protocol

One referee per declaration. The dispatcher builds the prompt in strict
cache-stability order: this protocol text first, byte-identical across
every referee of a pool (no timestamps, no pair data), then the per-pair
block, then the agentic turns. Changing the protocol text or the effort
level starts a new cache pool; do neither mid-sweep (the full invalidator
list, verdict trailer included: `references/dispatch.md`, "Cache
structure" and "Dispatch mechanics").

## The prompt

The protocol section (verbatim; fill only the bracketed probe command):

```text
You are judging whether one docstring claims exactly what one Lean
statement proves. You see the declaration's name, kind, pretty-printed
elaborated statement, its docstring, and the verified docstrings of its
direct dependencies. You have two tools: [probe command], which
elaborates Lean source from stdin against the built library (imports
allowed, exit code distinguishes success), and web search for the
mathematics. You cannot read the project's files, and you must not
speculate about its intent beyond what the pair itself supports.

Compare on five axes: quantifier (does the prose universalize what the
statement bounds?), hypothesis (does the prose state every side condition
that matters?), direction (implication versus equivalence; necessary
versus sufficient), strength ("the" versus "a"; "exactly" versus "at
most"), existence (does everything the prose names actually appear?).

Before indicting the prose, test the statement with three probes:
1. Satisfiability: construct an instance meeting all hypotheses. If none
   can exist, the statement is vacuous.
2. Triviality: try closing the statement with its load-bearing hypothesis
   deleted, and check whether the hypotheses alone prove False. A
   statement is trivial when its conclusion needs no hypothesis or its
   hypotheses are contradictory — not when it closes by `simp` because
   the library already carries the fact.
3. Strengthening: elaborate the docstring's stronger reading as an
   `example` and try to prove it. A provable stronger reading indicts
   the statement only when probe 1 or 2 also fires; otherwise the
   verdict is prose-overclaims, with the provable strengthening quoted
   as evidence.

If all probes are quiet and the docstring says more or less than the
statement, the prose is the problem. A side remark that the statement
carries dead weight (an inert hypothesis, an unused binder) belongs in
the evidence, not in the verdict. If the docstring instead describes a
different result altogether — neither a strengthening nor a weakening of
this statement — the defect cannot be localized from the pair alone:
report intent-unclear and quote both readings.

Report a single verdict with evidence: quote the docstring words and the
statement fragment they disagree over, and state each probe you ran with
its result. Do not restate or explain your reasoning process; the
evidence and probe results are the deliverable.
```

## The per-pair block

After the protocol, in this order:

```text
Declaration: [name] ([kind])
Statement:
[pretty-printed elaborated type]
Docstring:
[docstring]
Verified dependency docstrings:
[name₁]: [docstring₁]
[name₂]: [docstring₂]
…
```

The dependency docstrings are the ones the ledger has passed — never
unreviewed prose, never module docstrings, never the paper. If a
dependency is unverdicted, the pair is not ready; the wave ordering
exists to prevent this.

## Verdict schema

Structured output, one of:

| Verdict | Meaning | Routed to |
|---|---|---|
| `supported` | The docstring claims exactly what the statement proves | Ledger, via the project's writer |
| `prose-overclaims` | Prose says more (axis + quoted evidence) | Docstring edit by a full-context session |
| `prose-underclaims` | Prose says less, specifically enough to mislead (axis + evidence) | Docstring edit |
| `statement-suspect` | A probe indicts the statement (probe evidence + proposed Lean fix) | The maintainer — statement changes are theirs |
| `intent-unclear` | Two substantive readings, probes cannot arbitrate (both readings quoted) | The maintainer |

Every non-`supported` verdict carries: the axis, the quoted docstring
words, the quoted statement fragment, and the probes run with results.
`statement-suspect` additionally carries the proposed fix as Lean source
the maintainer can elaborate.

Two constraints on the schema's use. A truncated referee (hit its token
ceiling) is escalated, never inferred; the bundled renderer labels such
replies `unparsed`, outside the five verdicts, and routes them to the
findings log like `intent-unclear`. And the protocol asks for evidence
and probe results, not reasoning transcription — prompts that tell a
model to echo its internal reasoning as response text trigger refusals
on current models and add nothing the evidence does not.
