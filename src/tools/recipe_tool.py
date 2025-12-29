import json

from google.genai import types
from typing import List, Any

def get_db():
    raise NotImplementedError

# --- Tool Implementation ---
# This is the actual Python function that gets executed.
def _format_recipe_results(recipes: List[dict[str, Any]]):
    formatted_recipes = []
    for recipe in recipes:
        formatted_recipes.append({
            "type": recipe["recipe_type"],
            "output": f"{recipe['result_count']}x {recipe['result_name']}",
            "ingredients": json.loads(recipe["ingredients_json"]),
            "pattern": json.loads(recipe["pattern_json"]) if recipe["pattern_json"] else None
        })

    return formatted_recipes

def find_recipes(item_id: str) -> dict[str, list[dict[str, str | None]]]:
    """
    Finds all Minecraft recipes for a specific item.
    In a real application, this would query a database or an external API.
    """
    #print(f"TOOL: Searching for recipes with result_id '{item_id}'...")
    db = get_db()
    recipes = db.find_recipes_by_id(item_id)
    # Mock response for demonstration
    formatted_recipes = _format_recipe_results(recipes)
    return {"recipes": formatted_recipes}

# --- Tool Declaration for the LLM ---
# This is the schema that tells the LLM how to call the function.
find_recipes_declaration = types.FunctionDeclaration(
    name="find_recipes",
    description="Get all crafting recipes for a specific item ID (e.g., 'minecraft:stick').",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        required=["item_id"],
        properties={"item_id": types.Schema(type=types.Type.STRING,
                                            description="The technical ID of the item, e.g., 'minecraft:oak_planks'.")},
    ),
)