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

def calculate_square_root(number):
    # NEW - DAY 6: Added type validation
    try:
        number = float(number)
    except (ValueError, TypeError):
        return "ERROR: 'number' must be numeric."

    # NEW - DAY 6: Added negative number protection
    if number < 0:
        return "ERROR: Cannot compute square root of negative number."

    return str(math.sqrt(number))


# -------------------------
# TOOL SCHEMA
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

tool_registry = {
    "calculate_square_root": calculate_square_root
}

# -------------------------
# USER INPUT
# -------------------------
user_question = "What is the square root of -25?"  # NEW test case

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
        tool_choice="required"
    )

    message = response.choices[0].message
    conversation.append(message)

    if message.tool_calls:
        for tool_call in message.tool_calls:
            function_name = tool_call.function.name

            # NEW - DAY 6: Safe JSON parsing block

            try:
                arguments = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                tool_result = "ERROR: Invalid JSON arguments."
                conversation.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result
                })
                continue

            # OLD VERSION (Day 5 behavior)
            arguments = json.loads(tool_call.function.arguments)

            print("Requested:", function_name)
            print("Arguments:", arguments)

            if function_name in tool_registry:
                # NEW - DAY 6: Execution safety wrapper
                try:
                    tool_result = tool_registry[function_name](**arguments)
                except Exception as e:
                    tool_result = f"ERROR: {str(e)}"

                # OLD VERSION (Day 5 behavior)
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
