"""
Day 15 – Auditable Deterministic Risk Workflow Engine

Purpose
-------
Evolves the governed risk workflow into an auditable, replayable,
production-aligned financial decision engine.

Core Architectural Shift
------------------------
- Numeric risk scoring is fully deterministic (authoritative).
- LLM is used only for explanation and narrative reasoning.
- Critic model validates reasoning consistency (not arithmetic).
- All state transitions are journaled and replayable.

What This System Achieves
-------------------------

1. Deterministic Authority Layer
   - Debt-to-income and liquidity computed via strict validation.
   - Risk score computed in Python using fixed rubric.
   - Ensures reproducibility, auditability, and regulatory alignment.

2. AI Explanation Layer
   - LLM receives deterministic score and financial metrics.
   - Generates explanation + recommendation.
   - Prohibited from recomputing or altering numeric score.

3. Governance Layer (Critic)
   - Independent model verifies:
       • Score was not modified
       • Recommendation aligns with deterministic score
       • Explanation is logically consistent
   - Rejects workflow if inconsistency detected.

4. FSM Enforcement
   - All transitions validated against VALID_TRANSITIONS.
   - Illegal transitions force FAILED state.
   - Prevents state drift and logical bypass.

5. Transition Journal (Durability Layer)
   - Every state change recorded with:
       • from state
       • to state
       • timestamp
       • reason
       • step counter
   - Provides complete execution audit trail.

6. Deterministic Replay Engine
   - Reconstructs workflow from journal.
   - Validates historical state integrity.
   - Detects corruption, illegal jumps, or tampering.

7. Runtime Boundary Controls
   - step_counter prevents infinite loops.
   - max_steps enforces execution limits.
   - Structured error classification ensures controlled failure.

Architectural Outcome
---------------------
This program represents a transition from:

    "AI-based scoring demo"
        →
    "Deterministic, governed, auditable financial workflow engine"

Key Design Principle
--------------------
- Deterministic systems own authority.
- AI augments reasoning.
- Governance enforces consistency.
- Journaling guarantees historical integrity.
- Replay guarantees auditability.

Foundation for Future Upgrades
------------------------------
- Persistent storage (DB-backed journal)
- Multi-workflow orchestration
- State version migration
- API exposure (FastAPI layer)
- Observability and monitoring hooks
- Distributed execution support
"""

"""
Day 15 – Deterministic Core + Journaled FSM + Replay Engine

Upgrades:
- Deterministic numeric scoring (LLM no longer computes arithmetic)
- LLM generates explanation only
- Critic validates reasoning consistency only
- Authoritative transition journal
- Deterministic replay capability
- Versioned state schema
"""

from openai import OpenAI
from dotenv import load_dotenv
import json
from datetime import datetime

# -------------------------
# Setup
# -------------------------

load_dotenv()
client = OpenAI()

PRIMARY_MODEL = "gpt-4o-mini"
CRITIC_MODEL = "gpt-4o"

# -------------------------
# Prompts
# -------------------------

EXPLANATION_PROMPT = """
You are a financial risk explanation engine.

You are given:
- financial_metrics
- deterministic_risk_score

Your job:
- Explain how the score was derived
- Provide a short narrative risk explanation
- Provide a recommendation (APPROVE / REVIEW / REJECT)

You MUST NOT recompute the score.
You MUST NOT change the score.
You MUST respect the provided deterministic_risk_score.

Return STRICT JSON ONLY:

{
  "score": <same deterministic score>,
  "recommendation": "APPROVE" or "REVIEW" or "REJECT",
  "explanation": "short explanation"
}
"""

CRITIC_PROMPT = """
You are an independent reasoning validator.

You are given:
- financial_metrics
- deterministic_score
- llm_output

Validate:
1. LLM did NOT change the deterministic score.
2. Recommendation logically aligns with deterministic_score.
3. Explanation is consistent with metrics.

Return STRICT JSON ONLY:

{
  "decision": "APPROVE" or "REJECT",
  "reason": "brief explanation"
}
"""

# -------------------------
# Error Classification
# -------------------------

class ErrorType:
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RANGE_ERROR = "RANGE_ERROR"
    PERMANENT_ERROR = "PERMANENT_ERROR"
    LLM_ERROR = "LLM_ERROR"
    CRITIC_ERROR = "CRITIC_ERROR"
    FSM_ERROR = "FSM_ERROR"
    CONSISTENCY_ERROR = "CONSISTENCY_ERROR"

# -------------------------
# Deterministic Tools
# -------------------------

def debt_to_income(income, debt):
    try:
        income = float(income)
        debt = float(debt)

        if income <= 0:
            return {"status": "error", "error_type": ErrorType.VALIDATION_ERROR}

        if debt < 0:
            return {"status": "error", "error_type": ErrorType.VALIDATION_ERROR}

        ratio = debt / income

        if ratio < 0 or ratio > 10:
            return {"status": "error", "error_type": ErrorType.RANGE_ERROR}

        return {"status": "success", "output": ratio}

    except Exception:
        return {"status": "error", "error_type": ErrorType.PERMANENT_ERROR}


def liquidity_score(years):
    try:
        years = int(years)

        if years < 0:
            return {"status": "error", "error_type": ErrorType.VALIDATION_ERROR}

        score = min(5 * years, 40)

        return {"status": "success", "output": score}

    except Exception:
        return {"status": "error", "error_type": ErrorType.PERMANENT_ERROR}

# -------------------------
# Deterministic Scoring Authority
# -------------------------

