# AI Agents Service

A FastAPI-based service that provides an interface to Google's Gemini AI, designed to act as a smart backend for chat applications. It manages user sessions, handles context, and supports function calling capabilities.

## Features

*   **Smart Session Management**: Automatically handles user sessions with configurable timeouts.
*   **Gemini Integration**: Utilizes Google's GenAI SDK for advanced LLM capabilities.
*   **Function Calling**: Supports dynamic tool execution via the LLM (configured via `tool_registry`).
*   **Decentralized Agent Architecture**: The agent logic is decoupled and can be instantiated dynamically.
*   **Docker Ready**: Includes Dockerfile and docker-compose setup for easy deployment.
*   **Async Architecture**: Built on FastAPI and Uvicorn for high-performance asynchronous processing.

## Prerequisites

*   Python 3.12+
*   Docker & Docker Compose (optional, for containerized deployment)
*   Google Gemini API Key

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/NickBelaneDev/ai-agent
    cd ai-agents
    ```

2.  **Set up the environment:**
    Create a `.env` file in the root directory (you can use `empty.env` as a template):
    ```properties
    GEMINI_API_KEY=your_api_key_here
    APP_API_TOKEN=your_secret_api_token_here
    # Optional overrides
    # PROJECT_ROOT=/path/to/project
    # HOME_AGENT_CONFIG_PATH=/path/to/config.toml
    ```
    **Important**: The `APP_API_TOKEN` is crucial for securing your service. Choose a strong, unique token.

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

### Running Locally

Start the server using Uvicorn:

```bash
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.

### Running with Docker

1.  **Build and start the container:**
    ```bash
    docker-compose up --build -d
    ```

2.  The service will be accessible at `http://localhost:8083` (as configured in `docker-compose.yml`).

## Authentication

All API endpoints under `/gemini/` require authentication using an `APP_API_TOKEN`. You must include an `X-Auth-Token` header with your requests, containing the value of your `APP_API_TOKEN` defined in your `.env` file.

**Example using `curl`:**

```bash
curl -X POST "http://localhost:8000/gemini/chat" \
     -H "X-Auth-Token: your_secret_api_token_here" \
     -H "Content-Type: application/json" \
     -d '{
           "user_name": "test_user",
           "prompt": "Hello, Gemini!"
         }'
```

## API Endpoints

*   `GET /`: Health check and welcome message.
*   `POST /gemini/generate_content`: Simple one-off content generation.
    *   **Params**: `prompt` (str)
*   `POST /gemini/chat`: Stateful chat endpoint returning a JSON response.
    *   **Params**: `user_name` (str), `prompt` (str)
*   `POST /gemini/chat/text`: Stateful chat endpoint returning a plain text response.
    *   **Params**: `user_name` (str), `prompt` (str)

## Configuration

*   **`src/config/settings.py`**: Manages environment variables and global settings.
*   **`src/config/llm_config.toml`**: (Default) Configuration for the LLM model parameters (temperature, tokens, etc.).
*   **`src/llms/tools.py`**: Handles the registration of tools available to the LLM.
