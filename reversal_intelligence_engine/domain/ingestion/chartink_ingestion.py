# DEPRECATED -- moved to infrastructure/adapters/ingestion/chartink_ingestion.py
import warnings
warnings.warn(
    "domain.ingestion.chartink_ingestion is deprecated. "
    "Import from infrastructure.adapters.ingestion.chartink_ingestion instead.",
    DeprecationWarning, stacklevel=2,
)
from infrastructure.adapters.ingestion.chartink_ingestion import load_from_chartink  # noqa: F401, E402
__all__ = ["load_from_chartink"]
