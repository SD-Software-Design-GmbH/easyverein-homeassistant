"""Client logic against a fake session. Run: python -m unittest discover -s tests"""

import asyncio
import importlib.util
import pathlib
import sys
import types
import unittest

# Load api.py/const.py without importing the package (which needs Home Assistant).
base = pathlib.Path(__file__).parent.parent / "custom_components" / "easyverein"
pkg = types.ModuleType("ev")
pkg.__path__ = [str(base)]
sys.modules["ev"] = pkg
for name in ("const", "api"):
    spec = importlib.util.spec_from_file_location(f"ev.{name}", base / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"ev.{name}"] = mod
    spec.loader.exec_module(mod)
api = sys.modules["ev.api"]


class FakeResponse:
    def __init__(self, status, payload):
        self.status, self._payload = status, payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def raise_for_status(self):
        if self.status >= 400:
            raise RuntimeError(self.status)

    async def json(self):
        return self._payload


class FakeSession:
    """Maps URL suffix -> (status, payload); records calls."""

    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def get(self, url, params=None, headers=None):
        self.calls.append((url, params, headers))
        key = next(k for k in self.routes if url.endswith(k))
        return FakeResponse(*self.routes[key])


def run(coro):
    return asyncio.run(coro)


class ClientTest(unittest.TestCase):
    def test_count_asks_for_one_row_and_returns_count(self):
        s = FakeSession({"member": (200, {"count": 42, "results": []})})
        c = api.EasyVereinClient(s, "tok")
        self.assertEqual(run(c.count("member", custom_filter=7)), 42)
        _, params, headers = s.calls[0]
        self.assertEqual(
            params, {"custom_filter": 7, "limit": 1, "show_count": "true"}
        )
        self.assertEqual(headers["Authorization"], "Bearer tok")

    def test_auth_error(self):
        c = api.EasyVereinClient(FakeSession({"member": (401, {})}), "tok")
        with self.assertRaises(api.EasyVereinAuthError):
            run(c.count("member"))

    def test_custom_filters_paginates_and_skips_unsupported_models(self):
        s = FakeSession(
            {
                "custom-filter": (
                    200,
                    {
                        "next": "https://x/page2",
                        "results": [
                            {"id": 1, "name": "Anträge", "model": "userFilter"},
                            {"id": 2, "name": "Logs", "model": "loginLogsFilter"},
                        ],
                    },
                ),
                "page2": (
                    200,
                    {
                        "next": None,
                        "results": [{"id": 3, "name": "Offen", "model": "invoiceFilter"}],
                    },
                ),
            }
        )
        got = run(api.EasyVereinClient(s, "tok").custom_filters())
        self.assertEqual([f["id"] for f in got], [1, 3])

    def test_refresh_token_replaces_token(self):
        s = FakeSession({"refresh-token": (200, {"Bearer": "new"})})
        c = api.EasyVereinClient(s, "old")
        self.assertEqual(run(c.refresh_token()), "new")
        self.assertEqual(c.token, "new")


if __name__ == "__main__":
    unittest.main()
