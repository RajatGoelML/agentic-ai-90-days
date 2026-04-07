
"""
Day 24 – Tool Routing Agent Workflow

Purpose
-------
This program upgrades the workflow engine to support **AI-driven tool selection**.

Architecture
------------
Planner Node (AI_RISK_REVIEW)
        ↓
Tool Execution Node
        ↓
Tool Nodes (fraud_check, credit_lookup, sector_risk)
        ↓
Aggregator Node
        ↓
Policy Governance Node
        ↓
Final Decision

Key Capabilities Added
----------------------
AI tool selection
Sequential tool execution
Tool output aggregation
Restricted tool access (safety guard)
Deterministic policy enforcement
"""

from openai import OpenAI
from dotenv import load_dotenv
import json

load_dotenv()

client = OpenAI()

# ------------------------------------------------------------------
# STATE OBJECT
# ------------------------------------------------------------------

state = {
    "current_node": "START",
    "history": [],
    "status": "RUNNING",

    "data": {
        "application": {
            "loan_amount": 800000,
            "income": 2400000,
            "debt": 300000,
            "emi": 15000,
            "credit_score": 785,
            "years_operating": 8,
            "sector": "IT Services"
        },

        "deterministic_score": None,
        "risk_tier": None,

        "tools_to_run": [],
        "tool_outputs": {},

        "final_decision": None
    }
}

# ------------------------------------------------------------------
# NODE CLASS
# ------------------------------------------------------------------

class Node:

    def __init__(self, name, handler, next_nodes):

        self.name = name
        self.handler = handler
        self.next_nodes = next_nodes


# ------------------------------------------------------------------
# HANDLERS
# ------------------------------------------------------------------

def start_handler(state):

    return "LOAD_APPLICATION"


def load_application_handler(state):

    app = state["data"]["application"]

    income = app["income"]
    loan_amount = app["loan_amount"]
    debt = app["debt"]
    emi = app["emi"]
    credit_score = app["credit_score"]

    if income <= 0 or loan_amount <= 0:
        state["status"] = "FAILED"

    return "DETERMINISTIC_SCORING"


# ------------------------------------------------------------------
# DETERMINISTIC SCORING
# ------------------------------------------------------------------

def deterministic_scoring_handler(state):

    app = state["data"]["application"]

    debt = app["debt"]
    income = app["income"]
    emi = app["emi"]
    credit_score = app["credit_score"]

    dti_ratio = debt / income
    emi_ratio = (emi * 12) / income

    total_score = 0

    if dti_ratio <= 0.25:
        total_score += 30
    elif dti_ratio <= 0.40:
        total_score += 25
    elif dti_ratio <= 0.60:
        total_score += 15
    else:
        total_score += 5

    if emi_ratio <= 0.20:
        total_score += 25
    elif emi_ratio <= 0.35:
        total_score += 15
    else:
        total_score += 5

    if credit_score >= 750:
        total_score += 30
    elif credit_score >= 700:
        total_score += 20
    elif credit_score >= 650:
        total_score += 10
    else:
        total_score += 5

    if total_score >= 70:
        tier = "LOW"
    elif total_score >= 55:
        tier = "MEDIUM"
    else:
        tier = "HIGH"

    state["data"]["deterministic_score"] = total_score
    state["data"]["risk_tier"] = tier

    return "AI_RISK_REVIEW"


# ------------------------------------------------------------------
# AI RISK REVIEW
# ------------------------------------------------------------------

