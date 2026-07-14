# Schema Drift Repair Loops With tiny-validator: July 2026 Field Note

Agent workflows fail in a familiar way: the tool contract changes, the prompt still emits the old shape, and a side-effecting call receives a payload that is almost right. The better pattern is not to relax validation. It is to validate strictly, turn the error into a small repair task, then validate again before any external action happens.

Schema drift repair is becoming a core developer workflow for tools that let agents write configs, submit forms, open issues, generate patches, or call MCP-style commands.

## Trend Signals

- **Tool schemas change faster than prompts.** Developers iterate on arguments, defaults, and enum values while agent instructions lag behind.
- **Strict validation saves side effects.** A failed local validation is cheaper than a malformed GitHub, cloud, or filesystem operation.
- **Repair prompts need structure.** Feeding a model the original payload plus exact path errors works better than generic "try again" text.
- **Drift metrics expose weak contracts.** Repeated repairs on the same field show where docs, schemas, or examples need work.
- **Human review remains useful.** Some repairs should produce a patch or diff instead of silently retrying.

## What Developers Need

1. Path-specific validation errors.
2. A normalized repair input that includes schema name, failed payload, and allowed values.
3. A retry cap so bad prompts do not loop forever.
4. Redaction before sending invalid payloads to a model.
5. Logging for repaired, rejected, and escalated outputs.

## Fit For `tiny-validator`

`tiny-validator` already returns compact structured errors and supports strict schemas. That makes it a good boundary before repair loops, especially inside small agent tools that cannot justify a larger validation stack.

Recommended near-term additions:

- Add a repair-loop recipe for generated tool payloads.
- Show how to redact invalid payloads before constructing a repair prompt.
- Document a `max_repairs=1` or `max_repairs=2` convention for side-effecting tools.
- Pair validation failures with `tiny-log` fields such as `schema`, `path`, `decision`, and `repair_attempt`.

## Example Shape

```python
def validate_or_repair(schema, payload, repair):
    try:
        return schema(payload), "accepted"
    except ValidationError as exc:
        fixed = repair({
            "payload": payload,
            "errors": exc.errors,
            "instruction": "Return only corrected JSON.",
        })
        return schema(fixed), "repaired"
```

For write operations, keep the repaired payload visible in logs or review output before execution.

## OpenClaw Workflow Relevance

OpenClaw's autonomous bounty and repo-update work depends on tool payloads staying correct across changing schemas. Strict validation plus small repair loops makes automation more resilient without weakening the safety boundary before public actions.
