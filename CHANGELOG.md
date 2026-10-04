# Changelog

All notable changes to tiny-validator are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
