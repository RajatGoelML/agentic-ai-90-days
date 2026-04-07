"""
Program: Planner-Executor Agent (Day 9)

Purpose:
--------
Separates reasoning (planner) from execution (executor).
The LLM returns structured action JSON.
Controller validates and executes safely.
"""

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
# TOOL DEFINITIONS & TOOL REGISTRY
# -------------------------
def calculate_square_root(number):
    try:
        number = float(number)
    except (ValueError, TypeError):
        return "ERROR: number must be numeric."

    if number < 0:
        return "ERROR: Cannot compute square root of negative number."

    return str(math.sqrt(number))


tool_registry = {
    "calculate_square_root": calculate_square_root
}

# -------------------------
# PLANNER PROMPT
# -------------------------

SYSTEM_PROMPT = """
You are a planner agent.

Always respond in strict JSON format.

Available actions:

1. call_tool
{
  "action": "call_tool",
  "tool_name": "<tool_name>",
  "arguments": { ... }
}

2. final_answer
{
  "action": "final_answer",
  "content": "<your answer>"
}

3. ask_clarification
{
  "action": "ask_clarification",
  "question": "<question to user>"
}

4. reflect_and_retry
{
  "action": "reflect_and_retry",
  "reason": "<why retry>",
  "modified_arguments": { ... }
}

Policy:
- Prefer using tool for square root.
- If tool fails due to invalid user input, ask clarification.
- If tool fails due to tool limitation, reason appropriately.
"""

# -------------------------
# USER INPUT
# -------------------------
user_question = "What is the square root of abc?"

conversation = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": user_question}
]

max_steps = 5
step = 0

# -------------------------
# CONTROLLER LOOP
# -------------------------
while step < max_steps:
    print("debug --")

    step += 1
    print(f"\n--- Step {step} ---")

    # Ask planner what to do
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=conversation
    )


    planner_output = response.choices[0].message.content
    print("RAW >>>", repr(planner_output))

    print("Planner Raw Output:", planner_output)

    # Validate JSON
    try:
        action_data = json.loads(planner_output)
    except json.JSONDecodeError:
        print("ERROR: Planner returned invalid JSON.")
        break

    action = action_data.get("action")

    # -------------------------
    # EXECUTION PATH
    # -------------------------

    if action == "call_tool":

        tool_name = action_data.get("tool_name")
        arguments = action_data.get("arguments", {})

        if tool_name not in tool_registry:
            print("ERROR: Tool not found.")
            break

        print("Executing Tool:", tool_name)
        print("Arguments:", arguments)

        try:
            result = tool_registry[tool_name](**arguments)
        except Exception as e:
            result = f"ERROR: {str(e)}"

        print("Tool Result:", result)

                # Feed result back to planner
        conversation.append({
            "role": "assistant",
            "content": planner_output
        })

        conversation.append({
            "role": "user",
            "content": f"Tool result: {result}"
        })

    elif action == "final_answer":

        print("\nFinal Answer:", action_data.get("content"))
        break

    elif action == "ask_clarification":
         print("\nClarification Needed:", action_data.get("question"))
         break
    
    elif action == "reflect_and_retry":
        print("Planner wants retry:", action_data.get("reason"))

        arguments = action_data.get("modified_arguments", {})
        result = tool_registry[tool_name](**arguments)

        conversation.append({
             "role": "user",
             "content": f"Tool retry result: {result}"
         })

    else:
        print("ERROR: Unknown action.")
        break