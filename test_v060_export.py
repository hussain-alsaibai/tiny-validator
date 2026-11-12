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

# ---------- v0.7.1: export must not contradict validation ----------


def test_default_field_is_not_declared_required():
    """A defaulted field is optional; required= must not name it.

    validate() only reports "missing required field" when
    `required and default is ...`, so a field constructed as
    List(String(), default=[]) is optional in practice. The exporter read
    field.required alone and emitted it in `required`, producing a JSON
    Schema that rejected payloads this library accepts.
    """
    got = to_json_schema(Schema({"tags": List(String(), default=[])}))
    assert "required" not in got or "tags" not in got["required"]


def test_required_without_default_still_declared():
    got = to_json_schema(Schema({"name": String(required=True)}))
    assert got["required"] == ["name"]


def test_explicit_optional_not_declared_required():
    got = to_json_schema(Schema({"n": String(required=False)}))
    assert "required" not in got or "n" not in got["required"]


@pytest.mark.parametrize(
    "schema,payload",
    [
        (Schema({"tags": List(String(), default=[])}), {}),
        (Schema({"tags": List(String(), default=[])}), {"tags": ["a"]}),
        (Schema({"name": String(required=True)}), {"name": "a"}),
        (Schema({"n": String(required=False)}), {}),
    ],
)
def test_export_agrees_with_validate(schema, payload):
    """tiny_validator and the exported JSON Schema must agree on accept/reject."""
    jsonschema = pytest.importorskip("jsonschema")
    exported = to_json_schema(schema)

    library_ok = not schema.validate(payload)
    try:
        jsonschema.validate(payload, exported)
        jsonschema_ok = True
    except jsonschema.ValidationError:
        jsonschema_ok = False

    assert library_ok == jsonschema_ok, (
        f"disagreement on {payload!r}:\n"
        f"  tiny_validator accepted={library_ok}\n"
        f"  exported schema accepted={jsonschema_ok}\n"
        f"  schema={exported}"
    )


def test_required_and_optional_mixed():
    got = to_json_schema(
        Schema(
            {
                "name": String(required=True),
                "nick": String(default="anon"),
                "age": Integer(required=False),
            }
        )
    )
    assert got["required"] == ["name"]
    assert got["properties"]["nick"]["default"] == "anon"
