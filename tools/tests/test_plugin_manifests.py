"""Tests for the Claude Code plugin manifests under .claude-plugin/. Run:
    python3 -m unittest discover -s tools/tests

These encode distribution rules that are invisible from here: every one of them
passes on a machine that never installs the plugin, and fails only for someone
downstream. The one that earned the file is the version pin.

Claude Code resolves a plugin's version from `plugin.json`, then the
marketplace entry, then the source commit SHA, and skips the update when the
resolved version matches what a user already has. A literal `"version":
"1.0.0"` that nobody remembers to bump therefore freezes every existing
install, silently, no matter how many commits land — and nothing local reports
it, because locally there is no install to freeze. This repository carried that
pin in both manifests for fourteen commits. Omitting the field makes each
commit its own version, which is what an actively-developed repository with no
release channels wants. If that ever changes and releases get cut, the pin
belongs in `plugin.json` alone (it wins over the marketplace entry without
warning) and must be bumped per release.

    https://code.claude.com/docs/en/plugin-marketplaces#version-resolution-and-release-channels
"""

import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import validate_skills as vs  # noqa: E402

MARKETPLACE = vs.REPO_ROOT / ".claude-plugin" / "marketplace.json"
PLUGIN = vs.REPO_ROOT / ".claude-plugin" / "plugin.json"
README = vs.REPO_ROOT / "README.md"

KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# Names reserved for Anthropic. A third-party marketplace using one stops
# loading entirely and reports as registered from an untrusted source. Claude
# Code re-checks the list on every load, not only when a marketplace is added,
# so a name that was fine when it was chosen can be reserved later.
RESERVED = frozenset({
    "claude-code-marketplace", "claude-code-plugins", "claude-plugins-official",
    "claude-plugins-community", "claude-community", "anthropic-marketplace",
    "anthropic-plugins", "agent-skills", "anthropic-agent-skills",
    "knowledge-work-plugins", "life-sciences", "claude-for-legal",
    "claude-for-financial-services", "financial-services-plugins",
    "first-party-plugins", "healthcare",
})

PINNED = (
    "pins the plugin: Claude Code compares the resolved version against what a "
    "user already has and skips the update when they match, so pushing commits "
    "without bumping this string reaches nobody. Omit it and each commit "
    "becomes its own version."
)


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


class Marketplace(unittest.TestCase):
    def setUp(self):
        self.data = load(MARKETPLACE)
        self.entries = self.data.get("plugins", [])

    def test_required_fields(self):
        self.assertTrue(self.data.get("name"), "marketplace needs a `name`")
        self.assertTrue(self.data.get("owner", {}).get("name"), "owner needs a `name`")
        self.assertTrue(self.entries, "marketplace needs at least one plugin entry")

    def test_name_is_kebab_case_and_unreserved(self):
        name = self.data["name"]
        self.assertRegex(name, KEBAB, f"marketplace name `{name}` must be kebab-case")
        self.assertNotIn(name, RESERVED, f"`{name}` is reserved for Anthropic")

    def test_entries_are_well_formed(self):
        for entry in self.entries:
            name = entry.get("name", "")
            self.assertRegex(name, KEBAB, f"plugin name `{name}` must be kebab-case")
            source = entry.get("source")
            self.assertTrue(source, f"{name}: needs a `source`")
            if isinstance(source, str):
                self.assertTrue(
                    source.startswith("./"),
                    f"{name}: relative source `{source}` must start with ./",
                )
                self.assertTrue(
                    (vs.REPO_ROOT / source).is_dir(),
                    f"{name}: source `{source}` does not resolve",
                )

    def test_no_entry_pins_a_version(self):
        for entry in self.entries:
            self.assertNotIn("version", entry, f"{entry.get('name')}: `version` {PINNED}")

    def test_metadata_holds_only_plugin_root(self):
        # `description` and `version` are top-level marketplace fields.
        # `metadata` still accepts those two for backward compatibility, but
        # `pluginRoot` is the only key documented as belonging there, so
        # anything else under `metadata` is silently ignored. Keeping the block
        # empty means a misfiled key surfaces here instead of vanishing.
        for key in self.data.get("metadata", {}):
            self.assertEqual(key, "pluginRoot", f"metadata.{key} is not a documented field")


class Plugin(unittest.TestCase):
    def setUp(self):
        self.data = load(PLUGIN)

    def test_name_matches_the_marketplace_entry(self):
        names = [e.get("name") for e in load(MARKETPLACE).get("plugins", [])]
        self.assertIn(
            self.data.get("name"),
            names,
            "plugin.json `name` must match a marketplace entry; users install by that name",
        )

    def test_does_not_pin_a_version(self):
        # plugin.json wins over the marketplace entry without warning, so a
        # stale value here masks anything set there.
        self.assertNotIn("version", self.data, f"plugin.json `version` {PINNED}")

    def test_license_is_backed_by_a_license_file(self):
        if self.data.get("license"):
            self.assertTrue(
                (vs.REPO_ROOT / "LICENSE").is_file(),
                "plugin.json declares a license but the repo ships no LICENSE",
            )

    def test_skills_are_auto_discovered(self):
        # No `skills` path is declared, so Claude Code discovers skills/ in the
        # plugin root. Declaring one is only for non-standard layouts, and it
        # would then have to be kept in step with the tree by hand.
        self.assertNotIn("skills", self.data)
        self.assertTrue((vs.REPO_ROOT / "skills").is_dir())

    def test_description_names_the_domains_not_the_skill_list(self):
        # A description that enumerates the current skills dates itself the
        # next time one is added. Name domains instead. This is a floor, not a
        # proof: it only catches the description going stale by omission.
        description = self.data.get("description", "")
        self.assertTrue(description, "plugin.json needs a `description`")
        self.assertIn("Lean", description)
        self.assertIn("Mathlib", description)


class Readme(unittest.TestCase):
    """The install path a reader copies has to work for a reader without an
    SSH key. GitHub `owner/repo` shorthand clones over SSH by default, so a
    README offering only the shorthand fails for exactly the people who have
    not installed a plugin before."""

    def setUp(self):
        self.text = README.read_text(encoding="utf-8")

    def test_documents_an_https_install_path(self):
        self.assertTrue(
            "CLAUDE_CODE_PLUGIN_PREFER_HTTPS" in self.text
            or "https://github.com/matt-w-horn/lean-skills.git" in self.text,
            "README must offer an HTTPS clone path: the owner/repo shorthand "
            "clones over SSH and fails without a key in ssh-agent",
        )

    def test_documents_how_to_pull_later_changes(self):
        for command in ("/plugin marketplace update", "/plugin update"):
            self.assertIn(
                command,
                self.text,
                f"README must document `{command}`; a marketplace refresh alone "
                f"does not update installed plugins",
            )


if __name__ == "__main__":
    unittest.main()
