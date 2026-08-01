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


class RealRepo(unittest.TestCase):
    def test_this_repo_validates(self):
        script = Path(__file__).resolve().parent.parent / "validate_skills.py"
        p = subprocess.run([sys.executable, str(script)],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("all checks passed", p.stdout)


if __name__ == "__main__":
    unittest.main()
