"""
Program: Loan Approval AI Workflow Engine (Day 22)

Purpose
-------
This program implements a production-style workflow system that evaluates
loan applications using a hybrid decision architecture combining:

1. Deterministic financial risk scoring
2. LLM-based reasoning analysis
3. Policy-driven governance rules

The goal is not only to evaluate loans but also to demonstrate how modern
AI systems are orchestrated using a state-driven workflow engine.

The workflow engine itself is generic and reusable. It executes a graph of
nodes where each node represents a step in the decision process.

Architectural Objective
-----------------------
The system demonstrates how to build an AI-driven workflow pipeline where:

- A workflow engine controls execution
- Nodes define the workflow structure
- Handler functions implement business logic
- State acts as the single source of truth

This separation ensures that business logic can evolve independently from
the orchestration engine.

Workflow Execution Model
------------------------
Each loan application runs its own workflow instance.

For every application:
    1. A new workflow state is created
    2. The GraphEngine executes nodes sequentially
    3. Each node reads and updates the shared state
    4. The workflow progresses until it reaches the END node

Workflow Graph
--------------
START
  ↓
LOAD_APPLICATION
  ↓
DETERMINISTIC_SCORING
  ↓
AI_RISK_REVIEW
  ↓
POLICY_CHECK
  ↓
FINAL_DECISION
  ↓
END

Node Responsibilities
---------------------
START
    Initializes workflow execution.

LOAD_APPLICATION
    Validates application data and enforces input constraints.

DETERMINISTIC_SCORING
    Calculates financial risk metrics such as:
        - Debt-to-Income Ratio (DTI)
        - EMI Ratio
        - Deterministic Risk Score
        - Risk Tier

AI_RISK_REVIEW
    Uses an LLM to provide advisory reasoning on the loan based on:
        - application data
        - deterministic risk metrics

POLICY_CHECK
    Combines deterministic scoring and AI recommendation to produce
    a governed final decision. AI is advisory and cannot override
    deterministic policy rules.

FINAL_DECISION
    Records the final decision outcome for the workflow.

END
    Terminates the workflow execution.

State Model
-----------
The workflow state acts as the single source of truth and contains:

current_node
    Tracks the current workflow step.

history
    Records execution path for debugging and auditing.

data
    Stores business data including:
        application details
        deterministic scoring metrics
        AI reasoning output
        final decision

retry_counts
    Tracks retries per node.

step_count / max_steps
    Prevents infinite workflow loops.

Reliability Mechanisms
----------------------
The engine includes several production-style safety features:

Step Guard
    Prevents infinite execution loops.

Retry Logic
    Allows nodes to retry transient failures.

Timeout Guard
    Ensures slow nodes do not block execution.

Transition Validation
    Prevents illegal workflow transitions.

State Isolation
    Each loan application executes with its own independent workflow state.

What This Program Demonstrates
------------------------------
This system illustrates a simplified version of the architecture used in
modern AI orchestration platforms such as:

LangGraph
Temporal
Prefect
Airflow

It shows how to combine:
    deterministic algorithms
    LLM reasoning
    workflow orchestration
    state-driven execution

into a robust AI decision system.

Future Enhancements
-------------------
This architecture can be extended to support:

- dynamic graph configuration
- parallel workflow execution
- observability and tracing
- structured LLM outputs
- multi-agent reasoning
- persistent workflow state
"""

def create_state(application):

    return {
        "current_node": "START",
        "history": [],
        "status": "RUNNING",

        "data": {
            "application": application,
            "deterministic_score": None,
            "risk_tier": None,
            "dti_ratio": None,
            "emi_ratio": None,
            "ai_review": None,
            "final_decision": None
        },

        "step_count": 0,
        "max_steps": 20,
        "retry_counts": {}
    }

class Node:

    def __init__(self, name, handler, next_nodes, max_retries=0, timeout=5):

        self.name = name              # node identifier
        self.handler = handler        # function executed at this node
        self.next_nodes = next_nodes  # allowed transitions
        self.max_retries = max_retries
        self.timeout = timeout

nodes = {
    "START": Node("START", start_handler, ["LOAD_APPLICATION"]),
    "LOAD_APPLICATION": Node("LOAD_APPLICATION", load_application_handler, ["DETERMINISTIC_SCORING"]),
    "DETERMINISTIC_SCORING": Node("DETERMINISTIC_SCORING", deterministic_scoring_handler, ["AI_RISK_REVIEW"]),
    "AI_RISK_REVIEW": Node("AI_RISK_REVIEW", ai_risk_review_handler, ["POLICY_CHECK"]),
    "POLICY_CHECK": Node("POLICY_CHECK", policy_check_handler, ["FAST_APPROVAL", "FRAUD_CHECK", "POLICY_CHECK"]),
    "FINAL_DECISION": Node("FINAL_DECISION", final_decision_handler, ["END"]),
    "END": Node("END", end_handler, [])
}

