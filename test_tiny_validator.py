"""Tests for tiny_validator. Run with: python test_tiny_validator.py"""

from __future__ import annotations

import unittest

from tiny_validator import (
    Boolean,
    Date,
    DateTime,
    Decimal,
    Dict,
    Email,
    Field,
    Float,
    Integer,
    List,
    Schema,
    String,
    Url,
    Uuid,
    ValidationError,
    fields,
    from_json_schema,
    http_error_response,
    validate,
)


class TestPrimitives(unittest.TestCase):
    def test_string_ok(self) -> None:
        s = Schema({"name": String(min_length=1, max_length=5)})
        self.assertEqual(s.validate({"name": "abc"}), [])

    def test_string_too_short(self) -> None:
        s = Schema({"name": String(min_length=5)})
        errs = s.validate({"name": "ab"})
        self.assertEqual(len(errs), 1)
        self.assertIn("5 characters", errs[0]["message"])

    def test_string_too_long(self) -> None:
        s = Schema({"name": String(max_length=2)})
        errs = s.validate({"name": "abc"})
        self.assertEqual(len(errs), 1)

    def test_string_type(self) -> None:
        s = Schema({"name": String()})
        errs = s.validate({"name": 42})
        self.assertEqual(len(errs), 1)
        self.assertEqual(errs[0]["message"], "expected string")

    def test_string_choices(self) -> None:
        s = Schema({"role": String(choices=["a", "b"])})
        self.assertEqual(s.validate({"role": "a"}), [])
        self.assertEqual(len(s.validate({"role": "c"})), 1)

    def test_string_pattern(self) -> None:
        s = Schema({"slug": String(pattern=r"^[a-z0-9-]+$")})
        self.assertEqual(s.validate({"slug": "abc-123"}), [])
        self.assertEqual(len(s.validate({"slug": "ABC"})), 1)

    def test_integer(self) -> None:
        s = Schema({"n": Integer(min_value=0, max_value=10)})
        self.assertEqual(s.validate({"n": 5}), [])
        self.assertEqual(len(s.validate({"n": 11})), 1)
        self.assertEqual(len(s.validate({"n": "5"})), 1)

    def test_integer_rejects_bool(self) -> None:
        s = Schema({"n": Integer()})
        errs = s.validate({"n": True})
        self.assertEqual(len(errs), 1)

    def test_float(self) -> None:
        s = Schema({"x": Float(min_value=0.0, max_value=1.0)})
        self.assertEqual(s.validate({"x": 0.5}), [])
        self.assertEqual(len(s.validate({"x": 2.0})), 1)

    def test_boolean(self) -> None:
        s = Schema({"on": Boolean()})
        self.assertEqual(s.validate({"on": True}), [])
        self.assertEqual(len(s.validate({"on": "yes"})), 1)


class TestRequiredAndDefault(unittest.TestCase):
    def test_required_missing(self) -> None:
        s = Schema({"x": Integer()})
        errs = s.validate({})
        self.assertEqual(len(errs), 1)
        self.assertIn("missing", errs[0]["message"])

    def test_optional_missing_ok(self) -> None:
        s = Schema({"x": Integer(required=False)})
        self.assertEqual(s.validate({}), [])

    def test_default(self) -> None:
        s = Schema({"x": Integer(default=10)})
        result = s({"x": 5})  # call to materialize defaults
        self.assertEqual(result["x"], 5)

    def test_default_when_missing(self) -> None:
        s = Schema({"x": Integer(default=42)})
        result = s({})
        self.assertEqual(result["x"], 42)


class TestComposite(unittest.TestCase):
    def test_list_with_items(self) -> None:
        s = Schema({"ids": List(Integer(), min_length=1, max_length=3)})
        self.assertEqual(s.validate({"ids": [1, 2]}), [])
        errs = s.validate({"ids": []})
        self.assertEqual(len(errs), 1)
        errs = s.validate({"ids": [1, 2, 3, 4]})
        self.assertEqual(len(errs), 1)
        errs = s.validate({"ids": [1, "x"]})
        self.assertEqual(len(errs), 1)
        # Error path includes index
        self.assertIn("[1]", errs[0]["path"])

    def test_list_unique(self) -> None:
        s = Schema({"ids": List(Integer(), unique=True)})
        self.assertEqual(s.validate({"ids": [1, 2, 3]}), [])
        self.assertEqual(len(s.validate({"ids": [1, 1]})), 1)

    def test_nested_dict(self) -> None:
        nested = Schema({"name": String()})
        s = Schema({"user": Dict(schema=nested)})
        self.assertEqual(s.validate({"user": {"name": "alice"}}), [])
        errs = s.validate({"user": {"name": 123}})
        self.assertEqual(len(errs), 1)
        self.assertIn("user.name", errs[0]["path"])

    def test_strict(self) -> None:
        s = Schema({"x": Integer()}, strict=True)
        errs = s.validate({"x": 1, "y": 2})
        self.assertEqual(len(errs), 1)
        self.assertIn("y", errs[0]["path"])


