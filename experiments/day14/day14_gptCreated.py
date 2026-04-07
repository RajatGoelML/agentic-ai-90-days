"""
Day 14 – Runtime Control + Dual-Model Validation Layer

Upgrades:
- Deterministic scoring rubric enforced inside LLM prompt
- Separate critic model for independent validation
- Timeout boundary
- Transition enforcement
- Idempotency guard
- Range validation
- Structured failure escalation
"""

from openai import OpenAI
from dotenv import load_dotenv
import json
import uuid
# import signal
from datetime import datetime

# -------------------------
# Setup
# -------------------------

load_dotenv()
client = OpenAI()

PRIMARY_MODEL = "gpt-4o-mini"          # LLM call (risk scoring)
CRITIC_MODEL = "gpt-4o"                # LLM call (independent critic)

# -------------------------
# FSM Definition
# -------------------------

VALID_TRANSITIONS = {
    "RECEIVED": ["FINANCIAL_ANALYSIS"],
    "FINANCIAL_ANALYSIS": ["RISK_SCORING", "FAILED"],
    "RISK_SCORING": ["CRITIC_REVIEW", "FAILED"],
    "CRITIC_REVIEW": ["POLICY_CHECK", "FAILED"],
    "POLICY_CHECK": ["FINAL_DECISION"],
    "FINAL_DECISION": ["APPROVED", "REJECT"],
}

TERMINAL_STATES = ["APPROVED", "REJECT", "FAILED"]  # FSM boundary definition

# -------------------------
# Error Classification
# -------------------------

class ErrorType:
    TRANSIENT = "TRANSIENT"
    PERMANENT = "PERMANENT"
    LLM_ERROR = "LLM_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    FSM_ERROR = "FSM_ERROR"
    CRITIC_REJECTION = "CRITIC_REJECTION"

# -------------------------
# Timeout Infrastructure
# -------------------------

class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException("LLM execution exceeded timeout")  # Error handling

# -------------------------
# Deterministic Tools
# -------------------------

def calculate_debt_to_revenue(revenue, debt):

    try:
        revenue = float(revenue)  # Validation layer
        debt = float(debt)

        if revenue <= 0:
            return {"status": "error", "error_type": ErrorType.PERMANENT, "output": "Revenue must be positive"}  # Business rule

        ratio = debt / revenue  # Deterministic logic

        if ratio < 0 or ratio > 10:
            return {"status": "error", "error_type": ErrorType.VALIDATION_ERROR, "output": "DTI out of valid range"}  # Range constraint

        return {"status": "success", "output": ratio}

    except Exception as e:
        return {"status": "error", "error_type": ErrorType.PERMANENT, "output": str(e)}  # Error handling


def liquidity_check(years_operating):

    try:
        years = int(years_operating)  # Validation layer

        if years < 0:
            return {"status": "error", "error_type": ErrorType.VALIDATION_ERROR, "output": "Invalid years_operating"}  # Range constraint

        score = min(years * 5, 40)  # Deterministic logic

        return {"status": "success", "output": score}

    except Exception as e:
        return {"status": "error", "error_type": ErrorType.PERMANENT, "output": str(e)}  # Error handling

# -------------------------
# Primary Risk Scoring Prompt
# -------------------------

RISK_SCORING_PROMPT = """
You are a structured financial scoring engine.

Apply this deterministic rubric:

Debt-to-Income (40 max):
<=0.25:40
0.26-0.40:30
0.41-0.60:20
>0.60:10

Liquidity (30 max):
>=35:30
20-34:20
<20:10

Credit Score (30 max):
>=750:30
700-749:25
650-699:15
<650:5

risk_score = sum of above.

Return STRICT JSON:
{
  "risk_score": <integer>,
  "decision_recommendation": "APPROVE" or "REVIEW" or "REJECT",
  "factors": ["explain component scoring briefly"]
}
"""

# -------------------------
# Critic Prompt
# -------------------------

CRITIC_PROMPT = """
You are an independent audit model.

Given:
- financial_metrics
- risk_score output

logic given to llm for proving the risk score

Debt-to-Income (40 max):
<=0.25:40
0.26-0.40:30
0.41-0.60:20
>0.60:10

Liquidity (30 max):
>=35:30
20-34:20
<20:10

Credit Score (30 max):
>=750:30
700-749:25
650-699:15
<650:5

Verify:
1. Risk score correctly computed as per rubric.
2. Recommendation consistent with score.
3. No logical inconsistencies.

Return STRICT JSON:
{
  "verdict": "APPROVE" or "REJECT",
  "reason": "short explanation"
}
"""

# -------------------------
# LLM Risk Scoring
# -------------------------

