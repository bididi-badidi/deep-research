import asyncio
import json
from unittest.mock import MagicMock
from config import Config, Backend
from agents.receptionist import run_with_queue


async def test_run_with_queue_tool_call():
    """Test that run_with_queue correctly calls on_brief when a tool is called."""
    config = Config(backend=Backend.API)
    in_q = asyncio.Queue()
    out_q = asyncio.Queue()
    brief_received = []

    async def on_brief(brief):
        brief_received.append(brief)

    # Mock provider that simulates a tool call
    mock_provider = MagicMock()

    # First call returns some text
    # Second call (after user input) returns a tool call
    # Third call (after tool output) returns closing text

    brief_data = {
        "topic": "test topic",
        "scope": "test scope",
        "questions": "test questions",
        "depth": "moderate",
    }

    async def side_effect(*args, **kwargs):
        tool_executor = kwargs.get("tool_executor")
        messages = kwargs.get("messages")
        print(f"DEBUG: provider called with {len(messages)} messages")

        result = "Done."
        if len(messages) == 1:  # Initial input
            result = "Tell me more."
        elif len(messages) == 3:  # After second user input
            # Simulate calling the tool via tool_executor
            if tool_executor:
                await tool_executor("submit_brief", brief_data)
            result = "I have submitted the brief."

        if messages is not None:
            messages.append({"role": "assistant", "content": result})
        return result

    mock_provider.side_effect = side_effect

    # We need to patch get_provider to return our mock
    with patch("agents.receptionist.get_provider", return_value=mock_provider):
        # Start run_with_queue in a task
        task = asyncio.create_task(run_with_queue(config, in_q, out_q, on_brief))

        # 1. Send initial message
        await in_q.put("I want to research X")
        resp1 = await out_q.get()
        assert resp1 == "Tell me more."

        # 2. Send second message
        await in_q.put("Here is more info")
        resp2 = await out_q.get()
        assert resp2 == "I have submitted the brief."

        # Check if on_brief was called
        assert len(brief_received) == 1
        assert brief_received[0] == brief_data

        await task


async def test_run_with_queue_json_fallback():
    """Test that run_with_queue correctly calls on_brief when JSON is output (fallback)."""
    config = Config(backend=Backend.API)
    in_q = asyncio.Queue()
    out_q = asyncio.Queue()
    brief_received = []

    async def on_brief(brief):
        brief_received.append(brief)

    mock_provider = MagicMock()

    brief_data = {
        "topic": "test topic",
        "scope": "test scope",
        "questions": "test questions",
        "depth": "moderate",
    }

    async def side_effect(*args, **kwargs):
        messages = kwargs.get("messages")
        result = "Done."
        if len(messages) == 1:
            result = "Tell me more."
        elif len(messages) == 3:
            # Return JSON directly
            result = json.dumps(brief_data)

        if messages is not None:
            messages.append({"role": "assistant", "content": result})
        return result

    mock_provider.side_effect = side_effect

    with patch("agents.receptionist.get_provider", return_value=mock_provider):
        task = asyncio.create_task(run_with_queue(config, in_q, out_q, on_brief))

        await in_q.put("I want to research X")
        await out_q.get()

        await in_q.put("Here is more info")
        resp2 = await out_q.get()
        assert json.loads(resp2) == brief_data

        assert len(brief_received) == 1
        assert brief_received[0] == brief_data

        await task


if __name__ == "__main__":
    from unittest.mock import patch

    asyncio.run(test_run_with_queue_tool_call())
    print("test_run_with_queue_tool_call passed")
    asyncio.run(test_run_with_queue_json_fallback())
    print("test_run_with_queue_json_fallback passed")
