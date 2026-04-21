import asyncio
from config import Config
from providers import gemini_api


async def test_loop():
    cfg = Config()

    # Define a dummy tool
    dummy_tool = {
        "name": "get_current_time",
        "description": "Get the current time for a given location.",
        "parameters": {
            "location": {
                "type": "string",
                "description": "The location to get the time for.",
            }
        },
        "required": ["location"],
    }

    async def tool_executor(name: str, args: dict) -> str:
        if name == "get_current_time":
            return f"The current time in {args.get('location')} is 2:00 PM."
        return "Unknown tool"

    prompt = "What is the population of Tokyo and what time is it there right now?"

    try:
        final_text = await gemini_api.run(
            model=cfg.subagent_model,
            system="You are a helpful assistant.",
            prompt=prompt,
            tools=[dummy_tool],
            tool_executor=tool_executor,
            include_search=True,
        )
        print("\nFinal response:")
        print(final_text)

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_loop())
