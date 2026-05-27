# ================================
# Compatibility shim — api/main.py
# ================================
# After restructuring, the real app lives at infrastructure/api/main.py
# This shim lets the old command still work:
#   uvicorn api.main:app --reload
# ================================

from infrastructure.api.main import app  # noqa: F401

__all__ = ["app"]

