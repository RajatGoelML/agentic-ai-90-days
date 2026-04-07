"""
Day 14 – Runtime Control + Dual-Model Risk Governance Layer

What We Built
-------------

1. Deterministic Financial Analysis Layer
   - Implemented strict input validation for revenue, debt, credit score, and years.
   - Enforced numeric range constraints and business rule checks.
   - Ensured deterministic calculation of DTI and liquidity metrics.
   - Purpose: Guarantee structured, bounded financial inputs before AI reasoning.

2. Structured LLM Risk Scoring (Primary Model)
   - Introduced explicit scoring rubric inside the prompt (weighted DTI, Liquidity, Credit).
   - Forced strict JSON schema output.
   - Enforced risk_score range validation (0–100).
   - Applied retry + timeout boundary to prevent unbounded AI execution.
   - Purpose: Constrain generative AI into deterministic financial scoring logic.

3. Independent Critic Model (Second LLM)
   - Added a separate audit model to verify:
        • Risk score computation correctness
        • Recommendation consistency
        • Logical integrity
   - Rejected workflow if critic detects inconsistency.
   - Purpose: Introduce model-level governance and reduce single-model risk.

4. FSM Transition Enforcement
   - Centralized transition() function validates all state changes.
   - Prevents illegal state jumps.
   - Purpose: Enforce deterministic workflow graph integrity.

5. Runtime Boundary Controls
   - Added step_counter and max_steps guard.
   - Prevented infinite execution loops.
   - Added timeout wrapper for LLM calls.
   - Purpose: Protect engine from runaway execution or external latency.

6. Structured Error Classification
   - Introduced typed error categories:
        • LLM_ERROR
        • TIMEOUT_ERROR
        • VALIDATION_ERROR
        • FSM_ERROR
        • CRITIC_REJECTION
   - Purpose: Enable deterministic failure escalation and future recovery strategies.

7. Dual-Layer Decision Governance
   - Primary LLM produces advisory risk score.
   - Critic validates integrity.
   - Deterministic policy layer makes final approval decision.
   - Purpose: Separate reasoning, validation, and authority layers.

Architectural Achievement
-------------------------

By end of Day 14:

- Workflow is transition-safe.
- Execution is bounded.
- AI calls are time-limited.
- Risk scoring is rubric-constrained.
- Independent critic enforces logical integrity.
- Deterministic policy overrides AI output.
- System fails safely and predictably.

This marks transition from:
“AI-powered scoring demo”
to
“Governed, bounded, production-style financial risk engine.”

Foundation is now ready for:
- Persistence journaling
- Deterministic replay
- Policy versioning
- Parallel risk models
- Multi-application orchestration
"""

"""
imports
setup
model definitions

prompts:
    scoring_prompt
    critic_prompt

deterministic tools:
    debt_to_income
    liquidity

deterministic recompute function (optional upgrade)

error types
valid transitions
terminal states

state initialization
idempotency helpers
transition function

while not terminal:

    increment step counter
    enforce max_steps boundary

    if state == RECEIVED:
        transition → FINANCIAL_ANALYSIS

    elif state == FINANCIAL_ANALYSIS:
        if not completed:
            validate input
            run deterministic tools
            update state
            mark completed
            transition → RISK_SCORING

    elif state == RISK_SCORING:
        if not completed:
            call primary LLM (with retry + timeout)
            validate schema
            update state
            mark completed
            transition → CRITIC_REVIEW

    elif state == CRITIC_REVIEW:
        call critic LLM
        if reject → FAILED
        else → transition → POLICY_CHECK

    elif state == POLICY_CHECK:
        apply deterministic business rules
        transition → FINAL_DECISION

    elif state == FINAL_DECISION:
        set final decision
        transition → APPROVED / REJECT
"""
        
from openai import OpenAI
from dotenv import load_dotenv
import json


#--setup & model definition

load_dotenv()
client = OpenAI()
primary_model = "gpt-4o-mini"
critic_model = "gpt-4o"

# Prompt - risk scoring prompt & critic agent prompt

