# ================================
# Workflow Timeline Builder
# ================================

def build_timeline(state):

    """
    Constructs a chronologically sorted execution timeline
    from the workflow's execution log.

    Each node contributes a NODE_START and NODE_END event.
    Used by the API's /timeline endpoint for observability.
    """

    timeline = []

    for log in state.get("execution_log", []):

        timeline.append({
            "time":   log["start_time"],
            "type":   "NODE_START",
            "node":   log["node"],
        })

        timeline.append({
            "time":     log["end_time"],
            "type":     "NODE_END",
            "node":     log["node"],
            "duration": log["duration"],
            "status":   log["status"],
        })

    timeline.sort(key=lambda x: x["time"])

    return timeline