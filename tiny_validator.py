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


__version__ = "0.1.0"


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


__all__ = [
    "Schema",
    "Field",
    "ValidationError",
    "fields",
    "validate",
    "http_error_response",
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
