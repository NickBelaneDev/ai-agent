import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request, Header, HTTPException, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.config.settings import env_settings
from src.services.chat_service import SmartGeminiBackend
from src.config.logging_config import logger
from src.db.connection import init_db
from src.llms.gemini_default.gemini import DefaultGeminiLLM

# --- Rate Limiting Setup ---
if env_settings.REDIS_URL:
    # Profi-Modus: Synchronisiert über alle Instanzen hinweg
    logger.info(f"Verwende Redis für Rate-Limiting: {env_settings.REDIS_URL}")
    limiter = Limiter(key_func=get_remote_address, storage_uri=env_settings.REDIS_URL)
else:
    # Einfacher Modus: Nur lokaler Speicher (für Einzel-Instanzen)
    logger.info("Kein Redis konfiguriert. Verwende In-Memory Rate-Limiting.")
    limiter = Limiter(key_func=get_remote_address)

async def verify_api_token(x_auth_token: str = Header(alias="X-Auth-Token")):
    """
    Checks, if the x_auth_token is matching the APP_API_TOKEN.
    """
    if x_auth_token != env_settings.APP_API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Invalid Token."
        )

@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    """
    Manages the application's lifespan.
    Initializes the SmartGeminiBackend on startup and stores it in the app state.
    """
    logger.info("Application startup...")
    
    # Initialize Database
    await init_db()
    logger.info("Database initialized.")

    # Initialize Backend Service
    gemini_backend = SmartGeminiBackend(DefaultGeminiLLM)
    fastapi_app.state.gemini_backend = gemini_backend
    
    logger.info("SmartGeminiBackend initialized and attached to app state.")
    
    yield  # The application runs here
    
    logger.info("Application shutdown...")


# --- App Initialization ---
app = FastAPI(lifespan=lifespan)

# Attach Limiter to App State (Required by slowapi)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


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
@limiter.limit("10/minute")
async def generate_content(request: Request,
                           prompt: str,
                           gemini: SmartGeminiBackend = Depends(get_gemini_backend)):
    logger.info(f">> Incoming generate content request: {prompt}")
    response = await gemini.generate_content(prompt)
    return {"response": response}

@app.post("/gemini/chat", dependencies=[Depends(verify_api_token)])
@limiter.limit("10/minute")
async def chat_json(request: Request,
                    chat_req: ChatRequest,
                    gemini: SmartGeminiBackend = Depends(get_gemini_backend)):
    """
    Receives a chat prompt and returns the response as a JSON array of strings,
    with each string being a line of the response.
    """
    logger.info(f">> Incoming JSON request: player='{chat_req.user_name}', prompt='{chat_req.prompt}'")
    response = await gemini.chat(chat_req.user_name, chat_req.prompt)
    return {"response": response}

@app.post("/gemini/chat/text", dependencies=[Depends(verify_api_token)])
@limiter.limit("10/minute")
async def chat_text(request: Request,
                    chat_req: ChatRequest,
                    gemini: SmartGeminiBackend = Depends(get_gemini_backend)):
    """
    Receives a chat prompt and returns the response as a single plain text block,
    with lines separated by newline characters.
    """
    logger.info(f">> Incoming Text request: player='{chat_req.user_name}', prompt='{chat_req.prompt}'")
    response = await gemini.chat(chat_req.user_name, chat_req.prompt)
    # Join the list of lines into a single string with newlines for the PlainTextResponse
    logger.debug(f"response: {response}")
    return PlainTextResponse(response)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)