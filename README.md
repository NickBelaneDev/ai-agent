# AI Agents - Rapid Gemini API Wrapper

## Overview

**AI Agents** is a lightweight, flexible boilerplate designed to help you rapidly deploy a custom API endpoint for Google's Gemini models. It serves as a playground and a solid foundation for building your own AI assistants.

The core philosophy is simplicity and extensibility: **You provide the tools and the context, and this project provides the infrastructure.**

Whether you want to build a smart home controller, a personal coding assistant, or a "board computer" for an embedded display, this project lets you focus on *what* your agent can do, rather than *how* to connect it to the web.

## Key Features

*   **Instant API:** Get a production-ready FastAPI server up and running in minutes.
*   **Tool-First Design:** Easily "feed" your agent with custom Python functions (tools). The system handles the complex function calling loop automatically.
*   **Context Aware:** Built-in session management keeps track of conversations per user, so your agent remembers what was just said.
*   **Configurable Persona:** Define your agent's personality, constraints, and system instructions via a simple TOML file.
*   **Docker Ready:** Includes Dockerfile and docker-compose setup for easy deployment.

## How It Works

1.  **Define a Tool:** Write a standard Python function (e.g., `turn_on_lights()`, `query_database()`).
2.  **Register It:** Add your function to the `ToolRegistry`.
3.  **Chat:** Send a prompt to the API. Gemini decides if it needs to use your tool, the backend executes it, and the result is fed back to the AI for the final response.

## Getting Started

### Prerequisites

*   Python 3.12+
*   A Google Gemini API Key

### Quick Start

1.  **Clone & Install:**
    ```bash
    git clone https://github.com/NickBelaneDev/ai-agent
    cd ai-agents
    python3 -m venv .venv # create a venv if you not already have one.
    pip install -r requirements.txt
    ```

2.  **Configure:**
    Create a `.env` file and add your API key:
    ```env
    GEMINI_API_KEY="your_api_key_here"
    ```

3.  **Run:**
    ```bash
    # For development
    uvicorn main:app --reload
    
    # For production
    gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
    ```

4.  **Interact:**
    Open your browser to `http://127.0.0.1:8000/docs` to test the endpoints.

## Customization

### 1. Giving your Agent a Personality
Edit `src/config/home_agent_config.toml` to change the system instructions.
```toml
[config]
system_instruction="You are a sarcastic robot assistant."
model="gemini-1.5-flash"
```

### 2. Adding Capabilities (Tools)
This is where the magic happens. To give your agent new powers:

1.  **Create a Tool File:** Add a new file in `src/llm/tools/` (e.g., `my_tools.py`).
2.  **Define the Function:** Write your Python logic.
3.  **Define the Schema:** Create a `types.FunctionDeclaration` so Gemini knows how to use it.
4.  **Register:** Import your tool in `src/llm/registry.py` and add it to the list.

*See `src/llm/tools/example_tool.py` for a complete reference.*

## API Endpoints

*   `POST /gemini/chat`: The main endpoint. Sends a user message and returns the AI's response (handling any tool calls internally).
*   `POST /gemini/chat/text`: Same as above, but returns a plain text response (useful for simple clients like microcontrollers).
*   `POST /gemini/generate_content`: For single, stateless prompts without history.

## Deployment

The project includes a `Dockerfile` and `docker-compose.yml` for easy containerization.

```bash
docker-compose up --build
```

## Project Structure

*   `main.py`: The API entry point.
*   `src/llm/`: Contains the Gemini client, tool registry, and tool definitions.
*   `src/services/`: Business logic (chat session management).
*   `src/config/`: Configuration files.
