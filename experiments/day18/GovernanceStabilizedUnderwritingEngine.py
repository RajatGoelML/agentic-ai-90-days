"""
Day 18 – Governance Stabilized Multi-Agent Underwriting Engine

Upgrades:
- Feature-bounded reasoning enforcement
- Escalation guard rules
- Arbiter escalation validation layer
- Governance violation logging
"""


from openai import OpenAI
from dotenv import load_dotenv
import json

load_dotenv()
client = OpenAI()

PRIMARY_MODEL = "gpt-4o-mini"


# -------------------------
# Error Classification
# -------------------------

class ErrorType:
    VALIDATION_ERROR = "VALIDATION_ERROR"
    LLM_SCHEMA_ERROR = "LLM_SCHEMA_ERROR"
    ESCALATION_VIOLATION = "ESCALATION_VIOLATION"

# -------------------------
# Application
# -------------------------

def create_application():
    return {
        "borrower_profile": {
            "age": 34,
            "employment_type": "salaried",
            "years_at_current_employer": 5
        },
        "financial_profile": {
            "annual_income": 1800000,
            "monthly_obligations": 35000,
            "existing_total_debt": 400000,
            "bank_cashflow_volatility_score": 0.2
        },
        "credit_profile": {
            "credit_score": 735,
            "recent_delinquency": False
        }
    }

# -------------------------
# Deterministic Scoring
# -------------------------

def deterministic_score(app):

    score = 0

    income = app["financial_profile"]["annual_income"]
    obligations = app["financial_profile"]["monthly_obligations"]
    debt = app["financial_profile"]["existing_total_debt"]
    credit = app["credit_profile"]["credit_score"]
    volatility = app["financial_profile"]["bank_cashflow_volatility_score"]
    years = app["borrower_profile"]["years_at_current_employer"]
    delinquency = app["credit_profile"]["recent_delinquency"]

    dti = debt / income
    emi_ratio = (obligations * 12) / income

    # Credit (25)
    score += 20 if credit >= 700 else 12

    # DTI (20)
    score += 15 if dti <= 0.35 else 8

    # EMI (15)
    score += 10 if emi_ratio <= 0.35 else 5

    # Employment (15)
    score += 15 if years >= 5 else 10

    # Volatility (15)
    score += 15 if volatility <= 0.2 else 10

    # Behaviour (10)
    score += 10 if not delinquency else 2

    return {
        "score": score,
        "metrics": {
            "dti": dti,
            "emi_ratio": emi_ratio,
            "volatility": volatility,
            "delinquency": delinquency
        }
    }

# -------------------------
# Strict LLM Call
# -------------------------

def call_llm(messages):
    response = client.chat.completions.create(
        model=PRIMARY_MODEL,
        messages=messages,
        response_format={"type": "json_object"}
    )

    return json.loads(response.choices[0].message.content)

# -------------------------
# Feature-Bounded Prompts
# -------------------------

def optimistic_prompt(app, score_data):
    return [
        {
            "role": "system",
            "content":
            "You are an optimistic NBFC analyst.\n"
            "You MUST reason only using these features:\n"
            "credit_score, dti, emi_ratio, years_at_current_employer, "
            "bank_cashflow_volatility_score, recent_delinquency.\n"
            "You MUST NOT introduce macroeconomic or external assumptions.\n"
            "Return STRICT JSON:\n"
            "{"
            "\"recommendation\": \"APPROVE|REVIEW|REJECT\","
            "\"reason\": \"feature bounded explanation\""
            "}"
        },
        {
            "role": "user",
            "content": json.dumps(score_data)
        }
    ]

def conservative_prompt(app, score_data):
    return [
        {
            "role": "system",
            "content":
            "You are a conservative NBFC analyst.\n"
            "You MUST reason only using provided deterministic features.\n"
            "No external speculation allowed.\n"
            "Return STRICT JSON:\n"
            "{"
            "\"recommendation\": \"APPROVE|REVIEW|REJECT\","
            "\"reason\": \"feature bounded explanation\""
            "}"
        },
        {
            "role": "user",
            "content": json.dumps(score_data)
        }
    ]

def arbiter_prompt(score_data, a, b):
    return [
        {
            "role": "system",
            "content":
            "You are senior credit arbiter.\n"
            "You MUST validate arguments strictly against provided features.\n"
            "You MAY escalate to REVIEW only if feature risk justifies it.\n"
            "Return STRICT JSON:\n"
            "{"
            "\"recommendation\": \"APPROVE|REVIEW|REJECT\","
            "\"reason\": \"justification\""
            "}"
        },
        {
            "role": "user",
            "content": json.dumps({
                "score_data": score_data,
                "agent_a": a,
                "agent_b": b
            })
        }
    ]

# -------------------------
# Escalation Guard Logic
# -------------------------

def validate_escalation(score_data, arbiter_recommendation):

    score = score_data["score"]
    metrics = score_data["metrics"]

    # Deterministic baseline
    baseline = "APPROVE" if score >= 75 else "REJECT"

    # Guard Conditions
    escalation_allowed = (
        score < 80 or
        metrics["delinquency"] or
        metrics["volatility"] >= 0.4 or
        metrics["dti"] >= 0.5
    )

    if arbiter_recommendation == "REVIEW" and not escalation_allowed:
        print("\n[Governance Warning] Illegal escalation attempt blocked.")
        return baseline

    if arbiter_recommendation == "REVIEW" and escalation_allowed:
        return "REVIEW"

    return baseline

# -------------------------
# Execution
# -------------------------

application = create_application()

score_data = deterministic_score(application)

agent_a = call_llm(optimistic_prompt(application, score_data))
agent_b = call_llm(conservative_prompt(application, score_data))

arbiter = call_llm(arbiter_prompt(score_data, agent_a, agent_b))

final_decision = validate_escalation(score_data, arbiter["recommendation"])

# -------------------------
# Output
# -------------------------

print("Deterministic Score:", score_data["score"])
print("\nAgent A:", agent_a)
print("\nAgent B:", agent_b)
print("\nArbiter:", arbiter)
print("\nFinal Decision:", final_decision)    