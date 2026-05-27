# DEPRECATED -- domain/dto/signal_payload.py moved to domain/models/signal_payload.py
import warnings
warnings.warn(
    "domain.dto.signal_payload is deprecated. Import from domain.models.signal_payload instead.",
    DeprecationWarning, stacklevel=2,
)
from domain.models.signal_payload import SignalPayload  # noqa: F401, E402
__all__ = ["SignalPayload"]