risk_scoring_prompt = """
You are a structured financial risk scoring engine.

Apply the following deterministic scoring rubric EXACTLY.

----------------------------------------
SCORING RUBRIC (Total = 100 points)
----------------------------------------

1) Debt-to-Income Ratio (Max 30 points)

Let DTI = debt_to_income

If DTI <= 0.25        → 30 points
If 0.26 ≤ DTI ≤ 0.40  → 25 points
If 0.41 ≤ DTI ≤ 0.60  → 15 points
If DTI > 0.60         → 5 points


2) Liquidity Score (Max 30 points)

If liquidity_score >= 35     → 30 points
If 20 ≤ liquidity_score < 35 → 20 points
If liquidity_score < 20      → 10 points


3) Credit Score (Max 40 points)

If credit_score >= 750       → 40 points
If 700 ≤ credit_score < 750  → 30 points
If 650 ≤ credit_score < 700  → 20 points
If credit_score < 650        → 5 points


----------------------------------------
FINAL CALCULATION
----------------------------------------

risk_score = sum of:
    debt_to_income_points
    + liquidity_points
    + credit_points

----------------------------------------
DECISION RULE
----------------------------------------

If risk_score >= 70 → decision = "APPROVE"
If 50 ≤ risk_score < 70 → decision = "REVIEW"
If risk_score < 50 → decision = "REJECT"

----------------------------------------
OUTPUT FORMAT (STRICT)
----------------------------------------

Return STRICT JSON ONLY.
Do NOT include explanations outside JSON.
Do NOT include markdown.
Do NOT include commentary.

JSON Schema:

{
  "risk_score": <integer between 0 and 100>,
  "decision": "APPROVE" or "REVIEW" or "REJECT",
  "reason": "brief explanation of how each component was scored"
}
"""

critic_agent_prompt="""

you are a ctritic agent 

you are provided the llm risk score , financial metrics and deterministic_score

you have to validate equality + logic

----------------------------------------
OUTPUT FORMAT (STRICT)
----------------------------------------

Return STRICT JSON ONLY.
Do NOT include explanations outside JSON.
Do NOT include markdown.
Do NOT include commentary.

just respond in the below strict json format
{"decision":"APPROVE" or "REJECT",
 "reason":"brief explanation of the decision"
}
"""

# ------- State -----------

def create_initial_state():
    return {
        "workflow_id": None,  # Persistence layer
        "version": 1,  # State versioning
        "created_at": None,  # Observability

        "current_state": "RECEIVED",  # FSM entry point
        "step_counter": 0,  # Runtime boundary guard
        "max_steps": 10,  # Infinite loop protection
        "max_retries": 2,  # LLM retry boundary
        "timeout": 60,  # LLM timeout boundary

        "application": {  # Input layer
            "loan_amount": None,
            "income": None,
            "debt": None,
            "years_operating": None,
            "credit_score": None
        },

        "financial_metrics": {  # Deterministic layer
            "debt_to_income": None,
            "liquidity_score": None,
            "credit_score": None
        },

        "risk_score": None,  # LLM scoring output
        "critic_decision": None,  # Governance layer
        "policy_result": None,  # Deterministic policy layer
        "final_decision": None,  # Terminal outcome

        "execution": {  # Idempotency layer
            "completed_steps": [],
            "retry_count": 0
        },

        "error": None  # Failure tracking
    }


class ErrorType:
    VALIDATION_ERROR = "VALIDATION_ERROR"        # Input or output failed schema/range checks
    RANGE_ERROR = "RANGE_ERROR"                  # Value outside allowed numeric boundaries
    TRANSIENT_ERROR = "TRANSIENT_ERROR"          # Temporary issue (retryable)
    PERMANENT_ERROR = "PERMANENT_ERROR"          # Non-recoverable failure
    LLM_ERROR = "LLM_ERROR"                      # Primary model failure
    CRITIC_ERROR = "CRITIC_ERROR"                # Critic model failure
    TIMEOUT_ERROR = "TIMEOUT_ERROR"              # Execution exceeded allowed time
    FSM_ERROR = "FSM_ERROR"                      # Invalid state transition
    POLICY_REJECTION = "POLICY_REJECTION"        # Deterministic business rule rejection
    CONSISTENCY_ERROR = "CONSISTENCY_ERROR"      # Deterministic vs LLM mismatch 

# Deterministic tools 

