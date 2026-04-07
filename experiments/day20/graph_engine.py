
# -----------------------------
# Initial State
# -----------------------------

state = {
    "current_node": "START",
    "data": {},
    "history": [],
    "status": "RUNNING"
}

class Node:
    """
    Represents a single execution unit in the workflow graph.

    Each node:
    - Owns its execution logic (handler)
    - Declares allowed transitions (next_nodes)
    """

    def __init__(self, name, handler, next_nodes):
        self.name = name                    # Node identifier
        self.handler = handler              # Function executed when node runs
        self.next_nodes = next_nodes        # Allowed outgoing transitions


# -----------------------------
# Sample Node Handlers (Test Only)
# -----------------------------

def start_handler(state):
    print("Executing START")
    return "LOAD"

def load_handler(state):
    print("Executing LOAD")
    state["data"]["value"] = 75  # Inject test data
    return "PROCESS"

def process_handler(state):
    print("Executing PROCESS")

    # Conditional branching
    if state["data"].get("value", 0) > 50:
        return "HIGH_PATH"
    else:
        return "LOW_PATH"

def high_handler(state):
    print("Executing HIGH_PATH")
    return "END"

def low_handler(state):
    print("Executing LOW_PATH")
    return "END"

def end_handler(state):
    print("Executing END")
    state["status"] = "COMPLETED"
    return None  

# -----------------------------
# Node Registry
# -----------------------------

nodes = {
    "START": Node("START", start_handler, ["LOAD"]),
    "LOAD": Node("LOAD", load_handler, ["PROCESS"]),
    "PROCESS": Node("PROCESS", process_handler, ["HIGH_PATH", "LOW_PATH"]),
    "HIGH_PATH": Node("HIGH_PATH", high_handler, ["END"]),
    "LOW_PATH": Node("LOW_PATH", low_handler, ["END"]),
    "END": Node("END", end_handler, [])
}





class GraphEngine:
    """
    Core execution engine for static workflow graphs.

    Responsibilities:
    - Maintain execution lifecycle
    - Enforce transition contracts
    - Track execution history
    - Handle terminal conditions
    - Prevent illegal state movement
    """
    print("hello")

    def __init__(self, nodes):
        self.nodes = nodes  # Registry of Node objects

    def run(self, state):
        """
        Executes the workflow until completion or failure.
        """

        while state["status"] == "RUNNING":

            current_name = state["current_node"]

            # Track execution trace
            state["history"].append(current_name)

            # Fetch current node object
            current_node = self.nodes.get(current_name)

            if not current_node:
                state["status"] = "FAILED"
                break

            # Execute node logic
            next_node = current_node.handler(state)

            # If handler directly completes workflow
            if state["status"] == "COMPLETED":
                break

            # Validate transition contract
            if next_node not in current_node.next_nodes:
                state["status"] = "FAILED"
                break

            # Move execution pointer
            state["current_node"] = next_node
          

# -----------------------------
# Execute Engine
# -----------------------------

engine = GraphEngine(nodes)
engine.run(state)

print("\nFinal State:")
print(state)