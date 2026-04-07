"""
Day 13 – Financial Risk Approval Workflow
Execution Safety Layer

Sequential Evolution Summary
-----------------------------

1. Domain Upgrade
   - Moved from abstract math demo to real-world SME loan risk engine.
   - Introduced business-aligned FSM (Finite state machine )states:
     RECEIVED → FINANCIAL_ANALYSIS → RISK_SCORING → POLICY_CHECK → FINAL_DECISION → APPROVED/REJECT.
   - Reason: Make architecture meaningful and production-oriented.

2. Hybrid Tool Layer
   - Deterministic tools:
       • Debt-to-income ratio
       • Liquidity score
   - LLM-assisted tool:
       • Structured risk scoring
   - Reason: Combine deterministic guarantees with reasoning-based evaluation.

3. Structured LLM Scoring Framework
   - Defined explicit scoring weights (DTI, Liquidity, Credit).
   - Defined score thresholds and recommendation rules.
   - Forced strict JSON output.
   - Reason: Prevent generative ambiguity and enforce deterministic reasoning boundaries.

4. Advisory vs Authoritative Separation
   - LLM provides advisory risk score.
   - Deterministic policy layer overrides final decision.
   - Reason: Production safety — LLM cannot directly approve loans.

5. Idempotent Step Execution
   - Added execution["completed_steps"] tracking.
   - Each FSM state executes only once.
   - Prevents duplicate tool execution on resume.
   - Reason: Safe recovery and side-effect protection.

6. Retry Cap for LLM
   - Added retry loop for malformed/invalid LLM responses.
   - Reason: Handle transient AI output failures.

7. Error Classification
   - Introduced structured error types (TRANSIENT, PERMANENT, LLM_ERROR, TOOL_ERROR).
   - Reason: Foundation for future intelligent recovery strategies.

8. Output Validation Layer
   - Enforced:
       • Score range validation (0–100)
       • Recommendation consistency with score
   - Reason: Guard against logically inconsistent LLM outputs.

Architectural Outcome
---------------------
By end of Day 13:
- FSM is business-aligned.
- Execution is idempotent.
- LLM reasoning is constrained by policy framework.
- Deterministic override ensures safety.
- System behaves like a real risk engine, not a demo.

This marks transition from tutorial agent → production-style workflow engine.
"""

from openai import OpenAI
from dotenv import load_dotenv
import json
import os
import uuid
from datetime import datetime
import math

# -------------------------
# Setup
# -------------------------
print("Script started")
load_dotenv()
client = OpenAI()


# -------------------------
# States
# -------------------------

VALID_TRANSITIONS={
    "RECEIVED":["FINANCIAL_ANALYSIS"],
    "FINANCIAL_ANALYSIS":["RISK_SCORING","FAILED"],
    "RISK_SCORING":["POLICY_CHECK","FAILED"],
    "POLICY_CHECK":["FINAL_DECISION"],
    "FINAL_DECISION":["APPROVED","REJECT"]
}

# -------------------------
# Error Classification
# -------------------------

class Errortype:
    TRANSIENT = "TRANSIENT"    # can be retried
    PERMANENT = "PERMANENT"    # no need to  retry
    LLM_ERROR = "LLM_ERROR"
    TOOL_ERROR = "TOOL_ERROR"


# -------------------------
# TOOL - 1 Debt-to-Income Ratio
# -------------------------

def calculate_debt_to_revenue(revenue,debt):

    try:
     revenue = float(revenue)
     debt = float(debt)

     if revenue < 0:
        return {"status": "error","Error_Type":Errortype.PERMANENT,"output":"Revenue must be positive."}
    
     ratio = debt / revenue
     return{"status": "success","output":ratio}
    
    except Exception as e:
        return {"status": "error","Error_Type":Errortype.PERMANENT,"output":str(e)}


# -------------------------
# TOOL - 2 Basic Liquidity Score
# -------------------------

def liquidity_check(years_operating):
   try:
     years_operating = int(years_operating)
     liquidity_score= min(years_operating * 5,40)
     
     return {"status": "success","output":liquidity_score}

   except Exception as e:  
    return {"status": "error","Error_Type":Errortype.PERMANENT,"output":str(e)}
   

# -------------------------
# LLM Risk Scoring (Hybrid Layer)
# -------------------------   

RISK_SCORING_PROMPT = """
You are a structured financial risk scoring engine.

You MUST compute risk_score deterministically using this framework:

Scoring Rules (Total 100 points):

1. Debt-to-Income Ratio (Max 40 points):
   - <= 0.25 → 40 points
   - 0.26–0.40 → 30 points
   - 0.41–0.60 → 20 points
   - > 0.60 → 10 points

2. Liquidity Score (Max 30 points):
   - >= 35 → 30 points
   - 20–34 → 20 points
   - < 20 → 10 points

3. Credit Score (Max 30 points):
   - >= 750 → 30 points
   - 700–749 → 25 points
   - 650–699 → 15 points
   - < 650 → 5 points

risk_score = sum of all three components.

Decision Recommendation:
- risk_score >= 70 → APPROVE
- 50–69 → REVIEW
- < 50 → REJECT

You must:
- Apply rules exactly as defined.
- Compute intermediate points.
- Ensure recommendation matches computed risk_score.
- Return STRICT JSON only.

Return:

{
  "risk_score": <integer>,
  "decision_recommendation": "APPROVE" or "REVIEW" or "REJECT",
  "factors": [
    "explain component scores briefly"
  ]
}
"""
#----------------------------------------------------------
# LLM scoring function with retry cap + idempotency awareness:
#----------------------------------------------------------