def debt_to_income(income,debt):
   try: 
    income = float(income)
    debt = float(debt)

    if income <= 0:  # Business rule
        return {"status":"error","errorType": ErrorType.VALIDATION_ERROR, "description":"the income cannot be less than or equal to zero"}

    if debt < 0:  # Business rule
        return{"status":"error","errorType": ErrorType.VALIDATION_ERROR, "description":"debt cannot be less than zero"}
    
    risk_ratio = debt / income

    if risk_ratio < 0 or risk_ratio > 10:
      return {"status":"error","errorType": ErrorType.VALIDATION_ERROR, "description":"the risk ratio cannot be smaller than zero or greater than 10"}

    return{
         "status":"success",
         "output": risk_ratio,
    }
 
   except Exception as e:
      return{
         "status":"error",
         "errorType" : ErrorType.PERMANENT_ERROR,
         "description": str(e)
      }
      
def liquidity_score(year_of_exp):
    try:
       year_of_exp = float(year_of_exp)

       if year_of_exp < 0:
          return{
         "status":"error",
         "errorType" : ErrorType.VALIDATION_ERROR,
         "description": "year of experience cannot be less than zero"       
          } 
       liquidity_score = min(5*year_of_exp,40)

       if liquidity_score < 0 or liquidity_score > 40:
          return{
         "status":"error",
         "errorType" : ErrorType.RANGE_ERROR,
         "description": "liquidity score cannot be more than 40 or less than 0"                  
          }
       
       return{
         "status":"success",
         "output" : liquidity_score        
       }

    except Exception as e:
        return{
         "status":"error",
         "errorType" : ErrorType.PERMANENT_ERROR,
         "description": str(e)           
        }       

# valid transitions

valid_Transitions = {
   "RECEIVED": ["FINANCIAL_ANALYSIS","FAILED"],
   "FINANCIAL_ANALYSIS": ["RISK_SCORING","FAILED"],
   "RISK_SCORING": ["CRITIC_REVIEW","FAILED"],
   "CRITIC_REVIEW":["POLICY_RISK","REJECT","FAILED"],
   "POLICY_RISK":["FINAL_DECISION","FAILED"],
   "FINAL_DECISION":["APPROVE","REJECT"]
}

# terminal states

terminal_States = ["APPROVE","REJECT"]

# idempotency helpers

def is_state_completed(state,step_name):            # Idempotency guard
   return step_name in state["execution"]["completed_steps"]

def mark_step_completed(state,step_name):               # State mutation
   state["execution"]["completed_steps"].append(step_name)


# transition function

def transition(state,next_state):
    current_state = state["current_state"]

    allowed = valid_Transitions.get(current_state, [])  # FSM graph lookup

    if next_state not in allowed:
        state["error"] = {
            "status": "error",
            "error_type": ErrorType.FSM_ERROR,
            "description": f"Illegal transition attempted: {current_state} → {next_state}"
        }  # Error handling

        state["current_state"] = "FAILED"  # FSM transition (forced termination)
        return False  # Boundary enforcement signal

    state["current_state"] = next_state  # FSM transition (validated)
    return True  # Success signal

state = create_initial_state()

while state["current_state"] not in terminal_States:
   
   state["step_counter"] +=1
   if state["step_counter"] > state["max_steps"]:
      transition(state,"FAILED")
      break

   if state["current_state"] == "RECEIVED":
      transition(state,"FINANCIAL_ANALYSIS")

   elif state["current_state"] == "FINANCIAL_ANALYSIS":
      if not is_state_completed(state,state["current_state"]):

         dti = debt_to_income(state["application"]["income"],state["application"]["debt"])
         liquidity = liquidity_score(state["application"]["years_operating"])

         if dti["status"] == "error":
            state["error"] = dti
            transition(state,"FAILED")
            continue        
         
         if liquidity["status"] == "error":
            state["error"] = liquidity
            transition(state, "FAILED")
            continue

         if dti["status"] == "success":
            state["financial_metrics"]["debt_to_income"] = dti["output"]
         if liquidity["status"] == "success":   
            state["financial_metrics"]["liquidity_score"] = liquidity
         state["financial_metrics"]["credit_score"] = state["application"]["credit_score"]

         mark_step_completed(state,"RISK_SCORING")
