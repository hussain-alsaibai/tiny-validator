"""Cross-field validation rules for tiny-validator.

Schema validation answers "is each field individually well-formed?". This
module answers the question a schema cannot: "are these fields consistent
with each other?".

Usage::

    from tiny_validator import Schema, String, Integer
    from rules import Rule

    errors = check_rules(data, [
        Rule(lambda d: d["start"] <= d["end"], "start must be <= end"),
    ])

Computed fields derive a value from the validated data::

    result = apply_computed(data, {
        "full_name": lambda d: d["first"] + " " + d["last"],
    })

Stdlib only. Zero dependencies.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

__all__ = [
    "Computed",
    "CrossFieldError",
    "Rule",
    "RuleError",
    "apply_computed",
    "check_rules",
]


class CrossFieldError(Exception):
    """Raised when a cross-field rule fails."""


class RuleError:
    """A rule failure, shaped like the error dicts a Schema returns."""

    __slots__ = ("path", "message", "rule")

    def __init__(self, path: str, message: str, rule: Optional["Rule"] = None) -> None:
        self.path = path
        self.message = message
        self.rule = rule

    def to_dict(self) -> Dict[str, Any]:
        return {"path": self.path, "message": self.message}

    def __repr__(self) -> str:
        return "RuleError(path=%r, message=%r)" % (self.path, self.message)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RuleError):
            return NotImplemented
        return self.path == other.path and self.message == other.message


class Rule:
    """A cross-field validation rule.

    Args:
        check: Callable that receives the validated data mapping. Returns True
            if the rule passes; returns False or raises to fail.
        message: Error message used when the rule fails.
        path: Error path the failure is reported at. Defaults to "".
        name: Optional name for debugging. Auto-generated when omitted.

    Example::

        Rule(lambda d: d["start"] <= d["end"], "start must precede end")
    """

    _counter: int = 0

    def __init__(
        self,
        check: Callable[[Mapping[str, Any]], bool],
        message: str = "",
        *,
        path: str = "",
        name: Optional[str] = None,
    ) -> None:
        if not callable(check):
            raise TypeError("Rule() requires a callable, got %s" % type(check).__name__)
        self.check = check
        self.message = message
        self.path = path
        if name is None:
            type(self)._counter += 1
            self.name = "rule_%d" % type(self)._counter
        else:
            self.name = name

    def evaluate(self, data: Mapping[str, Any]) -> Optional[RuleError]:
        """Run the rule. Returns a RuleError on failure, None on success."""
        try:
            ok = self.check(data)
        except CrossFieldError as exc:
            return RuleError(self.path, str(exc) or self.message, self)
        except AssertionError as exc:
            return RuleError(self.path, str(exc) or self.message, self)
        if ok is False:
            return RuleError(self.path, self.message, self)
        return None

    def __repr__(self) -> str:
        return "Rule(name=%r, path=%r)" % (self.name, self.path)


class Computed:
    """A field whose value is derived from the other validated fields.

    The callable receives the validated data mapping and returns the value.
    Computed fields are not part of a schema field definition; they are
    resolved after validation succeeds.

    Example::

        full_name = Computed(lambda d: d["first"] + " " + d["last"])
    """

    __slots__ = ("fn", "name")

    def __init__(self, fn: Callable[[Mapping[str, Any]], Any]) -> None:
        if not callable(fn):
            raise TypeError("Computed() requires a callable, got %s" % type(fn).__name__)
        self.fn = fn
        self.name: Optional[str] = None

    def __set_name__(self, owner: Any, name: str) -> None:
        self.name = name

    def compute(self, data: Mapping[str, Any]) -> Any:
        return self.fn(data)

    def __repr__(self) -> str:
        return "Computed(name=%r)" % (self.name,)


def check_rules(
    data: Mapping[str, Any],
    rules: Sequence[Rule],
) -> List[Dict[str, Any]]:
    """Run every rule against data and return the failures.

    Returns a list of error dicts shaped like the ones a Schema returns:
    ``[{"path": ..., "message": ...}, ...]``. An empty list means every rule
    passed.
    """
    errors: List[Dict[str, Any]] = []
    for rule in rules:
        failure = rule.evaluate(data)
        if failure is not None:
            errors.append(failure.to_dict())
    return errors


def apply_computed(
    data: Mapping[str, Any],
    computed: Mapping[str, Callable[[Mapping[str, Any]], Any]],
) -> Dict[str, Any]:
    """Return a copy of data with the computed fields resolved.

    Computed fields are resolved in insertion order, so a later computed
    field can read an earlier one.
    """
    result: Dict[str, Any] = dict(data)
    for name, fn in computed.items():
        if not callable(fn):
            raise TypeError("computed field %r is not callable" % name)
        result[name] = fn(result)
    return result
