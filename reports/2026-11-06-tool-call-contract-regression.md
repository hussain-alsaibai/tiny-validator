# Tool-Call Contract Regression: November 2026 Field Note

Agent tool calls are a contract, and contracts regress. The schema an MCP
server publishes in October is not the schema it accepts in November: a field
gets renamed, an enum gains a value, `required` moves. The agent's prompt still
emits the old shape, and the failure surfaces as a *tool error* at
side-effect time rather than as a *contract mismatch* at validation time.

This note is about catching that regression before it reaches the side effect,
and about the one mistake that makes the check useless: **validating the
arguments you sent instead of the arguments the tool will receive.**

## Trend Signals

- **MCP servers ship breaking argument changes in minor versions.** The
  protocol has version negotiation; the *tool schemas* inside it do not.
- **Agents cache tool definitions at session start.** A server restart
  mid-session leaves the agent with a schema nobody accepts.
- **Strict validation is cheap; a partial side effect is not.** Opening half a
  PR, writing half a file, or charging a card with the wrong amount cannot be
  un-validated.
- **`additionalProperties: false` is the load-bearing default** in tool-call
  contracts, because a typo'd key is silently dropped by permissive schemas and
  the tool then runs with a default the caller never chose.

## The regression to watch for

A contract check that runs on the *prepared* payload proves nothing about the
*received* payload. These two differ more often than they look:

```python
from tiny_validator import from_json_schema, ValidationError

OPEN_PR = from_json_schema({
    "type": "object",
    "required": ["repo", "title", "branch"],
    "properties": {
        "repo": {"type": "string", "pattern": r"^[^/]+/[^/]+$"},
        "title": {"type": "string", "minLength": 8, "maxLength": 120},
        "branch": {"type": "string", "minLength": 1, "maxLength": 120},
        "draft": {"type": "boolean", "default": True},
    },
    "additionalProperties": False,
})

def gate(payload: dict) -> dict:
    """Validate the payload AT THE BOUNDARY, not before serialisation."""
    try:
        return {"ok": True, "args": OPEN_PR(payload)}
    except ValidationError as exc:
        return {"ok": False, "errors": exc.errors}
```

The failure mode this prevents: `payload` passes a local check, then a
serialisation step drops `None` values, then the tool receives a dict that no
longer has the required field. Validate after serialisation — or validate both
sides and assert they agree, which is the same idea with better evidence.

## Four checks worth having in CI

1. **Schema snapshot.** Record the schema your tool publishes; diff it per
   release. A renamed argument breaks callers silently.
2. **Round-trip parity.** `validate(serialise(validate(payload)))` must equal
   the first result. If the second pass rejects what the first accepted, the
   serialiser is changing the contract.
3. **Negative case per required field.** For each `required` key, remove it and
   assert rejection. A schema that accepts its own missing field is worse than
   no schema, because it reports success.
4. **Enum drift.** Adding a value is backwards-compatible for callers and
   forward-breaking for servers. Pin the enum set and decide which direction
   you are allowed to move in.

## Fit for `tiny-validator`

`tiny-validator` covers 1 and 3 directly — strict schemas plus
`from_json_schema()` for contracts already written as JSON Schema — and its
error shape (`path`, `message`, allowed values) is what a repair loop needs.
Checks 2 and 4 are three or four lines each on top of `Schema`.

Pair with:

- `tiny-mcp-client`'s `tiny_mcp_contract` for pinning the *server's* tool
  list and diffing it per release — the server-side half of this note.
- `tiny-dist-audit` for recording what the release artifact actually contained,
  so a schema regression can be tied to a specific built file rather than a
  branch name.

## What this does not fix

Validation proves shape, never intent. A perfectly-shaped
`{"repo": "attacker/repo", "title": "...", "branch": "main"}` passes every
schema in this note. Authorization belongs after validation and is not the
validator's job — saying that plainly is cheaper than the incident review that
follows forgetting it.