def llm_risk_scoring(financial_metrics, max_retries=2):

    attempts = 0

    while attempts < max_retries:
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": RISK_SCORING_PROMPT},
                    {"role": "user", "content": json.dumps(financial_metrics)}
                ]
            )

            output = response.choices[0].message.content
            parsed = json.loads(output)

            if "risk_score" not in parsed:
                raise ValueError("Missing risk_score")

            return {"status": "success", "output": parsed}

        except Exception as e:
            attempts += 1
            if attempts >= max_retries:
                return {
                    "status": "error",
                    "error_type": Errortype.LLM_ERROR,
                    "output": str(e)
                }
            
#--------------------------
# State structure (new SOT):
# -------------------------

def create_initial_state():
    return{
       "workflow_id":f"workflow_{uuid.uuid4().hex}",
       "version":1,
       "created_at":datetime.now(),
       "current_state": "RECEIVED",
        "application": {
            "loan_amount": 5000000,
            "annual_revenue": 12000000,
            "existing_debt": 3000000,
            "credit_score": 720,
            "years_operating": 6
        },
        "financial_metrics": None,  #deterministic math
        "risk_score_data": None,    #LLM reasoning
        "policy_result": None,      #hard business rules
        "final_decision": None,     #system output
        "execution": {
            "completed_steps": [],
            "retry_count": 0,
            "max_retries": 2
        },

        "error": None
    }

#-------------
# HELPERS
#-------------

def is_step_completed(state, step_name):                                         # Read Operation
    return step_name in state["execution"]["completed_steps"]


def mark_step_completed(state, step_name):                                       # Write Operation
    state["execution"]["completed_steps"].append(step_name)


# -------------------------
# FSM LOOP
# -------------------------

state = create_initial_state()

while state["current_state"] not in ["APPROVED", "REJECT", "FAILED"]:

    print("\nCurrent State:", state["current_state"])


    # -------------------------
    # RECEIVED
    # -------------------------
    if state["current_state"] == "RECEIVED":
        state["current_state"] = "FINANCIAL_ANALYSIS"


    # -------------------------
    # FINANCIAL_ANALYSIS
    # -------------------------
    elif state["current_state"] == "FINANCIAL_ANALYSIS":

        if not is_step_completed(state, "FINANCIAL_ANALYSIS"):

            dti = calculate_debt_to_revenue(
                state["application"]["annual_revenue"],
                state["application"]["existing_debt"]
            )

            liquidity = liquidity_check(
                state["application"]["years_operating"]
            )

            if dti["status"] == "error":
                state["error"] = dti
                state["current_state"] = "FAILED"

            elif liquidity["status"] == "error":
                state["error"] = liquidity
                state["current_state"] = "FAILED"    

            else:
                state["financial_metrics"] = {
                    "debt_to_income": dti["output"],
                    "liquidity_score": liquidity["output"],
                    "credit_score": state["application"]["credit_score"]
                }

                mark_step_completed(state, "FINANCIAL_ANALYSIS")
                state["current_state"] = "RISK_SCORING"    

    # -------------------------
    # RISK_SCORING
    # -------------------------
    elif state["current_state"] == "RISK_SCORING":

        if not is_step_completed(state, "RISK_SCORING"):

            result = llm_risk_scoring(state["financial_metrics"])

            if result["status"] == "error":
                state["error"] = result
                state["current_state"] = "FAILED"

            else:
                parsed = result["output"]

                # --- NEW: Strict Validation Layer ---
                try:
                    score = parsed["risk_score"]
                    recommendation = parsed["decision_recommendation"]

                # Validate score range
                    if not isinstance(score, int) or score < 0 or score > 100:
                      raise ValueError("Invalid risk_score range")

                # Validate consistency rule (example logic)
                    if score < 50 and recommendation == "APPROVE":
                        raise ValueError("Inconsistent recommendation for low score")

                except Exception as e:
                    state["error"] = {
                    "status": "error",
                    "error_type": Errortype.LLM_ERROR,
                    "output": str(e)
                    }
                    state["current_state"] = "FAILED"
                    continue
            # --- END VALIDATION ---

            state["risk_score_data"] = parsed
            mark_step_completed(state, "RISK_SCORING")
            state["current_state"] = "POLICY_CHECK"  

    # -------------------------
    # POLICY_CHECK
    # -------------------------
    elif state["current_state"] == "POLICY_CHECK":

        score = state["risk_score_data"]["risk_score"]
        credit = state["application"]["credit_score"]

        if credit < 650:
            decision = "REJECT"
        elif score >= 70:
            decision = "APPROVE"
        else:
            decision = "REJECT"

        state["policy_result"] = decision
        state["current_state"] = "FINAL_DECISION"      


    # -------------------------
    # FINAL_DECISION
    # -------------------------
    elif state["current_state"] == "FINAL_DECISION":

        state["final_decision"] = state["policy_result"]

        if state["final_decision"] == "APPROVE":
            state["current_state"] = "APPROVED"
        else:
            state["current_state"] = "REJECT"       


print("\nFinal Decision:", state["current_state"])
print("Risk Score Data:", state["risk_score_data"])                      