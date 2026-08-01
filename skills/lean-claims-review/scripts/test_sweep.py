"""Tests for sweep.py, on constructed fixtures.

Every gate is exercised in both directions: the frontier must exclude
what it should (unpassed deps, excluded names, already-passed rows) and
include what it should; record must write the ledger exactly for
`supported` and queue everything else; the protocol builder must fail
loudly on a reference file with no fenced block. Run:
    python3 -m unittest discover -s skills/lean-claims-review/scripts
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import sweep

MANIFEST = [
    {"name": "Lib.base", "kind": "theorem", "type": "T0", "doc": "d0",
     "consumers": ["Lib.mid", "Lib.leaf"]},
    {"name": "Lib.mid", "kind": "theorem", "type": "T1", "doc": "d1",
     "consumers": ["Lib.leaf"]},
    {"name": "Lib.leaf", "kind": "def", "type": "T2", "doc": "d2",
     "consumers": []},
    {"name": "Lib.lone", "kind": "theorem", "type": "T3", "doc": "d3",
     "consumers": []},
]

LEDGER = """-- comment line
mode: advisory

Lib.base | h1 | h2 | h3 | supported | 2026-01-01
Lib.lone | h1 | h2 | h3 | accepted | 2026-01-01 | maintainer note
"""


class Fixture(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.root = Path(self.dir.name)
        self.manifest = self.root / "manifest.json"
        self.manifest.write_text(json.dumps(MANIFEST))
        self.ledger = self.root / "claims.lock"
        self.ledger.write_text(LEDGER)

    def tearDown(self):
        self.dir.cleanup()


class TestLedger(Fixture):
    def test_passed_includes_supported_and_accepted(self):
        self.assertEqual(sweep.ledger_passed(self.ledger),
                         {"Lib.base", "Lib.lone"})

    def test_missing_ledger_is_empty(self):
        self.assertEqual(sweep.ledger_passed(self.root / "absent"), set())

    def test_non_passing_verdict_not_counted(self):
        self.ledger.write_text(
            "Lib.base | h1 | h2 | h3 | prose-overclaims | 2026-01-01\n")
        self.assertEqual(sweep.ledger_passed(self.ledger), set())


class TestDeps(Fixture):
    def test_edges_are_inverted_consumers(self):
        rows, deps = sweep.load_manifest(self.manifest)
        self.assertEqual(sorted(deps["Lib.leaf"]), ["Lib.base", "Lib.mid"])
        self.assertEqual(deps["Lib.base"], [])

    def test_cyclic_manifest_fails_loudly(self):
        # Two rows consuming each other: frontier would otherwise report
        # them "waiting on deps" forever and plan would print wrong depths.
        m = self.root / "cyclic.json"
        m.write_text(json.dumps([
            {"name": "A", "kind": "theorem", "type": "T", "doc": "d",
             "consumers": ["B"]},
            {"name": "B", "kind": "theorem", "type": "T", "doc": "d",
             "consumers": ["A"]},
        ]))
        with self.assertRaises(SystemExit) as ctx:
            sweep.load_manifest(m)
        self.assertIn("cycle", str(ctx.exception))

    def test_namespace_parent_is_a_dep(self):
        # `S.f` depends on `S` even with no consumers edge — context hashes
        # cover prefix parents, so wave order and prompts must too.
        m = self.root / "m2.json"
        m.write_text(json.dumps(MANIFEST + [
            {"name": "Lib.base.f", "kind": "theorem", "type": "T",
             "doc": "df", "consumers": []}]))
        rows, deps = sweep.load_manifest(m)
        self.assertIn("Lib.base", deps["Lib.base.f"])
        block = sweep.pair_block("Lib.base.f", rows, deps)
        self.assertIn("Lib.base: d0", block)


class TestPairBlock(Fixture):
    def test_block_carries_dep_docstrings(self):
        rows, deps = sweep.load_manifest(self.manifest)
        block = sweep.pair_block("Lib.leaf", rows, deps)
        self.assertIn("Declaration: Lib.leaf (def)", block)
        self.assertIn("Lib.base: d0", block)
        self.assertIn("Lib.mid: d1", block)

    def test_no_dep_section_when_no_deps(self):
        rows, deps = sweep.load_manifest(self.manifest)
        self.assertNotIn("Verified dependency docstrings",
                         sweep.pair_block("Lib.base", rows, deps))


class TestProtocol(unittest.TestCase):
    def test_probe_placeholder_filled_and_trailer_appended(self):
        text = sweep.protocol_text("my/probe.sh")
        self.assertIn("my/probe.sh", text)
        self.assertNotIn("[probe command]", text)
        self.assertTrue(text.endswith(sweep.TRAILER))

    def test_missing_fence_fails_loudly(self):
        real = sweep.SKILL
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "references").mkdir()
            (Path(d) / "references" / "referee-protocol.md").write_text("no fence")
            sweep.SKILL = Path(d)
            try:
                with self.assertRaises(SystemExit):
                    sweep.protocol_text("p")
            finally:
                sweep.SKILL = real


def run_cli(args, cwd):
    return subprocess.run(
        [sys.executable, str(Path(__file__).parent / "sweep.py")] + args,
        capture_output=True, text=True, cwd=cwd)


class TestFrontier(Fixture):
    def args(self, extra):
        return (["--manifest", str(self.manifest), "--ledger", str(self.ledger),
                 "frontier", "r1"] + extra + ["--outdir", str(self.root)])

    def test_gating(self):
        # Lib.base passed, Lib.lone passed -> ready: Lib.mid (dep base
        # passed); waiting: Lib.leaf (dep mid unverdicted).
        p = run_cli(self.args(["1"]), self.root)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("1 ready", p.stdout)
        self.assertIn("1 waiting", p.stdout)
        script = (self.root / "claims-r1-a.js").read_text()
        self.assertIn("Lib.mid", script)
        self.assertNotIn("Lib.leaf", script)

    def test_exclude_removes_pair(self):
        ex = self.root / "exclude.txt"
        ex.write_text("Lib.mid\n")
        p = run_cli(self.args(["1", "--exclude", str(ex)]), self.root)
        self.assertIn("0 ready", p.stdout)
        self.assertIn("1 excluded", p.stdout)

    def test_splits_partition_without_loss(self):
        self.ledger.write_text("mode: advisory\n")  # nothing passed
        p = run_cli(self.args(["2"]), self.root)  # ready: base, lone
        self.assertEqual(p.returncode, 0, p.stderr)
        a = (self.root / "claims-r1-a.js").read_text()
        b = (self.root / "claims-r1-b.js").read_text()
        names = {"Lib.base", "Lib.lone"}
        found = {n for n in names if n in a} | {n for n in names if n in b}
        self.assertEqual(found, names)
        self.assertFalse({n for n in names if n in a} & {n for n in names if n in b})

    def test_redo_reenters_ledgered_name(self):
        redo = self.root / "redo.txt"
        redo.write_text("Lib.base\n")
        p = run_cli(self.args(["1", "--redo", str(redo)]), self.root)
        self.assertEqual(p.returncode, 0, p.stderr)
        script = (self.root / "claims-r1-a.js").read_text()
        self.assertIn("Lib.base", script)  # re-dispatched despite ledger

    def test_scripts_carry_config(self):
        # Values differ from every argparse default, so a dropped flag fails.
        p = run_cli(self.args(["1", "--model", "sonnet", "--effort", "medium",
                               "--chunk", "4"]), self.root)
        self.assertEqual(p.returncode, 0, p.stderr)
        script = (self.root / "claims-r1-a.js").read_text()
        self.assertIn('model: "sonnet"', script)
        self.assertIn('effort: "medium"', script)
        self.assertIn("const CHUNK = 4", script)

    def test_missing_exclude_file_fails(self):
        p = run_cli(self.args(["1", "--exclude",
                               str(self.root / "typo.txt")]), self.root)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("--exclude file not found", p.stderr)

    def test_missing_redo_file_fails(self):
        p = run_cli(self.args(["1", "--redo",
                               str(self.root / "typo.txt")]), self.root)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("--redo file not found", p.stderr)

    def test_splits_beyond_alphabet_fails(self):
        p = run_cli((["--manifest", str(self.manifest), "--ledger",
                      str(self.ledger), "frontier", "r1", "27",
                      "--outdir", str(self.root)]), self.root)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("splits", p.stderr)

    def test_label_with_quote_rejected(self):
        # The label lands inside single-quoted JS; a quote would emit N
        # syntactically broken workflow scripts.
        p = run_cli((["--manifest", str(self.manifest), "--ledger",
                      str(self.ledger), "frontier", "r1'x", "1",
                      "--outdir", str(self.root)]), self.root)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("label", p.stderr)


class TestRecord(Fixture):
    def setUp(self):
        super().setUp()
        # A fake ledger writer that logs its argv and fails on demand.
        self.log = self.root / "writer.log"
        self.writer = self.root / "writer.py"
        self.writer.write_text(
            "import sys, pathlib\n"
            f"pathlib.Path({str(self.log)!r}).open('a').write(' '.join(sys.argv[1:]) + '\\n')\n"
            "sys.exit(1 if 'FAIL' in sys.argv[1] else 0)\n")
        self.findings = self.root / "findings.jsonl"

    def record(self, results):
        rf = self.root / "results.json"
        rf.write_text(json.dumps(results))
        return run_cli(
            ["record", str(rf), "rX",
             "--ledger-writer", f"{sys.executable} {self.writer}",
             "--findings", str(self.findings)], self.root)

    def test_supported_hits_writer_rest_queue(self):
        p = self.record([
            {"name": "Lib.base", "verdict": "supported", "text": ""},
            {"name": "Lib.mid", "verdict": "prose-overclaims", "text": "ev"},
        ])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(self.log.read_text(), "Lib.base supported\n")
        row = json.loads(self.findings.read_text())
        self.assertEqual((row["name"], row["round"]), ("Lib.mid", "rX"))

    def test_writer_failure_aborts(self):
        # The finding sorts before the failing writer call; the abort must
        # leave the findings file unwritten so a re-run cannot duplicate rows.
        p = self.record([
            {"name": "Lib.mid", "verdict": "prose-overclaims", "text": "ev"},
            {"name": "FAILNAME", "verdict": "supported", "text": ""},
        ])
        self.assertNotEqual(p.returncode, 0)
        self.assertFalse(self.findings.exists())

    def test_wrapper_without_result_key_fails(self):
        rf = self.root / "resultless.json"
        rf.write_text(json.dumps({"summary": "s", "error": "timeout"}))
        p = run_cli(["record", str(rf), "rX",
                     "--ledger-writer", f"{sys.executable} {self.writer}",
                     "--findings", str(self.findings)], self.root)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("no 'result' key", p.stderr)

    def test_task_output_wrapper_unwrapped(self):
        rf = self.root / "wrapped.json"
        rf.write_text(json.dumps(
            {"summary": "s", "result": json.dumps(
                [{"name": "Lib.base", "verdict": "supported", "text": ""}])}))
        p = run_cli(["record", str(rf), "rX",
                     "--ledger-writer", f"{sys.executable} {self.writer}",
                     "--findings", str(self.findings)], self.root)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("supported", self.log.read_text())


if __name__ == "__main__":
    unittest.main()
