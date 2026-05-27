# ================================
# State Helper Utilities
# ================================

def get_data(state, key, default=None):
    """Safe read from workflow state. Returns default if key is absent."""
    return state.get(key, default)


def set_data(state, key, value):
    """Write a value into workflow state."""
    state[key] = value