# ================================
# Workflow State Updater
# ================================

def apply_node_result(state, result):
    """Merges a NodeResult's data dict into the shared workflow state."""
    if result and result.data:

        state.update(result.data)