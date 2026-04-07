
from core.nodes.node_base import Node

from workflow.agents.credit_agent import credit_agent_node
from workflow.agents.fraud_agent import fraud_agent_node
from workflow.agents.sector_agent import sector_agent_node
from workflow.agents.aggregator import aggregator_node
from workflow.agents.critic import critic_node

from workflow.nodes.deterministic_node import deterministic_scoring_node
from workflow.nodes.final_decision_node import final_decision_node
from workflow.nodes.policy_node import policy_node

# ------------------------------------------------
# Node Registry (stores Node objects)
# ------------------------------------------------

NODE_REGISTRY = {

    "DETERMINISTIC_SCORING": Node(
        name="DETERMINISTIC_SCORING",
        node_type="DETERMINISTIC",
        description="Compute financial risk signals",
        node_function=deterministic_scoring_node,
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