
import asyncio
import os
from google import genai
from google.genai import types
from config import Config

async def test_grounding():
    cfg = Config()
    client = genai.Client()
    print(f"Testing model: {cfg.subagent_model}")
    try:
        response = await client.aio.models.generate_content(
            model=cfg.subagent_model,
            contents='What is the current population of Tokyo?',
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        print("Response received:")
        print(response.text)
        for candidate in response.candidates:
            if candidate.grounding_metadata:
                print("Grounding metadata found!")
                # print(candidate.grounding_metadata)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_grounding())
