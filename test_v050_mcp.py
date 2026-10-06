"""v0.5.0 - Tests for tiny_validator_mcp (MCP-specific schemas)."""
from __future__ import annotations

import unittest

from tiny_validator import (
    Integer,
    Schema,
    String,
)
from tiny_validator_mcp import (
    DEFAULT_CAPABILITIES,
    DEFAULT_TRANSPORTS,
    MCP_PROTOCOL_VERSIONS,
    McpError,
    McpManifest,
    McpPrompt,
    McpResource,
    McpServer,
    McpTool,
    PROMETHEUS_METRIC_PATTERN,
    SERVER_NAME_PATTERN,
    metric_label_check,
    to_mcp_tool_schema,
    validate_mcp_manifest,
)


class TestMcpServerBasics(unittest.TestCase):
    def test_minimal_server(self):
        s = McpServer(name="my-mcp", version="0.1.0")
        out = s.to_dict()
        self.assertEqual(out["name"], "my-mcp")
        self.assertEqual(out["version"], "0.1.0")
        self.assertEqual(out["transport"], "stdio")
        self.assertEqual(out["protocolVersion"], "1.0")
        self.assertNotIn("tools", out)
        self.assertNotIn("title", out)

    def test_with_title_and_description(self):
        s = McpServer(
            name="x",
            version="1.0.0",
            title="X Server",
            description="Does X things.",
        )
        out = s.to_dict()
        self.assertEqual(out["title"], "X Server")
        self.assertEqual(out["description"], "Does X things.")

    def test_invalid_name_raises(self):
        with self.assertRaises(McpError):
            McpServer(name="MyServer!", version="0.1.0")

    def test_invalid_version_raises(self):
        with self.assertRaises(McpError):
            McpServer(name="ok", version="not-semver")

    def test_invalid_transport_raises(self):
        with self.assertRaises(McpError):
            McpServer(name="ok", version="0.1.0", transport="carrier-pigeon")

    def test_invalid_protocol_version_raises(self):
        with self.assertRaises(McpError):
            McpServer(name="ok", version="0.1.0", protocol_version="2099-01-01")

    def test_capabilities_passthrough(self):
        s = McpServer(
            name="ok",
            version="0.1.0",
            capabilities={"tools": {"listChanged": True}},
        )
        self.assertEqual(s.to_dict()["capabilities"], {"tools": {"listChanged": True}})

    def test_full_server(self):
        s = McpServer(
            name="full",
            version="2.3.4",
            title="Full Server",
            description="Everything",
            transport="http",
            protocol_version="1.0",
            capabilities={"tools": {}, "resources": {"subscribe": True}},
            tools=[McpTool(name="a", description="A")],
            resources=[McpResource(uri="file:///x", name="x")],
            prompts=[McpPrompt(name="p", description="P")],
            metrics=["mcp_full_calls_total", "mcp_full_errors_total"],
        )
        d = s.to_dict()
        self.assertEqual(len(d["tools"]), 1)
        self.assertEqual(len(d["resources"]), 1)
        self.assertEqual(len(d["prompts"]), 1)
        self.assertEqual(len(d["metrics"]), 2)


class TestMcpTool(unittest.TestCase):
    def test_basic(self):
        t = McpTool(
            name="echo",
            description="Echo input",
            input_schema=Schema({"text": String(min_length=1)}),
        )
        d = t.to_dict()
        self.assertEqual(d["name"], "echo")
        self.assertEqual(d["description"], "Echo input")
        self.assertEqual(d["inputSchema"]["type"], "object")
        self.assertEqual(d["inputSchema"]["properties"]["text"]["type"], "string")
        self.assertIn("text", d["inputSchema"]["required"])

    def test_no_input_schema(self):
        t = McpTool(name="ping", description="Pings back")
        d = t.to_dict()
        self.assertNotIn("inputSchema", d)

    def test_invalid_name(self):
        with self.assertRaises(McpError):
            McpTool(name="1bad", description="x")

    def test_short_description(self):
        with self.assertRaises(McpError):
            McpTool(name="ok", description="")

    def test_annotations(self):
        t = McpTool(
            name="delete",
            description="Delete a record.",
            input_schema=Schema({"id": String()}),
            annotations={"destructiveHint": True, "idempotentHint": False},
        )
        self.assertEqual(t.to_dict()["annotations"]["destructiveHint"], True)

    def test_dict_input_schema(self):
        t = McpTool(
            name="echo",
            description="Echo input",
            input_schema={"type": "object", "properties": {"x": {"type": "string"}}},
        )
        self.assertEqual(t.to_dict()["inputSchema"]["properties"]["x"]["type"], "string")


class TestMcpResource(unittest.TestCase):
    def test_basic(self):
        r = McpResource(
            uri="file:///etc/hosts",
            name="hosts",
            description="System hosts file",
            mime_type="text/plain",
        )
        d = r.to_dict()
        self.assertEqual(d["uri"], "file:///etc/hosts")
        self.assertEqual(d["name"], "hosts")
        self.assertEqual(d["mimeType"], "text/plain")

    def test_invalid_uri(self):
        with self.assertRaises(McpError):
            McpResource(uri="not a uri", name="x")


class TestMcpPrompt(unittest.TestCase):
    def test_basic(self):
        p = McpPrompt(
            name="summarize",
            description="Summarize text",
            arguments=[{"name": "text", "required": True}],
        )
        d = p.to_dict()
        self.assertEqual(d["name"], "summarize")
        self.assertEqual(len(d["arguments"]), 1)

    def test_no_arguments(self):
        p = McpPrompt(name="ping")
        self.assertNotIn("arguments", p.to_dict())


