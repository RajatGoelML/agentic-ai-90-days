"""
Program: State Machine Agent (Day 11)

Purpose:
--------
Refactors planner-executor-critic architecture into an explicit
finite state machine (FSM) using structured state as the single
source of truth (SOT).

No conversation history is stored as memory.
State dictionary drives all transitions.
"""

from openai import OpenAI
from dotenv import load_dotenv
import json
import math

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
        return {"status": "error", "output": "number must be numeric."}

    if number < 0:
        return {"status": "error", "output": "Cannot compute square root of negative number."}

    return {"status": "success", "output": str(math.sqrt(number))}


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
{
  "action": "call_tool",
  "tool_name": "<tool_name>",
  "arguments": { ... }
}

{
  "action": "final_answer",
  "content": "<answer>"
}

Policy:
- Prefer using tool for square root.
"""

CRITIC_PROMPT = """
You are a verification agent.

Given a question and proposed answer,
decide if it is correct.

Respond strictly in JSON:
{
  "verdict": "approve" or "reject",
  "reason": "<short explanation>"
}
"""

# -------------------------
# INITIAL STATE (SOT)
# -------------------------

state = {
    "question":"What is the sqaure root of 144?",
    "current_State":"PLANNING",
    "plan": None,
    "tool_result": None,
    "final_answer": None,
    "verification_status": None,
    "error": None
}

# -------------------------
# FSM LOOP
# -------------------------
while state["current_state"] not in ["COMPLETED", "FAILED"]:

    print(f"\nCurrent State: {state['current_state']}")

    # -------------------------
    # PLANNING STATE
    # -------------------------
    if state["current_state"] == "PLANNING":

        messages = [
            {"role": "system", "content": PLANNER_PROMPT},
            {"role": "user", "content": f"Question: {state['question']}\nTool Result: {state['tool_result']}"}
        ]

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )

        planner_output = response.choices[0].message.content
        print("Planner Output:", planner_output)

        try:
            plan = json.loads(planner_output)
        except json.JSONDecodeError:
            state["error"] = "Planner returned invalid JSON."
            state["current_state"] = "FAILED"
            continue

        state["plan"] = plan

        if plan["action"] == "call_tool":
            state["current_state"] = "EXECUTING"
        elif plan["action"] == "final_answer":
            state["final_answer"] = plan["content"]
            state["current_state"] = "VERIFYING"
        else:
            state["error"] = "Unknown planner action."
            state["current_state"] = "FAILED"

    # -------------------------
    # EXECUTING STATE
    # -------------------------
    elif state["current_state"] == "EXECUTING":

        tool_name = state["plan"].get("tool_name")
        arguments = state["plan"].get("arguments", {})

        if tool_name not in tool_registry:
            state["error"] = "Tool not found."
            state["current_state"] = "FAILED"
            continue

        result = tool_registry[tool_name](**arguments)
        print("Tool Execution Result:", result)

        state["tool_result"] = result
        state["current_state"] = "PLANNING"

    # -------------------------
    # VERIFYING STATE
    # -------------------------
    elif state["current_state"] == "VERIFYING":

        messages = [
            {"role": "system", "content": CRITIC_PROMPT},
            {"role": "user", "content": f"Question: {state['question']}\nAnswer: {state['final_answer']}"}
        ]

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )

        critic_output = response.choices[0].message.content
        print("Critic Output:", critic_output)

        try:
            verdict_data = json.loads(critic_output)
        except json.JSONDecodeError:
            state["error"] = "Critic returned invalid JSON."
            state["current_state"] = "FAILED"
            continue

        state["verification_status"] = verdict_data["verdict"]

        if verdict_data["verdict"] == "approve":
            state["current_state"] = "COMPLETED"
        else:
            state["current_state"] = "PLANNING"

# -------------------------
# FINAL OUTPUT
# -------------------------
print("\nFinal System State:", state)

if state["current_state"] == "COMPLETED":
    print("\nFinal Answer:", state["final_answer"])
else:
    print("\nExecution Failed:", state["error"])