class TestSpecializedStrings(unittest.TestCase):
    def test_email(self) -> None:
        s = Schema({"e": Email()})
        self.assertEqual(s.validate({"e": "a@b.co"}), [])
        self.assertEqual(len(s.validate({"e": "nope"})), 1)

    def test_url(self) -> None:
        s = Schema({"u": Url()})
        self.assertEqual(s.validate({"u": "https://x.io"}), [])
        self.assertEqual(len(s.validate({"u": "ftp://x"})), 1)

    def test_uuid(self) -> None:
        s = Schema({"id": Uuid()})
        self.assertEqual(s.validate({"id": "12345678-1234-1234-1234-123456789abc"}), [])
        self.assertEqual(len(s.validate({"id": "nope"})), 1)

    def test_date(self) -> None:
        s = Schema({"d": Date()})
        self.assertEqual(s.validate({"d": "2026-06-29"}), [])
        self.assertEqual(len(s.validate({"d": "2026-13-01"})), 1)
        self.assertEqual(len(s.validate({"d": "not-a-date"})), 1)

    def test_datetime(self) -> None:
        s = Schema({"t": DateTime()})
        self.assertEqual(s.validate({"t": "2026-06-29T12:00:00"}), [])
        self.assertEqual(s.validate({"t": "2026-06-29 12:00:00"}), [])
        self.assertEqual(s.validate({"t": "2026-06-29T12:00:00Z"}), [])


class TestDecimal(unittest.TestCase):
    def test_decimal_from_string(self) -> None:
        s = Schema({"price": Decimal(min_value=0)})
        self.assertEqual(s.validate({"price": "9.99"}), [])
        self.assertEqual(len(s.validate({"price": "-1"})), 1)

    def test_decimal_from_number(self) -> None:
        s = Schema({"price": Decimal()})
        self.assertEqual(s.validate({"price": 9.99}), [])

    def test_decimal_invalid(self) -> None:
        s = Schema({"price": Decimal()})
        self.assertEqual(len(s.validate({"price": "abc"})), 1)


class TestErrors(unittest.TestCase):
    def test_validation_error_str(self) -> None:
        s = Schema({"x": Integer()})
        try:
            s({"x": "nope"})
        except ValidationError as exc:
            self.assertIn("x", str(exc))
            self.assertEqual(len(exc.errors), 1)
            d = exc.to_dict()
            self.assertEqual(d["error"], "validation_failed")
            self.assertIn("details", d)
            return
        self.fail("expected ValidationError")

    def test_http_error_response(self) -> None:
        s = Schema({"x": Integer()})
        try:
            s({"x": "nope"})
        except ValidationError as exc:
            d = http_error_response(exc)
            self.assertEqual(d["error"], "validation_failed")
            return
        self.fail("expected ValidationError")


class TestDecorator(unittest.TestCase):
    def test_decorator_validates_body(self) -> None:
        schema = Schema({"name": String()})

        @validate(body=schema)
        def handler(body: dict) -> dict:
            return {"name": body["name"]}

        result = handler(body={"name": "alice"})
        self.assertEqual(result, {"name": "alice"})

        with self.assertRaises(ValidationError):
            handler(body={"name": 42})

    def test_decorator_validates_multiple_parts(self) -> None:
        body_schema = Schema({"name": String()})
        query_schema = Schema({"q": String()})

        @validate(body=body_schema, query=query_schema)
        def handler(body: dict, query: dict) -> dict:
            return {"name": body["name"], "q": query["q"]}

        result = handler(body={"name": "a"}, query={"q": "b"})
        self.assertEqual(result, {"name": "a", "q": "b"})

        with self.assertRaises(ValidationError):
            handler(body={"name": "a"}, query={})


class TestJsonSchemaBridge(unittest.TestCase):
    def test_from_json_schema_validates_tool_arguments(self) -> None:
        schema = from_json_schema(
            {
                "type": "object",
                "required": ["query", "limit", "source"],
                "properties": {
                    "query": {"type": "string", "minLength": 3, "maxLength": 80},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 10},
                    "source": {"type": "string", "enum": ["github", "docs", "web"]},
                    "include_archived": {"type": "boolean", "default": False},
                },
                "additionalProperties": False,
            }
        )

        result = schema({"query": "tiny router", "limit": 5, "source": "github"})
        self.assertEqual(result["include_archived"], False)
        self.assertEqual(schema.validate({"query": "tiny router", "limit": 5, "source": "github"}), [])

        errors = schema.validate({"query": "x", "limit": 11, "source": "email", "extra": True})
        messages = [error["message"] for error in errors]
        self.assertIn("unexpected field", messages)
        self.assertTrue(any("at least 3" in message for message in messages))
        self.assertTrue(any("<= 10" in message for message in messages))
        self.assertTrue(any("one of" in message for message in messages))

    def test_from_json_schema_supports_nested_arrays_and_formats(self) -> None:
        schema = from_json_schema(
            {
                "type": "object",
                "required": ["owner", "targets"],
                "properties": {
                    "owner": {"type": "string", "format": "email"},
                    "targets": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "required": ["url"],
                            "properties": {"url": {"type": "string", "format": "uri"}},
                        },
                    },
                },
            }
        )

        self.assertEqual(
            schema.validate({"owner": "ops@example.com", "targets": [{"url": "https://example.com"}]}),
            [],
        )
        self.assertEqual(len(schema.validate({"owner": "bad", "targets": []})), 2)

    def test_from_json_schema_rejects_unknown_keywords(self) -> None:
        with self.assertRaises(ValueError):
            from_json_schema(
                {
                    "type": "object",
                    "properties": {"name": {"type": "string", "const": "fixed"}},
                }
            )


class TestFieldsNS(unittest.TestCase):
    def test_fields_namespace(self) -> None:
        self.assertIs(fields.String, String)
        self.assertIs(fields.Integer, Integer)
        self.assertIs(fields.Email, Email)
        self.assertIs(fields.Dict, Dict)


if __name__ == "__main__":
    unittest.main(verbosity=2)
