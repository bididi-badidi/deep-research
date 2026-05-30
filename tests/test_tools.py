import pytest
from tools import execute, get_tools_for_profile, list_tool_profiles


def test_get_tools_for_profile():
    # Full profile
    full = get_tools_for_profile("full")
    assert len(full) == 6
    assert any(t["name"] == "write_file" for t in full)
    assert any(t["name"] == "verify_url" for t in full)

    # Read-only profile
    ro = get_tools_for_profile("read_only")
    assert len(ro) == 4
    assert not any(t["name"] == "write_file" for t in ro)
    assert any(t["name"] == "read_file" for t in ro)

    # Search-only profile
    so = get_tools_for_profile("search_only")
    assert len(so) == 0

    # Default to full
    unknown = get_tools_for_profile("invalid-profile")
    assert len(unknown) == 6


def test_list_tool_profiles():
    summary = list_tool_profiles()
    assert "full" in summary
    assert "read_only" in summary
    assert "write_file" in summary["full"]
    assert "write_file" not in summary["read_only"]
    assert len(summary["search_only"]) == 0


@pytest.mark.asyncio
async def test_write_and_read_file(tmp_path):
    workspace = tmp_path
    path = "test.txt"
    content = "hello world"

    # Write
    res = await execute("write_file", {"path": path, "content": content}, workspace)
    assert res == f"Written to {path}"

    # Read
    res = await execute("read_file", {"path": path}, workspace)
    assert res == content


@pytest.mark.asyncio
async def test_list_files(tmp_path):
    workspace = tmp_path
    (workspace / "dir").mkdir()
    (workspace / "file.txt").write_text("content")

    res = await execute("list_files", {"path": "."}, workspace)
    assert "dir" in res
    assert "file.txt" in res


@pytest.mark.asyncio
async def test_path_escape(tmp_path):
    workspace = tmp_path
    res = await execute("read_file", {"path": "../outside.txt"}, workspace)
    assert "Access denied" in res and "escapes the workspace" in res


class _FakeResponse:
    def __init__(self, status_code, url="https://example.com/final"):
        self.status_code = status_code
        self.url = url


class _FakeAsyncClient:
    head_status = 405
    head_url = "https://example.com"
    get_status = 200
    get_url = "https://example.com/final"
    error = None

    def __init__(self, *args, **kwargs):
        self.head_calls = 0
        self.get_calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def head(self, url):
        self.head_calls += 1
        if self.error:
            raise self.error
        return _FakeResponse(self.head_status, self.head_url)

    async def get(self, url):
        self.get_calls += 1
        return _FakeResponse(self.get_status, self.get_url)


def _patch_fake_httpx(monkeypatch, tools, fake_client):
    instances = []

    def factory(*args, **kwargs):
        client = fake_client(*args, **kwargs)
        instances.append(client)
        return client

    monkeypatch.setattr(tools.httpx, "AsyncClient", factory)
    return instances


@pytest.mark.asyncio
async def test_verify_url_head_200(tmp_path, monkeypatch):
    import json
    import tools

    class FakeClient(_FakeAsyncClient):
        head_status = 200
        head_url = "https://example.com"

    instances = _patch_fake_httpx(monkeypatch, tools, FakeClient)

    res = await execute("verify_url", {"url": "https://example.com"}, tmp_path)
    data = json.loads(res)

    assert data == {
        "url": "https://example.com",
        "status": 200,
        "reachable": True,
        "final_url": "https://example.com",
    }
    assert instances[0].head_calls == 1
    assert instances[0].get_calls == 0


@pytest.mark.asyncio
async def test_verify_url_head_with_get_fallback(tmp_path, monkeypatch):
    import json
    import tools

    instances = _patch_fake_httpx(monkeypatch, tools, _FakeAsyncClient)

    res = await execute("verify_url", {"url": "https://example.com"}, tmp_path)
    data = json.loads(res)

    assert data["url"] == "https://example.com"
    assert data["status"] == 200
    assert data["reachable"] is True
    assert data["final_url"] == "https://example.com/final"
    assert instances[0].head_calls == 1
    assert instances[0].get_calls == 1


@pytest.mark.asyncio
async def test_verify_url_head_404(tmp_path, monkeypatch):
    import json
    import tools

    class FakeClient(_FakeAsyncClient):
        head_status = 404
        head_url = "https://example.com/missing"

    instances = _patch_fake_httpx(monkeypatch, tools, FakeClient)

    res = await execute("verify_url", {"url": "https://example.com/missing"}, tmp_path)
    data = json.loads(res)

    assert data["url"] == "https://example.com/missing"
    assert data["status"] == 404
    assert data["reachable"] is False
    assert data["final_url"] == "https://example.com/missing"
    assert instances[0].get_calls == 0


@pytest.mark.asyncio
async def test_verify_url_redirect(tmp_path, monkeypatch):
    import json
    import tools

    class FakeClient(_FakeAsyncClient):
        head_status = 200
        head_url = "https://example.com/final"

    _patch_fake_httpx(monkeypatch, tools, FakeClient)

    res = await execute("verify_url", {"url": "https://example.com/start"}, tmp_path)
    data = json.loads(res)

    assert data["url"] == "https://example.com/start"
    assert data["status"] == 200
    assert data["reachable"] is True
    assert data["final_url"] == "https://example.com/final"


@pytest.mark.asyncio
async def test_verify_url_connection_error(tmp_path, monkeypatch):
    import json
    import tools

    class FakeClient(_FakeAsyncClient):
        error = tools.httpx.ConnectError("connection failed")

    _patch_fake_httpx(monkeypatch, tools, FakeClient)

    res = await execute("verify_url", {"url": "https://example.com"}, tmp_path)
    data = json.loads(res)

    assert data["url"] == "https://example.com"
    assert data["reachable"] is False
    assert "connection failed" in data["error"]
