from core.engine.scheduler import run_workflow
from core.graph.validation import validate_graph
from core.graph.dependency_map import build_dependency_map
# from core.graph.visualizer import visualize_graph


from workflow.graph.graph_config import GRAPH_CONFIG
from workflow.nodes.node_registry import NODE_REGISTRY
from workflow.state.workflow_state import state


DEPENDENCY_MAP = build_dependency_map(GRAPH_CONFIG)

validate_graph(GRAPH_CONFIG, NODE_REGISTRY)

# # generate workflow graph
# graph = visualize_graph(GRAPH_CONFIG)
# graph.render("loan_workflow_graph", format="png", view=True)

run_workflow(state, GRAPH_CONFIG, NODE_REGISTRY, DEPENDENCY_MAP)