import pytest
import json
from unittest.mock import AsyncMock, patch
from tools import get_tools_for_profile, list_tool_profiles, TOOL_PROFILES
from agents import lead, subagent
from config import Config

def test_get_tools_for_profile():
    full_tools = get_tools_for_profile("full")
    assert len(full_tools) == len(TOOL_PROFILES["full"])
    
    read_only_tools = get_tools_for_profile("read_only")
    assert any(t["name"] == "read_file" for t in read_only_tools)
    assert not any(t["name"] == "write_file" for t in read_only_tools)
    
    search_only_tools = get_tools_for_profile("search_only")
    assert len(search_only_tools) == 0
    
    # Default case
    default_tools = get_tools_for_profile("invalid_profile")
    assert default_tools == TOOL_PROFILES["full"]

def test_list_tool_profiles():
    profiles = list_tool_profiles()
    assert "full" in profiles
    assert "read_only" in profiles
    assert "write_only" in profiles
    assert "search_only" in profiles
    
    assert "read_file" in profiles["read_only"]
    assert "write_file" not in profiles["read_only"]
    assert len(profiles["search_only"]) == 0

@pytest.mark.asyncio
async def test_lead_plan_defaults_tool_profile(tmp_path):
    config = Config(workspace=tmp_path)
    brief = {"primary_question": "test?"}
    
    # Mock provider to return a plan without tool_profiles
    mock_provider = AsyncMock()
    # For create_plan tool call, it returns the string output of the tool execution
    # but we need to mock the tool_executor side effect or the return value that sets plan_data.
    
    # Actually, the simplest way is to mock get_provider and make the provider call the executor
    with patch("agents.lead.get_provider") as mock_get_provider:
        mock_instance = AsyncMock()
        mock_get_provider.return_value = mock_instance
        
        # Simulating a plan without tool_profile
        plan_without_profile = [
            {"id": "t1", "title": "Task 1", "objective": "Obj 1", "search_hints": []}
        ]
        
        async def side_effect(*args, **kwargs):
            tool_executor = kwargs.get("tool_executor")
            await tool_executor("create_plan", {"tasks": json.dumps(plan_without_profile)})
            return "Plan created."
            
        mock_instance.side_effect = side_effect
        
        tasks = await lead.plan(config, brief)
        
        assert len(tasks) == 1
        assert tasks[0]["tool_profile"] == "full"

@pytest.mark.asyncio
async def test_subagent_run_uses_profile():
    config = Config()
    task = {
        "id": "t1",
        "title": "Task 1",
        "objective": "Obj 1",
        "search_hints": [],
        "tool_profile": "read_only"
    }
    
    with patch("agents.subagent.get_provider") as mock_get_provider:
        mock_instance = AsyncMock()
        mock_get_provider.return_value = mock_instance
        
        await subagent.run(config, task)
        
        # Verify that tools passed to provider are the read_only ones
        args, kwargs = mock_instance.call_args
        passed_tools = kwargs.get("tools")
        passed_tool_names = [t["name"] for t in passed_tools]
        
        assert "read_file" in passed_tool_names
        assert "write_file" not in passed_tool_names
