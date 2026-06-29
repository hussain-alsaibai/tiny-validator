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

Part of the **tiny-*** zero-dependency agent infrastructure toolkit:

- [tiny-router](https://github.com/hussain-alsaibai/tiny-router) — HTTP routing
- [tiny-log](https://github.com/hussain-alsaibai/tiny-log) — Structured logging
- [tiny-validator](https://github.com/hussain-alsaibai/tiny-validator) — Validation (this repo)
- [tiny-cli](https://github.com/hussain-alsaibai/tiny-cli) — CLI parser
- [tiny-config](https://github.com/hussain-alsaibai/tiny-config) — Config loader
- [fast-cache](https://github.com/hussain-alsaibai/fast-cache) — In-memory cache
- [tiny-mcp](https://github.com/hussain-alsaibai/tiny-mcp) — MCP server
- [tiny-agent](https://github.com/hussain-alsaibai/tiny-agent) — Agent framework
- [tiny-embed](https://github.com/hussain-alsaibai/tiny-embed) — Embeddings
- [snapdb](https://github.com/hussain-alsaibai/snapdb) — Embedded DB

## License

MIT — see [LICENSE](LICENSE).
