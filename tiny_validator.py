"""tiny_validator — zero-dependency input validation for Python.

A single-file validation library with a chainable, declarative API. No Pydantic,
no marshmallow, no attrs. Pure Python standard library.

Usage:
    from tiny_validator import Schema, validate, fields, ValidationError

    user_schema = Schema({
        "name": fields.String(min_length=1, max_length=100),
        "email": fields.Email(),
        "age": fields.Integer(min_value=0, max_value=150, required=False),
        "role": fields.String(choices=["admin", "user"]),
    })

    @validate(body=user_schema)
    def create_user(req, body):
        return {"created": body["name"]}
"""

from __future__ import annotations

import re
import typing
from collections.abc import Mapping as MappingABC
from datetime import date, datetime
from decimal import Decimal as _Decimal
from decimal import InvalidOperation
from typing import Any, Callable, Iterable, Mapping


__version__ = "0.2.0"


# ---------- Errors ----------


class ValidationError(Exception):
    """Raised when validation fails. Carries structured error info."""

    def __init__(self, errors: list[dict[str, Any]] | str) -> None:
        if isinstance(errors, str):
            errors = [{"path": "", "message": errors}]
        self.errors = errors
        super().__init__(self._format(errors))

    @staticmethod
    def _format(errors: list[dict[str, Any]]) -> str:
        if not errors:
            return "validation failed"
        parts = []
        for e in errors:
            path = e.get("path", "")
            msg = e.get("message", "invalid")
            if path:
                parts.append(f"{path}: {msg}")
            else:
                parts.append(msg)
        return "; ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return {"error": "validation_failed", "details": self.errors}


# ---------- Field types ----------


class Field:
    """Base class for all field types."""

    def __init__(
        self,
        *,
        required: bool = True,
        default: Any = ...,
        description: str = "",
    ) -> None:
        self.required = required
        self.default = default
        self.description = description
        self._validators: list[tuple[Callable[[Any], bool | None], str]] = []

    def add_validator(self, fn: Callable[[Any], bool | None], message: str) -> None:
        self._validators.append((fn, message))

    def with_default(self, default: Any) -> "Field":
        """Return a copy of this field with the given default value.

        Useful for fluent schema construction::

            f = fields.String(min_length=1).with_default("anonymous")
        """
        # Create a clone of the same class with default set. We use __class__
        # but the safest way is to construct a new instance via __init__ with
        # minimum args; instead, we just clone __dict__ and adjust default.
        new = self.__class__.__new__(self.__class__)
        new.__dict__.update(self.__dict__)
        new.default = default
        new.required = False
        return new

    def validate(self, value: Any, path: str) -> list[dict[str, Any]]:
        errors: list[dict[str, Any]] = []
        if value is _MISSING:
            if self.required and self.default is ...:
                errors.append({"path": path, "message": "missing required field"})
            return errors
        if value is None:
            if not self.allow_none:
                errors.append({"path": path, "message": "value is null"})
            return errors
        errors.extend(self._validate_type(value, path))
        if not errors:
            # Coerce strings to Decimal for Decimal_ field so validators can compare
            if getattr(self, "_coerce_to_decimal", False) and isinstance(value, str):
                try:
                    value = _Decimal(value)
                except InvalidOperation:
                    return errors
            for fn, msg in self._validators:
                try:
                    res = fn(value)
                except Exception as exc:  # noqa: BLE001
                    errors.append({"path": path, "message": f"{msg}: {exc}"})
                    continue
                if res is False:
                    errors.append({"path": path, "message": msg})
                elif isinstance(res, str):
                    errors.append({"path": path, "message": res})
        return errors

    @property
    def allow_none(self) -> bool:
        return False

    def _validate_type(self, value: Any, path: str) -> list[dict[str, Any]]:
        return []


_MISSING = object()


# ---------- Primitive fields ----------


class Any(Field):
    allow_none = True

    def _validate_type(self, value: Any, path: str) -> list[dict[str, Any]]:
        return []