def deterministic_score(metrics):
    dti = metrics["debt_to_income"]
    liquidity = metrics["liquidity_score"]
    credit = metrics["credit_score"]

    score = 0

    # DTI (30)
    if dti <= 0.25:
        score += 30
    elif dti <= 0.40:
        score += 25
    elif dti <= 0.60:
        score += 15
    else:
        score += 5

    # Liquidity (30)
    if liquidity >= 35:
        score += 30
    elif liquidity >= 20:
        score += 20
    else:
        score += 10

    # Credit (40)
    if credit >= 750:
        score += 40
    elif credit >= 700:
        score += 30
    elif credit >= 650:
        score += 20
    else:
        score += 5

    return score

# -------------------------
# FSM Definition
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
        "version": 2,  # State versioning
        "current_state": "RECEIVED",
        "step_counter": 0,
        "max_steps": 15,
        "journal": [],  # Persistence layer (transition ledger)
        "application": {
            "income": 12000000,
            "debt": 3000000,
            "years_operating": 6,
            "credit_score": 720
        },
        "financial_metrics": {},
        "deterministic_score": None,
        "llm_output": None,
        "critic_result": None,
        "policy_result": None,
        "final_decision": None,
        "error": None
    }

# -------------------------
# Transition with Journal
# -------------------------

def transition(state, next_state, reason):

    current = state["current_state"]

    if next_state not in VALID_TRANSITIONS.get(current, []):
        state["error"] = {
            "error_type": ErrorType.FSM_ERROR,
            "description": f"Illegal transition {current} → {next_state}"
        }
        state["current_state"] = "FAILED"
        return False

    state["journal"].append({
        "from": current,
        "to": next_state,
        "timestamp": datetime.utcnow().isoformat(),
        "reason": reason,
        "step_counter": state["step_counter"]
    })

    state["current_state"] = next_state
    return True

# -------------------------
# Replay Engine
# -------------------------

def replay_workflow(journal):

    replay_state = "RECEIVED"

    for entry in journal:
        if entry["to"] not in VALID_TRANSITIONS.get(replay_state, []):
            return False
        replay_state = entry["to"]
        print(replay_state)

    return replay_state

# -------------------------
# Execution
# -------------------------

state = create_initial_state()

while state["current_state"] not in TERMINAL_STATES:

    state["step_counter"] += 1

    if state["step_counter"] > state["max_steps"]:
        transition(state, "FAILED", "Max step limit exceeded")
        break

    if state["current_state"] == "RECEIVED":
        transition(state, "FINANCIAL_ANALYSIS", "Start analysis")

    elif state["current_state"] == "FINANCIAL_ANALYSIS":

        dti = debt_to_income(
            state["application"]["income"],
            state["application"]["debt"]
        )

        liquidity = liquidity_score(
            state["application"]["years_operating"]
        )

        if dti["status"] == "error" or liquidity["status"] == "error":
            transition(state, "FAILED", "Deterministic tool failure")
            continue

        state["financial_metrics"] = {
            "debt_to_income": dti["output"],
            "liquidity_score": liquidity["output"],
            "credit_score": state["application"]["credit_score"]
        }

        state["deterministic_score"] = deterministic_score(state["financial_metrics"])

        transition(state, "EXPLANATION", "Deterministic score computed")

    elif state["current_state"] == "EXPLANATION":

        try:
            response = client.chat.completions.create(
                model=PRIMARY_MODEL,
                messages=[
                    {"role": "system", "content": EXPLANATION_PROMPT},
                    {"role": "user", "content": json.dumps({
                        "financial_metrics": state["financial_metrics"],
                        "deterministic_risk_score": state["deterministic_score"]
                    })}
                ]
            )

            parsed = json.loads(response.choices[0].message.content)
            state["llm_output"] = parsed

            transition(state, "CRITIC_REVIEW", "LLM explanation generated")

        except Exception:
            transition(state, "FAILED", "LLM explanation failure")

    elif state["current_state"] == "CRITIC_REVIEW":

        try:
            response = client.chat.completions.create(
                model=CRITIC_MODEL,
                messages=[
                    {"role": "system", "content": CRITIC_PROMPT},
                    {"role": "user", "content": json.dumps({
                        "financial_metrics": state["financial_metrics"],
                        "deterministic_score": state["deterministic_score"],
                        "llm_output": state["llm_output"]
                    })}
                ]
            )

            critic = json.loads(response.choices[0].message.content)
            state["critic_result"] = critic

            if critic["decision"] == "REJECT":
                transition(state, "FAILED", "Critic rejected explanation")
            else:
                transition(state, "POLICY_CHECK", "Critic approved explanation")

        except Exception:
            transition(state, "FAILED", "Critic failure")

    elif state["current_state"] == "POLICY_CHECK":

        score = state["deterministic_score"]

        if score >= 70:
            state["policy_result"] = "APPROVED"
        else:
            state["policy_result"] = "REJECT"

        transition(state, "FINAL_DECISION", "Policy applied")

    elif state["current_state"] == "FINAL_DECISION":

        state["final_decision"] = state["policy_result"]

        if state["final_decision"] == "APPROVED":
            transition(state, "APPROVED", "Approved by policy")
        else:
            transition(state, "REJECT", "Rejected by policy")

# -------------------------
# Output + Replay
# -------------------------

print("Final State:", state["current_state"])
print("Deterministic Score:", state["deterministic_score"])
print("Journal:")
for entry in state["journal"]:
    print(entry)

print("Replay Result:", replay_workflow(state["journal"]))