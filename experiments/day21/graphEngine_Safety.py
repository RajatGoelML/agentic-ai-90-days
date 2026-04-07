
#---- State------------

state = {
    "current_node":"START",
    "history": [],
    "data": {},
    "status": "RUNNING",
    "step_count":0,
    "max_steps": 20,
    "retry_counts":{}
}


def unstable_handler(state):
    print("Executing UNSTABLE NODE")

    if state["retry_counts"].get("UNSTABLE", 0) < 1:
        raise Exception("Simulated failure")

    return "END"

class WorkflowError(Exception):
    """
    Custom workflow error used to classify failures.
    """

    def __init__(self, message, error_type):
        super().__init__(message)
        self.error_type = error_type


class Node:

    def __init__(self, name, handler, next_nodes, max_retries=0):
        self.name = name
        self.handler = handler
        self.next_nodes = next_nodes
        self.max_retries = max_retries

def run(self,state):

    # while state["current_node"] == "RUNNING"
    # if currnet steps > max steps then fail
    # extract name and then append in history
    # get node object from nodes (nodes is a dictionory and we are passing key to get value which is a objct )
    # if no current node object then fail it
    # if current name not in retry counts then initialise it with zero
    # in try block execute the handler and fetch next node
    # except for exception
    # if e.errotype is transient then retry counter +1  then retry it else fail it 
    # check for illegal transition to incorrect state
    # check next node not in 
    # 

    while state["status"] == "RUNNING":

        # -------- Step Guard --------
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

            next_node = current_node.handler(state)


        except WorkflowError as e:

            # Retry only transient errors
            if e.error_type == "TRANSIENT":

                state["retry_counts"][current_name] += 1

                if state["retry_counts"][current_name] <= current_node.max_retries:
                    print(f"Retrying {current_name}")
                    continue

            print(f"Node {current_name} failed: {str(e)}")
            state["status"] = "FAILED"
            break


        except Exception as e:

            print("Unhandled exception:", str(e))
            state["status"] = "FAILED"
            break


        # Validate transition
        if next_node not in current_node.next_nodes:
            print("Illegal transition")
            state["status"] = "FAILED"
            break


        state["current_node"] = next_node              