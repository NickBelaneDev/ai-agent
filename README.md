# mc-gemini

## Description

`mc-gemini` is a project that integrates Google's Gemini API into Minecraft, allowing players to interact with an AI through a chat command. This enables a wide range of possibilities, from answering questions to generating content directly within the game.

## How it Works

The project consists of two main components:

1.  **FastAPI Backend:** A Python-based web server that acts as a bridge between the Minecraft server and the Gemini API. It receives requests from the game, forwards them to the Gemini API, and returns the AI's response.
2.  **Skript Plugin:** A script for the Skript plugin on a Minecraft server. This script defines the in-game command that players use to interact with the AI and handles the communication with the FastAPI backend.

The architecture is as follows:
`Minecraft Server (with Skript) -> FastAPI Backend -> Gemini API`

## Components

### FastAPI Backend

The backend is a simple FastAPI application that exposes an endpoint to receive chat prompts from the Minecraft server. It manages chat sessions for each player, ensuring that conversations have context.

-   **`main.py`**: The main entry point of the FastAPI application.
-   **`src/services/chat_service.py`**: Handles the logic for managing chat sessions and communicating with the Gemini API.
-   **`src/llm/client.py`**: The client for the Gemini API.

### Skript Plugin

The `ask_ai.sk` script defines the `/askai` command in the game. When a player uses this command, the script sends an HTTP request to the FastAPI backend with the player's prompt. The response from the backend is then formatted and displayed in the in-game chat.

-   **`src/skript-lang/ask_ai.sk`**: The Skript file to be placed in the Minecraft server's `plugins/Skript/scripts` directory.

## Setup and Installation

### Backend

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/mc-gemini.git
    cd mc-gemini
    ```
2.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Set up your Gemini API key:**
    -   Create a `.env` file in the root directory.
    -   Add your Gemini API key to the `.env` file:
        ```
        GEMINI_API_KEY="your_api_key"
        ```
4.  **Run the backend server:**
    For a production environment, use `uvicorn` to run the application:
    ```bash
    uvicorn main:app --host 0.0.0.0 --port 8000
    ```

### Skript Plugin

1.  **Install the Skript plugin** on your Minecraft server.
2.  **Place the `ask_ai.sk` script** in the `plugins/Skript/scripts` directory of your server.
3.  **Reload the scripts** in-game with the command `/sk reload all`.

## Usage

Once the backend is running and the Skript plugin is set up, you can use the `/askai` command in Minecraft to interact with the AI.

**Syntax:**
`/askai <your_prompt>`

**Example:**
`/askai What is the crafting recipe for a diamond pickaxe?`

The AI's response will be displayed in the chat.
