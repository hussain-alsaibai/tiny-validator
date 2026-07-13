# JSON Schema Tool Contracts With tiny-validator

Date: 2026-07-13

## Trend

Agent platforms increasingly describe callable tools with JSON Schema:
MCP tools, OpenAI tool calls, LangChain tools, browser actions, GitHub actions,
and internal automation endpoints all need the same thing: validate generated
arguments before a side effect happens.

The heavy answer is to install a full JSON Schema implementation or a model
framework. That is often right for public APIs. It is less appealing inside
small agent scripts, bounty repros, CI helpers, and webhook receivers where the
contract is narrow and must be easy to audit.

## Today's Update

`tiny-validator` now ships `from_json_schema()`, a zero-dependency bridge from a
practical JSON Schema subset into existing `Schema` and `Field` validators.

Supported keywords include:

- `type`: object, string, integer, number, boolean, array, null
- `properties` and `required`
- nested `items` and object properties
- `enum`, `pattern`, `format`
- `minimum`, `maximum`, `exclusiveMinimum`, `exclusiveMaximum`
- `minLength`, `maxLength`, `minItems`, `maxItems`
- `default`, `description`, `additionalProperties`

Unsupported keywords raise `ValueError` instead of being silently ignored. That
matters in agent workflows: a half-applied schema can be worse than no schema.

## Recommended Pattern

```python
from tiny_validator import from_json_schema

tool_args = from_json_schema({
    "type": "object",
    "required": ["repo", "issue", "limit"],
    "properties": {
        "repo": {"type": "string", "pattern": r"^[^/]+/[^/]+$"},
        "issue": {"type": "integer", "minimum": 1},
        "limit": {"type": "integer", "minimum": 1, "maximum": 20},
        "include_closed": {"type": "boolean", "default": False},
    },
    "additionalProperties": False,
})

args = tool_args({"repo": "hussain-alsaibai/tiny-validator", "issue": 12, "limit": 5})
```

## Why It Fits OpenClaw

OpenClaw's autonomous workflows need validation at the boundary between
generated text and action: GitHub mutations, browser steps, filesystem writes,
callback payloads, and cron config. The bridge makes MCP-style tool contracts
copyable into local scripts while keeping error messages structured enough for
repair loops.

Pairings:

- `tiny-router` receives the HTTP request.
- `tiny-validator.from_json_schema()` validates the payload contract.
- `fast-cache.add()` claims delivery IDs atomically for dedupe.
- `tiny-log` records structured repairable failures.

## Engagement Hooks

- "Validate MCP-style tool arguments without importing a framework."
- "Unsupported schema keywords fail loudly instead of becoming pretend safety."
- "Turn generated JSON into either clean args or repairable errors."

