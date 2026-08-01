#!/usr/bin/env python3
"""Sweep orchestration for the blinded claims review.

Project-agnostic: everything project-specific arrives as a flag. Assumes
the project supplies (see SKILL.md, "What the project must supply"):

- a manifest: JSON array of rows with `name`, `kind`, `type` (the
  pretty-printed statement), `doc`, `consumers` (names), and the three
  claim hashes;
- a ledger: pipe-separated text file whose verdict rows carry the name in
  the first column and the verdict in the fifth, `name | h1 | h2 | h3 |
  verdict | ...` (`--` comment lines and a `mode:` line ignored), written
  only by the project's ledger tool;
- a probe: one whitelisted command elaborating Lean from stdin.

The --manifest/--ledger/--probe defaults are one common layout; point them
at your project's paths.

Dependency edges are the inverse of `consumers`. The referee prompt is
the protocol block extracted from this skill's references/
referee-protocol.md — the `[probe command]` placeholder filled with
--probe — plus a fixed verdict-line trailer; the prompt text is
pool-defining, so calibrate with it and do not edit it mid-sweep.

Subcommands:
  plan      print the dependency-wave sizes (a dispatch preview)
  frontier  emit N workflow scripts covering every unverdicted pair
            whose dependencies are all ledger-passed
  record    tally a results JSON; run the ledger writer per `supported`,
            append the rest to a findings log

Typical loop: frontier -> dispatch the emitted scripts as parallel
workflows -> record each result file -> fix findings between rounds ->
repeat until frontier prints "0 ready".
"""
import argparse
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
PASSING = ("supported", "accepted")

# Must list exactly the verdicts in references/referee-protocol.md's schema
# table; a schema change edits both.
TRAILER = """The last line of your reply must be `Verdict: <one of supported,
prose-overclaims, prose-underclaims, statement-suspect, intent-unclear>`.
"""

WORKFLOW = """export const meta = {{
  name: '{name}',
  description: 'Claims sweep {label}/{tag}: blinded referees, concurrency {chunk}',
  phases: [{{ title: 'Referee', detail: 'one blinded referee per pair' }}],
}}
const PROTOCOL = {protocol}
const PAIRS = {pairs}
const CHUNK = {chunk}
const results = []
for (let i = 0; i < PAIRS.length; i += CHUNK) {{
  const chunk = PAIRS.slice(i, i + CHUNK)
  const rs = await parallel(chunk.map(p => () =>
    agent(PROTOCOL + '\\n' + p.block, {{
      label: p.name, phase: 'Referee',
      agentType: {agent_type}, model: {model}, effort: {effort},
    }}).then(text => {{
      const s = text === null ? '' : String(text)
      const ms = s.match(/Verdict:\\s*([a-z-]+)/gi)
      const verdict = ms
        ? ms[ms.length - 1].replace(/Verdict:\\s*/i, '').trim().toLowerCase()
        : (text === null ? 'dispatch-error' : 'unparsed')
      return {{ name: p.name, verdict, text: verdict === 'supported' ? '' : s }}
    }})
  ))
  rs.forEach((r, j) => results.push(
    r ?? {{ name: chunk[j].name, verdict: 'dispatch-error', text: '' }}))
  log(results.length + '/' + PAIRS.length + ' judged')
}}
return results
"""


