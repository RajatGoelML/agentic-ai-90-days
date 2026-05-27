# ================================
# Workflow State Model
# ================================


def initialize_state():

    """
    Creates and returns the initial shared workflow state dict.

    All node outputs are merged into this dict by the executor.
    The completed_nodes set drives the scheduler's dependency resolution.
    """

    return {
        "ingested_stocks":       [],
        "enriched_stocks":       [],
        "signal_payloads":       [],
        "final_recommendations": [],
        "completed_nodes":       set(),
        "execution_log":         [],
    }