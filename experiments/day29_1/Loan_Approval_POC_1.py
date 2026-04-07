





# ------------------------------------------------
# Deterministic Scoring Node
# ------------------------------------------------

def deterministic_scoring_node(state):

    # --- Deterministic logic: read application data
    app = state["data"]["application"]

    income = app["income"]
    debt = app["debt"]
    emi = app["emi"]
    credit_score = app["credit_score"]

    # --- Derived financial ratios
    debt_to_income = debt / income
    emi_to_income = (emi * 12) / income

    # --- Basic scoring model
    score = 0

    if credit_score > 750:
        score += 40
    elif credit_score > 700:
        score += 30
    else:
        score += 10

    if debt_to_income < 0.2:
        score += 30
    elif debt_to_income < 0.4:
        score += 20
    else:
        score += 5

    if emi_to_income < 0.25:
        score += 30
    elif emi_to_income < 0.4:
        score += 20
    else:
        score += 5

    # --- Determine risk bucket
    if score >= 80:
        risk_bucket = "LOW"
    elif score >= 60:
        risk_bucket = "MEDIUM"
    else:
        risk_bucket = "HIGH"

    return NodeResult(

        data_updates={
            "financial_score": score,
            "risk_bucket": risk_bucket
        }
    )


# ------------------------------------------------
# Node Registry (stores Node objects)
# ------------------------------------------------

NODE_REGISTRY = {

    "DETERMINISTIC_SCORING": Node(
        name="DETERMINISTIC_SCORING",
        node_type="DETERMINISTIC",
        description="Compute financial risk signals",
        node_function=deterministic_scoring_node,
        next_nodes=["CREDIT_AGENT", "FRAUD_AGENT", "SECTOR_AGENT"],
        max_retry=0
    ),
    "CREDIT_AGENT": Node(
    name="CREDIT_AGENT",
    node_type="AGENT",
    description="Evaluates repayment risk",
    node_function=credit_agent_node,
    max_retry=0
    ),

    "FRAUD_AGENT": Node(
        name="FRAUD_AGENT",
        node_type="AGENT",
        description="Detects potential fraud signals",
        node_function=fraud_agent_node
    ),

    "SECTOR_AGENT": Node(
        name="SECTOR_AGENT",
        node_type="AGENT",
        description="Evaluates industry risk",
        node_function=sector_agent_node
    ),

    "AGGREGATOR": Node(
    name="AGGREGATOR",
    node_type="AGENT",
    description="Combines agent outputs into unified risk",
    node_function=aggregator_node
    ),

    "CRITIC": Node(
    name="CRITIC",
    node_type="AGENT",
    description="Checks consistency of agent outputs",
    node_function=critic_node
    ),

    "POLICY": Node(
    name="POLICY",
    node_type="DETERMINISTIC",
    description="Applies deterministic loan approval rules",
    node_function=policy_node
    ),

    "FINAL_DECISION": Node(
    name="FINAL_DECISION",
    node_type="TERMINAL",
    description="Outputs final decision and ends workflow",
    node_function=final_decision_node
    )
}



def execute_node(state, node_name):

    # --- Fetch node object from registry
    node = NODE_REGISTRY[node_name]

    # --- Update execution pointer
    state["current_node"] = node_name

    try:

        # --- Execute node logic
        result = node.node_function(state)

    except Exception as e:

        # --- Retry handling
        retry_count = state["retry_count"].get(node_name, 0)

        if retry_count < node.max_retry:

            state["retry_count"][node_name] = retry_count + 1

            print(f"Retrying node {node_name} ({retry_count+1}/{node.max_retry})")

            return [node_name]

        else:

            state["status"] = "FAILED"

            raise RuntimeError(f"Node {node_name} failed after retries") from e

    # --- Apply result to state
    apply_node_result(state, result)

    next_nodes = GRAPH_CONFIG[node_name]["next"]

    # --- Record execution event
    record_execution_event(state, node_name,next_nodes, result)

    # --- Mark node as completed
    state["completed_nodes"].add(node_name)

    state["step_count"] += 1


def build_dependency_map(graph_config):

    dependency_map = {}

    for node, config in graph_config.items():

        for next_node in config["next"]:

            if next_node not in dependency_map:
                dependency_map[next_node] = []

            dependency_map[next_node].append(node)

    return dependency_map

DEPENDENCY_MAP = build_dependency_map(GRAPH_CONFIG)

def get_runnable_nodes(state):

    runnable = []

    for node in GRAPH_CONFIG:

        if node in state["completed_nodes"]:
            continue

        dependencies = DEPENDENCY_MAP.get(node, [])

        # node is runnable if all dependencies completed
        if all(dep in state["completed_nodes"] for dep in dependencies):
            runnable.append(node)

    return runnable

def run_workflow(state):

    while state["status"] == "RUNNING":

        # safety guard
        if state["step_count"] >= state["max_steps"]:
            print("Max steps exceeded")
            break

        runnable_nodes = get_runnable_nodes(state)

        if not runnable_nodes:
            break

        for node in runnable_nodes:

            if node == "START":
                state["completed_nodes"].add("START")
                continue

            execute_node(state, node)

    print("Workflow finished")

validate_graph(GRAPH_CONFIG, NODE_REGISTRY)

