"""
Program: Memory Controlled Autonomous Agent (Day 8)

Purpose:
--------
This program implements a multi-step AI agent with structured tool execution,
duplicate call prevention, validation handling, and controlled memory management.

What This Agent Does:
---------------------
1. Accepts a user question.
2. Lets the LLM decide whether to call a tool.
3. Executes tools safely with:
   - JSON argument parsing
   - Type validation
   - Runtime error protection
4. Prevents repeated execution of identical tool calls.
5. Implements structured memory control:
   - Preserves original user question.
   - Maintains a working memory window.
   - Summarizes older conversation into a system message.
6. Stops naturally when no tool call is required.
7. Includes a hard safety cap using max_steps.

Key Architectural Concepts:
---------------------------
- LLM = Reasoning Engine
- Tool Registry = Execution Layer
- Control Loop = Orchestrator
- Structured Memory = Context Management
- Duplicate Detection = Stability Mechanism
- Validation + Exception Handling = Robustness Layer

Why This Matters:
-----------------
This transforms a simple API call into a controlled autonomous reasoning system.
It prevents infinite loops, context explosion, and unsafe tool execution.

Learning Milestone:
-------------------
By this stage, the agent supports:
- Multi-step reasoning
- Parameterized tools
- Execution safety
- Memory trimming
- Summarization stub
- Deterministic stopping behavior

This is no longer a toy script — it is a foundational agent architecture.
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
# TOOL DEFINITIONS
# -------------------------

def calculate_square_root(number):
    try:
        number = float(number)
    except(ValueError,TypeError):
        return "ERROR : number must be numeric"
    
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

# -------------------------
# TOOL Registry
# -------------------------

tool_registry = {"calculate_square_root":calculate_square_root}


# -------------------------
# USER INPUT
# -------------------------

user_question = "What is the square root of -25?"

conversation = [
    {"role": "user", "content": user_question}
]

max_steps = 5
step = 0
tool_call_history = []


# -------------------------
# Memory Config
# -------------------------

MAX_WORKING_MEMORY = 6

def summarize_conversation(old_messages):
    return "Summary: Previous steps included tool calls and validations."


# -------------------------
# AGENT LOOP
# -------------------------

while step < max_steps:

    print("Starting agent...")

    step += 1
    print(f"\n--- Step {step} ---")

    if len(conversation) > MAX_WORKING_MEMORY:
        print("Applying structured memory trimming...")

        core_memory = conversation[:1]

        older_memory = conversation[1:-MAX_WORKING_MEMORY]

        if older_memory:
            summary_text = summarize_conversation(older_memory)
            summary_message = {"role":"system", "content": summary_text}

            conversation = core_memory + [summary_message] + conversation[-MAX_WORKING_MEMORY:]
        else:
            conversation = core_memory + conversation[-MAX_WORKING_MEMORY:]

# -------------------------
    # LLM CALL
    # -------------------------
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=conversation,
        tools=tools,
        tool_choice="required"
        # Removed tool_choice="required" for natural stopping
    )

    message = response.choices[0].message
    conversation.append(message)

    print("Conversation length:", len(conversation))

    # -------------------------
    # NATURAL TERMINATION
    # -------------------------
    if not message.tool_calls:
        print("\nFinal Answer:", message.content)
        break

    # -------------------------
    # TOOL EXECUTION
    # -------------------------
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

        # Duplicate detection
        call_signature = (function_name, json.dumps(arguments, sort_keys=True))

        if call_signature in tool_call_history:
            print("Duplicate tool call detected. Stopping loop.")
            step = max_steps
            break

        tool_call_history.append(call_signature)

        # Safe execution
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
