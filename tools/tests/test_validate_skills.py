"""Tests for tools/validate_skills.py, on constructed skill trees.

Each check is exercised in both directions: a constructed defective skill
must produce the problem line, and the minimal clean skill must produce
none. The last test runs the validator over the real repository. Run:
    python3 -m unittest discover -s tools/tests
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import validate_skills as vs  # noqa: E402

# Long enough for the MIN_DESCRIPTION bound; content is irrelevant.
DESC = "x" * 100


class Tree(unittest.TestCase):
    """A throwaway repo root with a skills/ directory, patched into the
    validator's module globals for the duration of one test."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.skills = self.root / "skills"
        self.skills.mkdir()
        self._saved = (vs.REPO_ROOT, vs.SKILLS_DIR)
        vs.REPO_ROOT, vs.SKILLS_DIR = self.root, self.skills
        self.addCleanup(self._restore)

    def _restore(self):
        vs.REPO_ROOT, vs.SKILLS_DIR = self._saved

    def make_skill(self, name, skill_md, files=()):
        sdir = self.skills / name
        for rel, content in (("SKILL.md", skill_md),) + tuple(files):
            path = sdir / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return sdir

    def check(self, name, names=None):
        return vs.check_skill(self.skills / name, names or {name})


class TestStructure(Tree):
    def test_clean_skill_passes(self):
        self.make_skill("good",
                        f"---\nname: good\ndescription: {DESC}\n---\n"
                        "See `references/guide.md`.\n",
                        files=(("references/guide.md", "detail"),))
        self.assertEqual(self.check("good"), [])

    def test_missing_skill_md(self):
        (self.skills / "empty").mkdir()
        self.assertTrue(any("no SKILL.md" in p for p in self.check("empty")))

    def test_missing_frontmatter(self):
        self.make_skill("bare", "# No frontmatter\n")
        self.assertTrue(any("frontmatter" in p for p in self.check("bare")))

    def test_name_mismatch(self):
        self.make_skill("dirname",
                        f"---\nname: othername\ndescription: {DESC}\n---\n")
        self.assertTrue(any("does not match directory" in p
                            for p in self.check("dirname")))

    def test_description_too_short(self):
        self.make_skill("terse", "---\nname: terse\ndescription: brief\n---\n")
        self.assertTrue(any("description is 5 chars" in p
                            for p in self.check("terse")))

    def test_when_to_use_counts_toward_the_description_budget(self):
        # The runtime appends `when_to_use` to `description` in the skill
        # listing and truncates the pair. A description that fits alone can
        # still lose its tail once when_to_use is added, so the two are
        # measured together or not at all.
        long = "x" * (vs.MAX_DESCRIPTION - 100)
        self.make_skill("verbose",
                        f"---\nname: verbose\ndescription: {long}\n"
                        f"when_to_use: {'y' * 200}\n---\n")
        problems = self.check("verbose")
        self.assertTrue(any("description + when_to_use" in p for p in problems),
                        problems)

    def test_short_when_to_use_stays_within_budget(self):
        self.make_skill("concise",
                        f"---\nname: concise\ndescription: {DESC}\n"
                        "when_to_use: When the task is a concise one.\n---\n")
        self.assertEqual(self.check("concise"), [])

    def test_quoted_name_matches_directory(self):
        # The runtime's YAML parser sees `lake`, not `"lake"`.
        self.make_skill("quoted",
                        f'---\nname: "quoted"\ndescription: {DESC}\n---\n')
        self.assertEqual(self.check("quoted"), [])

    def test_folded_description_measured_without_indicator(self):
        # A `>-` block scalar: the indicator is not part of the value, and the
        # continuation lines are.
        self.make_skill("folded",
                        "---\nname: folded\ndescription: >-\n"
                        f"  {DESC}\n  {DESC}\n---\n")
        self.assertEqual(self.check("folded"), [])


