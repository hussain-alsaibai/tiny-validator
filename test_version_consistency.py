"""The version is stated in three places; they must agree.

A pyproject that says 0.7.0 while `__version__` says 0.6.0 produces a wheel
whose metadata and whose runtime disagree, and the README badge disagrees with
both. This test exists because that is exactly what happened in the 0.7.0
bump.
"""

import os
import re
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))


def read(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as fh:
        return fh.read()


def pyproject_version():
    return re.search(r'^version\s*=\s*"([^"]+)"', read("pyproject.toml"), re.M).group(1)


def module_version():
    return re.search(r'^__version__\s*=\s*"([^"]+)"', read("tiny_validator.py"), re.M).group(1)


def readme_badge_version():
    m = re.search(r"badge/version-([0-9][^-]*)-blue", read("README.md"))
    return m.group(1) if m else None


def changelog_has(version):
    return re.search(r"^## \[%s\]" % re.escape(version), read("CHANGELOG.md"), re.M) is not None


class TestVersionConsistency(unittest.TestCase):
    def test_pyproject_matches_module(self):
        self.assertEqual(pyproject_version(), module_version())

    def test_readme_badge_matches(self):
        self.assertEqual(readme_badge_version(), pyproject_version())

    def test_changelog_documents_the_version(self):
        self.assertTrue(
            changelog_has(pyproject_version()),
            "CHANGELOG.md has no entry for %s" % pyproject_version(),
        )


if __name__ == "__main__":
    unittest.main()
