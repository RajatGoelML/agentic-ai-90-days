from openai import OpenAI
from dotenv import load_dotenv
import math
import json

# -------------------------
# Setup
# -------------------------
load_dotenv()
client = OpenAI()

# -------------------------
# TOOL DEFINITIONS
# -------------------------
def calculate_square_root(number: float):
    if number < 0:
        return "ERROR: Cannot compute square root of negative number."
    return str(math.sqrt(number))

# -------------------------
# TOOL SCHEMA (LLM VIEW)
# -------------------------
tools = [
    {
        "type": "function",
        "function": {
            "name": "calculate_square_root",
            "description": "Calculates the square root of a given number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "number": {
                        "type": "number",
                        "description": "The number to compute square root for."
                    }
                },
                "required": ["number"]
            }
        }
    }
]

# -------------------------
# TOOL REGISTRY
# -------------------------
tool_registry = {
    "calculate_square_root": calculate_square_root
}

# -------------------------
# USER INPUT
# -------------------------
user_question = "What is the square root of 144?"

conversation = [
    {"role": "user", "content": user_question}
]

max_steps = 5
step = 0

# -------------------------
# AGENT LOOP
# -------------------------
while step < max_steps:
    step += 1
    print(f"\n--- Step {step} ---")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=conversation,
        tools=tools,
    )

    message = response.choices[0].message
    conversation.append(message)

    print("DEBUG tool_calls:", message.tool_calls)
    print("DEBUG content:", message.content)

    if message.tool_calls:
        for tool_call in message.tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)

            print("Model requested:", function_name)
            print("Arguments:", arguments)

            if function_name in tool_registry:
                tool_result = tool_registry[function_name](**arguments)
            else:
                tool_result = f"ERROR: Tool '{function_name}' not available."

            print("Tool Result:", tool_result)

            conversation.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_result
            })

    else:
        print("\nFinal Answer:", message.content)
        break
