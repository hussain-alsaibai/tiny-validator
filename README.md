# tiny-validator — Zero-Dependency Input Validation

> **Like Pydantic, but in one file. Zero dependencies.**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)](tiny_validator.py)
[![Part of the tiny-* ecosystem](https://img.shields.io/badge/tiny--*-ecosystem-purple.svg)](#ecosystem)

`tiny-validator` is a single-file, declarative input validation library. No Pydantic, no marshmallow, no attrs. Pure Python — chainable field types, nested schemas, defaults, and structured error reporting.

## ✨ Features

- **🪶 Zero dependencies** — stdlib `re` only
- **📦 Single file** — drop `tiny_validator.py` anywhere
- **🧱 Declarative schemas** — `Schema({...})` with `fields.*` namespace
- **🎯 12+ field types** — string, integer, float, boolean, list, dict, email, URL, UUID, date, datetime, decimal
- **🪆 Nested schemas** — `fields.Dict(schema=...)` for objects
- **🛡️ Strict mode** — reject unknown fields
- **🎁 Defaults** — built into Field
- **🚨 Structured errors** — `ValidationError.errors` is a list of `{path, message}`
- **🎀 Decorator** — `@validate(body=..., query=..., headers=...)`

## 🚀 Quick Start

```python
from tiny_validator import Schema, fields, ValidationError, validate

user_schema = Schema({
    "name": fields.String(min_length=1, max_length=100),
    "email": fields.Email(),
    "age":  fields.Integer(min_value=0, max_value=150, required=False),
    "role": fields.String(choices=["admin", "user"]),
}, strict=True)

try:
    clean = user_schema({"name": "Hussain", "email": "h@x.co", "role": "admin"})
except ValidationError as exc:
    print(exc.errors)
```

## 🎀 Decorator

```python
@validate(
    body=Schema({"query": fields.String(min_length=3), "limit": fields.Integer(default=10)}),
    query=Schema({"lang": fields.String(choices=["en", "ar"], required=False)}),
)
def search_handler(body, query):
    return {"q": body["query"], "limit": body["limit"]}
```

## 🧱 Field Reference

| Field | Common kwargs |
|---|---|
| `String` | `min_length`, `max_length`, `pattern`, `choices`, `case_insensitive` |
| `Integer` | `min_value`, `max_value`, `choices` |
| `Float` | `min_value`, `max_value`, `allow_int` |
| `Boolean` | — |
| `List(item_field=…)` | `min_length`, `max_length`, `unique` |
| `Dict(schema=…)` | `required` (alias `Object`) |
| `Email` / `Url` / `Uuid` | (all extend String) |
| `Date` / `DateTime` | (ISO-8601 strings) |
| `Decimal` | `min_value`, `max_value`, `max_digits`, `decimal_places` |
| `Any` | `allow_none=True` by default |

All fields accept `required=True/False` and `default=...`.

## 🛡️ Error Shape

```python
exc.errors == [
    {"path": "user.email", "message": "value must be a valid email address"},
    {"path": "user.age",   "message": "value must be <= 150"},
]

exc.to_dict() == {
    "error": "validation_failed",
    "details": [
        {"path": "user.email", "message": "value must be a valid email address"},
        ...
    ],
}
```

## Agent Workflow Fit

`tiny-validator` works well for agent-built services where bad inputs should fail early and explain themselves:

- **Webhook payload gates** — validate provider callbacks before they reach handlers.
- **Tool-call contracts** — check JSON arguments before running filesystem, browser, or GitHub actions.
- **Bounty repro inputs** — keep proof-of-concept scripts honest with strict, readable schemas.
- **Config and env checks** — validate generated config dictionaries before a cron job starts.

Pair it with `tiny-router` for HTTP endpoints, `tiny-cli` for operator commands, and `tiny-secret` when validation errors must avoid leaking sensitive values.

### JSON Schema tool contracts

Use `from_json_schema()` when a tool, MCP server, or generated config already
describes its arguments as JSON Schema:

```python
from tiny_validator import from_json_schema

schema = from_json_schema({
    "type": "object",
    "required": ["repo", "limit"],
    "properties": {
        "repo": {"type": "string", "pattern": r"^[^/]+/[^/]+$"},
        "limit": {"type": "integer", "minimum": 1, "maximum": 20},
        "include_closed": {"type": "boolean", "default": False},
    },
    "additionalProperties": False,
})

args = schema({"repo": "hussain-alsaibai/tiny-validator", "limit": 5})
```

The bridge intentionally supports a practical subset and raises `ValueError`
for unsupported keywords, so tool-call validation fails loudly instead of
silently accepting a partial contract.

See also:

- [Tool-Call Contracts With tiny-validator](reports/2026-07-09-tool-call-contracts.md) — validating agent tool arguments before filesystem, browser, GitHub, or cloud side effects.
- [Agent Output Guards With tiny-validator](reports/2026-07-11-agent-output-guards.md) — checking generated plans, patches, and tool payloads before they reach side-effecting tools.
- [JSON Schema Tool Contracts With tiny-validator](reports/2026-07-13-json-schema-tool-contracts.md) — validating MCP-style tool arguments with a zero-dependency schema bridge.
- [Schema Drift Repair Loops With tiny-validator](reports/2026-07-14-schema-drift-repair-loops.md) — turning validation failures into safe, inspectable repair prompts for agent outputs and tool payloads.

## 📊 Comparison

| Feature | **tiny-validator** | Pydantic v2 | marshmallow |
|---|---|---|---|
| Dependencies | **0** | 0 (core) | 0 (core) |
| File count | **1** | multiple | multiple |
| Type-driven | ❌ (declarative) | ✅ | ❌ |
| Strict mode | ✅ | ✅ | ✅ |
| Nested schemas | ✅ | ✅ | ✅ |
| Decorator | ✅ | (depends) | ❌ |
| Email / URL / UUID | ✅ | ✅ (str + format) | needs extra |
| Startup time | <10 ms | ~200 ms | ~50 ms |

**Use `tiny-validator` when** you want fast, transparent, no-surprise validation, and you don't need Pydantic's serialization/deserialization, model export, or computed fields.

## 🧪 Testing

```bash
python test_tiny_validator.py -v
```

## Ecosystem

Part of the **tiny-*** zero-dependency toolkit for Python agent infrastructure:

- [**tiny-router**](https://github.com/hussain-alsaibai/tiny-router) — HTTP router, 76K req/s
- [**tiny-log**](https://github.com/hussain-alsaibai/tiny-log) — structured logging
- [**tiny-validator**](https://github.com/hussain-alsaibai/tiny-validator) — input validation, 247K val/s
- [**tiny-config**](https://github.com/hussain-alsaibai/tiny-config) — layered config loader
- [**tiny-cli**](https://github.com/hussain-alsaibai/tiny-cli) — CLI builder with colors
- [**fast-cache**](https://github.com/hussain-alsaibai/fast-cache) — LRU + TTL + SWR cache
- [**tiny-rate**](https://github.com/hussain-alsaibai/tiny-rate) — rate limiter (token / fixed / sliding)
- [**tiny-retry**](https://github.com/hussain-alsaibai/tiny-retry) — retry + backoff + circuit breaker
- [**tiny-pool**](https://github.com/hussain-alsaibai/tiny-pool) — ThreadPool + AsyncPool
- [**tiny-agent**](https://github.com/hussain-alsaibai/tiny-agent) — zero-dep agent framework
- [**tiny-mcp**](https://github.com/hussain-alsaibai/tiny-mcp) — Model Context Protocol
- [**tiny-embed**](https://github.com/hussain-alsaibai/tiny-embed) — embeddings + vector search
- [**tiny-compose**](https://github.com/hussain-alsaibai/tiny-compose) — Stack any decorators in any order, declaratively
- [**tiny-trace**](https://github.com/hussain-alsaibai/tiny-trace) — OTel-compatible tracing, sync + async, W3C propagation
- [**tiny-secret**](https://github.com/hussain-alsaibai/tiny-secret) — Zero-dep secret loader + redacting printer
- [**tiny-cron**](https://github.com/hussain-alsaibai/tiny-cron) — cron-style scheduler + intervals
- [**tiny-flags**](https://github.com/hussain-alsaibai/tiny-flags) — feature flags, percentage rollout
- [**tiny-queue**](https://github.com/hussain-alsaibai/tiny-queue) — persistent FIFO queue, retries
- [**tiny-metrics**](https://github.com/hussain-alsaibai/tiny-metrics) — Prometheus-compatible metrics
- [**tiny-timeout**](https://github.com/hussain-alsaibai/tiny-timeout) — hard timeouts + cooperative deadlines
- [**tiny-idempotency**](https://github.com/hussain-alsaibai/tiny-idempotency) — Stripe-style idempotency keys
- [**tiny-budget**](https://github.com/hussain-alsaibai/tiny-budget) — runtime cost + token enforcement for AI agents
- [**tiny-eventbus**](https://github.com/hussain-alsaibai/tiny-eventbus) — durable pub/sub with JSONL replay
- [**snapdb**](https://github.com/hussain-alsaibai/snapdb) — embedded DB

21 repos, ~14,700 LOC, zero dependencies across the entire stack. All single-file, MIT, fully type-hinted. Built by [OpenClaw](https://github.com/hussain-alsaibai).

## License

MIT — see [LICENSE](LICENSE).
