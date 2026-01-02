# This is an example tool to showcase how to create your own.
# We create a singleton of the tool, which you will further import to your 'ToolRegistry' Class

from google.genai import types
from llm_core import ToolDefinition
# --- Tool Implementation ---
# This is the actual Python function that gets executed.
def request_weather(city: str):
    return f"Sunny, 20°C in {city}"

request_weather_tool = ToolDefinition(
    name="request_weather",
    description="Make a request to the OpenWeatherAPI.",
    func=request_weather,
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "city": types.Schema(
                type=types.Type.STRING,
                description="The name of the city you want to get the weather from."
            )
        },
        required=["city"] # Wichtig: Gib an, welche Parameter zwingend sind
    )
)


