"""Regression tests for v0.6.0 constraint-export fixes.

Previously _schema_to_json_schema recovered min/max/length constraints by
parsing human-readable validator message strings. That silently dropped
choices and pattern, and could invent constraints from unrelated prose.
Fields now record constraints at construction time and the exporter reads
those directly.
"""

import pytest

from tiny_validator import (
    Float,
    Integer,
    List,
    Schema,
    String,
    from_json_schema,
    to_json_schema,
    to_openapi_schema,
)


def prop(schema, key):
    return to_json_schema(schema)["properties"][key]


@pytest.mark.parametrize(
    "field,expected",
    [
        (String(min_length=2, max_length=8), {"type": "string", "minLength": 2, "maxLength": 8}),
        (String(choices=["a", "b"]), {"type": "string", "enum": ["a", "b"]}),
        (String(pattern=r"[0-9]+"), {"type": "string", "pattern": r"[0-9]+"}),
        (
            String(min_length=1, choices=["x"]),
            {"type": "string", "minLength": 1, "enum": ["x"]},
        ),
    ],
)
def test_string_constraints_export(field, expected):
    assert prop(Schema({"a": field}), "a") == expected


@pytest.mark.parametrize(
    "field,expected",
    [
        (Integer(min_value=1, max_value=9), {"type": "integer", "minimum": 1, "maximum": 9}),
        (Integer(choices=[1, 2]), {"type": "integer", "enum": [1, 2]}),
        (
            Integer(min_value=0, choices=[0, 5]),
            {"type": "integer", "minimum": 0, "enum": [0, 5]},
        ),
    ],
)
def test_integer_constraints_export(field, expected):
    assert prop(Schema({"a": field}), "a") == expected


def test_float_constraints_export():
    assert prop(Schema({"a": Float(min_value=0.5)}), "a") == {"type": "number", "minimum": 0.5}


def test_list_constraints_export():
    got = prop(Schema({"a": List(String(), min_length=1, max_length=3)}), "a")
    assert got == {
        "type": "array",
        "items": {"type": "string"},
        "minItems": 1,
        "maxItems": 3,
    }


def test_arbitrary_validator_message_does_not_invent_constraints():
    """Prose in a custom validator message must not become a JSON Schema limit."""
    field = String()
    field.add_validator(lambda v: True, "must be at least 999 characters of prose")
    assert prop(Schema({"a": field}), "a") == {"type": "string"}


def test_custom_validator_message_without_bounds_is_ignored():
    field = Integer()
    field.add_validator(lambda v: v % 2 == 0, "value must be <= 1000 for no reason")
    assert "maximum" not in prop(Schema({"a": field}), "a")


def test_enum_round_trips_through_json_schema():
    original = Schema({"role": String(choices=["admin", "user"])})
    restored = from_json_schema(to_json_schema(original))
    assert restored.validate({"role": "nope"})
    assert not restored.validate({"role": "admin"})


def test_pattern_round_trips_through_json_schema():
    original = Schema({"code": String(pattern=r"[0-9]{3}")})
    restored = from_json_schema(to_json_schema(original))
    assert restored.validate({"code": "abc"})
    assert not restored.validate({"code": "123"})


def test_constraints_available_as_public_attribute():
    field = String(min_length=1, max_length=4, choices=["ab", "cd"])
    assert field.constraints == {"minLength": 1, "maxLength": 4, "enum": ["ab", "cd"]}


def test_constraints_property_returns_a_copy():
    field = String(min_length=1)
    snapshot = field.constraints
    snapshot["minLength"] = 999
    assert field.constraints["minLength"] == 1


def test_plain_field_has_empty_constraints():
    assert String().constraints == {}


def test_openapi_export_includes_constraints():
    got = to_openapi_schema(Schema({"role": String(choices=["admin"])}), title="User")
    assert got["properties"]["role"]["enum"] == ["admin"]
    assert got["title"] == "User"


def test_description_still_exported_alongside_constraints():
    got = prop(Schema({"a": String(min_length=1, description="Some text")}), "a")
    assert got["description"] == "Some text"
    assert got["minLength"] == 1


def test_default_still_exported_alongside_constraints():
    field = String(min_length=1, default="abc")
    field.required = False
    got = prop(Schema({"a": field}), "a")
    assert got["default"] == "abc"
    assert got["minLength"] == 1

