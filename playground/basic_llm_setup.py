import os

import dotenv
from dotenv import load_dotenv, find_dotenv
from google import genai
from google.genai import types
load_dotenv(find_dotenv())

gemini_api_key = os.getenv("GEMINI_API_KEY")
# The client gets the API key from the environment variable `GEMINI_API_KEY`.
client = genai.Client(api_key=gemini_api_key)


def create_addieren_tool():
    _addieren_tool = types.Tool(
        function_declarations=[types.FunctionDeclaration(
            name="addiere",
            description="Erhalte die Summe beliebig vieler Zahlen. Die Zahlen müssen in einem 'Iterable' übergeben werden.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "a": types.Schema(type=types.Type.INTEGER, description="Die erste Zahl"),
                    "*nums": types.Schema(
                        type=types.Type.ARRAY, # Es ist eine Liste
                        description="Eine Liste von Zahlen, die addiert werden sollen.",
                        # Wir sagen, was IN der Liste sein soll:
                        items=types.Schema(type=types.Type.INTEGER)
                    )
                },
                required=["a", "*nums"]
            )
        )]
    )

    return _addieren_tool

addieren_tool = create_addieren_tool()

content_config = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_budget=0),
    temperature=0.01,
    max_output_tokens=100,
    system_instruction="Halte dich kurz und direkt. Antworte immer auf Deutsch.",
    tool_config=types.ToolConfig(),
    tools=[addieren_tool]
)

chat = client.chats.create(
    model="gemini-2.5-flash",
    config=content_config
)

def chat_with_llm(prompt: str):
    """"""
    response = chat.send_message(prompt)
    return response.text

def receive_text_response_from_llm(prompt: str):
    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents=prompt,
        config=content_config
    )
    return response.text


if __name__ == "__main__":

    #print(receive_text_response_from_llm("Warum sind Bananen gelb? Antworte in einem Satz."))
    chatverlauf = chat_with_llm("Erkläre in einem Satz, wie ein Differential funktioniert.")
    print(chatverlauf)


    client.close()