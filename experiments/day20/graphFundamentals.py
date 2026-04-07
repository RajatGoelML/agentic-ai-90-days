
state = {
    "current_node": "START",
    "data": {},
    "history": [],
    "status": "RUNNING"
}

GRAPH = {
    "START": ["LOAD"],
    "LOAD": ["PROCESS"],
    "PROCESS": ["END"],
    "END": []
}

def run_graph(state, graph):

    print("hello")

    while state["status"] == "RUNNING":

        current_node = state["current_node"]

        state["history"].append(current_node)

        # Terminal handling
        if current_node == "END":
            state["status"] = "COMPLETED"
            break

        allowed_next = graph.get(current_node, [])

        # Dead-end detection (non-terminal node)
        if not allowed_next:
            state["status"] = "FAILED"
            break

        # Select next node (static flow)
        next_node = allowed_next[0]

        # Transition validation (defensive)
        if next_node not in graph[current_node]:
            state["status"] = "FAILED"
            break

        # State mutation
        state["current_node"] = next_node

run_graph(state,GRAPH)
print(state)        

class Node:
    def __init__(self,name,handler,next_node):
        self.name = name
        self.handler = handler
        self.next_node = next_node

def start_handler(state):
    print("Executing START")
    return "LOAD"

def load_handler(state):
    print("Executing LOAD")
    return "PROCESS"

def process_handler(state):
    print("Executing PROCESS")
    return "END"

def end_handler(state):
    print("Executing END")
    state["status"] = "COMPLETED"
    return None

nodes = {
    "START": Node("START",start_handler,["LOAD"]),
    "LOAD": Node("LOAD",load_handler,["PROCESS"]),
    "PROCESS": Node("PROCESS",process_handler,["END"]),
    "END": Node("END",end_handler,[])
}        


def run_graph(state, nodes):

    while state["status"] == "RUNNING":

        current_name = state["current_node"]
        state["history"].append(current_name)

        current_node = nodes.get(current_name)

        if not current_node:
            state["status"] = "FAILED"
            break

        next_node = current_node.handler(state)

        if state["status"] == "COMPLETED":
            break

        if next_node not in current_node.next_nodes:
            state["status"] = "FAILED"
            break

        state["current_node"] = next_node

        def process_handler(state):
    print("Executing PROCESS")

    # simple condition
    if state["data"].get("value", 0) > 50:
        return "HIGH_PATH"
    else:
        return "LOW_PATH"
    
    GRAPH_NODES = {
    "START": Node("START", start_handler, ["LOAD"]),
    "LOAD": Node("LOAD", load_handler, ["PROCESS"]),
    "PROCESS": Node("PROCESS", process_handler, ["HIGH_PATH", "LOW_PATH"]),
    "HIGH_PATH": Node("HIGH_PATH", high_handler, ["END"]),
    "LOW_PATH": Node("LOW_PATH", low_handler, ["END"]),
    "END": Node("END", end_handler, [])
}
    
    def load_handler(state):
    print("Executing LOAD")

    state["data"]["value"] = 75   # Try 30 later

    return "PROCESS"