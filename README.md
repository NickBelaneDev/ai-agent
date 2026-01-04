# AI Agents Service

A FastAPI-based service that provides an interface to Google's Gemini AI, designed to act as a smart backend for chat applications. It manages user sessions, handles context, supports function calling capabilities, and includes robust security and performance features.

## Features

*   **Smart Session Management**: Automatically handles user sessions with configurable timeouts and database persistence.
*   **Gemini Integration**: Utilizes Google's GenAI SDK (via `generic-llm-lib`) for advanced LLM capabilities.
*   **Function Calling**: Supports dynamic tool execution via the LLM (configured via `tool_registry`).
*   **Decentralized Agent Architecture**: The agent logic is decoupled and can be instantiated dynamically.
*   **Rate Limiting**: Built-in rate limiting using `slowapi`, with optional Redis support for distributed environments.
*   **Enhanced Security**: Includes SQL injection prevention, session isolation, and header-based authentication.
*   **Docker Ready**: Includes Dockerfile and docker-compose setup for easy deployment.
*   **Async Architecture**: Built on FastAPI and Uvicorn for high-performance asynchronous processing.

## Prerequisites

*   Python 3.12+
*   Docker & Docker Compose (optional, for containerized deployment)
*   Google Gemini API Key
*   Redis (optional, for distributed rate limiting)

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/NickBelaneDev/ai-agent
    cd ai-agents
    ```

2.  **Set up the environment:**
    Create a `.env` file in the root directory using `empty.env` as a template:
    ```bash
    cp empty.env .env
    ```
    Edit `.env` and fill in your details:
    ```properties
    GEMINI_API_KEY=your_api_key_here
    APP_API_TOKEN=your_secret_api_token_here
    DATABASE_URL=sqlite+aiosqlite:///./chat_database.db
    # Optional: Redis for rate limiting
    # REDIS_URL=redis://localhost:6379/0
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

### Database Inspection

A utility script is provided to quickly inspect the contents of the database (Users and Chat Sessions) for debugging purposes.

```bash
python inspect_db.py
```

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
    *   **Params**: `user_name` (str), `prompt` (str), `session_id` (optional str)
*   `POST /gemini/chat/text`: Stateful chat endpoint returning a plain text response.
    *   **Params**: `user_name` (str), `prompt` (str), `session_id` (optional str)

## Configuration

*   **`src/config/settings.py`**: Manages environment variables and global settings.
*   **`src/llms/gemini_default/llm_config.toml`**: (Default) Configuration for the LLM model parameters (temperature, tokens, etc.).
*   **`src/llms/gemini_default/tool_registry.py`**: Handles the registration of tools available to the LLM.

## Testing

The project includes a comprehensive test suite covering services, database operations, security, and race conditions.

Run tests using `pytest`:

```bash
pytest
```
