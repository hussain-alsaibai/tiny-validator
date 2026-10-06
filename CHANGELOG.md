# Changelog

All notable changes to tiny-validator are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
