# Agent Output Guards With tiny-validator

Date: 2026-07-11

## Trend

Developers are asking agents to emit JSON plans, patches, tool arguments,
workflow manifests, and deployment metadata. A lot of failures happen after a
model produced something that looked plausible but had the wrong shape: a
missing target repo, an unbounded shell command, an invalid webhook URL, or an
unexpected optional field treated as trusted.

The next useful layer is output guarding: validate generated objects before
they reach tools with side effects.

## Why tiny-validator Fits

`tiny-validator` gives agent workflows a small contract layer:

- Keep schemas close to the tool function that needs them.
- Reject unexpected keys with `strict=True`.
- Return structured errors an agent can repair on the next attempt.
- Vendor the validator into one-file bounty or ops scripts without a model
  framework dependency.

For autonomous bounty and maintenance work, this is especially valuable around
GitHub mutations, local file writes, cron updates, and outbound notifications.

## Recommended Pattern

```python
from tiny_validator import Schema, fields, ValidationError

patch_plan = Schema({
    "repo": fields.String(pattern=r"^[^/]+/[^/]+$"),
    "branch": fields.String(min_length=3, max_length=80),
    "files": fields.List(fields.String(min_length=1), min_length=1),
    "run_tests": fields.Boolean(default=True),
    "notify": fields.Boolean(default=False),
}, strict=True)

def guard_agent_plan(plan):
    try:
        return True, patch_plan(plan)
    except ValidationError as exc:
        return False, exc.to_dict()
```

## Product Opportunities

- Add `examples/agent_output_guard.py` with a repair-loop friendly error
  response.
- Document schema placement beside dangerous tools: filesystem writes, GitHub
  comments, browser automation, and message sends.
- Show a paired `tiny-cli` command that validates a generated plan before a
  human approves execution.

## Engagement Hooks

- "Generated JSON is not a contract until it has been validated."
- "Guard agent output before it becomes a file write or GitHub mutation."
- "Small schemas for the tools that actually need trust."

