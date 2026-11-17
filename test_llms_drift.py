"""Doc-drift guard for llms.txt.

`llms.txt` is the file an AI agent reads before deciding whether to use this
library. It is also prose, so nothing in the build has ever checked it. That
is how it drifted four minor versions while every test stayed green.

The 2026-11-17 audit found:

  - `Version: 0.3.0` against a `pyproject.toml` at 0.7.2
  - `Language: Python (3.8+)` and "Python 3.8 - 3.13 confirmed" while the
    reader was told nothing about the async validator, the OpenAPI export or
    the JSON Schema exporter added in 0.4.0 - 0.7.0
  - a public API list missing `Schema`, `AsyncValidator`, `to_json_schema`,
    `to_openapi_schema` and `from_json_schema`

A version header is cheap to assert. The API list is the part that matters:
a reader told the library has five field types will not look for `Decimal_`,
and the library looks unusable for the job it was built for.

These tests fail on the stale file and pass on the corrected one.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import tiny_validator as tv

ROOT = Path(__file__).parent
LLMS = ROOT / "llms.txt"
PYPROJECT = ROOT / "pyproject.toml"

# Every name a reader may reasonably look for. Each is exported by
# `tiny_validator` today; `test_listed_api_names_are_real` proves it rather
# than trusting this list.
DOCUMENTED_API = [
    "validate",
    "Schema",
    "PartialSchema",
    "from_json_schema",
    "to_json_schema",
    "to_openapi_schema",
    "http_error_response",
    "AsyncValidator",
    "AsyncField",
    "ValidationError",
]

DOCUMENTED_FIELDS = [
    "String", "Integer", "Float", "Boolean", "Any", "List", "Dict_",
    "Email", "Url", "Uuid", "Date", "DateTime", "Decimal_", "Json",
    "IP", "Slug", "Regex", "HexColor",
]


def _llms_text() -> str:
    assert LLMS.is_file(), "llms.txt is missing; an agent has nothing to read"
    return LLMS.read_text(encoding="utf-8")


def _pyproject_version() -> str:
    m = re.search(r'^version\s*=\s*"([^"]+)"', PYPROJECT.read_text(encoding="utf-8"), re.M)
    assert m, "pyproject.toml has no [project].version"
    return m.group(1)


def _pyproject_python_floor() -> str:
    m = re.search(r'^requires-python\s*=\s*"([^"]+)"', PYPROJECT.read_text(encoding="utf-8"), re.M)
    assert m, "pyproject.toml has no requires-python"
    # ">=3.8" -> "3.8"
    return m.group(1).lstrip(">=~^ ")


def test_version_header_matches_pyproject():
    text = _llms_text()
    m = re.search(r"^- Version:\s*(\S+)\s*$", text, re.M)
    assert m, "llms.txt has no '- Version:' line"
    assert m.group(1) == _pyproject_version(), (
        f"llms.txt advertises {m.group(1)}, pyproject.toml says {_pyproject_version()}"
    )


def test_python_floor_matches_pyproject():
    text = _llms_text()
    m = re.search(r"^- Language:\s*Python \(([^)]+)\)", text, re.M)
    assert m, "llms.txt has no '- Language: Python (...)' line"
    claim = m.group(1).rstrip("+")
    assert claim == _pyproject_python_floor(), (
        f"llms.txt claims Python {m.group(1)}, requires-python is "
        f"{_pyproject_python_floor()}"
    )


def test_runtime_version_matches_package():
    """The header, pyproject and the module must agree with each other."""
    text = _llms_text()
    header = re.search(r"^- Version:\s*(\S+)\s*$", text, re.M).group(1)
    assert header == tv.__version__ == _pyproject_version()


@pytest.mark.parametrize("name", DOCUMENTED_API)
def test_documented_api_present(name):
    assert re.search(rf"\b{re.escape(name)}\b", _llms_text()), (
        f"llms.txt never mentions `{name}`, which this version exports"
    )


@pytest.mark.parametrize("name", DOCUMENTED_FIELDS)
def test_documented_field_present(name):
    assert re.search(rf"\b{re.escape(name)}\b", _llms_text()), (
        f"llms.txt never mentions field type `{name}`"
    )


@pytest.mark.parametrize("name", DOCUMENTED_API + DOCUMENTED_FIELDS)
def test_listed_api_names_are_real(name):
    """The reverse direction: do not document what does not exist."""
    assert hasattr(tv, name), (
        f"llms.txt documents `{name}` but `tiny_validator` does not export it"
    )


def test_no_dangling_version_claims():
    """Every `X.Y.Z` mentioned must exist in this or an older release."""
    text = _llms_text()
    # Split on the changelog header; the changelog legitimately names old versions.
    body = text.split("## Changelog", 1)[0]
    versions = set(re.findall(r"\bv?(\d+\.\d+\.\d+)\b", body))
    current = tuple(int(p) for p in _pyproject_version().split("."))
    for v in versions:
        parts = tuple(int(p) for p in v.split("."))
        assert parts <= current, (
            f"llms.txt body claims version {v}, newer than the published {tv.__version__}"
        )
