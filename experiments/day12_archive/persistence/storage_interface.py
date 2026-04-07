"""
Storage Interface (Persistence Contract)

Purpose:
--------
Defines the abstract contract for all persistence backends.

This ensures that the controller and repository layers depend
on an interface rather than a concrete implementation.

Why This Exists:
----------------
To allow storage backend swapping without changing controller logic.
Future backends may include:
- SQLite
- Redis
- PostgreSQL
- Cloud storage

Required Capabilities:
----------------------
- Save workflow state
- Load workflow state
- Check workflow existence
- List stored workflows

Architectural Principle:
------------------------
Dependency inversion — high-level modules depend on abstractions,
not concrete implementations.

This file contains no storage logic.
It only defines the expected behavior of storage implementations.
"""

from abc import ABC,abstractmethod
from typing import Dict, List

class StorageInterface(ABC):
    """
    Abstract base class for storage backends.
    Any storage implementation (JSON, SQLite, Redis, etc.)
    must implement these methods.
    """
        
    @abstractmethod
    def save_state(self,workflow_id: str, state: Dict) -> None:
        """Persist workflow state."""
        pass       
    
    @abstractmethod
    def load_state(self,workflow_id: str) -> Dict:
        """Load workflow state."""
        pass

    @abstractmethod
    def exists(self,workflow_id: str) -> bool:
        """Check if workflow exists."""
        pass

    @abstractmethod
    def list_workflows(self) -> List[str]:
         """Return all stored workflow IDs."""
         pass