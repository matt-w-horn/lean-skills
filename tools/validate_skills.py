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
  5. Every relative path a skill mentions in backticks or as a Markdown link
     target resolves on disk, when it is checkable from here: paths under
     references/ always, paths under a subdirectory this skill actually has
     (scripts/, assets/), and paths prefixed with a skill's name
     (lean-proving/references/foo.md), which resolve against that skill —
     the skill's own name included. Anything else is a path into the user's
     project and is skipped.
  6. Every file under references/ is reachable from SKILL.md through those
     mentions. A reference file no chain from SKILL.md mentions is never
     loaded, so it is dead weight; a mention inside an unreachable file does
     not count.
  7. Backticked names shaped like sibling skills are flagged when no such
     skill exists. Only lines that also contain the word "skill" are
     considered, and only names starting with `lean-` or `lake-`, since other
     hyphenated backticked tokens are far more often filenames. Known
     non-skill filenames (`lean-toolchain`) are exempt.

Repo-level check: every skill appears in README.md's skill table (as a
backticked name), and every backticked table row names a real skill.

Exit status is 0 when everything passes, 1 otherwise.
"""

from __future__ import annotations

import re
import sys
from collections import deque
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

# `references/foo.md`, `scripts/bar.py` — a relative path with any extension.
# The first path component decides below whether the mention is checkable, so
# the extension is not restricted here: the orphan check walks references/
# with rglob("*"), and the two checks must recognize the same set of files.
PATH_REF = re.compile(r"`([a-zA-Z0-9_.-]+/[a-zA-Z0-9_./-]+\.[a-z0-9]+)`")

# The same path as a Markdown link target: `[text](references/foo.md)`.
# URLs never match: the character class has no colon.
LINK_REF = re.compile(r"\]\(([a-zA-Z0-9_.-]+/[a-zA-Z0-9_./-]+\.[a-z0-9]+)\)")

# A backticked bare word that looks like a sibling skill name.
SKILL_REF = re.compile(r"`([a-z][a-z0-9]*(?:-[a-z0-9]+)+)`")

# Real files in the Lean ecosystem that match the sibling-skill shape.
NOT_SKILLS = frozenset({"lean-toolchain"})


def parse_frontmatter(text: str) -> dict[str, str] | None:
    """Return the frontmatter mapping, or None when the block is missing.

    Deliberately minimal: skill frontmatter is flat `key: value` pairs, so a
    real YAML parser would be a dependency bought for nothing. Values may be
    quoted or written as `>`/`|` block scalars with indented continuation
    lines; both forms yield the value the runtime's YAML parser would see.
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
            fields[key] = (fields[key] + " " + line.strip()).strip()
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value in {">", ">-", ">+", "|", "|-", "|+"}:
            value = ""  # block scalar: the continuation lines carry the text
        elif len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        fields[key] = value
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
    # Local paths each Markdown file mentions, keyed by the file's path
    # relative to the skill root. Feeds the reachability walk below.
    mentions: dict[str, set[str]] = {}

    for md in markdown:
        body = text if md == skill_md else md.read_text(encoding="utf-8")
        md_rel = md.relative_to(REPO_ROOT)
        md_key = str(md.relative_to(skill_dir))
        mentions.setdefault(md_key, set())

        for ref in PATH_REF.findall(body) + LINK_REF.findall(body):
            first, _, rest = ref.partition("/")

            # A path prefixed with a skill's name resolves against that skill
            # (the skill's own name included), so cross-references stay honest.
            if first in all_skill_names:
                if first == skill_dir.name:
                    mentions[md_key].add(rest)
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
            mentions[md_key].add(ref)
            if not (skill_dir / ref).is_file():
                problems.append(f"{md_rel}: references missing file '{ref}'")

        for line in body.splitlines():
            if "skill" not in line.lower():
                continue
            for ref in SKILL_REF.findall(line):
                if ref in all_skill_names or ref in NOT_SKILLS:
                    continue
                if ref.startswith(("lean-", "lake-")):
                    problems.append(f"{md_rel}: names unknown sibling skill '{ref}'")

    refs_dir = skill_dir / "references"
    if refs_dir.is_dir():
        # Walk mentions from SKILL.md: a reference file counts as loaded only
        # when a chain of mentions from SKILL.md reaches it. A file that only
        # mentions itself, or is mentioned only by an unreachable file, is
        # still dead weight.
        reachable: set[str] = set()
        queue = deque(["SKILL.md"])
        seen = {"SKILL.md"}
        while queue:
            for ref in mentions.get(queue.popleft(), ()):
                reachable.add(ref)
                if ref.endswith(".md") and ref in mentions and ref not in seen:
                    seen.add(ref)
                    queue.append(ref)

        for ref_file in sorted(refs_dir.rglob("*")):
            if not ref_file.is_file():
                continue
            rel_ref = str(ref_file.relative_to(skill_dir))
            if rel_ref not in reachable:
                problems.append(
                    f"{rel}/{rel_ref}: not reachable from SKILL.md through any "
                    f"mention, so it will never be loaded"
                )

    return problems


def check_readme(names: set[str]) -> list[str]:
    """The README's skill table and the skills/ directory must agree."""
    readme = REPO_ROOT / "README.md"
    if not readme.is_file():
        return ["README.md: missing"]
    text = readme.read_text(encoding="utf-8")

    problems = [
        f"README.md: skill '{name}' is not mentioned (add it to the skill table)"
        for name in sorted(names)
        if f"`{name}`" not in text
    ]
    for row_name in re.findall(r"^\| `([a-z0-9-]+)` \|", text, re.MULTILINE):
        if row_name not in names:
            problems.append(
                f"README.md: table row names '{row_name}', which is not a "
                f"skill directory"
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
    problems.extend(check_readme(names))

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
