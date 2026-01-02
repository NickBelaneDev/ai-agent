from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request, Header, HTTPException, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from src.config.settings import env_settings
from src.services.chat_service import SmartGeminiBackend
from src.config.logging_config import logger
from src.db.connection import init_db
from src.llms.gemini_default.gemini import DefaultGeminiLLM


async def verify_api_token(x_auth_token: str = Header(alias="X-Auth-Token")):
    """
    Checks, if the x_auth_token is matching the APP_API_TOKEN.
    """
    if x_auth_token != env_settings.APP_API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Zugriff verweigert: Ungültiger Token."
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the application's lifespan.
    Initializes the SmartGeminiBackend on startup and stores it in the app state.
    """
    logger.info("Application startup...")
    await init_db()
    logger.info("Database initialized.")

    gemini_backend = SmartGeminiBackend(DefaultGeminiLLM)
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
    user_name: str
    prompt: str

@app.get("/")
async def root():
    return {"message": "Welcome to the Smart Gemini API. See /docs for endpoints."}

@app.post("/gemini/generate_content", dependencies=[Depends(verify_api_token)])
async def generate_content(prompt: str,
                           gemini: SmartGeminiBackend = Depends(get_gemini_backend)):
    logger.info(f">> Incoming generate content request: {prompt}")
    response = await gemini.generate_content(prompt)
    return {"response": response}

@app.post("/gemini/chat", dependencies=[Depends(verify_api_token)])
async def chat_json(request: ChatRequest,
                    gemini: SmartGeminiBackend = Depends(get_gemini_backend)):
    """
    Receives a chat prompt and returns the response as a JSON array of strings,
    with each string being a line of the response.
    """
    logger.info(f">> Incoming JSON request: player='{request.user_name}', prompt='{request.prompt}'")
    response = await gemini.chat(request.user_name, request.prompt)
    return {"response": response}

@app.post("/gemini/chat/text", dependencies=[Depends(verify_api_token)])
async def chat_text(request: ChatRequest,
                    gemini: SmartGeminiBackend = Depends(get_gemini_backend)):
    """
    Receives a chat prompt and returns the response as a single plain text block,
    with lines separated by newline characters.
    """
    logger.info(f">> Incoming Text request: player='{request.user_name}', prompt='{request.prompt}'")
    response = await gemini.chat(request.user_name, request.prompt)
    # Join the list of lines into a single string with newlines for the PlainTextResponse
    logger.debug(f"response: {response}")
    return PlainTextResponse(response)