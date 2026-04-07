"""
Day 16 – Idempotent Resume-from-Journal Workflow Engine

Upgrades:
- Journal becomes authoritative state source
- Resume-from-last-successful-state capability
- Idempotent execution enforcement
- Deterministic state reconstruction
"""

from openai import OpenAI
from dotenv import load_dotenv
import json
from datetime import datetime

load_dotenv()
client = OpenAI()

PRIMARY_MODEL = "gpt-4o-mini"
CRITIC_MODEL = "gpt-4o"

# -------------------------
# Error Classification
# -------------------------

class ErrorType:
    FSM_ERROR = "FSM_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    CONSISTENCY_ERROR = "CONSISTENCY_ERROR"

# -------------------------
# FSM Graph
# -------------------------

VALID_TRANSITIONS = {
    "RECEIVED": ["FINANCIAL_ANALYSIS", "FAILED"],
    "FINANCIAL_ANALYSIS": ["EXPLANATION", "FAILED"],
    "EXPLANATION": ["CRITIC_REVIEW", "FAILED"],
    "CRITIC_REVIEW": ["POLICY_CHECK", "FAILED"],
    "POLICY_CHECK": ["FINAL_DECISION"],
    "FINAL_DECISION": ["APPROVED", "REJECT"],
}

TERMINAL_STATES = ["APPROVED", "REJECT", "FAILED"]

# -------------------------
# State Initialization
# -------------------------

def create_initial_state():
    return {
        "version": 3,  # State versioning
        "current_state": "RECEIVED",  # FSM entry
        "step_counter": 0,  # Runtime guard
        "max_steps": 20,  # Infinite loop protection
        "journal": [],  # Transition ledger (Persistence layer)
        "completed_steps": set(),  # Idempotency guard
        "application": {
            "income": 12000000,
            "debt": 3000000,
            "years_operating": 6,
            "credit_score": 720
        },
        "financial_metrics": None,
        "deterministic_score": None,
        "llm_output": None,
        "critic_result": None,
        "final_decision": None,
        "error": None
    }

# -------------------------
# Transition with Journal
# -------------------------

def transition(state, next_state, reason):

    current = state["current_state"]  # Deterministic read

    if next_state not in VALID_TRANSITIONS.get(current, []):
        state["error"] = {
            "error_type": ErrorType.FSM_ERROR,
            "description": f"Illegal transition {current} → {next_state}"
        }  # Error handling
        state["current_state"] = "FAILED"  # FSM transition
        return False

    state["journal"].append({
        "from": current,
        "to": next_state,
        "timestamp": datetime.utcnow().isoformat(),
        "reason": reason
    })  # Persistence layer

    state["completed_steps"].add(current)  # Idempotency guard

    state["current_state"] = next_state  # FSM transition
    return True

# -------------------------
# Reconstruction Logic
# -------------------------

def reconstruct_from_journal(state):
    """
    Rebuilds current_state and completed_steps
    from authoritative journal.
    """

    replay_state = "RECEIVED"  # Deterministic baseline

    for entry in state["journal"]:

        expected_next = entry["to"]

        if expected_next not in VALID_TRANSITIONS.get(replay_state, []):
            raise Exception("Journal integrity violation")  # Validation layer

        state["completed_steps"].add(replay_state)  # Idempotency rebuild
        replay_state = expected_next  # State mutation

    state["current_state"] = replay_state  # Final reconstructed state

# -------------------------
# Deterministic Tools
# -------------------------

def deterministic_score(app):
    score = 0

    dti = app["debt"] / app["income"]
    liquidity = min(5 * app["years_operating"], 40)
    credit = app["credit_score"]

    if dti <= 0.25:
        score += 30
    elif dti <= 0.40:
        score += 25
    elif dti <= 0.60:
        score += 15
    else:
        score += 5

    if liquidity >= 35:
        score += 30
    elif liquidity >= 20:
        score += 20
    else:
        score += 10

    if credit >= 750:
        score += 40
    elif credit >= 700:
        score += 30
    elif credit >= 650:
        score += 20
    else:
        score += 5

    return score  # Deterministic authority

# -------------------------
# Resume Mode Switch
# -------------------------

state = create_initial_state()

resume_mode = False  # Simplified for learning — production would load journal externally

if resume_mode and state["journal"]:
    reconstruct_from_journal(state)  # Persistence recovery

# -------------------------
# Execution Loop
# -------------------------

while state["current_state"] not in TERMINAL_STATES:

    state["step_counter"] += 1  # Runtime guard

    if state["step_counter"] > state["max_steps"]:
        transition(state, "FAILED", "Max step limit exceeded")
        break

    current = state["current_state"]

    if current == "RECEIVED":
        transition(state, "FINANCIAL_ANALYSIS", "Begin workflow")

    elif current == "FINANCIAL_ANALYSIS":

        if current in state["completed_steps"]:
            transition(state, "EXPLANATION", "Skipping completed step")
            continue

        state["deterministic_score"] = deterministic_score(state["application"])  # Deterministic logic

        transition(state, "EXPLANATION", "Score computed")

    elif current == "EXPLANATION":

        if current in state["completed_steps"]:
            transition(state, "CRITIC_REVIEW", "Skipping completed step")
            continue

        state["llm_output"] = {
            "score": state["deterministic_score"],
            "recommendation": "APPROVE"
        }  # Simplified for learning — production would call LLM

        transition(state, "CRITIC_REVIEW", "Explanation generated")

    elif current == "CRITIC_REVIEW":

        if state["llm_output"]["score"] != state["deterministic_score"]:
            state["error"] = {"error_type": ErrorType.CONSISTENCY_ERROR}
            transition(state, "FAILED", "Score mismatch")
            continue

        transition(state, "POLICY_CHECK", "Critic validated")

    elif current == "POLICY_CHECK":

        if state["deterministic_score"] >= 70:
            state["final_decision"] = "APPROVED"
        else:
            state["final_decision"] = "REJECT"

        transition(state, "FINAL_DECISION", "Policy applied")

    elif current == "FINAL_DECISION":

        transition(state, state["final_decision"], "Workflow complete")

# -------------------------
# Output
# -------------------------

print("Final State:", state["current_state"])
print("Journal:", json.dumps(state["journal"], indent=2))