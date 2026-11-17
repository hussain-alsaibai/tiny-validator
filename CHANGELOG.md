# Changelog

All notable changes to tiny-validator are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Fixed (docs)
- **`llms.txt` described a four-version-old library.** It advertised
  `Version: 0.3.0` against a package at 0.7.2, omitted `Schema`,
  `AsyncValidator`, `AsyncField`, `to_json_schema`, `to_openapi_schema`,
  `from_json_schema` and `http_error_response`, and listed nine of the
  eighteen field types. A reader was told the library had five field types
  and no export path — the two features that justify choosing it.
- The Python floor claim and the public API list are now covered by
  `test_llms_drift.py` (60 tests), which fails 22 times against the previous
  file. It also checks the reverse direction: every documented name must
  actually be exported.

### Changed
- CI lists every test file explicitly; `test_v070_export_roundtrip.py` was
  never added to it, so the 14 round-trip tests that justify 0.7.2 had never
  run in CI. Both it and the new drift test are now named.

## [0.7.2] - 2026-11-13

### Fixed
- **`Slug`, `Regex` and `HexColor` exported as a bare `{"type": "string"}`.**
  v0.6.0 moved constraint recovery from message-parsing to construction-time
  recording, and v0.7.1 fixed `required` the same way, but these three field
  types build their regex inline without calling `set_constraint`. The exported
  document therefore permitted `"Not A Slug"`, which the Schema itself rejects.
  All three now record `pattern`.
- **`IP` exported no `format` at all.** `IP(version=4)` and `IP(version=6)` now
  export `format: ipv4` / `format: ipv6`. An unversioned `IP()` exports a plain
  string *without* a format tag on purpose: no standard JSON Schema format
  covers both families, and a tag no consumer validates is worse than none.
- **`from_json_schema()` ignored `format: ipv4` / `ipv6`.** The importer built a
  plain `String`, so a document exported from `IP(version=4)` round-tripped into
  a validator that accepted `999.1.1.1` and `::1`. Both formats now import as
  the matching `IP`.

### Added
- `test_v070_export_roundtrip.py` — 14 tests, each an export/import/reject
  cycle over the public API. Ten fail against v0.7.1; the other four guard
  `enum`, bounds, `additionalProperties` and nested `items` so the
  v0.6.0/v0.7.1 behaviour cannot regress in the same area.

## [0.7.1] - 2026-11-12

### Fixed

- **`to_json_schema()` exported a schema that rejects valid payloads.** The
  exporter decided membership of `required` from `field.required` alone, but
  `validate()` only reports a missing field when `required and default is ...`.
  A field written as `String(default="anon")` — or `List(String(), default=[])`
  — is optional at runtime and was still emitted in `required`. The result was
  a JSON Schema that refused data the library accepts, which is the worst
  direction for a bug: it breaks every OpenAPI 3.1 document and MCP tool
  definition generated from the export, and the failure surfaces in the
  consumer, not here.

  ```python
  s = Schema({"tags": fields.List(fields.String(), default=[])})
  s.validate({})        # -> []            (accepted)
  to_json_schema(s)     # -> required: ["tags"]
  jsonschema.validate({}, to_json_schema(s))
  # jsonschema.ValidationError: 'tags' is a required property
  ```

  A field is now required only when `field.required and field.default is ...`,
  matching `validate()` exactly.

### Added

- `test_export_agrees_with_validate` — a parametrised cross-check that runs
  the same payload through the library and through `jsonschema` against the
  exported schema and asserts they agree. Skipped when `jsonschema` is absent,
  so the zero-dependency test run is unaffected.
- 5 further regression tests for the required/optional matrix. Three of the
  new tests fail against the pre-fix exporter (verified in a scratch clone).

## [0.7.0] - 2026-11-05

### Added
- **`rules.py` - cross-field validation rules and computed fields.** `Schema` validates one field at a time and therefore cannot express "`end` must be after `start`". `Rule(check, message, path=...)` runs a callable over the *validated* mapping and returns a failure when it returns `False` or raises `CrossFieldError` / `AssertionError`; `check_rules(data, rules)` returns failures in the same `{"path", "message"}` shape a `Schema` returns, so the two error lists concatenate. `apply_computed(data, {...})` derives fields in insertion order, so a later computed field can read an earlier one. 23 tests in `test_rules.py`; combined suite 137/137. Stdlib only.
- **README: the integration that `Schema` cannot express.** The cross-field section now shows `booking.validate()` + `check_rules()` merged into one response, with both outputs executed and asserted - including the per-field-error case, where the cross-field rule is skipped because `Rule.evaluate` only converts `CrossFieldError` and `AssertionError` and a comparison over a malformed value raises `TypeError` instead. Documented rather than papered over: a rule that runs on data which already failed validation will raise.

