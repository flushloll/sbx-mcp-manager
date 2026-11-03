"""Tests for the local SBX MCP Manager (no Docker required)."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("sbx_manager", Path(__file__).resolve().parents[1] / "src" / "server.py")
manager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manager)


class RegistrationTests(unittest.TestCase):
    def test_https_server(self):
        self.assertEqual(
            manager.registration_args({"name": "docs", "kind": "remote", "url": "https://mcp.example.com/mcp"}),
            ["mcp", "add", "docs", "--url", "https://mcp.example.com/mcp"],
        )

    def test_local_server(self):
        self.assertEqual(
            manager.registration_args({"name": "blender", "kind": "local", "command": "uvx", "args": ["mcp-for-blender"]}),
            ["mcp", "add", "blender", "--command", "uvx", "--args", "mcp-for-blender"],
        )

    def test_disallow_http(self):
        with self.assertRaises(ValueError):
            manager.registration_args({"name": "nope", "kind": "remote", "url": "http://example.com"})

    def test_disallow_url_credentials(self):
        with self.assertRaises(ValueError):
            manager.registration_args({"name": "nope", "kind": "remote", "url": "https://user:secret@example.com/mcp"})

    def test_disallow_bad_name(self):
        with self.assertRaises(ValueError):
            manager.registration_args({"name": "bad name", "kind": "remote", "url": "https://example.com/mcp"})

    def test_disallow_comma_in_local_arg(self):
        with self.assertRaises(ValueError):
            manager.registration_args({"name": "x", "kind": "local", "command": "npx", "args": ["a,b"]})


class ExecutionTests(unittest.TestCase):
    def test_disallow_unknown_action(self):
        with self.assertRaises(ValueError):
            manager.execute({"action": "delete_all"})

    @patch.object(manager, "run_sbx")
    def test_multiple_sandbox_attach(self, run):
        run.side_effect = ["docs\n", "alpha\nbeta\n", "loaded", "loaded"]
        result = manager.execute({"action": "load", "servers": ["docs"], "sandboxes": ["alpha", "beta"]})
        self.assertEqual(len(result), 2)
        self.assertTrue(all(x["success"] for x in result))
        self.assertEqual(run.call_args_list[-1].args[0], ["mcp", "load", "docs", "--sandbox", "beta"])

    @patch.object(manager, "run_sbx")
    def test_unknown_sandbox_refused(self, run):
        run.side_effect = ["docs\n", "alpha\n"]
        with self.assertRaises(ValueError):
            manager.execute({"action": "load", "servers": ["docs"], "sandboxes": ["other"]})

    @patch.object(manager, "run_sbx")
    def test_duplicate_targets_deduplicated(self, run):
        run.side_effect = ["docs\n", "alpha\n", "loaded"]
        result = manager.execute({"action": "load", "servers": ["docs", "docs"], "sandboxes": ["alpha", "alpha"]})
        self.assertEqual(len(result), 1)


if __name__ == "__main__":
    unittest.main()
