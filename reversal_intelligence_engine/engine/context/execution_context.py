# ================================
# Execution Context
# ================================

from datetime import datetime


class ExecutionContext:

    """
    Runtime container passed to each node during execution.

    Exposes shared workflow state and records execution metadata
    (start time, end time, duration, status) for observability.
    Nodes interact primarily with context.state.
    """

    def __init__(self, state, node_name):

        self.state = state
        self.node_name = node_name
        self.metadata = {}
        self.start_time = datetime.now()
        self.end_time = None
        self.duration = None

        self.status = "RUNNING"