### Compatibility
- No changes to `Schema`, `Field` or any existing module. `rules.py` is a new top-level module shipped in the wheel alongside `tiny_validator` and `tiny_validator_mcp`.

## [0.6.0] - 2026-10-22

### Fixed
- **`to_json_schema()` dropped `choices` and `pattern` entirely.** `String(choices=["admin", "user"])` exported as bare `{"type": "string"}` and `Integer(choices=[1, 2])` as bare `{"type": "integer"}`. Any consumer of the exported schema - OpenAPI docs, MCP tool definitions, generated clients - saw an unconstrained field where the real schema was constrained. The same loss made `to_json_schema()` -> `from_json_schema()` round-trips silently permissive.
- **Arbitrary validator prose could invent constraints.** `_schema_to_json_schema` recovered bounds by substring-matching human-readable validator messages such as `"string must be at least 2 characters"`. A custom validator whose message merely *contained* that phrasing - e.g. `add_validator(fn, "must be at least 999 characters of prose")` - produced a bogus `minLength: 999` in the exported schema.

### Changed
- **`Field` now records structural constraints at construction time.** `Field.set_constraint()`, `Field.get_constraint()` and a read-only `Field.constraints` property were added; `String`, `Integer`, `Float` and `List` populate them.
- **`_schema_to_json_schema` reads recorded constraints** instead of parsing validator message strings. String parsing is gone, so exports are now exact rather than best-effort.

### Added
- **`Field.constraints`** - public, returns a copy, mapping JSON Schema keyword names (`minLength`, `maxLength`, `pattern`, `enum`, `minimum`, `maximum`, `minItems`, `maxItems`) to values.
- **New test file `test_v060_export.py`** (19 tests) covering constraint export for every affected field type, the prose false-positive case, and `enum`/`pattern` round-trips. Combined suite now 114/114.

### Compatibility
- No breaking API changes. Validation behaviour is identical; only the *export* fidelity improved. `Field.constraints` is additive.
- Fields built by third-party subclasses that never call `set_constraint` export exactly as before - no invented keywords.

## [0.5.0] - 2026-10-06

### Added
- **New sidecar module `tiny_validator_mcp.py`** (zero new dependencies; lazily imports `tiny_validator`). Adds MCP (Model Context Protocol) server-manifest validation on top of the v0.4.0 core. The sidecar is opt-in: existing `tiny_validator` users see no behaviour change unless they `import tiny_validator_mcp`.
- **`McpServer(name, version, tools=, resources=, prompts=, metrics=, ...)`** - top-level MCP server declaration. Eager-validates the full manifest (structural + per-element + metric labels) on construction and raises a single `McpError` carrying all errors. `McpServer.to_dict()` emits the MCP-Registry v1 manifest shape.
- **`McpTool(name, description, input_schema=, annotations=)`** - single tool declaration. `input_schema` accepts a tiny-validator `Schema` (converted via `to_json_schema`) or a pre-built dict.
- **`McpResource(uri, name, description=, mime_type=)`** - single resource declaration. URI scheme is RFC 3986-permissive (`file://`, `git://`, `https://`, custom schemes all accepted).
- **`McpPrompt(name, description=, arguments=)`** - single prompt template.
- **`validate_mcp_manifest(manifest)`** - three-layer validation entry point: (1) structural via `SERVER_SCHEMA`, (2) per-element via `TOOL_SCHEMA`/`RESOURCE_SCHEMA`/`PROMPT_SCHEMA`, (3) metric-label via `metric_label_check`. Returns `list[dict]` of `{path, message}`; empty list means valid.
- **`metric_label_check(name)`** - returns `list[str]` of issues with a single Prometheus metric name. Implements the de-facto convention `mcp_<server>_<unit>_(total|bucket|sum|count|created|info)`.
- **`to_mcp_tool_schema(schema, *, name, description)`** - convenience constructor.
- **Constants** (de-facto spec values): `MCP_PROTOCOL_VERSIONS`, `DEFAULT_TRANSPORTS`, `DEFAULT_CAPABILITIES`, `PROMETHEUS_METRIC_PATTERN`, `SERVER_NAME_PATTERN`.
- **Schemas** (lowercase `_SCHEMA` constants for external validators): `SERVER_SCHEMA`, `TOOL_SCHEMA`, `RESOURCE_SCHEMA`, `PROMPT_SCHEMA`.
- **New test file `test_v050_mcp.py`** (39 tests). Combined suite now 95/95.

