from llm_impl import GeminiToolRegistry

registry = GeminiToolRegistry()

@registry.tool
def get_weather(location: str):
    return f"The weather is sunny in {location}"