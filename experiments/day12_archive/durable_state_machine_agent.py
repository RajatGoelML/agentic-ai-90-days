"""
Durable State Machine Agent (Day 12)

Purpose:
--------
This module upgrades the Day 11 FSM-based agent into a durable workflow engine
by integrating persistent state storage.

Key Responsibilities:
---------------------
- Initialize or resume workflows.
- Drive the deterministic FSM execution loop.
- Enforce valid state transitions.
- Persist state after every transition.
- Enable crash recovery and resumability.

Architectural Role:
-------------------
This file acts as the Controller layer in the architecture.
It orchestrates Planner, Executor, and Critic layers but does not
contain storage logic directly.

Persistence is handled via the WorkflowRepository abstraction,
ensuring clean separation of concerns.

Durability Guarantees:
----------------------
- Each workflow has a unique workflow_id.
- State is saved after every valid transition.
- Execution can resume from disk after failure or crash.
- No reliance on conversation history as source-of-truth.

This module transforms the system from:
    Ephemeral deterministic agent
into:
    Durable workflow engine.
"""

"""
Durable State Machine Agent (Day 12)

Upgrades FSM-based agent to support persistent state.
Allows workflow resumption after crash.
"""

import os
from persistence.json_storage import JSONStorage
from persistence.workflow_repository import WorkflowRepository


# Initialize persistence layer
BASE_PATH = os.path.join(os.path.dirname(__file__), "workflows")
storage = JSONStorage(BASE_PATH)
repository = WorkflowRepository(storage)


VALID_TRANSITIONS = {
    "PLANNING": ["EXECUTING", "VERIFYING"],
    "EXECUTING": ["PLANNING"],
    "VERIFYING": ["COMPLETED", "RETRYING"],
    "RETRYING": ["PLANNING"],
}


def initialize_or_resume(workflow_id=None):
    if workflow_id and repository.exists(workflow_id):
        print(f"Resuming workflow: {workflow_id}")
        return repository.load(workflow_id)

    print("Creating new workflow...")
    return repository.create_new()


def transition_state(state, next_state):
    current = state["current_state"]

    if next_state not in VALID_TRANSITIONS.get(current, []):
        raise ValueError(f"Invalid transition: {current} → {next_state}")

    state["current_state"] = next_state

    # Persist immediately after transition
    repository.save(state)


def run_fsm_loop(state):
    while state["current_state"] != "COMPLETED":
        print("Current State:", state["current_state"])

        if state["current_state"] == "PLANNING":
            transition_state(state, "EXECUTING")

        elif state["current_state"] == "EXECUTING":
            transition_state(state, "VERIFYING")

        elif state["current_state"] == "VERIFYING":
            transition_state(state, "COMPLETED")


if __name__ == "__main__":
    workflow_id_input = input("Enter workflow_id to resume (or press Enter): ").strip()
    workflow_id_input = workflow_id_input if workflow_id_input else None

    state = initialize_or_resume(workflow_id_input)
    run_fsm_loop(state)

    print("Workflow completed:", state["workflow_id"])