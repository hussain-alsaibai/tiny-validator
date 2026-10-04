"""v0.4.0 — Tests for to_json_schema() and to_openapi_schema()."""
from __future__ import annotations

import unittest

from tiny_validator import (
    Boolean,
    DateTime,
    Dict,
    Email,
    Integer,
    List,
    Schema,
    String,
    Url,
    Uuid,
    fields,
    from_json_schema,
    to_json_schema,
    to_openapi_schema,
)


class TestToJsonSchema(unittest.TestCase):
    def test_basic_string(self) -> None:
        s = Schema({"name": String(min_length=1, max_length=100)})
        out = to_json_schema(s)
        self.assertEqual(out["type"], "object")
        self.assertEqual(out["properties"]["name"]["type"], "string")
        self.assertEqual(out["properties"]["name"]["minLength"], 1)
        self.assertEqual(out["properties"]["name"]["maxLength"], 100)
        self.assertEqual(out["required"], ["name"])

    def test_integer_with_bounds(self) -> None:
        s = Schema({"age": Integer(min_value=0, max_value=150, required=False)})
        out = to_json_schema(s)
        self.assertEqual(out["properties"]["age"]["type"], "integer")
        self.assertEqual(out["properties"]["age"]["minimum"], 0)
        self.assertEqual(out["properties"]["age"]["maximum"], 150)
        # When all fields are optional, "required" is omitted entirely.
        self.assertNotIn("required", out)

    def test_email_format(self) -> None:
        s = Schema({"email": Email()})
        out = to_json_schema(s)
        self.assertEqual(out["properties"]["email"]["type"], "string")
        self.assertEqual(out["properties"]["email"]["format"], "email")

    def test_url_format(self) -> None:
        s = Schema({"homepage": Url()})
        out = to_json_schema(s)
        self.assertEqual(out["properties"]["homepage"]["format"], "uri")

    def test_uuid_format(self) -> None:
        s = Schema({"id": Uuid()})
        out = to_json_schema(s)
        self.assertEqual(out["properties"]["id"]["format"], "uuid")

    def test_datetime_format(self) -> None:
        s = Schema({"ts": DateTime()})
        out = to_json_schema(s)
        self.assertEqual(out["properties"]["ts"]["format"], "date-time")

    def test_boolean(self) -> None:
        s = Schema({"active": Boolean()})
        out = to_json_schema(s)
        self.assertEqual(out["properties"]["active"]["type"], "boolean")

    def test_default_value(self) -> None:
        s = Schema({"role": String(default="user", required=False)})
        out = to_json_schema(s)
        self.assertEqual(out["properties"]["role"]["default"], "user")

    def test_strict_mode(self) -> None:
        s = Schema({"a": String()}, strict=True)
        out = to_json_schema(s)
        self.assertEqual(out["additionalProperties"], False)

    def test_non_strict_no_additional(self) -> None:
        s = Schema({"a": String()})
        out = to_json_schema(s)
        self.assertNotIn("additionalProperties", out)

    def test_required_only_required_fields(self) -> None:
        s = Schema({
            "name": String(),
            "age": Integer(required=False),
            "email": String(),
        })
        out = to_json_schema(s)
        self.assertEqual(sorted(out["required"]), ["email", "name"])

    def test_nested_dict(self) -> None:
        s = Schema({
            "user": Dict(schema=Schema({
                "id": Uuid(),
            })),
        })
        out = to_json_schema(s)
        self.assertEqual(out["properties"]["user"]["type"], "object")
        self.assertEqual(
            out["properties"]["user"]["properties"]["id"]["format"], "uuid"
        )

    def test_list_of_strings(self) -> None:
        s = Schema({"tags": List(String())})
        out = to_json_schema(s)
        self.assertEqual(out["properties"]["tags"]["type"], "array")
        self.assertEqual(out["properties"]["tags"]["items"]["type"], "string")

    def test_list_of_urls(self) -> None:
        s = Schema({"urls": List(Url())})
        out = to_json_schema(s)
        self.assertEqual(out["properties"]["urls"]["items"]["format"], "uri")

    def test_no_required_when_all_optional(self) -> None:
        s = Schema({"a": String(required=False)})
        out = to_json_schema(s)
        self.assertNotIn("required", out)

    def test_empty_schema(self) -> None:
        s = Schema({})
        out = to_json_schema(s)
        self.assertEqual(out, {"type": "object", "properties": {}})


class TestToOpenAPISchema(unittest.TestCase):
    def test_basic_wrap(self) -> None:
        s = Schema({"name": String()})
        out = to_openapi_schema(s, title="User")
        self.assertEqual(out["title"], "User")
        self.assertIn("$schema", out)
        self.assertEqual(
            out["$schema"],
            "https://json-schema.org/draft/2020-12/schema",
        )

    def test_description(self) -> None:
        s = Schema({"name": String()})
        out = to_openapi_schema(s, description="A user record.")
        self.assertEqual(out["description"], "A user record.")

    def test_required_override(self) -> None:
        s = Schema({"a": String(required=False)})
        out = to_openapi_schema(s, required_override=["a"])
        self.assertEqual(out["required"], ["a"])

    def test_default_title(self) -> None:
        s = Schema({"name": String()})
        out = to_openapi_schema(s)
        self.assertEqual(out["title"], "Model")


class TestRoundTrip(unittest.TestCase):
    """A Schema exported to JSON Schema and re-imported validates equivalently."""

    def test_basic_round_trip(self) -> None:
        original = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "minLength": 1, "maxLength": 100},
                "email": {"type": "string", "format": "email"},
            },
            "required": ["name", "email"],
        }
        schema = from_json_schema(original)
        exported = to_json_schema(schema)
        schema2 = from_json_schema(exported)
        good = {"name": "Alice", "email": "alice@example.com"}
        self.assertEqual(schema2.validate(good), [])
        bad = {"name": "", "email": "not-an-email"}
        errs = schema2.validate(bad)
        self.assertGreater(len(errs), 0)

    def test_round_trip_preserves_strict(self) -> None:
        original = {
            "type": "object",
            "properties": {"a": {"type": "string"}},
            "required": ["a"],
            "additionalProperties": False,
        }
        schema = from_json_schema(original)
        exported = to_json_schema(schema)
        self.assertEqual(exported["additionalProperties"], False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
