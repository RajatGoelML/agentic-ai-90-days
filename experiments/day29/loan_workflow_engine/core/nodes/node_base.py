



# ------------------------------------------------
# Node Abstraction
# ------------------------------------------------

class Node:

    def __init__(self, name, node_type, description, node_function, next_nodes=None, max_retry=0, timeout=0):

        # --- Node metadata
        self.name = name
        self.node_type = node_type
        self.description = description

        # --- Execution handler
        self.node_function = node_function

        # --- Safety controls
        self.max_retry = max_retry
        self.timeout = timeout


# ------------------------------------------------
# Node Execution Result
# ------------------------------------------------

class NodeResult:

    def __init__(self, next_nodes=None, data_updates=None):

        # --- State mutations returned by node
        self.data_updates = data_updates or {}