def start_handler(state):

    print("Workflow started")
    return "LOAD_APPLICATION"

def load_application_handler(state):

    app = state["data"]["application"]

    income = app["income"]
    loan_amount = app["loan_amount"]
    debt = app["debt"]
    emi = app["emi"]
    credit_score = app["credit_score"]
    years_operating = app["years_operating"]
    sector = app["sector"]

    if income <= 0 or loan_amount <= 0 or debt < 0 or emi < 0 or credit_score < 300 or credit_score > 850 or years_operating < 0 or not sector:
        
        print("Application validation failed")
        state["status"] = "FAILED"
        return "END"
    
    return "DETERMINISTIC_SCORING"

def deterministic_scoring_handler(state):

    app = state["data"]["application"]

    income = app["income"]
    loan_amount = app["loan_amount"]
    debt = app["debt"]
    emi = app["emi"]
    credit_score = app["credit_score"]
    years_operating = app["years_operating"]
    sector = app["sector"]

    total_score = 0

    # ---- Calculate ratios ----
    dti_ratio = debt / income                     # Deterministic logic
    emi_ratio = (12 * emi) / income               # Deterministic logic (annual EMI burden)


# ---- DTI Scoring ----
    if dti_ratio <= 0.25:
         total_score += 30
    elif dti_ratio <= 0.40:
        total_score += 25
    elif dti_ratio <= 0.60:
        total_score += 15
    else:
        total_score += 5


# ---- EMI Ratio Scoring ----
    if emi_ratio <= 0.20:
        total_score += 25
    elif emi_ratio <= 0.35:
        total_score += 15
    else:
        total_score += 5


# ---- Credit Score Scoring ----
    if credit_score >= 750:
        total_score += 30
    elif credit_score >= 700:
        total_score += 20
    elif credit_score >= 650:
        total_score += 10
    else:
        total_score += 5


# ---- Determine Risk Tier ----
    if total_score >= 70:
        tier = "LOW"
    elif total_score >= 55:
        tier = "MEDIUM"
    else:
        tier = "HIGH"

        # ---- Save results in state ----
    state["data"]["deterministic_score"] = total_score        # State mutation
    state["data"]["risk_tier"] = tier                         # State mutation
    state["data"]["dti_ratio"] = dti_ratio                    # State mutation
    state["data"]["emi_ratio"] = emi_ratio                    # State mutation

    # ---- Transition to AI node ----
    return "AI_RISK_REVIEW"                                     # FSM transition



def ai_risk_review_handler(state):

    app = state["data"]["application"]
    score = state["data"]["deterministic_score"]
    tier = state["data"]["risk_tier"]

    prompt = f"""
    You are a financial risk analyst.

    Application:
    {app}

    Deterministic score: {score}
    Risk tier: {tier}

    Decide:

    recommendation → APPROVE / REVIEW / REJECT
    route → FAST_APPROVAL / FRAUD_CHECK / POLICY_CHECK

    Respond ONLY in JSON:

    {{
      "recommendation": "...",
      "route": "...",
      "reason": "..."
    }}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    output = json.loads(response.choices[0].message.content)

    state["data"]["ai_review"] = output

    return output["route"]



def fast_approval_handler(state):

    print("Fast approval candidate")

    return "POLICY_CHECK"

def fraud_check_handler(state):

    print("Performing fraud analysis")

    return "POLICY_CHECK"


def policy_check_handler(state):

    tier = state["data"]["risk_tier"]                     # Read deterministic tier
    ai_rec = state["data"]["ai_review"]["recommendation"] # Read AI advisory


    if tier == "LOW":

        if ai_rec == "APPROVE":
            decision = "APPROVE"
        else:
            decision = "REVIEW"


    elif tier == "MEDIUM":

        if ai_rec == "REJECT":
            decision = "REJECT"
        else:
            decision = "REVIEW"


    else:  # HIGH risk
        decision = "REJECT"


    state["data"]["final_decision"] = decision            # State mutation

    return "FINAL_DECISION"


def final_decision_handler(state):

    print("Final Decision:", state["data"]["final_decision"])

    return "END"


def end_handler(state):

    state["status"] = "COMPLETED"

    return "END"