run_workflow(state)


# ------------------------------------------------
# Credit Risk Agent
# ------------------------------------------------

def credit_agent_node(state):

    app = state["data"]["application"]

    financial_score = state["data"]["financial_score"]

    credit_score = app["credit_score"]
    debt = app["debt"]
    income = app["income"]

    debt_to_income = debt / income

    # --- Simple risk reasoning
    if financial_score >= 80 and credit_score >= 750 and debt_to_income < 0.3:
        risk = "LOW"

    elif financial_score >= 60 and credit_score >= 700:
        risk = "MEDIUM"

    else:
        risk = "HIGH"

    return NodeResult(

        data_updates={
            "agent_summary": {
                **state["data"]["agent_summary"],
                "credit_risk": risk
            }
        }
    )

# ------------------------------------------------
# Fraud Detection Agent
# ------------------------------------------------

def fraud_agent_node(state):

    app = state["data"]["application"]

    loan_amount = app["loan_amount"]
    income = app["income"]
    years_operating = app["years_operating"]

    loan_to_income = loan_amount / income

    # --- Simple fraud heuristics
    if loan_to_income > 1.5 or years_operating < 1:
        fraud_risk = "HIGH"

    elif loan_to_income > 0.8:
        fraud_risk = "MEDIUM"

    else:
        fraud_risk = "LOW"

    return NodeResult(

        data_updates={
            "agent_summary": {
                **state["data"]["agent_summary"],
                "fraud_risk": fraud_risk
            }
        }
    )

# ------------------------------------------------
# Sector Risk Agent
# ------------------------------------------------

def sector_agent_node(state):

    sector = state["data"]["application"]["sector"]

    high_risk_sectors = ["Crypto", "Gambling"]
    medium_risk_sectors = ["Manufacturing", "Construction"]

    if sector in high_risk_sectors:
        sector_risk = "HIGH"

    elif sector in medium_risk_sectors:
        sector_risk = "MEDIUM"

    else:
        sector_risk = "LOW"

    return NodeResult(

        data_updates={
            "agent_summary": {
                **state["data"]["agent_summary"],
                "sector_risk": sector_risk
            }
        }
    )

# ------------------------------------------------
# Agent Aggregator
# ------------------------------------------------

def aggregator_node(state):

    agent_summary = state["data"]["agent_summary"]

    risks = list(agent_summary.values())

    if "HIGH" in risks:
        overall_risk = "HIGH"

    elif "MEDIUM" in risks:
        overall_risk = "MEDIUM"

    else:
        overall_risk = "LOW"

    return NodeResult(

        data_updates={
            "aggregated_risk": overall_risk
        }
    )

# ------------------------------------------------
# Critic Node
# ------------------------------------------------

def critic_node(state):

    agent_summary = state["data"]["agent_summary"]

    credit = agent_summary["credit_risk"]
    fraud = agent_summary["fraud_risk"]
    sector = agent_summary["sector_risk"]

    # --- basic consistency checks
    if fraud == "HIGH":
        verdict = "REVIEW_REQUIRED"

    elif credit == "LOW" and sector == "HIGH":
        verdict = "REVIEW_REQUIRED"

    else:
        verdict = "CONSISTENT"

    return NodeResult(
        data_updates={
            "critic_verdict": verdict
        }
    )

# ------------------------------------------------
# Policy Decision Node
# ------------------------------------------------

def policy_node(state):

    financial_score = state["data"]["financial_score"]
    aggregated_risk = state["data"]["aggregated_risk"]
    critic_verdict = state["data"]["critic_verdict"]

    if critic_verdict == "REVIEW_REQUIRED":
        decision = "REVIEW"

    elif aggregated_risk == "HIGH":
        decision = "REJECT"

    elif financial_score >= 80 and aggregated_risk == "LOW":
        decision = "APPROVE"

    else:
        decision = "REVIEW"

    return NodeResult(
        data_updates={
            "final_decision": decision
        }
    )

# ------------------------------------------------
# Final Decision Node
# ------------------------------------------------

def final_decision_node(state):

    application_id = state["data"]["application"]["loan_id"]
    decision = state["data"]["final_decision"]

    print(f"Loan Application {application_id} → {decision}")

    # mark workflow finished
    state["status"] = "COMPLETED"

    return NodeResult(
        data_updates={}
    )

# ------------------------------------------------
# Graph Validation
# ------------------------------------------------

def validate_graph(graph_config, node_registry):

    # --- check START node
    if "START" not in graph_config:
        raise ValueError("Graph must contain START node")

    # --- check node handlers exist
    for node in graph_config:

        if node == "START":
            continue

        if node not in node_registry:
            raise ValueError(f"Node '{node}' missing in NODE_REGISTRY")

    # --- check transitions are valid
    for node, config in graph_config.items():

        for next_node in config["next"]:

            if next_node not in graph_config:
                raise ValueError(
                    f"Invalid transition: {node} → {next_node}"
                )

    # --- check terminal node exists
    terminal_nodes = [
        node for node, config in graph_config.items()
        if len(config["next"]) == 0
    ]

    if not terminal_nodes:
        raise ValueError("Graph must contain at least one terminal node")

    print("Graph validation successful")