def load_manifest(path):
    rows = {r["name"]: r
            for r in json.loads(Path(path).read_text(encoding="utf-8"))}
    deps = {n: [] for n in rows}
    for n, r in rows.items():
        for c in r.get("consumers", []):
            if c in deps:
                deps[c].append(n)
    # Namespace-parent edges: `A.B` depends on `A` whenever both are rows.
    # Projects commonly prune prefix edges from `consumers` while their
    # context hashes still cover them; deriving them from names keeps wave
    # ordering, cone-skipping, and dependency docstrings aligned with the
    # gate's staleness notion.
    for n in rows:
        parts = n.split(".")
        for i in range(1, len(parts)):
            parent = ".".join(parts[:i])
            if parent in rows and parent not in deps[n]:
                deps[n].append(parent)
    # Reject dependency cycles up front: plan's depths would be silently
    # wrong and frontier would report the cycle's members as "waiting on
    # deps" forever.
    remaining = {n: set(d) for n, d in deps.items()}
    rdeps = {}
    for n, d in remaining.items():
        for x in d:
            rdeps.setdefault(x, []).append(n)
    ready = [n for n, d in remaining.items() if not d]
    seen = 0
    while ready:
        n = ready.pop()
        seen += 1
        for c in rdeps.get(n, []):
            remaining[c].discard(n)
            if not remaining[c]:
                ready.append(c)
    if seen < len(rows):
        stuck = sorted(n for n, d in remaining.items() if d)
        sys.exit(f"sweep: dependency cycle in manifest involving: "
                 f"{', '.join(stuck[:5])}")
    return rows, deps


def ledger_passed(path):
    passed = set()
    p = Path(path)
    if not p.exists():
        print(f"sweep: ledger {path} not found — treating every pair as "
              f"unverdicted", file=sys.stderr)
        return passed
    for line in p.read_text(encoding="utf-8").splitlines():
        if "|" not in line or line.startswith("--"):
            continue
        parts = [x.strip() for x in line.split("|")]
        if len(parts) >= 5 and parts[4] in PASSING:
            passed.add(parts[0])
    return passed


def protocol_text(probe):
    """The fenced protocol block from referee-protocol.md, probe filled,
    trailer appended. Pool-defining text: byte-stable per configuration."""
    ref = (SKILL / "references" / "referee-protocol.md").read_text(
        encoding="utf-8")
    # Anchor on the section heading: the file also fences the per-pair block
    # as ```text, and position alone must not decide which one referees get.
    _, _, prompt_section = ref.partition("## The prompt")
    m = re.search(r"```text\n(.*?)```", prompt_section, re.DOTALL)
    if not m:
        sys.exit("sweep: no ```text block under '## The prompt' in "
                 "references/referee-protocol.md")
    return m.group(1).replace("[probe command]", probe) + "\n" + TRAILER


def pair_block(n, rows, deps):
    # Field order mirrors references/referee-protocol.md, "The per-pair
    # block"; a format change there edits both.
    r = rows[n]
    block = (f"Declaration: {n} ({r['kind']})\n"
             f"Statement:\n{r['type']}\n"
             f"Docstring:\n{r['doc']}\n")
    if deps[n]:
        block += "Verified dependency docstrings:\n" + "".join(
            f"{x}: {rows[x]['doc']}\n" for x in sorted(deps[n]))
    return block


def cmd_plan(args):
    rows, deps = load_manifest(args.manifest)
    passed = ledger_passed(args.ledger)
    memo = {}

    def depth(n):
        if n not in memo:  # load_manifest rejected cycles, so this terminates
            memo[n] = 0 if not deps[n] else 1 + max(depth(x) for x in deps[n])
        return memo[n]

    waves = {}
    for n in rows:
        waves.setdefault(depth(n), []).append(n)
    sizes = "/".join(str(len(waves[k])) for k in sorted(waves))
    print(f"waves: {len(waves)} sizes: {sizes} total: {len(rows)} "
          f"({len(passed)} already passed)")


def name_file(path, flag):
    """Non-empty lines of a names file; a missing file is an error, never
    silently an empty set."""
    p = Path(path)
    if not p.exists():
        sys.exit(f"sweep: --{flag} file not found: {path}")
    return {l.strip() for l in p.read_text(encoding="utf-8").splitlines()
            if l.strip()}


