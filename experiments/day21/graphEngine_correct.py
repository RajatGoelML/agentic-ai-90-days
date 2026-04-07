import time

# ---- State ------------

state = {
    "current_node": "START",
    "history": [],
    "data": {},
    "status": "RUNNING",
    "step_count": 0,
    "max_steps": 20,
    "retry_counts": {}
}


# ---- Error Class ------------

class WorkflowError(Exception):

    def __init__(self, message, error_type):
        super().__init__(message)
        self.error_type = error_type


# ---- Node Definition ------------

class Node:

    def __init__(self, name, handler, next_nodes, max_retries=0,timeout=5):
        self.name = name
        self.handler = handler
        self.next_nodes = next_nodes
        self.max_retries = max_retries
        self.timeout = timeout


# ---- Node Handlers ------------

def start_handler(state):
    print("Executing START")
    return "UNSTABLE"


def unstable_handler(state):
    print("Executing UNSTABLE NODE")

    if state["retry_counts"].get("UNSTABLE", 0) < 1:
        raise WorkflowError("Simulated failure", "TRANSIENT")

    return "END"


def end_handler(state):
    print("Executing END")
    state["status"] = "COMPLETED"
    return "END"


# ---- Node Registry ------------

nodes = {
    "START": Node("START", start_handler, ["UNSTABLE"]),
    "UNSTABLE": Node("UNSTABLE", unstable_handler, ["END"], max_retries=2,timeout=10),
    "END": Node("END", end_handler, [])
}


# ---- Graph Engine ------------

class GraphEngine:

    def __init__(self, nodes):
        self.nodes = nodes


    def run(self, state):

        while state["status"] == "RUNNING":

            state["step_count"] += 1

            if state["step_count"] > state["max_steps"]:
                print("Max steps exceeded")
                state["status"] = "FAILED"
                break


            current_name = state["current_node"]
            state["history"].append(current_name)

            current_node = self.nodes.get(current_name)

            if not current_node:
                state["status"] = "FAILED"
                break


            if current_name not in state["retry_counts"]:
                state["retry_counts"][current_name] = 0


            try:
                start_time = time.time()

                next_node = current_node.handler(state)
                duration = time.time() - start_time

                if duration > current_node.timeout:
                    raise WorkflowError(
                    f"Node {current_name} exceeded timeout ({duration:.2f}s)",
                    "TRANSIENT"
                    )

            except WorkflowError as e:

                if e.error_type == "TRANSIENT":

                    state["retry_counts"][current_name] += 1

                    if state["retry_counts"][current_name] <= current_node.max_retries:
                        print("Retrying node:", current_name)
                        continue

                state["status"] = "FAILED"
                break


            if next_node not in current_node.next_nodes:
                print("Illegal transition")
                state["status"] = "FAILED"
                break


            state["current_node"] = next_node


# ---- Run Engine ------------

engine = GraphEngine(nodes)
engine.run(state)

print("\nFinal State:", state)