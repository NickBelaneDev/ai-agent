from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from src.config.settings import env_settings
from src.services.chat_service import SmartGeminiBackend
from src.config.logging_config import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the application's lifespan.
    Initializes the SmartGeminiBackend on startup and stores it in the app state.
    """
    logger.info("Application startup...")
    gemini_backend = SmartGeminiBackend(env_settings.GEMINI_API_KEY)
    app.state.gemini_backend = gemini_backend
    logger.info("SmartGeminiBackend initialized and attached to app state.")
    
    yield  # The application runs here
    
    logger.info("Application shutdown...")
    # Cleanup logic could be added here if necessary


app = FastAPI(lifespan=lifespan)


def get_gemini_backend(request: Request) -> SmartGeminiBackend:
    """
    Returns the single SmartGeminiBackend instance stored in the app state.
    """
    return request.app.state.gemini_backend

class ChatRequest(BaseModel):
    """Defines the structure for a chat request body."""
    player_name: str
    prompt: str

@app.get("/")
async def root():
    return {"message": "Welcome to the Smart Gemini API. See /docs for endpoints."}

@app.post("/gemini/generate_content")
async def generate_content(prompt: str,
                           gemini: SmartGeminiBackend = Depends(get_gemini_backend)):
    logger.info(f">> Incoming generate content request: {prompt}")
    response = await gemini.generate_content(prompt)
    return {"response": response}

@app.post("/gemini/chat")
async def chat_json(user_name: str,
                    prompt: str,
                    gemini: SmartGeminiBackend = Depends(get_gemini_backend)):
    """
    Receives a chat prompt and returns the response as a JSON array of strings,
    with each string being a line of the response.
    """
    logger.info(f">> Incoming JSON request: player='{user_name}', prompt='{prompt}'")
    response = await gemini.chat(user_name, prompt)
    return {"response": response}

@app.post("/gemini/chat/text")
async def chat_text(user_name: str,
                    prompt: str,
                    gemini: SmartGeminiBackend = Depends(get_gemini_backend)):
    """
    Receives a chat prompt and returns the response as a single plain text block,
    with lines separated by newline characters.
    """
    logger.info(f">> Incoming Text request: player='{user_name}', prompt='{prompt}'")
    response = await gemini.chat(user_name, prompt)
    # Join the list of lines into a single string with newlines for the PlainTextResponse
    logger.debug(f"response: {response}")
    return PlainTextResponse(response)