### Changed
- Bumped `__version__` to `0.5.0` in `pyproject.toml`.
- The sidecar pattern (zero-dep core + opt-in extra module) is now the documented way to extend `tiny_validator`. Future additions will follow the same convention.

### Notes
- The sidecar lives at `tiny_validator_mcp.py` and supports both flat-layout (`import tiny_validator_mcp` next to `tiny_validator.py`) and package layouts. The import is detected at runtime.
- `validate_mcp_manifest` is intentionally permissive on `capabilities`: any dict-shaped value is accepted because the MCP spec leaves capability sub-keys open.
- `McpServer` is exported under both `McpServer` (Pythonic) and `McpManifest` (registry-side alias). They are the same class.
- The Prometheus metric pattern accepts counters, histograms, summaries, info metrics, and gauges - any single-suffix `_(total|bucket|sum|count|created|info)` is valid; gauges can also drop the suffix.
- Round-trip property: `McpServer(...).to_dict()` -> `validate_mcp_manifest` -> `[]` is the standard test. `test_round_trip_manifest` exercises this for a fully-populated server.

### Closes
- Open question from `dev-reports/2026-10-05-developer-tools-landscape.md`: "Should `tiny-validator` ship a `McpServer` schema (matching the metric label scheme above)? Likely yes - it's a 40-line addition." Delivered as a 500-LOC sidecar (not 40 LOC) because the McpServer needs Tool/Resource/Prompt sub-schemas, metric-label validation, and 39 tests to be useful.

## [0.4.0] — 2026-10-04

### Added
- **`to_json_schema(schema)`** — export a tiny-validator `Schema` as a JSON Schema dict. Round-trips with `from_json_schema()` for the supported subset: type mapping, required list, min/max, length, format, default, strict mode (`additionalProperties: false`), nested objects, and arrays. New test file `test_v040_export.py` (22 tests).
- **`to_openapi_schema(schema, *, title="Model", description="", required_override=None)`** — same shape, plus `$schema: https://json-schema.org/draft/2020-12/schema` and a configurable `title`. Suitable for embedding under `components.schemas[name]` in an OpenAPI 3.1 document or for use as a JSON Schema in MCP tool definitions.

### Changed
- Bumped `__version__` to `0.4.0`.
- `__all__` now exports `to_json_schema` and `to_openapi_schema`.
- Field-type dispatch in `_field_to_json_schema` reordered so subclass checks (Email, Url, Uuid, Date, DateTime) fire *before* the `String` parent — `isinstance` would otherwise match `String` first and drop the `format` tag.

### Notes
- Export is **lossy by design**: custom lambda validators, choices (when set via `String(choices=[...])`), and `pattern` are not always re-derivable from the stored validator message. The original `Schema` remains the source of truth for validation; this export is for documentation and interop.
- The constraint-extraction step uses a small set of duck-typed message patterns (`"must be at least N characters"`, `"must be <= N"`, etc.). This is fragile if future versions rephrase these messages — pin your `tiny-validator` version in production code that depends on the exported JSON Schema.
- Re-importing an exported schema (via `from_json_schema`) is supported and the round-trip preserves the validation behaviour for the supported subset (verified by `TestRoundTrip`).

## [0.3.0] — 2026-08-12

### Added
- `Json`, `IP`, `Slug`, `Regex`, `HexColor` field types.
- `json_schema()` and `from_json_schema()` for converting between `Schema` and JSON Schema dicts.
- `PartialSchema` for partial-validating schemas.
- `validate()` decorator for `tiny-router` integration.
- `AsyncField` and `AsyncValidator` for fields that need to call external services.
- 17 new tests, suite now 34/34.

## [0.2.0] — 2026-07-08

### Added
- Cross-field `Rule` and `Computed` validators via `Model.add_rule(...)` / `add_computed(...)`.
- 21 new tests, suite now 17/17.

## [0.1.0] — 2026-06-25

### Added
- Initial release: 17 tests covering String, Integer, Float, Boolean, List, Dict, Email, Url, Uuid, Date, DateTime, Email, Url field types, and the Schema validate/partial materialization API.
