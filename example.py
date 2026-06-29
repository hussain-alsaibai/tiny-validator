"""Example usage of tiny_validator."""

from __future__ import annotations

from tiny_validator import Schema, ValidationError, fields, validate


# A nested user schema
user_schema = Schema(
    {
        "id": fields.Uuid(),
        "name": fields.String(min_length=1, max_length=100),
        "email": fields.Email(),
        "age": fields.Integer(min_value=0, max_value=150, required=False),
        "role": fields.String(choices=["admin", "user", "guest"], case_insensitive=True),
        "tags": fields.List(fields.String(), unique=True, required=False, default=list),
        "billing": fields.Dict(
            schema=Schema(
                {
                    "plan": fields.String(choices=["free", "pro", "enterprise"]),
                    "renews": fields.Date(),
                }
            ),
            required=False,
        ),
    },
    strict=True,
)


def create_user(data: dict) -> dict:
    try:
        clean = user_schema(data)
    except ValidationError as exc:
        return {"ok": False, "errors": exc.errors}
    return {"ok": True, "user": clean}


# Decorator usage
@validate(
    body=Schema(
        {
            "query": fields.String(min_length=3),
            "limit": fields.Integer(min_value=1, max_value=100, default=10),
        }
    ),
    query=Schema({"lang": fields.String(choices=["en", "ar"], required=False)}),
)
def search_handler(body: dict, query: dict) -> dict:
    return {"q": body["query"], "limit": body["limit"], "lang": query.get("lang", "en")}


def main() -> None:
    good = {
        "id": "12345678-1234-1234-1234-123456789abc",
        "name": "Hussain",
        "email": "hussain@example.com",
        "age": 30,
        "role": "admin",
        "tags": ["alpha", "beta"],
        "billing": {"plan": "pro", "renews": "2027-01-01"},
    }
    print("good:", create_user(good))

    bad = {
        "id": "not-a-uuid",
        "name": "",
        "email": "not-an-email",
        "role": "wizard",
        "tags": ["a", "a"],
        "extra_field": "x",
    }
    print("bad:", create_user(bad))

    try:
        search_handler(body={"query": "hi"}, query={"lang": "fr"})
    except ValidationError as exc:
        print("search errors:", exc.errors)

    print("search ok:", search_handler(body={"query": "python"}, query={"lang": "en"}))


if __name__ == "__main__":
    main()
