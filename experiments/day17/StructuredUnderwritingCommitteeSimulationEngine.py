"""
Day 17 – Multi-Agent Underwriting Committee Engine
Hybrid Escalation Governance Model

Architecture:
- Deterministic 6-factor risk scoring (authoritative)
- Agent A (Optimistic Risk Analyst)
- Agent B (Conservative Risk Analyst)
- Rebuttal round
- Arbiter synthesis
- Hybrid escalation (AI can escalate to REVIEW only)
"""

from openai import OpenAI
from dotenv import load_dotenv
import json

# -------------------------
# Setup
# -------------------------

load_dotenv()
client = OpenAI()

PRIMARY_MODEL = "gpt-4o-mini"

# -------------------------
# Error Classification
# -------------------------

class ErrorType:
    VALIDATION_ERROR = "VALIDATION_ERROR"
    LLM_SCHEMA_ERROR = "LLM_SCHEMA_ERROR"
    CONSISTENCY_ERROR = "CONSISTENCY_ERROR"


# -------------------------
# Loan Application Schema
# -------------------------

def create_application():
    return {
        "borrower_profile": {
            "age": 34,
            "employment_type": "salaried",
            "years_at_current_employer": 5,
            "industry_sector": "IT Services"
        },
        "financial_profile": {
            "annual_income": 1800000,
            "monthly_obligations": 35000,
            "existing_total_debt": 400000,
            "bank_cashflow_volatility_score": 0.2  # 0–1 lower is stable
        },
        "credit_profile": {
            "credit_score": 735,
            "recent_delinquency": False,
            "number_of_active_loans": 2
        },
        "loan_request": {
            "loan_amount": 800000,
            "tenure_months": 36,
            "loan_purpose": "Business Expansion"
        }
    }

# -------------------------
# Deterministic Scoring Engine
# -------------------------

def deterministic_score(app):
    print("hello")

    score = 0  # Deterministic accumulator

    income = app["financial_profile"]["annual_income"]
    obligations = app["financial_profile"]["monthly_obligations"]
    debt = app["financial_profile"]["existing_total_debt"]
    credit = app["credit_profile"]["credit_score"]
    volatility = app["financial_profile"]["bank_cashflow_volatility_score"]
    years = app["borrower_profile"]["years_at_current_employer"]
    delinquency = app["credit_profile"]["recent_delinquency"]

        # Validation layer
    if credit < 300 or credit > 900:
        raise ValueError("Invalid credit score range")

    # 1️⃣ Credit Score (25)
    if credit >= 750:
        score += 25
    elif credit >= 700:
        score += 20
    elif credit >= 650:
        score += 12
    else:
        score += 5

    # 2️⃣ Debt-to-Income (20)
    dti = debt / income
    if dti <= 0.2:
        score += 20
    elif dti <= 0.35:
        score += 15
    elif dti <= 0.5:
        score += 8
    else:
        score += 3

    # 3️⃣ EMI Burden (15)
    emi_ratio = (obligations * 12) / income
    if emi_ratio <= 0.2:
        score += 15
    elif emi_ratio <= 0.35:
        score += 10
    else:
        score += 5

    # 4️⃣ Employment Stability (15)
    if years >= 5:
        score += 15
    elif years >= 3:
        score += 10
    else:
        score += 5

    # 5️⃣ Cashflow Stability (15)
    if volatility <= 0.2:
        score += 15
    elif volatility <= 0.4:
        score += 10
    else:
        score += 5

    # 6️⃣ Behaviour Risk (10)
    if delinquency:
        score += 2
    else:
        score += 10

    return score  # Deterministic authority

# -------------------------
# LLM Debate Agents
# -------------------------

def call_llm(prompt_payload):
    
        response = client.chat.completions.create(
            model=PRIMARY_MODEL,
            messages=prompt_payload,
            response_format={"type": "json_object"} 
        )

        raw = response.choices[0].message.content
        try:
            parsed = json.loads(raw)
        except Exception:
            raise ValueError(ErrorType.LLM_SCHEMA_ERROR)
        
        return parsed
    
# -------------------------
# Debate Prompts
# -------------------------

def optimistic_prompt(app, score):
    return [
        {
            "role": "system",
            "content":
            "You are an optimistic NBFC risk analyst.\n"
            "Rules:\n"
            "1. You MUST NOT recompute or modify deterministic_score.\n"
            "2. You MUST base reasoning strictly on provided metrics.\n"
            "3. You MUST acknowledge deterministic_score explicitly.\n"
            "4. You MUST argue in favor of approval where logically defensible.\n"
            "5. You MUST return STRICT JSON only.\n"
            "{"
            "\"position\": \"short stance referencing score\","
            "\"key_points\": [\"point1\",\"point2\"],"
            "\"recommendation\": \"APPROVE|REVIEW|REJECT\""
            "}"
        },
        {
            "role": "user",
            "content": json.dumps({
                "application": app,
                "deterministic_score": score
            })
        }
    ]

