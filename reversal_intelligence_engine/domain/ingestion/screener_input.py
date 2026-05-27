# DEPRECATED -- moved to infrastructure/adapters/ingestion/screener_input.py
import warnings
warnings.warn(
    "domain.ingestion.screener_input is deprecated. "
    "Import from infrastructure.adapters.ingestion.screener_input instead.",
    DeprecationWarning, stacklevel=2,
)
from infrastructure.adapters.ingestion.screener_input import fetch_weekly_candidates  # noqa: F401, E402
__all__ = ["fetch_weekly_candidates"]
