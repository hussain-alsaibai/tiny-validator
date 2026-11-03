import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rules import (
    Computed,
    CrossFieldError,
    Rule,
    RuleError,
    apply_computed,
    check_rules,
)


class TestRule(unittest.TestCase):
    def test_passing_rule_returns_no_error(self):
        rule = Rule(lambda d: d["start"] <= d["end"], "start must be <= end")
        self.assertIsNone(rule.evaluate({"start": 1, "end": 5}))

    def test_failing_rule_returns_error(self):
        rule = Rule(lambda d: d["start"] <= d["end"], "start must be <= end")
        err = rule.evaluate({"start": 9, "end": 5})
        self.assertIsInstance(err, RuleError)
        self.assertEqual(err.message, "start must be <= end")

    def test_rule_path_is_carried(self):
        rule = Rule(lambda d: False, "boom", path="range")
        err = rule.evaluate({})
        self.assertEqual(err.path, "range")

    def test_rule_raising_cross_field_error_is_caught(self):
        def check(d):
            raise CrossFieldError("custom message")

        err = Rule(check, "fallback").evaluate({})
        self.assertEqual(err.message, "custom message")

    def test_rule_raising_assertion_error_is_caught(self):
        def check(d):
            assert d["a"] < d["b"], "a must be less than b"

        err = Rule(check, "fallback").evaluate({"a": 2, "b": 1})
        # Python appends the failed expression to an assert message, so the
        # text is a prefix, not an exact match.
        self.assertTrue(err.message.startswith("a must be less than b"))
        self.assertIsNotNone(err)

    def test_rule_raising_other_exception_propagates(self):
        def check(d):
            raise KeyError("missing")

        with self.assertRaises(KeyError):
            Rule(check, "x").evaluate({})

    def test_rule_requires_callable(self):
        with self.assertRaises(TypeError):
            Rule("not callable", "x")

    def test_rule_names_are_unique(self):
        a = Rule(lambda d: True)
        b = Rule(lambda d: True)
        self.assertNotEqual(a.name, b.name)

    def test_rule_accepts_explicit_name(self):
        self.assertEqual(Rule(lambda d: True, name="mine").name, "mine")


class TestCheckRules(unittest.TestCase):
    def test_no_rules_passes(self):
        self.assertEqual(check_rules({"a": 1}, []), [])

    def test_all_rules_pass(self):
        rules = [Rule(lambda d: True, "a"), Rule(lambda d: True, "b")]
        self.assertEqual(check_rules({}, rules), [])

    def test_one_failure_reported(self):
        rules = [Rule(lambda d: True, "a"), Rule(lambda d: False, "b")]
        errors = check_rules({}, rules)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["message"], "b")

    def test_error_shape_matches_schema_errors(self):
        errors = check_rules({}, [Rule(lambda d: False, "boom", path="p")])
        self.assertEqual(set(errors[0].keys()), {"path", "message"})
        self.assertEqual(errors[0]["path"], "p")

    def test_all_failures_reported(self):
        rules = [Rule(lambda d: False, "a"), Rule(lambda d: False, "b")]
        errors = check_rules({}, rules)
        self.assertEqual([e["message"] for e in errors], ["a", "b"])


class TestComputed(unittest.TestCase):
    def test_requires_callable(self):
        with self.assertRaises(TypeError):
            Computed("nope")

    def test_compute_calls_the_callable(self):
        c = Computed(lambda d: d["a"] * 2)
        self.assertEqual(c.compute({"a": 3}), 6)

    def test_set_name_records_the_field_name(self):
        class Holder:
            total = Computed(lambda d: 1)

        self.assertEqual(Holder.total.name, "total")

    def test_repr_mentions_name(self):
        c = Computed(lambda d: 1)
        c.name = "x"
        self.assertIn("x", repr(c))


class TestApplyComputed(unittest.TestCase):
    def test_adds_computed_field(self):
        out = apply_computed({"a": 1}, {"double": lambda d: d["a"] * 2})
        self.assertEqual(out, {"a": 1, "double": 2})

    def test_does_not_mutate_source(self):
        src = {"a": 1}
        apply_computed(src, {"double": lambda d: d["a"] * 2})
        self.assertEqual(src, {"a": 1})

    def test_no_computed_fields_returns_copy(self):
        src = {"a": 1}
        out = apply_computed(src, {})
        self.assertEqual(out, src)
        self.assertIsNot(out, src)

    def test_computed_fields_resolve_in_order(self):
        out = apply_computed(
            {"n": 2},
            {
                "squared": lambda d: d["n"] ** 2,
                "plus_one": lambda d: d["squared"] + 1,
            },
        )
        self.assertEqual(out["squared"], 4)
        self.assertEqual(out["plus_one"], 5)

    def test_non_callable_raises(self):
        with self.assertRaises(TypeError):
            apply_computed({}, {"bad": "not callable"})


if __name__ == "__main__":
    unittest.main()
