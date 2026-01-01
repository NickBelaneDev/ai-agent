# This is an example tool to showcase how to create your own.
# We create a singleton of the tool, which you will further import to your 'ToolRegistry' Class

from google.genai import types

# --- Tool Implementation ---
# This is the actual Python function that gets executed.
def request_weather(city: str):
    return f"Sunny, 20°C in {city}"

# --- Tool Declaration for the LLM ---
# This is the schema that tells the LLM how to call the function.
request_weather_declaration = types.FunctionDeclaration(
    name="request_weather",
    description="Make a request to the OpenWeatherAPI.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        required=["city"],
        properties={"city": types.Schema(type=types.Type.STRING,
                                            description="The name of the city you want to get the weather from.")},
    ),
)


