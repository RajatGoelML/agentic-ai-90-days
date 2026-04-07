
"""
Day 26–27 – Workflow Graph Validation + Execution Trace

Context
-------
By Day 25 the system had evolved into a **config-driven workflow engine**.
The workflow graph was defined using `GRAPH_CONFIG` and dynamically converted
into Node objects that the engine executed.

However two major production problems still existed:

1. Invalid workflow configurations could run and fail at runtime.
2. There was no visibility into what happened during workflow execution.

To address these issues we implemented:

    Day 26 → Graph Validation (Workflow Compilation)
    Day 27 → Execution Trace (Observability Layer)


----------------------------------------------------
Day 26 – Graph Validation Layer
----------------------------------------------------

Before building the graph, the engine now validates the workflow configuration.

The validation step ensures the workflow structure is correct before execution
begins. If any structural issue is detected, execution stops immediately.

The validator performs the following checks:

1. Handler Existence
   Every node must reference a handler function registered in the
   HANDLER_REGISTRY.

2. Transition Validity
   All "next" nodes referenced by a node must exist in the graph.

3. Terminal Node Detection
   At least one terminal node must exist (node with no outgoing edges).

4. Reachability Analysis
   Every node must be reachable from the START node.
   Unreachable nodes indicate configuration errors.

This validation stage acts like **workflow compilation**, similar to how
real orchestration systems validate DAGs before execution.

Examples of systems using similar validation:
    - Apache Airflow
    - Temporal
    - Prefect
    - LangGraph

New architecture:

    GRAPH_CONFIG
          ↓
    Graph Validation
          ↓
    Graph Builder
          ↓
    Graph Engine


----------------------------------------------------
Day 27 – Execution Trace / Observability
----------------------------------------------------

The engine previously only stored execution order using:

    state["history"]

This showed which nodes executed but did not explain what actually happened
inside each node.

To improve observability we introduced **Execution Trace Logging**.

Each node execution now records:

    - node name
    - timestamp of execution
    - output / routing decision

Example trace entry:

{
    "node": "DETERMINISTIC_SCORING",
    "timestamp": "2026-03-08T14:21:03",
    "output": "POLICY_CHECK"
}

This creates an **execution audit trail** which helps with:

    debugging workflow behavior
    understanding AI decisions
    investigating failures
    analyzing system performance

Trace entries are appended to:

    state["trace"]


----------------------------------------------------
Engine Execution Flow
----------------------------------------------------

Workflow execution now follows this lifecycle:

    1. Validate workflow configuration
    2. Build Node objects from config
    3. Execute workflow engine loop
    4. Record execution trace at each node
    5. Validate transitions between nodes
    6. Stop when a terminal node completes


----------------------------------------------------
Outcome
----------------------------------------------------

After Day 26–27 the workflow engine now supports:

    Config-driven workflow graphs
    Structural validation of workflows
    Safe execution of nodes
    Execution trace logging
    Retry tracking
    Step guard against infinite loops

The engine now resembles a simplified orchestration runtime similar to
systems like LangGraph, Airflow, and Temporal.

This prepares the system for future capabilities such as:

    tool orchestration
    parallel node execution
    multi-agent workflows
    graph visualization
"""

from datetime import datetime

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

#-- Node Result --

class NodeResult:

    def __init__(self, next_node=None, data_updates=None):

        self.next_node = next_node
        self.data_updates = data_updates or {}


# ----------------------------------------------------
# STATE OBJECT
# ----------------------------------------------------

state = {

    "current_node": "START",
    "status": "RUNNING",
    "history": [],
    "trace":[],

    "data": {
        "application": {
            "loan_amount": 800000,
            "income": 2400000,
            "debt": 300000,
            "emi": 15000,
            "credit_score": 785,
            "years_operating": 8,
            "sector": "IT Services"
        }
    },
    "deterministic_score": None,
    "risk_tier": None,
    "final_decision": None,
    "step_count": 0,
    "max_steps": 20,
    "retry_counts": {}
}        

# ----------------------------------------------------
# HANDLER FUNCTIONS
# ----------------------------------------------------

def start_handler(state):

    return NodeResult(
        next_node="LOAD_APPLICATION"
    )  


