#!/usr/bin/env python3
"""Validate the structure and cross-references of every skill in this repo.

Runs in CI and as a pre-commit hook. Standard library only, so CI installs
nothing.

Checks, per skill directory under skills/:

  1. SKILL.md exists.
  2. Its YAML frontmatter parses and carries `name` and `description`.
  3. `name` matches the directory name.
  4. `description` is long enough to trigger reliably and short enough to stay
     in the metadata budget.
  5. Every relative path a skill mentions (references/foo.md, scripts/bar.py)
     resolves on disk. A skill pointing at a file that does not exist sends the
     agent looking for guidance that is not there. Paths prefixed with a
     sibling skill's name (lean-proving/references/foo.md) are resolved against
     that skill, which is how cross-skill pointers should be written.
  6. Every file under references/ is mentioned by some Markdown in the skill.
     An unreferenced reference file is never loaded, so it is dead weight.
  7. Every sibling skill named in backticks resolves to a real skill directory.
     Only lines that also contain the word "skill" are considered, since
     hyphenated backticked tokens are far more often filenames (lean-toolchain)
     than cross-references.

Exit status is 0 when everything passes, 1 otherwise.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"

# Bounds on the description field. Too short and the model cannot tell when the
# skill applies; too long and it crowds the always-resident metadata budget.
MIN_DESCRIPTION = 80
MAX_DESCRIPTION = 1500

# `references/` is checked whether or not the directory exists, because a skill
# pointing at references/foo.md when it has no references/ directory is exactly
# the broken case, and prose in these skills never uses that path for anything
# else. `scripts/` and `assets/` are deliberately NOT in this set: skills
# legitimately discuss a *user project's* scripts/ directory, so checking those
# unconditionally produces false positives. They are still checked when the
# skill actually has such a directory.
ALWAYS_CHECKED_SUBDIRS = frozenset({"references"})

# `references/foo.md`, `scripts/bar.py` — a relative path inside the skill.
PATH_REF = re.compile(r"`([a-zA-Z0-9_.-]+/[a-zA-Z0-9_./-]+\.(?:md|py|sh|json|toml))`")

# A backticked bare word that looks like a sibling skill name.
SKILL_REF = re.compile(r"`([a-z][a-z0-9]*(?:-[a-z0-9]+)+)`")


def parse_frontmatter(text: str) -> dict[str, str] | None:
    """Return the frontmatter mapping, or None when the block is missing.

    Deliberately minimal: skill frontmatter is flat `key: value` pairs, so a
    real YAML parser would be a dependency bought for nothing.
    """
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None

    fields: dict[str, str] = {}
    key = None
    for line in text[4:end].splitlines():
        if not line.strip():
            continue
        if line[0] in " \t" and key:  # continuation of a folded value
            fields[key] += " " + line.strip()
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        fields[key] = value.strip()
    return fields


def check_skill(skill_dir: Path, all_skill_names: set[str]) -> list[str]:
    """Return a list of problems found in one skill directory."""
    problems: list[str] = []
    rel = skill_dir.relative_to(REPO_ROOT)
    skill_md = skill_dir / "SKILL.md"

    if not skill_md.is_file():
        return [f"{rel}: no SKILL.md"]

    text = skill_md.read_text(encoding="utf-8")
    fields = parse_frontmatter(text)
    if fields is None:
        return [f"{rel}/SKILL.md: missing or malformed YAML frontmatter"]

    name = fields.get("name")
    description = fields.get("description")

    if not name:
        problems.append(f"{rel}/SKILL.md: frontmatter has no `name`")
    elif name != skill_dir.name:
        problems.append(
            f"{rel}/SKILL.md: name '{name}' does not match directory '{skill_dir.name}'"
        )

    if not description:
        problems.append(f"{rel}/SKILL.md: frontmatter has no `description`")
    elif not MIN_DESCRIPTION <= len(description) <= MAX_DESCRIPTION:
        problems.append(
            f"{rel}/SKILL.md: description is {len(description)} chars; "
            f"keep it between {MIN_DESCRIPTION} and {MAX_DESCRIPTION}"
        )

    markdown = sorted(skill_dir.rglob("*.md"))
    mentioned: set[str] = set()

    for md in markdown:
        body = md.read_text(encoding="utf-8")
        md_rel = md.relative_to(REPO_ROOT)

        for ref in PATH_REF.findall(body):
            first, _, rest = ref.partition("/")

            # A path prefixed with a sibling skill's name points across skills;
            # resolve it there so cross-references stay honest.
            if first in all_skill_names and first != skill_dir.name:
                if not (SKILLS_DIR / first / rest).is_file():
                    problems.append(
                        f"{md_rel}: references missing file '{ref}' in skill '{first}'"
                    )
                continue

            # Otherwise validate paths under references/ always, and paths
            # under a real subdirectory of this skill. Anything else is a path
            # into the user's own project and cannot be checked from here.
            if first not in ALWAYS_CHECKED_SUBDIRS and not (skill_dir / first).is_dir():
                continue
            mentioned.add(ref)
            if not (skill_dir / ref).is_file():
                problems.append(f"{md_rel}: references missing file '{ref}'")

        for line in body.splitlines():
            if "skill" not in line.lower():
                continue
            for ref in SKILL_REF.findall(line):
                if ref in all_skill_names:
                    continue
                if ref.startswith(("lean-", "lake-")):
                    problems.append(f"{md_rel}: names unknown sibling skill '{ref}'")

    refs_dir = skill_dir / "references"
    if refs_dir.is_dir():
        for ref_file in sorted(refs_dir.rglob("*")):
            if not ref_file.is_file():
                continue
            rel_ref = str(ref_file.relative_to(skill_dir))
            if rel_ref not in mentioned:
                problems.append(
                    f"{rel}/{rel_ref}: not mentioned by any Markdown in this "
                    f"skill, so it will never be loaded"
                )

    return problems


def main() -> int:
    if not SKILLS_DIR.is_dir():
        print(f"error: no skills/ directory at {SKILLS_DIR}", file=sys.stderr)
        return 1

    skill_dirs = sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir())
    if not skill_dirs:
        print("error: skills/ contains no skill directories", file=sys.stderr)
        return 1

    names = {p.name for p in skill_dirs}
    problems: list[str] = []
    for skill_dir in skill_dirs:
        problems.extend(check_skill(skill_dir, names))

    file_count = sum(len(list(p.rglob("*.md"))) for p in skill_dirs)
    print(f"checked {len(skill_dirs)} skills, {file_count} Markdown files")

    if problems:
        print(f"\n{len(problems)} problem(s):\n", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1

    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