class TestReferences(Tree):
    def test_missing_reference_file_fails(self):
        self.make_skill("dangling",
                        f"---\nname: dangling\ndescription: {DESC}\n---\n"
                        "See `references/gone.md`.\n")
        self.assertTrue(any("missing file 'references/gone.md'" in p
                            for p in self.check("dangling")))

    def test_orphan_reference_file_fails(self):
        self.make_skill("hoarder",
                        f"---\nname: hoarder\ndescription: {DESC}\n---\nBody.\n",
                        files=(("references/unused.md", "never loaded"),))
        self.assertTrue(any("never be loaded" in p for p in self.check("hoarder")))

    def test_project_path_outside_skill_is_ignored(self):
        # `scripts/foo.py` with no scripts/ directory here is a path into the
        # user's own project, not a broken reference.
        self.make_skill("talker",
                        f"---\nname: talker\ndescription: {DESC}\n---\n"
                        "Run `scripts/verify.sh` in your project.\n")
        self.assertEqual(self.check("talker"), [])

    def test_markdown_link_reference_checked(self):
        self.make_skill("linker",
                        f"---\nname: linker\ndescription: {DESC}\n---\n"
                        "See [the guide](references/gone.md).\n")
        self.assertTrue(any("missing file 'references/gone.md'" in p
                            for p in self.check("linker")))

    def test_non_md_extension_checked_both_ways(self):
        # A mentioned .lean reference file passes; a dangling one is flagged.
        self.make_skill("leanly",
                        f"---\nname: leanly\ndescription: {DESC}\n---\n"
                        "See `references/demo.lean` and `references/gone.lean`.\n",
                        files=(("references/demo.lean", "example : True := ⟨⟩"),))
        problems = self.check("leanly")
        self.assertTrue(any("missing file 'references/gone.lean'" in p
                            for p in problems))
        self.assertFalse(any("demo.lean" in p for p in problems))

    def test_self_mention_does_not_rescue_orphan(self):
        # A reference file whose only mention is its own is still unreachable.
        self.make_skill("navel",
                        f"---\nname: navel\ndescription: {DESC}\n---\nBody.\n",
                        files=(("references/orphan.md",
                                "This file: `references/orphan.md`"),))
        self.assertTrue(any("orphan.md" in p and "never be loaded" in p
                            for p in self.check("navel")))

    def test_mention_chain_reaches_second_reference(self):
        # SKILL.md -> a.md -> b.md: b is reachable, so no problem.
        self.make_skill("chain",
                        f"---\nname: chain\ndescription: {DESC}\n---\n"
                        "See `references/a.md`.\n",
                        files=(("references/a.md", "Then `references/b.md`."),
                               ("references/b.md", "leaf")))
        self.assertEqual(self.check("chain"), [])

    def test_own_name_prefixed_path_checked(self):
        # `self-skill/references/gone.md` written inside self-skill must be
        # resolved, not skipped.
        self.make_skill("self-skill",
                        f"---\nname: self-skill\ndescription: {DESC}\n---\n"
                        "See `self-skill/references/gone.md`.\n")
        self.assertTrue(any("missing file 'self-skill/references/gone.md'" in p
                            for p in self.check("self-skill")))


class TestCrossSkill(Tree):
    def two_skills(self, a_body, b_files=()):
        self.make_skill("alpha-skill",
                        f"---\nname: alpha-skill\ndescription: {DESC}\n---\n"
                        + a_body)
        self.make_skill("beta-skill",
                        f"---\nname: beta-skill\ndescription: {DESC}\n---\nBody.\n",
                        files=b_files)
        return {"alpha-skill", "beta-skill"}

    def test_cross_skill_path_resolves(self):
        names = self.two_skills(
            "See `beta-skill/references/deep.md`.\n",
            b_files=(("references/deep.md", "cited: `references/deep.md`"),))
        self.assertEqual(self.check("alpha-skill", names), [])

    def test_cross_skill_path_missing_fails(self):
        names = self.two_skills("See `beta-skill/references/absent.md`.\n")
        self.assertTrue(any("in skill 'beta-skill'" in p
                            for p in self.check("alpha-skill", names)))

    def test_unknown_lean_sibling_fails(self):
        self.make_skill("solo",
                        f"---\nname: solo\ndescription: {DESC}\n---\n"
                        "Sibling skills: `lean-ghost` for nothing.\n")
        self.assertTrue(any("unknown sibling skill 'lean-ghost'" in p
                            for p in self.check("solo")))

    def test_known_sibling_passes(self):
        names = self.two_skills("The `beta-skill` skill covers the rest.\n")
        self.assertEqual(self.check("alpha-skill", names), [])

    def test_lean_toolchain_not_a_sibling(self):
        # A real ecosystem filename on a line containing "skill" is not a
        # cross-reference.
        self.make_skill("solo",
                        f"---\nname: solo\ndescription: {DESC}\n---\n"
                        "This skill never edits `lean-toolchain`.\n")
        self.assertEqual(self.check("solo"), [])


class TestReadme(Tree):
    def readme(self, text):
        (self.root / "README.md").write_text(text, encoding="utf-8")

    def test_missing_skill_flagged(self):
        self.readme("| `listed` | x | y |\n")
        problems = vs.check_readme({"listed", "unlisted"})
        self.assertTrue(any("'unlisted' is not mentioned" in p for p in problems))

    def test_stale_row_flagged(self):
        self.readme("| `ghost` | x | y |\n")
        problems = vs.check_readme({"ghost", "real"})
        self.assertTrue(any("'real' is not mentioned" in p for p in problems))
        self.readme("| `ghost` | x | y |\n| `real` | x | y |\n")
        problems = vs.check_readme({"real"})
        self.assertTrue(any("table row names 'ghost'" in p for p in problems))

    def test_matching_table_passes(self):
        self.readme("| `real` | x | y |\n")
        self.assertEqual(vs.check_readme({"real"}), [])


class RealRepo(unittest.TestCase):
    def test_this_repo_validates(self):
        script = Path(__file__).resolve().parent.parent / "validate_skills.py"
        p = subprocess.run([sys.executable, str(script)],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("all checks passed", p.stdout)


if __name__ == "__main__":
    unittest.main()
