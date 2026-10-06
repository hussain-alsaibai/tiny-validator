"""tiny_validator_mcp - MCP-specific schemas for tiny-validator v0.5.0.

Sidecar module that adds Model Context Protocol (MCP) validation on top of
the core tiny_validator package. Keep the v0.4.0 single-file experience
intact; this sidecar is only imported if MCP support is needed.

Exports:
    McpServer, McpTool, McpResource, McpPrompt, McpManifest, McpError,
    validate_mcp_manifest, to_mcp_tool_schema, metric_label_check,
    PROMETHEUS_METRIC_PATTERN, MCP_PROTOCOL_VERSIONS,
    DEFAULT_TRANSPORTS, DEFAULT_CAPABILITIES, SERVER_NAME_PATTERN

Usage::

    from tiny_validator import Schema, String
    from tiny_validator_mcp import (
        McpServer, McpTool, validate_mcp_manifest,
    )

    server = McpServer(
        name="my-mcp",
        version="0.1.0",
        tools=[McpTool(name="echo", description="Echo input",
                       input_schema=Schema({"text": String()}))],
    )
    errors = validate_mcp_manifest(server.to_dict())
    assert not errors
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

# Try the package-style relative import first, and fall back to a flat
# absolute import (the common case for the tiny-* family).
try:
    from .tiny_validator import (  # type: ignore
        Schema,
        Slug,
        String,
        Url,
        fields,
    )
except ImportError:  # pragma: no cover - flat-layout fallback
    from tiny_validator import (
        Schema,
        Slug,
        String,
        Url,
        fields,
    )


__version__ = "0.5.0"


# ---------- Constants (de-facto spec values) ----------

MCP_PROTOCOL_VERSIONS = (
    "2025-06-18",
    "2025-03-26",
    "2024-11-05",
    "2024-10-07",
    "1.0",
)

DEFAULT_TRANSPORTS = (
    "stdio",
    "sse",
    "http",
    "streamable-http",
    "websocket",
)

DEFAULT_CAPABILITIES = (
    "tools",
    "resources",
    "prompts",
    "logging",
    "sampling",
    "roots",
    "experimental",
)

# Pattern: mcp_<server>_<unit>_(total|bucket|sum|count|created|info)
PROMETHEUS_METRIC_PATTERN = re.compile(
    r"^mcp_[a-z][a-z0-9]*(?:_[a-z][a-z0-9]*)+"
    r"(?:_(?:total|bucket|sum|count|created|info))?$"
)

# Server names: lowercase, hyphen-or-underscore, must start with letter.
SERVER_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")


# ---------- Errors ----------


class McpError(Exception):
    """Raised by validate_mcp_manifest for shape/structural violations."""

    def __init__(self, errors):
        if isinstance(errors, str):
            errors = [{"path": "", "message": errors}]
        self.errors = errors
        super().__init__(self._format(errors))

    @staticmethod
    def _format(errors):
        if not errors:
            return "mcp validation failed"
        parts = []
        for e in errors:
            path = e.get("path", "")
            msg = e.get("message", "invalid")
            parts.append(f"{path}: {msg}" if path else msg)
        return "; ".join(parts)

    def to_dict(self):
        return {"error": "mcp_validation_failed", "details": self.errors}


# ---------- Schemas ----------


TOOL_SCHEMA = Schema(
    {
        "name": Slug(
            min_length=1,
            max_length=64,
            pattern=r"^[a-zA-Z][a-zA-Z0-9_-]*$",
            description="Unique tool name (used in MCP tool calls).",
        ),
        "description": String(
            min_length=1,
            max_length=2048,
            description="Human-readable description; surfaced to LLM clients.",
        ),
        "inputSchema": fields.Dict(
            required=False,
            description="JSON Schema dict for the tool's input arguments.",
        ),
        "annotations": fields.Dict(
            required=False,
            description="Optional hints: title, readOnlyHint, destructiveHint, idempotentHint, openWorldHint.",
        ),
    },
    strict=False,
)


RESOURCE_SCHEMA = Schema(
    {
        "uri": String(
            min_length=1,
            max_length=2048,
            # RFC 3986: scheme = ALPHA *( ALPHA / DIGIT / "+" / "-" / "." )
            # MCP resource URIs can use any scheme (file://, git://, https://, ...).
            pattern=r"^[a-zA-Z][a-zA-Z0-9+.\-]*://",
            description="Resource URI (unique within the server).",
        ),
        "name": Slug(
            min_length=1,
            max_length=128,
            pattern=r"^[a-zA-Z][a-zA-Z0-9_.-]*$",
            description="Human-readable resource name.",
        ),
        "description": String(
            min_length=1,
            max_length=2048,
            required=False,
        ),
        "mimeType": String(
            min_length=1,
            max_length=128,
            required=False,
            description="IANA media type, e.g. text/plain, application/json.",
        ),
    },
    strict=False,
)


PROMPT_SCHEMA = Schema(
    {
        "name": Slug(
            min_length=1,
            max_length=64,
            pattern=r"^[a-zA-Z][a-zA-Z0-9_-]*$",
        ),
        "description": String(min_length=1, max_length=2048, required=False),
        "arguments": fields.List(
            fields.Dict(),
            required=False,
            description="List of {name, description?, required?} objects.",
        ),
    },
    strict=False,
)


SERVER_SCHEMA = Schema(
    {
        "name": String(
            min_length=1,
            max_length=64,
            description="Server identifier; must match SERVER_NAME_PATTERN.",
        ),
        "version": String(
            min_length=1,
            max_length=64,
            pattern=r"^\d+\.\d+\.\d+([-+][A-Za-z0-9.-]+)?$",
            description="SemVer string; pre-release suffix allowed.",
        ),
        "title": String(
            min_length=1,
            max_length=128,
            required=False,
            description="Optional display name (e.g. for UIs).",
        ),
        "description": String(
            min_length=1,
            max_length=2048,
            required=False,
        ),
        "transport": String(
            choices=list(DEFAULT_TRANSPORTS),
            default="stdio",
            required=False,
        ),
        "protocolVersion": String(
            choices=list(MCP_PROTOCOL_VERSIONS),
            default="1.0",
            required=False,
        ),
        "capabilities": fields.Dict(
            required=False,
            description=(
                "Mapping of capability name -> config object. Known keys: "
                + ", ".join(DEFAULT_CAPABILITIES)
                + "."
            ),
        ),
        "tools": fields.List(
            fields.Dict(),
            required=False,
            description="List of TOOL_SCHEMA-shaped dicts.",
        ),
        "resources": fields.List(
            fields.Dict(),
            required=False,
            description="List of RESOURCE_SCHEMA-shaped dicts.",
        ),
        "prompts": fields.List(
            fields.Dict(),
            required=False,
            description="List of PROMPT_SCHEMA-shaped dicts.",
        ),
        "metrics": fields.List(
            fields.String(),
            required=False,
            description=(
                "Prometheus metric names exported by this server. "
                "Each name must match PROMETHEUS_METRIC_PATTERN."
            ),
        ),
    },
    strict=False,
)


# ---------- Helpers ----------


def _schema_to_input_schema(schema):
    """Convert a tiny-validator Schema to an MCP tool inputSchema."""
    try:
        try:
            from .tiny_validator import to_json_schema
        except ImportError:
            from tiny_validator import to_json_schema
        return to_json_schema(schema)
    except Exception:
        return {
            "type": "object",
            "properties": {
                key: (field.description or {"type": "string"})
                for key, field in schema.definition.items()
            },
            "required": [
                key for key, field in schema.definition.items() if field.required
            ],
        }


def _tool_dict(*, name, description, input_schema=None, annotations=None):
    """Build a TOOL_SCHEMA-shaped dict, validating on the way out."""
    out = {"name": name, "description": description}
    if input_schema is not None:
        if isinstance(input_schema, Schema):
            out["inputSchema"] = _schema_to_input_schema(input_schema)
        else:
            out["inputSchema"] = dict(input_schema)
    if annotations is not None:
        out["annotations"] = dict(annotations)
    errors = TOOL_SCHEMA.validate(out)
    if errors:
        raise McpError(
            [{"path": f"tools.{name}", "message": e["message"]} for e in errors]
        )
    return out


def _resource_dict(*, uri, name, description=None, mime_type=None):
    out = {"uri": uri, "name": name}
    if description is not None:
        out["description"] = description
    if mime_type is not None:
        out["mimeType"] = mime_type
    errors = RESOURCE_SCHEMA.validate(out)
    if errors:
        raise McpError(
            [{"path": f"resources.{name}", "message": e["message"]} for e in errors]
        )
    return out


def _prompt_dict(*, name, description=None, arguments=None):
    out = {"name": name}
    if description is not None:
        out["description"] = description
    if arguments is not None:
        out["arguments"] = [dict(a) for a in arguments]
    errors = PROMPT_SCHEMA.validate(out)
    if errors:
        raise McpError(
            [{"path": f"prompts.{name}", "message": e["message"]} for e in errors]
        )
    return out


class McpTool:
    """A single MCP tool declaration.

    Mirrors the tools[] entries in an MCP-Registry v1 manifest.
    """

    __slots__ = ("name", "description", "input_schema", "annotations")

    def __init__(self, *, name, description, input_schema=None, annotations=None):
        self.name = name
        self.description = description
        if input_schema is None:
            self.input_schema = None
        elif isinstance(input_schema, Schema):
            self.input_schema = _schema_to_input_schema(input_schema)
        else:
            self.input_schema = dict(input_schema)
        self.annotations = dict(annotations) if annotations is not None else None
        _tool_dict(
            name=self.name,
            description=self.description,
            input_schema=self.input_schema,
            annotations=self.annotations,
        )

    def to_dict(self):
        return _tool_dict(
            name=self.name,
            description=self.description,
            input_schema=self.input_schema,
            annotations=self.annotations,
        )


class McpResource:
    """A single MCP resource declaration."""

    __slots__ = ("uri", "name", "description", "mime_type")

    def __init__(self, *, uri, name, description=None, mime_type=None):
        self.uri = uri
        self.name = name
        self.description = description
        self.mime_type = mime_type
        _resource_dict(
            uri=self.uri,
            name=self.name,
            description=self.description,
            mime_type=self.mime_type,
        )

    def to_dict(self):
        return _resource_dict(
            uri=self.uri,
            name=self.name,
            description=self.description,
            mime_type=self.mime_type,
        )


class McpPrompt:
    """A single MCP prompt template declaration."""

    __slots__ = ("name", "description", "arguments")

    def __init__(self, *, name, description=None, arguments=None):
        self.name = name
        self.description = description
        self.arguments = (
            [dict(a) for a in arguments] if arguments is not None else None
        )
        _prompt_dict(
            name=self.name,
            description=self.description,
            arguments=self.arguments,
        )

    def to_dict(self):
        return _prompt_dict(
            name=self.name,
            description=self.description,
            arguments=self.arguments,
        )


class McpServer:
    """An MCP server declaration.

    Combines server metadata + tools + resources + prompts + metrics into
    a single object that can be validated as a unit and serialised to
    the MCP-Registry v1 manifest shape.
    """

    def __init__(
        self,
        *,
        name,
        version,
        title=None,
        description=None,
        transport="stdio",
        protocol_version="1.0",
        capabilities=None,
        tools=None,
        resources=None,
        prompts=None,
        metrics=None,
    ):
        if not SERVER_NAME_PATTERN.match(name):
            raise McpError(
                f"name {name!r} must match {SERVER_NAME_PATTERN.pattern}"
            )
        self.name = name
        self.version = version
        self.title = title
        self.description = description
        self.transport = transport
        self.protocol_version = protocol_version
        self.capabilities = dict(capabilities or {})
        self.tools = list(tools or [])
        self.resources = list(resources or [])
        self.prompts = list(prompts or [])
        self.metrics = list(metrics or [])
        errors = validate_mcp_manifest(self.to_dict())
        if errors:
            raise McpError(errors)

    def to_dict(self):
        out = {
            "name": self.name,
            "version": self.version,
            "transport": self.transport,
            "protocolVersion": self.protocol_version,
        }
        if self.title is not None:
            out["title"] = self.title
        if self.description is not None:
            out["description"] = self.description
        if self.capabilities:
            out["capabilities"] = self.capabilities
        if self.tools:
            out["tools"] = [t.to_dict() for t in self.tools]
        if self.resources:
            out["resources"] = [r.to_dict() for r in self.resources]
        if self.prompts:
            out["prompts"] = [p.to_dict() for p in self.prompts]
        if self.metrics:
            out["metrics"] = list(self.metrics)
        return out


# Compatibility alias
McpManifest = McpServer


# ---------- Validation entry points ----------


def metric_label_check(metric_name):
    """Return a list of human-readable issues with a Prometheus metric name."""
    issues = []
    if not isinstance(metric_name, str):
        return [f"metric name must be a string, got {type(metric_name).__name__}"]
    if not PROMETHEUS_METRIC_PATTERN.match(metric_name):
        issues.append(
            f"metric name {metric_name!r} must match pattern "
            f"{PROMETHEUS_METRIC_PATTERN.pattern}"
        )
    return issues


def validate_mcp_manifest(manifest):
    """Validate an MCP server manifest dict.

    Returns a list of structured error dicts ({path, message}). Empty
    list means the manifest is valid. Raises McpError if the manifest
    is not a mapping.
    """
    if not isinstance(manifest, Mapping):
        raise McpError(f"manifest must be a mapping, got {type(manifest).__name__}")

    errors = []

    # Layer 1: structural
    errors.extend(SERVER_SCHEMA.validate(manifest))

    # Layer 2: per-element schemas
    for idx, tool in enumerate(manifest.get("tools") or []):
        for e in TOOL_SCHEMA.validate(tool):
            errors.append({"path": f"tools[{idx}].{e['path']}", "message": e["message"]})
    for idx, resource in enumerate(manifest.get("resources") or []):
        for e in RESOURCE_SCHEMA.validate(resource):
            errors.append(
                {"path": f"resources[{idx}].{e['path']}", "message": e["message"]}
            )
    for idx, prompt in enumerate(manifest.get("prompts") or []):
        for e in PROMPT_SCHEMA.validate(prompt):
            errors.append(
                {"path": f"prompts[{idx}].{e['path']}", "message": e["message"]}
            )

    # Layer 3: metric labels
    for idx, metric in enumerate(manifest.get("metrics") or []):
        for issue in metric_label_check(metric):
            errors.append({"path": f"metrics[{idx}]", "message": issue})

    return errors


def to_mcp_tool_schema(schema, *, name, description):
    """Wrap a tiny-validator Schema as McpTool."""
    return McpTool(name=name, description=description, input_schema=schema)


__all__ = [
    "McpServer",
    "McpTool",
    "McpResource",
    "McpPrompt",
    "McpManifest",
    "McpError",
    "validate_mcp_manifest",
    "to_mcp_tool_schema",
    "metric_label_check",
    "SERVER_SCHEMA",
    "TOOL_SCHEMA",
    "RESOURCE_SCHEMA",
    "PROMPT_SCHEMA",
    "MCP_PROTOCOL_VERSIONS",
    "DEFAULT_TRANSPORTS",
    "DEFAULT_CAPABILITIES",
    "PROMETHEUS_METRIC_PATTERN",
    "SERVER_NAME_PATTERN",
    "__version__",
]
