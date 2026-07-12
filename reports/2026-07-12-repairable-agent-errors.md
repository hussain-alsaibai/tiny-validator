# Repairable Agent Errors With tiny-validator

Date: 2026-07-12

## Trend

Developers are putting generated JSON between agents and real tools: file
edits, GitHub comments, browser actions, deployment manifests, cron updates,
and notification payloads. Validation is already important, but the next step
is making validation failures repairable.

A generic "invalid input" message wastes a retry. A compact error object that
says which field failed, what was expected, and whether unknown keys were
rejected gives the agent or operator a useful next move.

## Why tiny-validator Fits

`tiny-validator` is well placed for repair loops:

- Schemas sit beside the tool or handler they protect.
- `strict=True` rejects surprise fields before side effects.
- Structured errors can be returned directly to an agent retry loop.
- The dependency footprint stays small enough for one-file automations and
  bounty repros.

The opportunity is to position validation as feedback, not just refusal.

## Recommended Pattern

```python
from tiny_validator import Schema, fields, ValidationError

tool_call = Schema({
    "action": fields.String(choices=["comment", "label", "close"]),
    "repo": fields.String(pattern=r"^[^/]+/[^/]+$"),
    "issue": fields.Integer(min_value=1),
    "dry_run": fields.Boolean(default=True),
}, strict=True)

def validate_for_repair(payload):
    try:
        return {"ok": True, "value": tool_call(payload)}
    except ValidationError as exc:
        return {
            "ok": False,
            "error": "invalid_tool_call",
            "repair_hint": "Return only the schema fields with valid values.",
            "details": exc.errors,
        }
```

## Product Opportunities

- Add an `examples/repairable_agent_error.py` example.
- Document an error response shape for agent retries: `ok`, `error`,
  `repair_hint`, and `details`.
- Show how `strict=True` protects filesystem, GitHub, browser, and message
  tools from unexpected generated fields.

## Engagement Hooks

- "Validation should teach the next retry what to fix."
- "Generated JSON needs repairable contracts before it touches tools."
- "Fail early, fail with structure, and let the agent try again safely."
