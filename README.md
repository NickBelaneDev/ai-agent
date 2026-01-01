# AI Agents

## Description

`ai-agents` is a project that integrates Google's Gemini API into a FastAPI backend, designed to act as an intelligent assistant. It supports chat sessions with context management and tool execution (function calling). The project is configured to run as a "board computer" style assistant, optimized for small displays (e.g., 128x64 pixels on an ESP32), but can be adapted for other interfaces like Minecraft or web apps.

## Features

*   **FastAPI Backend:** A robust Python-based web server.
*   **Gemini Integration:** Uses Google's Gemini API for intelligence.
*   **Context Management:** Maintains chat history per user/session with automatic timeout cleanup.
*   **Tool Support:** Extensible registry for defining and executing tools (function calls) that the AI can use.
*   **Configurable:** Uses TOML configuration for LLM settings (model, temperature, system instructions).
*   **Docker Ready:** Includes Dockerfile and docker-compose setup for easy deployment.

## Architecture

The system follows a clean architecture:
*   `main.py`: Entry point for the FastAPI application.
*   `src/services/chat_service.py`: Manages chat sessions and business logic.
*   `src/llm/client.py`: Handles direct interaction with the Gemini API.
*   `src/llm/registry.py`: Manages available tools for the LLM.
*   `src/config/`: Configuration loading and settings.

## Setup and Installation

### Prerequisites

*   Python 3.12+
*   A Google Gemini API Key

### Local Development

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd ai-agents
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # Linux/Mac
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Environment Configuration:**
    *   Create a `.env` file in the root directory (copy from `empty.env` or `service.template` if available, though `empty.env` seems to be a placeholder).
    *   Add your Gemini API key:
        ```env
        GEMINI_API_KEY="your_actual_api_key_here"
        ```

5.  **Run the server:**
    For production-like local testing, we use `gunicorn` with `uvicorn` workers:
    ```bash
    gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
    ```
    Alternatively, for simple development reloading:
    ```bash
    uvicorn main:app --reload
    ```
    The API will be available at `http://127.0.0.1:8000`.

### Docker

1.  **Build and Run:**
    ```bash
    docker-compose up --build
    ```

## Usage

### API Endpoints

*   `GET /`: Health check/Welcome message.
*   `POST /gemini/generate_content`: Simple one-off prompt generation.
    *   Query Param: `prompt`
*   `POST /gemini/chat`: Chat with context, returns JSON response.
    *   Query Params: `user_name`, `prompt`
*   `POST /gemini/chat/text`: Chat with context, returns plain text response.
    *   Query Params: `user_name`, `prompt`

### Configuration

You can modify the behavior of the AI agent by editing `src/config/home_agent_config.toml`.
*   `system_instruction`: Change the persona and rules for the AI.
*   `model`: Switch Gemini models (e.g., `gemini-1.5-flash`).
*   `temperature`: Adjust creativity.

## Tools

To add new tools:
1.  Define the tool function in `src/llm/tools/`.
2.  Register it in `src/llm/registry.py`.
The LLM will automatically be aware of the new tool and can call it during conversations.