class String(Field):
    def __init__(
        self,
        *,
        min_length: int | None = None,
        max_length: int | None = None,
        pattern: str | None = None,
        choices: Iterable[str] | None = None,
        case_insensitive: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        if min_length is not None:
            self.add_validator(
                lambda v: len(v) >= min_length,
                f"string must be at least {min_length} characters",
            )
        if max_length is not None:
            self.add_validator(
                lambda v: len(v) <= max_length,
                f"string must be at most {max_length} characters",
            )
        if pattern is not None:
            compiled = re.compile(pattern)
            self.add_validator(
                lambda v: bool(compiled.search(v)),
                f"string must match pattern {pattern!r}",
            )
        if choices is not None:
            choices_list = list(choices)
            if case_insensitive:
                lower = {c.lower(): c for c in choices_list}

                def check(v: str) -> bool:
                    return v.lower() in lower

                self.add_validator(check, f"value must be one of {choices_list}")
            else:
                self.add_validator(
                    lambda v: v in choices_list,
                    f"value must be one of {choices_list}",
                )

    def _validate_type(self, value: Any, path: str) -> list[dict[str, Any]]:
        if not isinstance(value, str):
            return [{"path": path, "message": "expected string"}]
        return []


class Integer(Field):
    def __init__(
        self,
        *,
        min_value: int | None = None,
        max_value: int | None = None,
        choices: Iterable[int] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        if min_value is not None:
            self.add_validator(lambda v: v >= min_value, f"value must be >= {min_value}")
        if max_value is not None:
            self.add_validator(lambda v: v <= max_value, f"value must be <= {max_value}")
        if choices is not None:
            choices_list = list(choices)
            self.add_validator(
                lambda v: v in choices_list,
                f"value must be one of {choices_list}",
            )

    def _validate_type(self, value: Any, path: str) -> list[dict[str, Any]]:
        # bool is a subclass of int — reject it explicitly
        if isinstance(value, bool) or not isinstance(value, int):
            return [{"path": path, "message": "expected integer"}]
        return []


class Float(Field):
    def __init__(
        self,
        *,
        min_value: float | None = None,
        max_value: float | None = None,
        allow_int: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._allow_int = allow_int
        if min_value is not None:
            self.add_validator(lambda v: v >= min_value, f"value must be >= {min_value}")
        if max_value is not None:
            self.add_validator(lambda v: v <= max_value, f"value must be <= {max_value}")

    def _validate_type(self, value: Any, path: str) -> list[dict[str, Any]]:
        if isinstance(value, bool):
            return [{"path": path, "message": "expected number"}]
        if isinstance(value, int) and not self._allow_int:
            return [{"path": path, "message": "expected float"}]
        if not isinstance(value, (int, float)):
            return [{"path": path, "message": "expected number"}]
        return []


class Boolean(Field):
    def _validate_type(self, value: Any, path: str) -> list[dict[str, Any]]:
        if not isinstance(value, bool):
            return [{"path": path, "message": "expected boolean"}]
        return []


class List(Field):
    def __init__(
        self,
        item_field: Field | None = None,
        *,
        min_length: int | None = None,
        max_length: int | None = None,
        unique: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._item_field = item_field
        if min_length is not None:
            self.add_validator(
                lambda v: len(v) >= min_length,
                f"list must have at least {min_length} items",
            )
        if max_length is not None:
            self.add_validator(
                lambda v: len(v) <= max_length,
                f"list must have at most {max_length} items",
            )
        if unique:
            self.add_validator(
                lambda v: len(set(map(repr, v))) == len(v),
                "list items must be unique",
            )

    def _validate_type(self, value: Any, path: str) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return [{"path": path, "message": "expected list"}]
        errors: list[dict[str, Any]] = []
        if self._item_field is not None:
            for i, item in enumerate(value):
                sub = self._item_field.validate(item, f"{path}[{i}]")
                errors.extend(sub)
        return errors


class Dict_(Field):
    """A nested dict. Use `schema=` to validate values against a Schema."""

    def __init__(self, schema: "Schema | None" = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._schema = schema

    def _validate_type(self, value: Any, path: str) -> list[dict[str, Any]]:
        if not isinstance(value, MappingABC):
            return [{"path": path, "message": "expected object"}]
        if self._schema is not None:
            return self._schema.validate(value, base_path=path)
        return []


Dict = Dict_  # `Dict` clashes with typing.Dict, alias to Dict_


# ---------- Specialized string fields ----------


class Email(String):
    EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.add_validator(
            lambda v: bool(self.EMAIL_RE.match(v)),
            "value must be a valid email address",
        )


class Url(String):
    URL_RE = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.add_validator(
            lambda v: bool(self.URL_RE.match(v)),
            "value must be a valid http(s) URL",
        )


class Uuid(String):
    UUID_RE = re.compile(
        r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
    )

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.add_validator(
            lambda v: bool(self.UUID_RE.match(v)),
            "value must be a valid UUID",
        )


class Date(String):
    DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.add_validator(
            lambda v: bool(self.DATE_RE.match(v)) and self._is_valid(v),
            "value must be a valid date (YYYY-MM-DD)",
        )

    @staticmethod
    def _is_valid(v: str) -> bool:
        try:
            date.fromisoformat(v)
            return True
        except ValueError:
            return False


class DateTime(String):
    DT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}")

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.add_validator(
            lambda v: bool(self.DT_RE.match(v)) and self._is_valid(v),
            "value must be a valid ISO-8601 datetime",
        )

    @staticmethod
    def _is_valid(v: str) -> bool:
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return True
        except ValueError:
            return False


class Decimal_(Field):
    def __init__(
        self,
        *,
        min_value: float | None = None,
        max_value: float | None = None,
        max_digits: int | None = None,
        decimal_places: int | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        if min_value is not None:
            self.add_validator(
                lambda v: v >= _Decimal(str(min_value)), f"value must be >= {min_value}"
            )
        if max_value is not None:
            self.add_validator(
                lambda v: v <= _Decimal(str(max_value)), f"value must be <= {max_value}"
            )
        if max_digits is not None:
            self.add_validator(
                lambda v: len(str(v).replace(".", "").replace("-", "")) <= max_digits,
                f"value must have at most {max_digits} digits",
            )
        if decimal_places is not None:
            self.add_validator(
                lambda v: -v.as_tuple().exponent <= decimal_places
                if isinstance(v.as_tuple().exponent, int)
                else True,
                f"value must have at most {decimal_places} decimal places",
            )

    def _validate_type(self, value: Any, path: str) -> list[dict[str, Any]]:
        if isinstance(value, bool):
            return [{"path": path, "message": "expected decimal"}]
        if isinstance(value, _Decimal):
            return []
        if isinstance(value, (int, float)):
            try:
                _Decimal(str(value))
                return []
            except InvalidOperation:
                return [{"path": path, "message": "expected decimal"}]
        if isinstance(value, str):
            try:
                _Decimal(value)
            except InvalidOperation:
                return [{"path": path, "message": "expected decimal"}]
            return []
        return [{"path": path, "message": "expected decimal"}]

    @property
    def _coerce_to_decimal(self) -> bool:
        return True


Decimal_ = Decimal_  # keep name; alias
Decimal = Decimal_


# Alias `fields` namespace for ergonomic imports
class _FieldsNS:
    Any = Any  # type: ignore[misc]
    String = String
    Integer = Integer
    Float = Float
    Boolean = Boolean
    List = List
    Dict = Dict_
    Object = Dict_
    Email = Email
    Url = Url
    Uuid = Uuid
    Date = Date
    DateTime = DateTime
    Decimal = Decimal_


fields = _FieldsNS()


# ---------- Schema ----------


class Schema:
    """A schema defines the shape of a dict and validates it."""

    def __init__(self, definition: Mapping[str, Field], *, strict: bool = False) -> None:
        self.definition = dict(definition)
        self.strict = strict

    def validate(
        self,
        data: Mapping[str, Any],
        *,
        base_path: str = "",
    ) -> list[dict[str, Any]]:
        errors: list[dict[str, Any]] = []
        if not isinstance(data, MappingABC):
            return [{"path": base_path or "", "message": "expected object"}]

        if self.strict:
            extras = set(data.keys()) - set(self.definition.keys())
            for extra in extras:
                errors.append(
                    {
                        "path": f"{base_path}.{extra}" if base_path else extra,
                        "message": "unexpected field",
                    }
                )

        for key, field in self.definition.items():
            full_path = f"{base_path}.{key}" if base_path else key
            value = data.get(key, _MISSING)
            if value is _MISSING and field.default is not Ellipsis:
                value = field.default
            errors.extend(field.validate(value, full_path))

        return errors

    def __call__(self, data: Mapping[str, Any]) -> Mapping[str, Any]:
        """Validate and return the (possibly defaulted) data, or raise."""
        errors = self.validate(data)
        if errors:
            raise ValidationError(errors)
        # Materialize defaults for missing keys
        result: dict[str, Any] = dict(data)
        for key, field in self.definition.items():
            if key not in result and field.default is not Ellipsis:
                result[key] = field.default
        return result

    def validate_many(self, items: list[Mapping[str, Any]]) -> dict[str, list[Any]]:
        """Validate a list of items. Returns ``{"valid": [...], "invalid": [...errors]}``.

        Usage::

            result = schema.validate_many([
                {"name": "Alice", "email": "alice@example.com"},
                {"name": "", "email": "bad"},
            ])
            # result["valid"]   = [valid_item]
            # result["invalid"] = [{"item": item, "errors": errors_for_invalid}]
        """
        valid: list[Any] = []
        invalid: list[dict[str, Any]] = []
        for item in items:
            errors = self.validate(item)
            if errors:
                invalid.append({"item": item, "errors": errors})
            else:
                valid.append(item)
        return {"valid": valid, "invalid": invalid}

    def partial(self) -> "PartialSchema":
        """Return a partial-validating schema (skips unknown fields).

        Usage::

            partial = schema.partial()  # ignore extra fields
            errors = partial.validate({"name": "Alice", "extra": "ignored"})
        """
        return PartialSchema(self)


class PartialSchema:
    """A schema that ignores unknown fields. Wraps Schema for partial validation."""

    def __init__(self, schema: "Schema") -> None:
        self._schema = schema
        self.fields = schema.definition

    def validate(self, data: Any) -> list[dict[str, Any]]:
        if not isinstance(data, MappingABC):
            return [{"path": "", "message": "expected dict"}]
        # Only validate known fields
        filtered = {k: v for k, v in data.items() if k in self._schema.definition}
        return self._schema.validate(filtered)


# ---------- Decorators ----------


def validate(
    body: Schema | None = None,
    query: Schema | None = None,
    headers: Schema | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator: validate request parts before calling the handler."""

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        sig = typing.get_type_hints(fn)
        # We can't introspect a generic request object here; the wrapped function
        # is expected to accept `body=...` / `query=...` / `headers=...` kwargs.
        from functools import wraps

        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            errors: list[dict[str, Any]] = []
            for part_name, schema in (("body", body), ("query", query), ("headers", headers)):
                if schema is None or part_name not in kwargs:
                    continue
                part = kwargs[part_name]
                if not isinstance(part, MappingABC):
                    errors.append({"path": part_name, "message": "expected object"})
                    continue
                part_errors = schema.validate(part)
                for e in part_errors:
                    e["path"] = f"{part_name}.{e['path']}" if e["path"] else part_name
                errors.extend(part_errors)
                # Materialize defaults so the handler sees them
                materialized = dict(part)
                for key, field in schema.definition.items():
                    if key not in materialized and field.default is not Ellipsis:
                        materialized[key] = field.default
                kwargs[part_name] = materialized
            if errors:
                raise ValidationError(errors)
            return fn(*args, **kwargs)

        return wrapper

    return decorator


# ---------- Helper: serialize errors to HTTP-friendly dict ----------


def http_error_response(exc: ValidationError) -> dict[str, Any]:
    return exc.to_dict()


# ---------- JSON Schema compatibility ----------


def json_schema(schema: Mapping[str, Any]) -> "Schema":
    """Convert a JSON Schema dict to a tiny-validator Schema.

    Supports a useful subset of JSON Schema:

    - ``type``: ``object``, ``string``, ``integer``, ``number``, ``boolean``,
      ``array``, ``null`` (or list of types).
    - ``properties`` + ``required`` for objects.
    - ``items`` for arrays (with ``minItems``/``maxItems``).
    - ``enum`` for fixed-value fields.
    - ``pattern`` for string regex.
    - ``minimum`` / ``maximum`` / ``exclusiveMinimum`` / ``exclusiveMaximum``
      for numeric bounds.
    - ``minLength`` / ``maxLength`` for strings.
    - ``format``: ``email``, ``uri``, ``url``, ``uuid``, ``date``, ``date-time``.
    - ``default`` for default values.
    - ``additionalProperties: False`` enables strict mode (reject unknown keys).

    Unknown keywords raise ``ValueError`` so callers get a clear error instead
    of silent acceptance. The goal is to validate the JSON Schemas used by
    MCP tool definitions and agent config files without pulling in
    ``jsonschema`` or ``pydantic``.

    Usage::

        js = {
            "type": "object",
            "properties": {
                "name":  {"type": "string", "minLength": 1},
                "age":   {"type": "integer", "minimum": 0},
                "email": {"type": "string", "format": "email"},
            },
            "required": ["name", "email"],
        }
        validator = json_schema(js)
        errors = validator.validate({"name": "Alice", "email": "alice@example.com"})
    """
    if not isinstance(schema, MappingABC):
        raise ValueError("json schema root must be an object")

    additional_properties = schema.get("additionalProperties", True)
    strict = additional_properties is False

    json_type = schema.get("type", "object")
    if isinstance(json_type, list):
        # JSON Schema allows ["string", "null"]. Take the first non-null type.
        non_null = [t for t in json_type if t != "null"]
        if not non_null:
            raise ValueError("root json schema: type list contains only null")
        json_type = non_null[0]

    if json_type != "object":
        # Wrap a primitive in a single-field Schema for ergonomic use.
        field = _json_schema_type_to_field("value", schema)
        return Schema({"value": field}, strict=strict)

    properties = schema.get("properties", {})
    if not isinstance(properties, MappingABC):
        raise ValueError("'properties' must be an object")

    required = set(schema.get("required", []) or [])
    if not required.issubset(properties.keys()):
        missing = sorted(required - properties.keys())
        raise ValueError(f"required fields missing from properties: {missing}")

    tiny_fields: Dict[str, Field] = {}
    for key, sub_schema in properties.items():
        field = _json_schema_type_to_field(key, sub_schema)
        if key in required:
            field.required = True
        else:
            field.required = False
        tiny_fields[key] = field

    return Schema(tiny_fields, strict=strict)


def _json_schema_type_to_field(name: str, sub_schema: Any) -> Field:
    """Convert a JSON Schema property to a tiny-validator field."""
    if not isinstance(sub_schema, MappingABC):
        raise ValueError(f"property {name!r}: schema must be an object")

    allowed = {
        "type",
        "properties",
        "required",
        "items",
        "enum",
        "pattern",
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "minLength",
        "maxLength",
        "minItems",
        "maxItems",
        "format",
        "default",
        "description",
        "additionalProperties",
    }
    unsupported = set(sub_schema) - allowed
    if unsupported:
        raise ValueError(f"property {name!r}: unsupported keywords: {sorted(unsupported)}")

    json_type = sub_schema.get("type", "string")
    if isinstance(json_type, list):
        non_null = [t for t in json_type if t != "null"]
        if not non_null:
            raise ValueError(f"property {name!r}: type list contains only null")
        json_type = non_null[0]

    field: Field
    if json_type == "string":
        field = _json_string_field(sub_schema)
    elif json_type == "integer":
        field = _json_integer_field(sub_schema)
    elif json_type in ("number", "float"):
        field = _json_float_field(sub_schema)
    elif json_type == "boolean":
        field = Boolean()
    elif json_type == "array":
        field = _json_array_field(sub_schema)
    elif json_type == "object":
        field = _json_object_field(sub_schema)
    elif json_type == "null":
        field = Any()
    else:
        raise ValueError(f"property {name!r}: unsupported type {json_type!r}")

    if "enum" in sub_schema:
        enum_values = sub_schema["enum"]
        if not isinstance(enum_values, list):
            raise ValueError(f"property {name!r}: 'enum' must be a list")
        field.add_validator(
            lambda value, choices=enum_values: value in choices,
            f"value must be one of {enum_values}",
        )
    if "description" in sub_schema and isinstance(sub_schema["description"], str):
        field.description = sub_schema["description"]
    if "default" in sub_schema:
        field.default = sub_schema["default"]
    return field


def _json_string_field(sub_schema: Mapping[str, Any]) -> String:
    fmt = sub_schema.get("format")
    kwargs: Dict[str, Any] = {
        "min_length": sub_schema.get("minLength") if isinstance(sub_schema.get("minLength"), int) else None,
        "max_length": sub_schema.get("maxLength") if isinstance(sub_schema.get("maxLength"), int) else None,
        "pattern": sub_schema.get("pattern") if isinstance(sub_schema.get("pattern"), str) else None,
    }
    if fmt == "email":
        return Email(**kwargs)
    if fmt == "uri" or fmt == "url":
        return Url(**kwargs)
    if fmt == "uuid":
        return Uuid(**kwargs)
    if fmt == "date":
        return Date(**kwargs)
    if fmt == "date-time":
        return DateTime(**kwargs)
    return String(**kwargs)


def _json_integer_field(sub_schema: Mapping[str, Any]) -> Integer:
    minimum = sub_schema.get("minimum")
    maximum = sub_schema.get("maximum")
    field = Integer(
        min_value=int(minimum) if isinstance(minimum, int) and not isinstance(minimum, bool) else None,
        max_value=int(maximum) if isinstance(maximum, int) and not isinstance(maximum, bool) else None,
    )
    exclusive_minimum = sub_schema.get("exclusiveMinimum")
    if isinstance(exclusive_minimum, (int, float)) and not isinstance(exclusive_minimum, bool):
        field.add_validator(
            lambda value, limit=exclusive_minimum: value > limit,
            f"value must be > {exclusive_minimum}",
        )
    exclusive_maximum = sub_schema.get("exclusiveMaximum")
    if isinstance(exclusive_maximum, (int, float)) and not isinstance(exclusive_maximum, bool):
        field.add_validator(
            lambda value, limit=exclusive_maximum: value < limit,
            f"value must be < {exclusive_maximum}",
        )
    return field


def _json_float_field(sub_schema: Mapping[str, Any]) -> Float:
    minimum = sub_schema.get("minimum")
    maximum = sub_schema.get("maximum")
    field = Float(
        min_value=float(minimum) if isinstance(minimum, (int, float)) and not isinstance(minimum, bool) else None,
        max_value=float(maximum) if isinstance(maximum, (int, float)) and not isinstance(maximum, bool) else None,
    )
    exclusive_minimum = sub_schema.get("exclusiveMinimum")
    if isinstance(exclusive_minimum, (int, float)) and not isinstance(exclusive_minimum, bool):
        field.add_validator(
            lambda value, limit=exclusive_minimum: value > limit,
            f"value must be > {exclusive_minimum}",
        )
    exclusive_maximum = sub_schema.get("exclusiveMaximum")
    if isinstance(exclusive_maximum, (int, float)) and not isinstance(exclusive_maximum, bool):
        field.add_validator(
            lambda value, limit=exclusive_maximum: value < limit,
            f"value must be < {exclusive_maximum}",
        )
    return field


def _json_array_field(sub_schema: Mapping[str, Any]) -> List:
    items_schema = sub_schema.get("items")
    min_items = sub_schema.get("minItems")
    max_items = sub_schema.get("maxItems")
    kwargs: Dict[str, Any] = {
        "min_length": min_items if isinstance(min_items, int) else None,
        "max_length": max_items if isinstance(max_items, int) else None,
    }
    if items_schema is None:
        return List(Any(), **kwargs)
    item_field = _json_schema_type_to_field("items", items_schema)
    return List(item_field, **kwargs)


def _json_object_field(sub_schema: Mapping[str, Any]) -> Dict_:
    nested = json_schema({"type": "object", **sub_schema})
    return Dict_(schema=nested)


def from_json_schema(
    source: "str | Mapping[str, Any]",
    *,
    strict: bool = True,
) -> Schema:
    """Load a Schema from a JSON Schema string or dict.

    Accepts either a JSON string or an already-parsed dict. Same supported
    subset as :func:`json_schema`.

    Usage::

        schema = from_json_schema('{"type": "object", "properties": {...}}')
        schema = from_json_schema({"type": "object", ...})
    """
    if isinstance(source, str):
        import json as _json
        try:
            source = _json.loads(source)
        except _json.JSONDecodeError as exc:
            raise ValidationError(f"invalid JSON Schema string: {exc}") from exc
    schema = json_schema(source)
    if strict and not schema.strict:
        # Honor the explicit strict request from the caller.
        schema.strict = True
    return schema


# ---------- Async field (for validator+async-fn patterns) ----------


class AsyncField(Field):
    """A field that validates asynchronously.

    ``validator_fn`` is called with the value and must return ``None`` on success
    or an error ``str`` on failure. ``await`` is stripped automatically by
    :class:`AsyncValidator`.

    Example::

        from tiny_validator import AsyncField, AsyncValidator

        async def check_repo_exists(value: str) -> str | None:
            exists = await check_github(value)
            return None if exists else "repository not found"

        schema = AsyncValidator({
            "repo": AsyncField(validator_fn=check_repo_exists),
        })

        errors = await schema.validate({"repo": "hussain-alsaibai/nonexistent"})
    """

    def __init__(
        self,
        validator_fn: "Callable[[Any], Awaitable[str | None] | str | None]",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._validator = validator_fn

    def validate(self, value: Any, path: str) -> list[dict[str, Any]]:
        # Sync call — wrap in sync error if called directly
        return []  # async fields must be validated by AsyncValidator

    async def avalidate(self, value: Any, path: str) -> list[dict[str, Any]]:
        errors: list[dict[str, Any]] = []
        if value is _MISSING:
            if self.required and self.default is ...:
                errors.append({"path": path, "message": "missing required field"})
            return errors
        if value is None:
            if not self.allow_none:
                errors.append({"path": path, "message": "value is null"})
            return errors
        try:
            result = self._validator(value)
            if hasattr(result, "__await__"):
                result = await result
        except Exception as exc:  # noqa: BLE001
            errors.append({"path": path, "message": f"async validation error: {exc}"})
            return errors
        if result is not None:
            msg = result if isinstance(result, str) else "invalid"
            errors.append({"path": path, "message": msg})
        return errors


class AsyncValidator:
    """Async-aware schema validator.

    Works like :class:`Schema` but supports :class:`AsyncField` for fields that
    need to call external services (databases, APIs) during validation.

    Usage::

        from tiny_validator import AsyncField, AsyncValidator, fields

        async def validate_github(value: str) -> str | None:
            return None if await repo_exists(value) else "repo not found"

        v = AsyncValidator({
            "repo": AsyncField(validate_github),
            "limit": fields.Integer(default=10),
        })

        errors = await v.validate({"repo": "owner/name"})
    """

    def __init__(self, definition: Mapping[str, Field], *, strict: bool = False) -> None:
        self.definition = dict(definition)
        self.strict = strict

    async def validate(
        self,
        data: Mapping[str, Any],
        *,
        base_path: str = "",
    ) -> list[dict[str, Any]]:
        errors: list[dict[str, Any]] = []
        if not isinstance(data, MappingABC):
            return [{"path": base_path or "", "message": "expected object"}]

        if self.strict:
            extras = set(data.keys()) - set(self.definition.keys())
            for extra in extras:
                errors.append(
                    {
                        "path": f"{base_path}.{extra}" if base_path else extra,
                        "message": "unexpected field",
                    }
                )

        for key, field in self.definition.items():
            full_path = f"{base_path}.{key}" if base_path else key
            value = data.get(key, _MISSING)
            if value is _MISSING and field.default is not Ellipsis:
                value = field.default
            if isinstance(field, AsyncField):
                errors.extend(await field.avalidate(value, full_path))
            else:
                errors.extend(field.validate(value, full_path))

        return errors

    async def __call__(self, data: Mapping[str, Any]) -> dict[str, Any]:
        errors = await self.validate(data)
        if errors:
            raise ValidationError(errors)
        result: dict[str, Any] = dict(data)
        for key, field in self.definition.items():
            if key not in result and field.default is not Ellipsis:
                result[key] = field.default
        return result


from typing import Awaitable


__all__ = [
    "Schema",
    "PartialSchema",
    "Field",
    "ValidationError",
    "fields",
    "validate",
    "json_schema",
    "from_json_schema",
    "http_error_response",
    "AsyncField",
    "AsyncValidator",
    "Any",
    "String",
    "Integer",
    "Float",
    "Boolean",
    "List",
    "Dict",
    "Dict_",
    "Email",
    "Url",
    "Uuid",
    "Date",
    "DateTime",
    "Decimal",
    "Decimal_",
    "__version__",
]
