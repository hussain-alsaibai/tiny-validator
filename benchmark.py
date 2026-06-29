"""Micro-benchmark for tiny_validator."""

from __future__ import annotations

import time

from tiny_validator import Schema, fields


def main() -> None:
    schema = Schema(
        {
            "name": fields.String(min_length=1, max_length=100),
            "email": fields.Email(),
            "age": fields.Integer(min_value=0, max_value=150),
            "tags": fields.List(fields.String(), max_length=10),
        }
    )

    good = {
        "name": "Hussain",
        "email": "h@example.com",
        "age": 30,
        "tags": ["python", "rust", "go"],
    }

    iters = 100_000
    t0 = time.perf_counter()
    for _ in range(iters):
        schema.validate(good)
    elapsed = time.perf_counter() - t0
    print(f"{iters} validations in {elapsed:.3f}s → {iters / elapsed:,.0f} val/s")


if __name__ == "__main__":
    main()
