from core.engine.scheduler import run_workflow
from core.graph.validation import validate_graph
from core.graph.dependency_map import build_dependency_map

from workflow.graph.graph_config import GRAPH_CONFIG
from workflow.nodes.node_registry import NODE_REGISTRY
from workflow.state.workflow_state import state


DEPENDENCY_MAP = build_dependency_map(GRAPH_CONFIG)

validate_graph(GRAPH_CONFIG, NODE_REGISTRY)

run_workflow(state, GRAPH_CONFIG, NODE_REGISTRY, DEPENDENCY_MAP)