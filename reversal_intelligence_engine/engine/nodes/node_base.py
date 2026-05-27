# ================================
# Core Abstraction — Node + NodeResult
# ================================

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional

from engine.context.execution_context import ExecutionContext


@dataclass
class NodeResult:
    """
    Standardized output contract returned by every node.

    Carries execution status, the output data payload, optional
    routing hints, error details, and observability metadata.
    """

    success: bool = True
    data: Dict[str, Any] = field(default_factory=dict)
    next_nodes: List[str] = field(default_factory=list)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class Node:

    """
    Abstract base class for all workflow nodes.

    Subclasses implement run(context) containing the node's business logic.
    The execute(state) method wraps run() with context creation, timing,
    and execution logging.
    """

    def run(self, context):
        raise NotImplementedError

    def execute(self, state):

        context = ExecutionContext(state, self.__class__.__name__)

        print(f"\nRunning node: {context.node_name}")

        try:
            result = self.run(context)

            context.end_time = datetime.now()
            context.duration = (context.end_time - context.start_time).total_seconds()
            context.status = "SUCCESS"

        except Exception as e:
            context.end_time = datetime.now()
            context.duration = (context.end_time - context.start_time).total_seconds()
            context.status = "FAILED"
            print(f"[Node] Error in {context.node_name}: {e}")
            raise e

        if "execution_log" not in state:
            state["execution_log"] = []

        state["execution_log"].append({
            "node":       context.node_name,
            "start_time": str(context.start_time),
            "end_time":   str(context.end_time),
            "duration":   context.duration,
            "status":     context.status,
        })

        return result