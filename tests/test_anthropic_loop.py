
import asyncio
import os
from config import Config
from providers import anthropic_api

async def test_anthropic():
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
    
    messages = [
        {"role": "user", "content": "What time is it in Tokyo right now?"}
    ]
    
    try:
        final_text = await anthropic_api.run(
            model=cfg.receptionist_model,
            system="You are a helpful assistant.",
            messages=messages,
            tools=[dummy_tool],
            tool_executor=tool_executor,
            max_tokens=1024
        )
        print("\nFinal response:")
        print(final_text)
        
        # Verify messages history
        print("\nMessage history length:", len(messages))
        # Expect: user, assistant (tool_use), user (tool_result), assistant (final text)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_anthropic())