class TestMetricLabelCheck(unittest.TestCase):
    def test_valid_total_counter(self):
        self.assertEqual(metric_label_check("mcp_my_mcp_calls_total"), [])

    def test_valid_histogram_bucket(self):
        self.assertEqual(metric_label_check("mcp_my_mcp_latency_seconds_bucket"), [])

    def test_valid_summary(self):
        self.assertEqual(metric_label_check("mcp_my_mcp_latency_seconds_sum"), [])
        self.assertEqual(metric_label_check("mcp_my_mcp_latency_seconds_count"), [])

    def test_valid_info(self):
        self.assertEqual(metric_label_check("mcp_my_mcp_build_info"), [])

    def test_valid_created(self):
        self.assertEqual(metric_label_check("mcp_my_mcp_started_created"), [])

    def test_missing_mcp_prefix(self):
        issues = metric_label_check("calls_total")
        self.assertEqual(len(issues), 1)
        self.assertIn("must match pattern", issues[0])

    def test_uppercase_rejected(self):
        self.assertEqual(len(metric_label_check("MCP_calls_total")), 1)

    def test_non_string(self):
        issues = metric_label_check(123)
        self.assertEqual(len(issues), 1)
        self.assertIn("must be a string", issues[0])

    def test_gauge_without_suffix_is_valid(self):
        # Gauges don't need a _total suffix; only counters do.
        self.assertEqual(metric_label_check("mcp_my_mcp_active_connections"), [])


class TestValidateMcpManifest(unittest.TestCase):
    def _ok_manifest(self):
        return McpServer(
            name="ok",
            version="0.1.0",
            tools=[McpTool(name="echo", description="Echo", input_schema=Schema({"text": String()}))],
            metrics=["mcp_ok_calls_total"],
        ).to_dict()

    def test_valid_manifest(self):
        errors = validate_mcp_manifest(self._ok_manifest())
        self.assertEqual(errors, [])

    def test_missing_name(self):
        m = self._ok_manifest()
        del m["name"]
        errors = validate_mcp_manifest(m)
        self.assertEqual(len(errors), 1)
        self.assertIn("name", errors[0]["path"])

    def test_bad_tool_name(self):
        m = self._ok_manifest()
        m["tools"][0]["name"] = "1bad"
        errors = validate_mcp_manifest(m)
        self.assertTrue(any("tools[0]" in e["path"] for e in errors))

    def test_bad_metric(self):
        m = self._ok_manifest()
        m["metrics"] = ["calls_total"]
        errors = validate_mcp_manifest(m)
        self.assertTrue(any("metrics[0]" in e["path"] for e in errors))

    def test_aggregate_errors(self):
        m = self._ok_manifest()
        m["version"] = "bad"
        m["transport"] = "carrier-pigeon"
        m["tools"][0]["name"] = "1bad"
        m["metrics"] = ["x"]
        errors = validate_mcp_manifest(m)
        paths = {e["path"] for e in errors}
        self.assertGreaterEqual(len(paths), 4)

    def test_non_mapping_raises(self):
        with self.assertRaises(McpError):
            validate_mcp_manifest(["not", "a", "mapping"])

    def test_round_trip_manifest(self):
        s = McpServer(
            name="rt",
            version="0.2.0",
            tools=[McpTool(name="a", description="A", input_schema=Schema({"x": Integer(min_value=0)}))],
            resources=[McpResource(uri="file:///a", name="a")],
            prompts=[McpPrompt(name="p", description="P")],
            metrics=["mcp_rt_calls_total", "mcp_rt_errors_total"],
        )
        m = s.to_dict()
        self.assertEqual(validate_mcp_manifest(m), [])


class TestConvenienceAndCompat(unittest.TestCase):
    def test_to_mcp_tool_schema(self):
        schema = Schema({"x": Integer(min_value=1)})
        tool = to_mcp_tool_schema(schema, name="f", description="F")
        self.assertEqual(tool.name, "f")
        self.assertEqual(tool.input_schema["properties"]["x"]["minimum"], 1)

    def test_mcp_manifest_alias(self):
        self.assertIs(McpManifest, McpServer)

    def test_constants_have_expected_values(self):
        self.assertIn("1.0", MCP_PROTOCOL_VERSIONS)
        self.assertIn("stdio", DEFAULT_TRANSPORTS)
        self.assertIn("tools", DEFAULT_CAPABILITIES)

    def test_pattern_objects_exist(self):
        self.assertTrue(PROMETHEUS_METRIC_PATTERN.pattern.startswith("^mcp_"))
        self.assertTrue(SERVER_NAME_PATTERN.pattern.startswith("^[a-z]"))


class TestSchemaExportIntegration(unittest.TestCase):
    def test_complex_schema_into_tool(self):
        schema = Schema({
            "name": String(min_length=1, max_length=50),
            "count": Integer(min_value=0, required=False),
        })
        tool = McpTool(name="t", description="T", input_schema=schema)
        d = tool.to_dict()
        self.assertEqual(d["inputSchema"]["properties"]["name"]["minLength"], 1)
        self.assertEqual(d["inputSchema"]["properties"]["name"]["maxLength"], 50)
        self.assertEqual(d["inputSchema"]["properties"]["count"]["type"], "integer")
        self.assertIn("name", d["inputSchema"]["required"])
        self.assertNotIn("count", d["inputSchema"]["required"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
