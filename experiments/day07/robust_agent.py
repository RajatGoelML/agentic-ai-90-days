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
    try:
        number = float(number)
    except (ValueError, TypeError):
        return "ERROR: 'number' must be numeric."

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
user_question = "What is the square root of -25?"

conversation = [
    {"role": "user", "content": user_question}
]

max_steps = 5
step = 0

# ✅ MUST be outside loop
tool_call_history = []

# -------------------------
# AGENT LOOP
# -------------------------
while step < max_steps:

    step += 1
    print(f"\n--- Step {step} ---")
    MAX_MESSAGES = 4

    if len(conversation) > MAX_MESSAGES:
        print("Trimming conversation memory...")
        conversation = conversation[-MAX_MESSAGES:]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=conversation,
        tools=tools,
        tool_choice="required"
    )

    message = response.choices[0].message
    conversation.append(message)

    print("Conversation length:", len(conversation))


    if message.tool_calls:
        for tool_call in message.tool_calls:
            function_name = tool_call.function.name

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

            print("Requested:", function_name)
            print("Arguments:", arguments)

            # ✅ Duplicate Detection
            call_signature = (function_name, json.dumps(arguments, sort_keys=True))

            if call_signature in tool_call_history:
                print("Duplicate tool call detected. Stopping loop.")
                step = max_steps
                break

            tool_call_history.append(call_signature)

            # ✅ Safe execution
            if function_name in tool_registry:
                try:
                    tool_result = tool_registry[function_name](**arguments)
                except Exception as e:
                    tool_result = f"ERROR: {str(e)}"
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
