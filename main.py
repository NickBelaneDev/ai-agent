from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
import uvicorn

from src.config.settings import GEMINI_API_KEY
from src.services.chat_service import SmartGeminiBackend

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
    print(f">> Incoming generate content request: {prompt}")
    response = await GEMINI.generate_content(prompt)
    return {"response": response}

@app.post("/gemini/chat")
async def chat_json(player_name: str, prompt: str):
    """
    Receives a chat prompt and returns the response as a JSON array of strings,
    with each string being a line of the response.
    """
    print(f">> Incoming JSON request: player='{player_name}', prompt='{prompt}'")
    response = await GEMINI.chat(player_name, prompt)
    return {"response": response}

@app.post("/gemini/chat/text")
async def chat_text(player_name: str, prompt: str):
    """
    Receives a chat prompt and returns the response as a single plain text block,
    with lines separated by newline characters.
    """
    print(f">> Incoming Text request: player='{player_name}', prompt='{prompt}'")
    response = await GEMINI.chat(player_name, prompt)
    # Join the list of lines into a single string with newlines for the PlainTextResponse
    print(f"response: {response}")
    return PlainTextResponse(response)

if __name__ == "__main__":
    # Dieser Block wird nur ausgeführt, wenn das Skript direkt mit `python main.py`
    # gestartet wird. Er dient dem lokalen Entwickeln.
    # - `uvicorn.run(...)`: Startet den ASGI-Server, der deine App ausführt.
    # - `reload=True`: Ist extrem nützlich in der Entwicklung. Der Server startet
    #   automatisch neu, sobald du eine Änderung im Code speicherst.
    # In einer Produktionsumgebung würdest du den Server anders starten,
    # z.B. mit: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app`
    print("Starting FastAPI server... Go to 0.0.0.0")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)