import pytest
from tools import execute, get_tools_for_profile, list_tool_profiles


def test_get_tools_for_profile():
    # Full profile
    full = get_tools_for_profile("full")
    assert len(full) == 5
    assert any(t["name"] == "write_file" for t in full)

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
    assert len(unknown) == 5


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
    assert "Error: path escapes workspace" in res