def llm_risk_scoring(financial_metrics, max_retries=2):

    attempts = 0  # Retry logic

    while attempts < max_retries:

        try:
            # signal.signal(signal.SIGALRM, timeout_handler)  # Timeout wrapper
            # signal.alarm(10)  # Simplified for learning — production would use async control

            response = client.chat.completions.create(  # LLM call
                model=PRIMARY_MODEL,
                messages=[
                    {"role": "system", "content": RISK_SCORING_PROMPT},
                    {"role": "user", "content": json.dumps(financial_metrics)}
                ]
            )

            # signal.alarm(0)  # Clear timeout

            parsed = json.loads(response.choices[0].message.content)  # Schema enforcement

            score = parsed["risk_score"]  # Validation layer

            if not isinstance(score, int) or score < 0 or score > 100:
                raise ValueError("Invalid risk_score range")  # Range constraint

            return {"status": "success", "output": parsed}

        except TimeoutException as e:
            attempts += 1  # Retry logic
            if attempts >= max_retries:
                return {"status": "error", "error_type": ErrorType.TIMEOUT_ERROR, "output": str(e)}

        except Exception as e:
            attempts += 1  # Retry logic
            if attempts >= max_retries:
                return {"status": "error", "error_type": ErrorType.LLM_ERROR, "output": str(e)}

# -------------------------
# Critic Validation
# -------------------------

def critic_review(financial_metrics, risk_output):

    try:
        response = client.chat.completions.create(  # LLM call
            model=CRITIC_MODEL,
            messages=[
                {"role": "system", "content": CRITIC_PROMPT},
                {"role": "user", "content": json.dumps({
                    "financial_metrics": financial_metrics,
                    "risk_output": risk_output
                })}
            ]
        )

        parsed = json.loads(response.choices[0].message.content)  # Schema enforcement

        return parsed

    except Exception as e:
        return {"verdict": "REJECT", "reason": str(e)}  # Error handling

# -------------------------
# State Initialization
# -------------------------

def create_initial_state():

    return {
        "workflow_id": f"workflow_{uuid.uuid4().hex}",
        "version": 3,  # State versioning
        # "created_at": datetime.d
        "current_state": "RECEIVED",
        "step_counter": 0,  # Runtime boundary guard
        "max_steps": 15,
        "application": {
            "loan_amount": 5000000,
            "annual_revenue": 12000000,
            "existing_debt": 3000000,
            "credit_score": 720,
            "years_operating": 6
        },
        "financial_metrics": None,
        "risk_score_data": None,
        "critic_verdict": None,
        "policy_result": None,
        "final_decision": None,
        "execution": {"completed_steps": []},
        "error": None
    }

# -------------------------
# FSM Transition Enforcement
# -------------------------

def transition(state, next_state):

    current = state["current_state"]
    allowed = VALID_TRANSITIONS.get(current, [])

    if next_state not in allowed:
        state["error"] = {"error_type": ErrorType.FSM_ERROR, "output": f"Illegal transition {current}->{next_state}"}  # Error handling
        state["current_state"] = "FAILED"  # FSM transition
        return

    state["current_state"] = next_state  # FSM transition

# -------------------------
# FSM LOOP
# -------------------------

state = create_initial_state()

while state["current_state"] not in TERMINAL_STATES:

    state["step_counter"] += 1  # Runtime boundary guard

    if state["step_counter"] > state["max_steps"]:
        state["error"] = {"error_type": ErrorType.FSM_ERROR, "output": "Max steps exceeded"}  # Error handling
        state["current_state"] = "FAILED"
        break

    if state["current_state"] == "RECEIVED":
        transition(state, "FINANCIAL_ANALYSIS")

    elif state["current_state"] == "FINANCIAL_ANALYSIS":

        dti = calculate_debt_to_revenue(
            state["application"]["annual_revenue"],
            state["application"]["existing_debt"]
        )

        liquidity = liquidity_check(
            state["application"]["years_operating"]
        )

        if dti["status"] == "error":
            state["error"] = dti
            transition(state, "FAILED")
        else:
            state["financial_metrics"] = {
                "debt_to_income": dti["output"],
                "liquidity_score": liquidity["output"],
                "credit_score": state["application"]["credit_score"]
            }
            transition(state, "RISK_SCORING")

    elif state["current_state"] == "RISK_SCORING":

        result = llm_risk_scoring(state["financial_metrics"])

        if result["status"] == "error":
            state["error"] = result
            transition(state, "FAILED")
        else:
            state["risk_score_data"] = result["output"]
            transition(state, "CRITIC_REVIEW")

    elif state["current_state"] == "CRITIC_REVIEW":

        verdict = critic_review(state["financial_metrics"], state["risk_score_data"])

        if verdict["verdict"] == "REJECT":
            state["error"] = {"error_type": ErrorType.CRITIC_REJECTION, "output": verdict["reason"]}
            transition(state, "FAILED")
        else:
            state["critic_verdict"] = verdict
            transition(state, "POLICY_CHECK")

    elif state["current_state"] == "POLICY_CHECK":

        score = state["risk_score_data"]["risk_score"]

        if score >= 70:
            state["policy_result"] = "APPROVED"
        else:
            state["policy_result"] = "REJECT"

        transition(state, "FINAL_DECISION")

    elif state["current_state"] == "FINAL_DECISION":

        state["final_decision"] = state["policy_result"]

        if state["final_decision"] == "APPROVED":
            transition(state, "APPROVED")
        else:
            transition(state, "REJECT")

print("Final State:", state["current_state"])
print("Error:", state["error"])