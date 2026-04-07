"""
Program: Planner-Executor-Critic Agent (Day 10)

Purpose:
--------
Adds a verification layer to the planner-executor architecture.
Before returning a final answer, a critic LLM validates correctness.
If rejected, the planner must reconsider.

This introduces self-reflection capability.
"""

from openai import OpenAI
from dotenv import load_dotenv
import json
import math

load_dotenv()
client = OpenAI()

# -------------------------
# TOOL DEFINITIONS
# -------------------------
def calculate_square_root(number):
    try:
        number = float(number)
    except (ValueError, TypeError):
        return "ERROR: number must be numeric."

    if number < 0:
        return "ERROR: Cannot compute square root of negative number."

    return str(math.sqrt(number))

# -------------------------
# TOOL REGISTRY
# -------------------------

tool_registry = {
    "calculate_square_root": calculate_square_root
}

# -------------------------
# PROMPTS
# -------------------------

PLANNER_PROMPT = """
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

Policy:
- Prefer using calculate_square_root tool for square root.
"""

CRITIC_PROMPT = """
You are a verification agent.

Given a user question and a proposed answer,
decide if the answer is logically correct.

Respond strictly in JSON:

{
  "verdict": "approve" or "reject",
  "reason": "<short explanation>"
}
"""

# -------------------------
# USER INPUT
# -------------------------
user_question = "What is the square root of 144?"

conversation = [
    {"role": "system", "content": PLANNER_PROMPT},
    {"role": "user", "content": user_question}
]

max_steps = 5
step = 0

# -------------------------
# CRITIC FUNCTION
# -------------------------
def verify_answer(question, answer):
    messages = [
        {"role": "system", "content": CRITIC_PROMPT},
        {"role": "user", "content": f"Question: {question}\nAnswer: {answer}"}
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )

    raw_output = response.choices[0].message.content

    try:
        return json.loads(raw_output)
    except:
        return {"verdict": "reject", "reason": "Invalid JSON from critic."}

# -------------------------
# CONTROLLER LOOP
# -------------------------
while step < max_steps:

    step += 1
    print(f"\n--- Step {step} ---")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=conversation
    )

    planner_output = response.choices[0].message.content
    print("Planner Output:", planner_output)

    try:
        action_data = json.loads(planner_output)
    except json.JSONDecodeError:
        print("ERROR: Invalid JSON from planner.")
        break

    action = action_data.get("action")


    # -------------------------
    # CALL TOOL
    # -------------------------
    if action == "call_tool":

        tool_name = action_data.get("tool_name")
        arguments = action_data.get("arguments", {})

        if tool_name not in tool_registry:
            print("ERROR: Tool not found.")
            break

        result = tool_registry[tool_name](**arguments)
        print("Tool Result:", result)

        conversation.append({
            "role": "assistant",
            "content": planner_output
        })

        conversation.append({
            "role": "user",
            "content": f"Tool result: {result}"
        })

    # -------------------------
    # FINAL ANSWER (with verification)
    # -------------------------
    elif action == "final_answer":

        proposed_answer = action_data.get("content")

        verification = verify_answer(user_question, proposed_answer)

        print("Critic Verdict:", verification)

        if verification.get("verdict") == "approve":
            print("\nFinal Answer:", proposed_answer)
            break
        else:
             print("Answer rejected. Replanning...")

        conversation.append({
                "role": "assistant",
                "content": f"Previous answer rejected: {verification.get('reason')}"
            })              
        
    # -------------------------
    # ASK CLARIFICATION
    # -------------------------
    elif action == "ask_clarification":

        print("Clarification Needed:", action_data.get("question"))
        break
    else:
        print("Unknown action.")
        break        