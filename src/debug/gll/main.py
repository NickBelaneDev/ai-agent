from llm_impl import (GenericGemini,
                          GeminiTokens,
                          GeminiChatResponse,
                          GeminiToolRegistry,
                          GeminiMessageResponse)

import asyncio
from google import genai
from dotenv import load_dotenv, find_dotenv
import os
from tools import registry

load_dotenv(find_dotenv())
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)
llm = GenericGemini(client, "gemini-2.0-flash-exp", "You are helpful.", registry)


# 4. Chat
async def main():
    gemini_chat = await llm.chat([], "Weather in Berlin?")
    print(gemini_chat.last_response.text)
    print(gemini_chat.last_response.tokens.total_token_count)
    print(gemini_chat.history)


if __name__ == "__main__":
    asyncio.run(main())

