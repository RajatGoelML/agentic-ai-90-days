"""
Day 25 – Config Driven Workflow Engine

Context
-------
In previous days the workflow graph was hardcoded directly in Python.
That meant every workflow change required modifying code and redeploying
the system.

Example problem:
If the risk team wanted to add a new fraud check step, developers had to:
    - modify Python code
    - update node definitions
    - redeploy the application

This approach does not scale in real production systems.

Solution Implemented
--------------------
This program converts the workflow engine into a **config-driven system**.

Instead of defining nodes directly in Python, the workflow is defined in a
configuration dictionary called `GRAPH_CONFIG`.

Each node in the config describes:
    - handler function to execute
    - allowed next nodes (graph transitions)
    - retry policy
    - timeout policy
    - node type (AI, TOOL, POLICY, etc.)
    - human readable description

Example node definition:

{
    "DETERMINISTIC_SCORING": {
        "handler": "deterministic_scoring_handler",
        "next": ["POLICY_CHECK"],
        "max_retries": 0,
        "timeout": 2,
        "node_type": "SCORING",
        "description": "Compute financial risk score"
    }
}

Architecture
------------
GRAPH_CONFIG (workflow specification)
        ↓
Graph Builder
        ↓
Node Objects
        ↓
Graph Engine
        ↓
Workflow Execution

The **Graph Builder** reads the config and dynamically constructs Node objects.
The **Graph Engine** then executes the workflow using those nodes.

Key Benefit
-----------
The engine becomes generic and reusable.

Now we can run different workflows by simply changing the configuration
instead of rewriting the engine code.

This design is similar to how real orchestration systems work, such as:
    - Airflow DAGs
    - Temporal workflows
    - LangGraph execution graphs
    - Prefect flows

Outcome
-------
The system has evolved from a simple script into a **general workflow engine**
capable of executing configurable AI workflows.
"""

#-- Node Class --

class Node:

    def __init__(self, name, handler, next_nodes, max_retries, timeout, node_type, description):
        self.name = name
        self.handler = handler
        self.next_nodes = next_nodes
        self.max_retries = max_retries
        self.timeout = timeout
        self.node_type = node_type
        self.description = description


# ----------------------------------------------------
# STATE OBJECT
# ----------------------------------------------------

state = {

    "current_node": "START",

    "status": "RUNNING",

    "history": [],

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
        "final_decision": None
    }
}        

# ----------------------------------------------------
# HANDLER FUNCTIONS
# ----------------------------------------------------

def start_handler(state):

    return "LOAD_APPLICATION"


def load_application_handler(state):

    app = state["data"]["application"]

    if app["income"] <= 0:
        state["status"] = "FAILED"

    return "DETERMINISTIC_SCORING"


def deterministic_scoring_handler(state):

    app = state["data"]["application"]

    income = app["income"]
    debt = app["debt"]
    emi = app["emi"]
    credit_score = app["credit_score"]

    dti = debt / income
    emi_ratio = (emi * 12) / income

    score = 0

    if dti <= 0.25:
        score += 30
    elif dti <= 0.40:
        score += 25
    elif dti <= 0.60:
        score += 15
    else:
        score += 5

    if emi_ratio <= 0.20:
        score += 25
    elif emi_ratio <= 0.35:
        score += 15
    else:
        score += 5

    if credit_score >= 750:
        score += 30
    elif credit_score >= 700:
        score += 20
    elif credit_score >= 650:
        score += 10
    else:
        score += 5

    if score >= 70:
        tier = "LOW"
    elif score >= 55:
        tier = "MEDIUM"
    else:
        tier = "HIGH"

    state["data"]["deterministic_score"] = score
    state["data"]["risk_tier"] = tier

    return "POLICY_CHECK"


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


# ----------------------------------------------------
# HANDLER REGISTRY
# ----------------------------------------------------

HANDLERS = {

    "start_handler": start_handler,
    "load_application_handler": load_application_handler,
    "deterministic_scoring_handler": deterministic_scoring_handler,
    "policy_check_handler": policy_check_handler,
    "final_decision_handler": final_decision_handler,
    "end_handler": end_handler
}


# ----------------------------------------------------
# GRAPH CONFIG
# ----------------------------------------------------

GRAPH_CONFIG = {

    "START": {
        "handler": "start_handler",
        "next": ["LOAD_APPLICATION"],
        "max_retries": 0,
        "timeout": 1,
        "node_type": "SYSTEM",
        "description": "Entry point of workflow"
    },

    "LOAD_APPLICATION": {
        "handler": "load_application_handler",
        "next": ["DETERMINISTIC_SCORING"],
        "max_retries": 1,
        "timeout": 2,
        "node_type": "VALIDATION",
        "description": "Validate loan application"
    },

    "DETERMINISTIC_SCORING": {
        "handler": "deterministic_scoring_handler",
        "next": ["POLICY_CHECK"],
        "max_retries": 0,
        "timeout": 2,
        "node_type": "SCORING",
        "description": "Compute financial risk score"
    },

    "POLICY_CHECK": {
        "handler": "policy_check_handler",
        "next": ["FINAL_DECISION"],
        "max_retries": 0,
        "timeout": 1,
        "node_type": "POLICY",
        "description": "Apply risk policy rules"
    },

    "FINAL_DECISION": {
        "handler": "final_decision_handler",
        "next": ["END"],
        "max_retries": 0,
        "timeout": 1,
        "node_type": "OUTPUT",
        "description": "Generate final decision"
    },

    "END": {
        "handler": "end_handler",
        "next": [],
        "max_retries": 0,
        "timeout": 1,
        "node_type": "SYSTEM",
        "description": "Workflow termination"
    }
}

# ----------------------------------------------------
# GRAPH BUILDER
# ----------------------------------------------------

def build_graph(config):

    nodes = {}

    for node_name, node_config in config.items():

        handler_name = node_config["handler"]

        handler = HANDLERS.get(handler_name)

        if handler is None:
            raise Exception(f"Handler {handler_name} not registered")

        node = Node(
            name=node_name,
            handler=handler,
            next_nodes=node_config["next"],
            max_retries=node_config["max_retries"],
            timeout=node_config["timeout"],
            node_type=node_config["node_type"],
            description=node_config["description"]
        )

        nodes[node_name] = node

    return nodes


# ----------------------------------------------------
# GRAPH ENGINE
# ----------------------------------------------------

def run_graph(state, nodes):

    while state["status"] == "RUNNING":

        current_node_name = state["current_node"]

        state["history"].append(current_node_name)

        node = nodes.get(current_node_name)

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


# ----------------------------------------------------
# EXECUTION
# ----------------------------------------------------

nodes = build_graph(GRAPH_CONFIG)

run_graph(state, nodes)

print("\nExecution History:")
print(state["history"])