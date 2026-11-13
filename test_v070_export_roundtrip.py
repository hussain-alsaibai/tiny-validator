"""v0.7.2 — the exported JSON Schema must be as strict as the Schema.

v0.6.0 fixed `choices` and `pattern` for `String`/`Integer`. v0.7.1
Three field types were missed and exported as a bare `{"type": "string"}`:
`Slug`, `Regex` and `HexColor`. `IP` exported nothing at all, and
`from_json_schema('format: ipv4')` built a plain `String`, so the round-trip
accepted `999.1.1.1` — a value the exported document itself forbids.

Every test here is a round-trip: export, import, then feed a value the
original Schema rejects and assert the imported Schema rejects it too.
Asserting only on the exported dict would let the import side drift.
"""

import unittest

import tiny_validator as tv
from tiny_validator import Schema, fields


def roundtrip(field):
    """Schema -> JSON Schema -> Schema."""
    return tv.from_json_schema(tv.to_json_schema(Schema({"v": field})))


def prop(field):
    return tv.to_json_schema(Schema({"v": field}))["properties"]["v"]


def rejects(schema, value):
    try:
        schema({"v": value})
    except tv.ValidationError:
        return True
    return False


def accepts(schema, value):
    try:
        schema({"v": value})
        return True
    except tv.ValidationError:
        return False


class TestPatternSurvivesExport(unittest.TestCase):
    def test_slug_exports_its_pattern(self):
        self.assertIn("pattern", prop(fields.Slug()))

    def test_slug_roundtrip_rejects_bad_slug(self):
        self.assertTrue(rejects(roundtrip(fields.Slug()), "Not A Slug"))
        self.assertTrue(accepts(roundtrip(fields.Slug()), "a-good-slug-2"))

    def test_regex_exports_the_caller_pattern(self):
        self.assertEqual(prop(fields.Regex(r"^\d+$"))["pattern"], r"^\d+$")

    def test_regex_roundtrip_rejects_non_matching(self):
        self.assertTrue(rejects(roundtrip(fields.Regex(r"^\d+$")), "abc"))
        self.assertTrue(accepts(roundtrip(fields.Regex(r"^\d+$")), "123"))

    def test_hexcolor_roundtrip(self):
        self.assertTrue(rejects(roundtrip(fields.HexColor()), "not-a-color"))
        self.assertTrue(accepts(roundtrip(fields.HexColor()), "#ff8800"))

    def test_regex_flags_do_not_leak_into_pattern(self):
        # re.compile(..., flags) returns a Pattern; the constraint must be the
        # original source string, not `str(compiled)`.
        self.assertEqual(prop(fields.Regex(r"^abc$", flags=2))["pattern"], r"^abc$")


class TestIpFormat(unittest.TestCase):
    def test_versioned_ip_exports_a_format(self):
        self.assertEqual(prop(fields.IP(version=4)).get("format"), "ipv4")
        self.assertEqual(prop(fields.IP(version=6)).get("format"), "ipv6")

    def test_unversioned_ip_promises_nothing_it_cannot_enforce(self):
        # No standard JSON Schema format covers v4-or-v6, so the export must
        # not claim `format: ip` that no consumer validates.
        self.assertNotIn("format", prop(fields.IP()))

    def test_ipv4_roundtrip_rejects_ipv6_and_garbage(self):
        schema = roundtrip(fields.IP(version=4))
        self.assertTrue(rejects(schema, "::1"))
        self.assertTrue(rejects(schema, "999.1.1.1"))
        self.assertTrue(accepts(schema, "10.0.0.1"))

    def test_ipv6_roundtrip_rejects_ipv4(self):
        schema = roundtrip(fields.IP(version=6))
        self.assertTrue(rejects(schema, "10.0.0.1"))
        self.assertTrue(accepts(schema, "::1"))

    def test_import_of_format_ipv4_directly(self):
        schema = tv.from_json_schema(
            {"type": "object", "properties": {"v": {"type": "string", "format": "ipv4"}}}
        )
        self.assertTrue(rejects(schema, "999.1.1.1"))


class TestAlreadyCoveredStaysCovered(unittest.TestCase):
    """Guards for the v0.6.0 behaviour, so a v0.6.1 refactor cannot undo it."""

    def test_string_choices_and_bounds(self):
        field = fields.String(min_length=2, max_length=4, choices=["ab", "abc"])
        self.assertEqual(prop(field)["enum"], ["ab", "abc"])
        self.assertEqual(prop(field)["minLength"], 2)
        self.assertEqual(prop(field)["maxLength"], 4)

    def test_strict_flag_survives(self):
        out = tv.to_json_schema(Schema({"v": fields.String()}, strict=True))
        self.assertIs(out["additionalProperties"], False)

    def test_nested_object_and_array_items(self):
        field = fields.List(fields.Dict(schema=Schema({"city": fields.String(min_length=2)})))
        self.assertEqual(
            prop(field)["items"]["properties"]["city"],
            {"type": "string", "minLength": 2},
        )


if __name__ == "__main__":
    unittest.main()