def load_application_handler(state):

    app = state["data"]["application"]

    if app["income"] <= 0:
        state["status"] = "FAILED"

    return NodeResult(
        next_node="DETERMINISTIC_SCORING"
    )    



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


    return NodeResult(
        next_node="POLICY_CHECK",
        data_updates={
            "deterministic_score":score,
            "risk_tier": tier
        }
    )


def policy_check_handler(state):

    score = state["data"]["deterministic_score"]

    if score >= 70:
        decision = "APPROVE"
    elif score >= 55:
        decision = "REVIEW"
    else:
        decision = "REJECT"

    state["data"]["final_decision"] = decision

    return NodeResult(
        next_node="FINAL_DECISION",
        data_updates={
            "final_decision":decision
        }
    )


def final_decision_handler(state):

    print("\nFINAL DECISION:", state["data"]["final_decision"])

    return NodeResult(
        next_node="END"
    )



def end_handler(state):

    state["status"] = "COMPLETED"

    return NodeResult(
        next_node=None
    )

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
# GRAPH VALIDATION
# ----------------------------------------------------

def validate_graph(graph_config, handler_registry):

    # -------- Check 1: Handlers exist --------
    for node_name, node_config in graph_config.items():

        handler_name = node_config["handler"]

        if handler_name not in handler_registry:
            raise Exception(
                f"Validation Error: Handler '{handler_name}' not found for node '{node_name}'"
            )


    # -------- Check 2: Transitions exist --------
    for node_name, node_config in graph_config.items():

        for next_node in node_config["next"]:

            if next_node not in graph_config:
                raise Exception(
                    f"Validation Error: Node '{node_name}' points to unknown node '{next_node}'"
                )


    # -------- Check 3: Terminal node exists --------
    terminal_nodes = [
        node for node, config in graph_config.items()
        if len(config["next"]) == 0
    ]

    if not terminal_nodes:
        raise Exception(
            "Validation Error: Workflow must contain at least one terminal node"
        )


    # -------- Check 4: Unreachable nodes --------
    visited = set()
    stack = ["START"]

    while stack:

        node = stack.pop()

        if node in visited:
            continue

        visited.add(node)

        for next_node in graph_config[node]["next"]:
            stack.append(next_node)


    unreachable_nodes = set(graph_config.keys()) - visited

    if unreachable_nodes:
        raise Exception(
            f"Validation Error: Unreachable nodes detected: {unreachable_nodes}"
        )


    print("Graph validation passed.")


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

        print( nodes, "this is what build grpah returns as nodes")

    return nodes


# ----------------------------------------------------
# GRAPH ENGINE
# ----------------------------------------------------

def run_graph(state, nodes):

    while state["status"] == "RUNNING":

        state["step_count"] += 1

        if state["step_count"] > state["max_steps"]:
            print("Max steps exceeded")
            state["status"] = "FAILED"
            break

        current_node_name = state["current_node"]

        state["history"].append(current_node_name)

        node = nodes.get(current_node_name)

        try:

             # ---- Execute Node ----
            result = node.handler(state)

            next_node = result.next_node

            if result.data_updates:
                for key, value in result.data_updates.items():
                    state["data"][key] = value

             # ---- Record Trace ----
            trace_entry = {
                "node": current_node_name,
                "timestamp": datetime.now().isoformat(),
                "output": next_node
                }

            state["trace"].append(trace_entry)


        except Exception as e:

            state["retry_counts"].setdefault(current_node_name, 0)

            state["retry_counts"][current_node_name] += 1

            if state["retry_counts"][current_node_name] <= node.max_retries:
                print(f"Retrying {current_node_name}")
                continue

            print(f"Node {current_node_name} failed: {str(e)}")
            state["status"] = "FAILED"
            break


        # ---- Validate transition ----
        if next_node not in node.next_nodes:
             print("Illegal transition")
             state["status"] = "FAILED"
             break


        state["current_node"] = next_node


# ----------------------------------------------------
# EXECUTION
# ----------------------------------------------------

validate_graph(GRAPH_CONFIG, HANDLERS)

nodes = build_graph(GRAPH_CONFIG)

run_graph(state, nodes)

print("\nExecution History:")
print(state["history"])

print("\nExecution Trace:\n")

for entry in state["trace"]:
    print(entry)