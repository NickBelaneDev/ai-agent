import asyncio
import time
from google import genai

from src.config.settings import GEMINI_API_KEY, TIMEOUT_SECONDS
from src.llm.client import HomeAgent, process_chat_turn

class SmartGeminiBackend:
    """
    A backend service to host and manage Minecraft chat sessions.
    It monitors chats, decides when to start a new one, and when to forget an old one.
    Chat sessions are stored in an in-memory dictionary.
    """
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.agent = HomeAgent(self.client)

        # We store sessions here: {'player_name': {'chat': chat_object, 'last_active': timestamp}}
        self.sessions = {}

    def _get_clean_session(self, player_name: str):
        current_time = time.time()

        if player_name in self.sessions:
            last_active = self.sessions[player_name]['last_active']

            if (current_time - last_active) > TIMEOUT_SECONDS:
                print(f"Session for {player_name} has expired. Starting a new context.")
                del self.sessions[player_name]
            else:
                return self.sessions[player_name]['chat']


        if player_name not in self.sessions:
            print(f"Creating a new chat for {player_name}...")
            new_chat = self.agent.get_chat()

            self.sessions[player_name] = {
                'chat': new_chat,
                'last_active': current_time
            }
            print(f"New chat for {player_name} created!\n")

        return self.sessions[player_name]['chat']

    async def generate_content(self, prompt: str) -> str:
        print(f"generate_content: {prompt}")
        return self.agent.ask(prompt)

    async def chat(self, player_name: str, prompt: str) -> str:
        """
        Handles a single chat turn for a given player.

        The response is split into multiple strings, one for each line,
        to make it suitable for display in Minecraft chat.
        """
        chat_session = self._get_clean_session(player_name)
        print(f"chat: {player_name=}, \n{prompt=}")
        response = await process_chat_turn(chat_session, prompt)
        print(f"response: {response}")
        self.sessions[player_name]['last_active'] = time.time()

        # Split the response by newlines to create separate chat messages.
        return response

    def cleanup_memory(self):
        """Clear all inactive chat sessions."""
        current_time = time.time()

        to_delete = [
            player for player, data in self.sessions.items()
            if (current_time - data['last_active']) > TIMEOUT_SECONDS
        ]
        for player in to_delete:
            del self.sessions[player]
            print(f"Cleaned up inactive session for {player}.")

# A small test function for the chat service.
async def main():
    """Main async function to run the chat client for testing."""
    print("Starting SmartGeminiBackend test client...")
    gemini = SmartGeminiBackend(GEMINI_API_KEY)

    while True:
        user_prompt = input("\nYou> ")
        if user_prompt.lower() in ["exit", "quit"]:
            break
        response_lines = await gemini.chat("Player1", user_prompt)
        
        # Print each line of the response, simulating how Minecraft would show it.
        for line in response_lines:
            print(f"LLM: {line}")

if __name__ == "__main__":
    # To run an async function from the top level, you use asyncio.run()
    asyncio.run(main())

        