def conservative_prompt(app, score):
    return [
        {
            "role": "system",
            "content":
            "You are a conservative NBFC risk analyst.\n"
            "Rules:\n"
            "1. You MUST NOT recompute or modify deterministic_score.\n"
            "2. You MUST identify risk vulnerabilities.\n"
            "3. You MUST acknowledge deterministic_score explicitly.\n"
            "4. You MUST argue for caution if justified.\n"
            "5. You MUST return STRICT JSON only.\n"
            "{"
            "\"position\": \"short stance referencing score\","
            "\"key_points\": [\"point1\",\"point2\"],"
            "\"recommendation\": \"APPROVE|REVIEW|REJECT\""
            "}"
        },
        {
            "role": "user",
            "content": json.dumps({
                "application": app,
                "deterministic_score": score
            })
        }
    ]

def rebuttal_prompt(app, score, opponent_argument, stance):
    return [
        {
            "role": "system",
            "content":
            f"You are a {stance} NBFC risk analyst providing a structured rebuttal.\n"
            "Governance Rules:\n"
            "1. You MUST NOT recompute or modify deterministic_score.\n"
            "2. You MUST explicitly acknowledge deterministic_score.\n"
            "3. You MUST critique weaknesses in the opponent's reasoning.\n"
            "4. You MUST defend your original stance logically.\n"
            "5. You MUST NOT introduce new numeric calculations.\n"
            "6. You MUST return STRICT JSON only.\n"
            "{"
            "\"counter_points\": [\"point1\",\"point2\"],"
            "\"recommendation\": \"APPROVE|REVIEW|REJECT\""
            "}"
        },
        {
            "role": "user",
            "content": json.dumps({
                "application": app,
                "deterministic_score": score,
                "opponent_argument": opponent_argument
            })
        }
    ]

def arbiter_prompt(app, score, a, b, ra, rb):
    return [
        {
            "role": "system",
            "content":
            "You are the senior credit committee arbiter.\n"
            "Governance Rules:\n"
            "1. Deterministic score is authoritative and cannot be changed.\n"
            "2. You MUST validate both arguments against deterministic_score.\n"
            "3. You MAY escalate to REVIEW only.\n"
            "4. You MUST return STRICT JSON only.\n"
            "{"
            "\"final_assessment\": \"summary referencing score\","
            "\"recommendation\": \"APPROVE|REVIEW|REJECT\""
            "}"
        },
        {
            "role": "user",
            "content": json.dumps({
                "application": app,
                "deterministic_score": score,
                "agent_a": a,
                "agent_b": b,
                "rebuttal_a": ra,
                "rebuttal_b": rb
            })
        }
    ]

# -------------------------
# Hybrid Escalation Logic
# -------------------------

def hybrid_policy(score, arbiter_recommendation):

    # Deterministic baseline
    if score >= 75:
        baseline = "APPROVE"
    elif score >= 60:
        baseline = "REVIEW"
    else:
        baseline = "REJECT"

    # AI can escalate to REVIEW only
    if baseline == "APPROVE" and arbiter_recommendation == "REVIEW":
        return "REVIEW"

    if baseline == "REJECT" and arbiter_recommendation == "REVIEW":
        return "REVIEW"

    return baseline

# -------------------------
# Execution
# -------------------------

application = create_application()

score = deterministic_score(application)

agent_a = call_llm(optimistic_prompt(application, score))
agent_b = call_llm(conservative_prompt(application, score))

rebut_a = call_llm(rebuttal_prompt(application, score, agent_b,"optimistic"))
rebut_b = call_llm(rebuttal_prompt(application, score, agent_a,"conservative"))

arbiter = call_llm(arbiter_prompt(application, score, agent_a, agent_b, rebut_a, rebut_b))

final_decision = hybrid_policy(score, arbiter["recommendation"])

# -------------------------
# Output
# -------------------------

print("Deterministic Score:", score)
print("\nAgent A:", agent_a)
print("\nAgent B:", agent_b)
print("\nRebuttal A:", rebut_a)
print("\nRebuttal B:", rebut_b)
print("\nArbiter:", arbiter)
print("\nFinal Decision:", final_decision)