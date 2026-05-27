# DEPRECATED -- domain/dto/stock_dto.py moved to domain/models/stock_dto.py
import warnings
warnings.warn(
    "domain.dto.stock_dto is deprecated. Import from domain.models.stock_dto instead.",
    DeprecationWarning, stacklevel=2,
)
from domain.models.stock_dto import StockDTO  # noqa: F401, E402
__all__ = ["StockDTO"]
