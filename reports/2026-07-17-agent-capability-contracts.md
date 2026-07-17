# Agent Capability Contracts With tiny-validator

Date: 2026-07-17

## Trend

Agent tooling is becoming less about one assistant calling arbitrary functions
and more about negotiated capabilities: MCP tools, runtime policies, approval
labels, isolated environments, and traceable actions. The weak point is often
the boundary between "the model proposed this payload" and "the system is about
to perform a side effect."

`tiny-validator` is useful at that boundary because it makes the allowed shape
small, local, and testable.

## Capability contract pattern

Define a schema for each capability before the handler runs.

```python
from tiny_validator import Schema, fields, ValidationError

open_pr_contract = Schema({
    "repo": fields.String(pattern=r"^[^/]+/[^/]+$"),
    "branch": fields.String(min_length=1, max_length=120),
    "title": fields.String(min_length=8, max_length=120),
    "draft": fields.Boolean(default=True),
}, strict=True)

def validate_open_pr(payload):
    try:
        return open_pr_contract(payload)
    except ValidationError as exc:
        return {"error": "invalid_capability_payload", "details": exc.errors}
```

The important property is `strict=True`: unknown fields are rejected instead of
being carried into the side-effecting layer.

## What to validate

- Repository names and branch names before GitHub actions.
- File paths before filesystem writes.
- Tool names and tool arguments before MCP execution.
- Cron schedules before background job creation.
- Message destinations before out-of-band sends.
- Budget, token, and timeout values before model calls.

## Contract tiers

| Tier | Example | Validator behavior |
|---|---|---|
| Read-only | list issues, fetch docs | Validate shape and limits |
| Local write | edit file, generate report | Validate path, mode, and payload |
| External draft | create PR draft, stage message | Validate strict schema and require review state |
| Public side effect | send message, deploy, publish | Validate schema plus explicit operator approval |

## Repair loop

Validation errors should feed a repair loop, not a raw exception dump:

1. Reject the payload before side effects.
2. Return structured `path` and `message` details.
3. Ask the model to produce only a corrected payload.
4. Revalidate the corrected payload.
5. Log both rejection and acceptance with redacted values.

## OpenClaw fit

OpenClaw runs autonomous workflows that touch GitHub, local repos, messaging,
cron, browser automation, and bounty systems. Capability contracts make those
workflows easier to audit: each side-effecting action has a small schema, a
known approval tier, and structured failure output that can be repaired or
reported.

## Source signals

- MCP ecosystem discussion is emphasizing explicit state handles, capability
  negotiation, and sharper authorization rules.
- Agent security platform messaging is emphasizing isolated, governed runtime
  environments.
- Developer productivity trend reports increasingly group production agents
  around observability, security boundaries, evaluations, and human-in-the-loop
  controls.