def cmd_frontier(args):
    if not re.fullmatch(r"[A-Za-z0-9._-]+", args.label):
        sys.exit(f"sweep: label must match [A-Za-z0-9._-]+ (it names files "
                 f"and is embedded in the workflow script): {args.label!r}")
    rows, deps = load_manifest(args.manifest)
    passed = ledger_passed(args.ledger)
    exclude = name_file(args.exclude, "exclude") if args.exclude else set()
    if args.redo:
        passed -= name_file(args.redo, "redo")
        # stale rows re-enter; record() refreshes their hashes
    proto = protocol_text(args.probe)
    out, waiting = [], 0
    for n in sorted(rows):
        if n in passed or n in exclude:
            continue
        if any(x not in passed for x in deps[n]):
            waiting += 1
            continue
        out.append({"name": n, "block": pair_block(n, rows, deps)})
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    if not 1 <= args.splits <= len(alphabet):
        sys.exit(f"sweep: splits must be between 1 and {len(alphabet)}, "
                 f"got {args.splits}")
    tags = alphabet[: args.splits]
    for i, tag in enumerate(tags):
        half = out[i:: args.splits]
        script = WORKFLOW.format(
            name=f"claims-{args.label}-{tag}", label=args.label, tag=tag,
            chunk=args.chunk, protocol=json.dumps(proto),
            pairs=json.dumps(half), agent_type=json.dumps(args.agent_type),
            model=json.dumps(args.model), effort=json.dumps(args.effort))
        (outdir / f"claims-{args.label}-{tag}.js").write_text(
            script, encoding="utf-8")
    sizes = "/".join(f"{len(out[i::args.splits])}{t}" for i, t in enumerate(tags))
    print(f"{args.label}: {len(out)} ready ({sizes}), {waiting} waiting on "
          f"deps, {len(exclude)} excluded -> {outdir}")


def cmd_record(args):
    results = json.loads(Path(args.results).read_text(encoding="utf-8"))
    if isinstance(results, dict):  # a task .output wrapper, not a bare array
        if "result" not in results:
            sys.exit(f"sweep: {args.results} is an object with no 'result' "
                     f"key (keys: {', '.join(sorted(results))}); expected a "
                     f"results array or a task output wrapper")
        results = results["result"]
        if isinstance(results, str):
            results = json.loads(results)
    tally, queue = {}, []
    writer = shlex.split(args.ledger_writer)
    for r in results:
        v = r["verdict"]
        tally[v] = tally.get(v, 0) + 1
        if v == "supported":
            p = subprocess.run(writer + [r["name"], "supported"],
                               capture_output=True, text=True)
            if p.returncode != 0:
                sys.exit(f"sweep: ledger writer failed for {r['name']}: "
                         f"{p.stderr.strip()}")
        else:
            queue.append(r)
    # Findings are appended only after every ledger write succeeded, so a
    # writer failure aborts before this file grows and a re-run of the same
    # results file cannot duplicate rows already queued.
    with Path(args.findings).open("a", encoding="utf-8") as fq:
        for r in queue:
            fq.write(json.dumps({"round": args.label, **r}) + "\n")
    print(f"{args.label}: {json.dumps(tally)} — {len(queue)} queued")


def main():
    ap = argparse.ArgumentParser(prog="sweep.py")
    ap.add_argument("--manifest", default=".verify/manifest.json")
    ap.add_argument("--ledger", default="tests/claims.lock")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("plan")
    fr = sub.add_parser("frontier")
    fr.add_argument("label")
    fr.add_argument("splits", type=int, nargs="?", default=2)
    fr.add_argument("--probe", default="scripts/claim-probe.sh")
    fr.add_argument("--exclude")
    fr.add_argument("--redo", help="file of ledgered-but-stale names to re-dispatch")
    fr.add_argument("--outdir", default=".")
    fr.add_argument("--chunk", type=int, default=8)
    fr.add_argument("--agent-type", default="claim-referee")
    fr.add_argument("--model", default="opus")
    fr.add_argument("--effort", default="high")
    rec = sub.add_parser("record")
    rec.add_argument("results")
    rec.add_argument("label")
    rec.add_argument("--ledger-writer", required=True,
                     help="command prefix; NAME and the verdict are appended")
    rec.add_argument("--findings", default="findings.jsonl")
    args = ap.parse_args()
    {"plan": cmd_plan, "frontier": cmd_frontier, "record": cmd_record}[args.cmd](args)


if __name__ == "__main__":
    main()
