import asyncio
from google import genai
from google.genai import types
from config import Config


async def test_tools_and_search():
    cfg = Config()
    client = genai.Client()

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

    from providers.gemini_api import to_gemini_tools

    api_tools = to_gemini_tools([dummy_tool], include_search=True)

    print(f"Tools: {api_tools}")

    config = types.GenerateContentConfig(
        system_instruction="You are a helpful assistant.",
        tools=api_tools,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    prompt = "What is the population of Tokyo and what time is it there right now?"
    contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]

    try:
        response = await client.aio.models.generate_content(
            model=cfg.subagent_model,
            contents=contents,
            config=config,
        )

        candidate = response.candidates[0]
        print("Model response parts:")
        for part in candidate.content.parts:
            if part.text:
                print(f"Text: {part.text}")
            if part.function_call:
                print(
                    f"Function Call: {part.function_call.name}({part.function_call.args})"
                )

        if candidate.grounding_metadata:
            print("Grounding metadata found!")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_tools_and_search())