def ai_risk_review_handler(state):

    app = state["data"]["application"]
    score = state["data"]["deterministic_score"]
    tier = state["data"]["risk_tier"]

    prompt = f"""
You are a financial risk analyst.

Application:
{json.dumps(app)}

Deterministic Score: {score}
Risk Tier: {tier}

Choose which tools should run.

Available tools:
FRAUD_CHECK
CREDIT_LOOKUP
SECTOR_RISK

Respond ONLY JSON:

{{
"tools": ["tool1","tool2"]
}}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}]
    )

    output = json.loads(response.choices[0].message.content)

    tools = output.get("tools", [])

    # Context based tool restriction
    allowed_tools = ["FRAUD_CHECK","CREDIT_LOOKUP","SECTOR_RISK"]

    filtered = [t for t in tools if t in allowed_tools]

    state["data"]["tools_to_run"] = filtered

    return "TOOL_EXECUTION"


# ------------------------------------------------------------------
# TOOL EXECUTION ORCHESTRATOR
# ------------------------------------------------------------------

def tool_execution_handler(state):

    tools = state["data"]["tools_to_run"]

    if not tools:
        return "AGGREGATE_RESULTS"

    next_tool = tools.pop(0)

    return next_tool


# ------------------------------------------------------------------
# TOOL NODES
# ------------------------------------------------------------------

def fraud_check_handler(state):

    app = state["data"]["application"]

    if app["loan_amount"] > app["income"] * 2:
        state["data"]["tool_outputs"]["fraud_check"] = "HIGH"
    else:
        state["data"]["tool_outputs"]["fraud_check"] = "LOW"

    return "TOOL_EXECUTION"


def credit_lookup_handler(state):

    credit = state["data"]["application"]["credit_score"]

    if credit > 750:
        rating = "EXCELLENT"
    elif credit > 700:
        rating = "GOOD"
    else:
        rating = "AVERAGE"

    state["data"]["tool_outputs"]["credit_lookup"] = rating

    return "TOOL_EXECUTION"


def sector_risk_handler(state):

    sector = state["data"]["application"]["sector"]

    risky = ["Construction","Hospitality"]

    if sector in risky:
        state["data"]["tool_outputs"]["sector_risk"] = "HIGH"
    else:
        state["data"]["tool_outputs"]["sector_risk"] = "NORMAL"

    return "TOOL_EXECUTION"


# ------------------------------------------------------------------
# AGGREGATOR NODE
# ------------------------------------------------------------------

def aggregate_results_handler(state):

    outputs = state["data"]["tool_outputs"]

    state["data"]["tool_summary"] = outputs

    return "POLICY_CHECK"


# ------------------------------------------------------------------
# POLICY GOVERNANCE
# ------------------------------------------------------------------

def policy_check_handler(state):

    score = state["data"]["deterministic_score"]

    if score >= 70:
        decision = "APPROVE"
    elif score >= 55:
        decision = "REVIEW"
    else:
        decision = "REJECT"

    state["data"]["final_decision"] = decision

    return "FINAL_DECISION"


def final_decision_handler(state):

    print("\nFINAL DECISION:", state["data"]["final_decision"])

    return "END"


def end_handler(state):

    state["status"] = "COMPLETED"

    return None


# ------------------------------------------------------------------
# NODE REGISTRY
# ------------------------------------------------------------------

nodes = {

    "START": Node("START", start_handler, ["LOAD_APPLICATION"]),

    "LOAD_APPLICATION": Node("LOAD_APPLICATION", load_application_handler, ["DETERMINISTIC_SCORING"]),

    "DETERMINISTIC_SCORING": Node("DETERMINISTIC_SCORING", deterministic_scoring_handler, ["AI_RISK_REVIEW"]),

    "AI_RISK_REVIEW": Node("AI_RISK_REVIEW", ai_risk_review_handler, ["TOOL_EXECUTION"]),

    "TOOL_EXECUTION": Node("TOOL_EXECUTION", tool_execution_handler, ["FRAUD_CHECK","CREDIT_LOOKUP","SECTOR_RISK","AGGREGATE_RESULTS"]),

    "FRAUD_CHECK": Node("FRAUD_CHECK", fraud_check_handler, ["TOOL_EXECUTION"]),

    "CREDIT_LOOKUP": Node("CREDIT_LOOKUP", credit_lookup_handler, ["TOOL_EXECUTION"]),

    "SECTOR_RISK": Node("SECTOR_RISK", sector_risk_handler, ["TOOL_EXECUTION"]),

    "AGGREGATE_RESULTS": Node("AGGREGATE_RESULTS", aggregate_results_handler, ["POLICY_CHECK"]),

    "POLICY_CHECK": Node("POLICY_CHECK", policy_check_handler, ["FINAL_DECISION"]),

    "FINAL_DECISION": Node("FINAL_DECISION", final_decision_handler, ["END"]),

    "END": Node("END", end_handler, [])
}


# ------------------------------------------------------------------
# GRAPH ENGINE
# ------------------------------------------------------------------

def run_graph(state, nodes):

    while state["status"] == "RUNNING":

        current = state["current_node"]

        state["history"].append(current)

        node = nodes.get(current)

        if not node:
            state["status"] = "FAILED"
            break

        next_node = node.handler(state)

        if next_node is None:
            break

        if next_node not in node.next_nodes:
            state["status"] = "FAILED"
            break

        state["current_node"] = next_node


# ------------------------------------------------------------------
# EXECUTION
# ------------------------------------------------------------------

run_graph(state, nodes)

print("\nExecution History:")
print(state["history"])


