"""
Workflow Repository (Persistence Coordinator)

Purpose:
--------
Acts as the abstraction layer between the controller and storage backend.

Responsibilities:
-----------------
- Generate new workflow IDs.
- Initialize new workflow state.
- Manage timestamps.
- Delegate persistence operations to storage backend.
- Ensure save-after-transition consistency.

Why This Layer Exists:
----------------------
To prevent the controller from:
- Managing file paths
- Generating IDs
- Handling timestamps
- Interacting directly with storage

This enforces separation of concerns and keeps the FSM controller clean.

Architectural Role:
-------------------
Repository Pattern implementation.

Controller → Repository → Storage Interface → Backend

This allows backend replacement without changing controller logic.
"""

import uuid
from datetime import datetime
from typing import Dict
from .storage_interface import StorageInterface

class WorkflowRepository:

    def __init__(self, storage: StorageInterface):
        self.storage = storage

    def create_new(self) -> Dict:
        workflow_id = f"workflow_{uuid.uuid4().hex}"

        now = datetime.utcnow().isoformat()

        state = {
            "workflow_id": workflow_id,
            "version": 1,
            "created_at": now,
            "last_updated": now,
            "current_state": "PLANNING",
            "retry_count": 0,
            "max_retries": 3,
            "data": {}            
        }

        self.storage.save_state(workflow_id, state)
        return state       

    def save(self, state: Dict) -> None:
        state["last_updated"] = datetime.utcnow().isoformat()
        self.storage.save_state(state["workflow_id"], state)

    def load(self, workflow_id: str) -> Dict:
        return self.storage.load_state(workflow_id)

    def exists(self, workflow_id: str) -> bool:
        return self.storage.exists(workflow_id)     