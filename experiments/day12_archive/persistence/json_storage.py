"""
JSON Storage Backend (Concrete Implementation)

Purpose:
--------
Implements the StorageInterface using JSON files on disk.

Storage Strategy:
-----------------
- One file per workflow.
- File name = <workflow_id>.json
- Atomic writes via temporary file replacement.
- Automatic directory creation.

Why JSON (Day 12 Phase):
------------------------
- Simple
- Transparent
- Human-readable
- Easy debugging
- No external dependencies

Production Considerations:
--------------------------
- Atomic file replacement prevents partial writes.
- Deterministic serialization.
- Strictly handles state dictionary only.

Limitations (Known & Intentional):
----------------------------------
- Not concurrent-safe.
- Not optimized for scale.
- No indexing or querying support.

This backend is designed for architectural validation before
introducing database-backed persistence in later phases.
"""

import os
import json
from typing import Dict, List
from .storage_interface import StorageInterface

class JSONStorage(StorageInterface):
    """
    Stores workflow state as JSON files on disk.
    """

    def __init__(self,base_path: str):
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)

    def _get_file_path(self,workflow_id: str) -> str:
        return os.path.join(self.base_path, f"{workflow_id}.json")   


    def save_state(self, workflow_id: str, state: Dict) -> None:
        file_path = self._get_file_path(workflow_id)
        temp_path = file_path + ".tmp"

        # Write to temp file first
        with open(temp_path, "w") as f:
            json.dump(state, f, indent=2)

        # Atomic replace
        os.replace(temp_path, file_path)


    def load_state(self, workflow_id: str) -> Dict:
        file_path = self._get_file_path(workflow_id)

        with open(file_path, "r") as f:
            return json.load(f)


    def exists(self, workflow_id: str) -> bool:
        return os.path.exists(self._get_file_path(workflow_id))


    def list_workflows(self) -> List[str]:
        return [
            f.replace(".json", "")
            for f in os.listdir(self.base_path)
            if f.endswith(".json")
        ]     