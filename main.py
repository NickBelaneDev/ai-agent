from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from src.config.settings import GEMINI_API_KEY
from src.services.chat_service import SmartGeminiBackend
from src.config.logging_config import logger

app = FastAPI()
# Initialize the backend service as a global instance
GEMINI = SmartGeminiBackend(GEMINI_API_KEY)

class ChatRequest(BaseModel):
    """Defines the structure for a chat request body."""
    player_name: str
    prompt: str

@app.get("/")
async def root():
    return {"message": "Welcome to the MC-Gemini API. See /docs for endpoints."}

@app.post("/gemini/generate_content")
async def generate_content(prompt: str):
    logger.info(f">> Incoming generate content request: {prompt}")
    response = await GEMINI.generate_content(prompt)
    return {"response": response}

@app.post("/gemini/chat")
async def chat_json(player_name: str, prompt: str):
    """
    Receives a chat prompt and returns the response as a JSON array of strings,
    with each string being a line of the response.
    """
    logger.info(f">> Incoming JSON request: player='{player_name}', prompt='{prompt}'")
    response = await GEMINI.chat(player_name, prompt)
    return {"response": response}

@app.post("/gemini/chat/text")
async def chat_text(player_name: str, prompt: str):
    """
    Receives a chat prompt and returns the response as a single plain text block,
    with lines separated by newline characters.
    """
    logger.info(f">> Incoming Text request: player='{player_name}', prompt='{prompt}'")
    response = await GEMINI.chat(player_name, prompt)
    # Join the list of lines into a single string with newlines for the PlainTextResponse
    logger.debug(f"response: {response}")
    return PlainTextResponse(response)