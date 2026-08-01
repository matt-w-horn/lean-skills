# Dispatch: waves, cache, effort, budget, models, calibration

## Waves

Topologically order the unverdicted set over the manifest's direct
dependency edges, dependencies first. Each wave's members are mutually
independent, so within a wave referees run freely; between waves the
ordering is what makes "verified dependency docstrings" true. Real
libraries are shallow — expect on the order of ten waves.

On a non-`supported` verdict, skip only that declaration's consumer cone
(the manifest's consumer edges give the exact set) and continue the
sweep. A fixed declaration re-enters on the next run, and its re-review
uses its new hashes.

## Fixing between waves

When the maintainer authorizes fixing prose findings during the sweep
(the skill's `--fix` argument, or an in-session grant), apply them in
the gap between waves — never while referees run, because
probes elaborate against the same build directory a rebuild rewrites.
The loop per wave: record `supported` verdicts and commit; fix that
wave's prose findings (statement indictments and ambiguities still stop
at the maintainer); rebuild the manifest; dispatch the next round as the
**frontier** — every unverdicted pair whose direct dependencies are all
ledger-passed, excluding declarations with unfixed findings. The
frontier folds re-reviews of just-fixed pairs in with the next wave, and
their cones unlock one round later.

During a bootstrap this is safe by construction: a pair enters the
ledger only when its dependencies are already ledger-passed, and only
flagged — never-ledgered — docstrings get edited, whose consumers are
cone-skipped and unverdicted. So a prose fix cannot stale an existing
ledger row, and the re-review set after a fix round is exactly the fixed
pairs. The one edit that breaks this: touching an already-passed
declaration's docstring, which stales its ledgered direct consumers'
context hashes — don't, without re-reviewing those consumers.

## Disposing statement findings

By default `statement-suspect` and `intent-unclear` stop at the
maintainer. A maintainer can instead grant standing authorization —
the skill's `--fix` argument, or an in-session grant — for the
dispatching session to dispose them itself, so the sweep never
blocks: every disposition is a commit plus a process-record entry, so
the exposure is a revertible change, and the worst case — an early bad
call propagating through later waves — is bounded by the record and the
re-review that follows any revert. The authorization covers any repair
the evidence supports — prose, statement, proof, or deletion — at the
dispatching session's judgment of what is worthwhile; the rules below
are the recurring shapes, not an exhaustive enumeration. Choose in
order:

1. **The claim already has a true home.** If the docstring's stronger
   claim is carried by an existing, more general declaration (often the
   flagged one's own dependency), fix the prose to disclose the
   instance and point at the general form. Never mint a duplicate of it.
2. **The statement is short of provable intent.** If the docstring's
   reading is provable and the statement can carry it without breaking
   consumers — keep any parent application in the proof, so pins keep
   pinning and coverage justifications keep holding — restate,
   regenerate the statement freeze deliberately, and record the change.
3. **The statement duplicates upstream.** If the library or its
   dependencies already carry the identical statement, delete after a
   blast-radius check (external citations, ledger and terminal records,
   consumers) and swap call sites to the upstream name.
4. **`intent-unclear` with no arbitrating probe.** Weaken the prose to
   what the statement carries — prose is the cheap, revertible side —
   and note the discarded reading in the process record so the
   maintainer can resurrect it as a statement change if it was the
   intent.

Every statement-level act still owes its process-record entry at the
time it is made; autonomous disposition changes who decides, not what
gets recorded.

## Cache structure

Referee prompts share one byte-identical protocol prefix per pool
(`references/referee-protocol.md`), written to cache once per session and
read at the cached rate by every subsequent referee. Dispatch a wave
back-to-back so the prefix stays inside the cache TTL. Two things
invalidate the pool's cache and are therefore forbidden mid-sweep:
editing the protocol text and changing the effort level. Caching
compresses the input side only; this workload is output-dominated, so
expect cache savings of 10–15% of total, and control cost with effort and
the verdict schema's tightness, not with cache tricks.

## Dispatch mechanics

The skill bundles the renderer: `scripts/sweep.py` (tests alongside it).
`frontier LABEL N` emits N workflow scripts covering every unverdicted
pair whose dependencies are ledger-passed — dispatch them as N parallel
workflow runs; `record` tallies a run's results, drives the project's
ledger writer for each `supported`, and appends the rest to a findings
log; `plan` previews the wave sizes. Project specifics (manifest,
ledger, probe, ledger-writer command, referee agent type/model/effort,
per-run concurrency) are flags; the referee prompt is built from this
skill's `references/referee-protocol.md` plus a fixed verdict-line
trailer, so the protocol text keeps one home. The renderer's `--effort`
default is `high`, the safe tier; pass `--effort medium` when
calibration clears the cheaper tier (the policy under "Effort" below).

Each emitted script *embeds* the rendered pair blocks and the protocol
text as constants. Passing rendered prompts through the orchestrator's
own messages instead multiplies every wave through its context window;
embedding keeps the payload in the run and states the protocol once per
script.

Have each referee end with a fixed final line naming its verdict, and
parse the last such line from its reply. That trailing instruction is
part of the pool-defining prompt text: calibrate with it in place, and
treat changing it like changing the protocol.

Enforce the probe-memory concurrency cap in the script (dispatch in
chunks of the cap's size) rather than trusting the runner's default. A
referee reply with no verdict line is a truncation: the renderer labels
it `unparsed` (a lost dispatch `dispatch-error`) and routes it to the
findings log, never the ledger. Treat both labels like `intent-unclear`:
escalate, never infer.

An interrupted run (crash, restart) loses nothing when the runner
journals per-referee results: resume the same run and completed referees
replay from the journal. The journal is also the recovery source for
results whose collected output was lost. Design the wave run to be
resumable before dispatching the first referee, not after the first
interruption.

## Effort

Effort is the primary cost/quality control on current models, and it
governs tool-call count as well as text. Referees are short-horizon,
sharply scoped, one to three probes — the wrong profile for `xhigh`
(long-horizon work) and for `max` (overthinking risk on structured
output). `low` is disqualified by the error asymmetry: a wrongly flagged
docstring costs minutes of review, a wrongly passed one seals drift in
looking reviewed, and `low` is where misses live.

Run the sweep pool at `medium` and keep an escalation pool at `high`:
every `intent-unclear`, every truncation, and every `statement-suspect`
needing confirmation is a **fresh dispatch** into the high pool — a fresh
pair of eyes, and a separate stable cache prefix — never a mid-
conversation effort bump. Calibration (below) decides whether `medium`
holds for the sweep; if any constructed defect slips at `medium`, the
sweep runs at `high` and costs roughly a third more.

## Budget

Four layers, hard to soft:

1. Per-referee `max_tokens` around 16k — a hard ceiling on thinking plus
   text. A truncated reply lands in the findings log (labeled `unparsed`,
   "Dispatch mechanics" above) and escalates; it never becomes a pass.
2. Per-referee effort, above.
3. Per-run budget, dispatcher-enforced from actual usage reported per
   referee. Stop dispatching when it is spent; the ledger is the resume
   state, so a run that stops mid-wave loses nothing.
4. Split roughly 90/10 between the sweep pool and the escalation pool;
   rebalance if the escalation rate surprises.

After the first wave, compare measured per-pair spend against the
estimate that sized the budget, and re-project before continuing —
projections from single-task measurements have been wrong by 2× in both
directions. For scale: one production bootstrap sweep measured ~30k
tokens per referee at a strong tier and high effort, roughly 10× the
estimate its design had derived from prompt size — probe iterations, not
the prompt, dominate.

## Models

Calibrate at least two model tiers before sweeping. If the cheaper tier
is clean on calibration, sweep with it and spend part of the difference
on the stronger tier as auditor: it re-judges every escalation plus a
random ~5% of the cheaper tier's `supported` verdicts to estimate the
miss rate. Any audit miss upgrades the rest of the sweep. Steady state
(a handful of changed pairs per week) uses the strongest tier
unconditionally — at that volume cost is noise and misses are the
expensive thing.

## Calibration procedure

The project supplies constructed defective pairs with an answer key kept
out of referee prompts. For each candidate configuration (model × effort
× protocol text):

1. Dispatch the calibration pairs exactly as real pairs — same prompt
   shape, same tools; the pair names are styled like real declarations so
   the referee cannot recognize a calibration run.
2. Require every constructed defect flagged with the expected verdict,
   and the ambiguous pair answered `intent-unclear` — a confident wrong
   answer on the ambiguous pair disqualifies the configuration as surely
   as a miss.
3. Record the matrix (configuration → per-pair results) with the run's
   date wherever the project keeps process records, and recalibrate after
   any change to the protocol text — an uncalibrated detector's verdict
   counts for nothing, however plausible its transcript.
