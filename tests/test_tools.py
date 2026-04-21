import pytest
from tools import execute


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
