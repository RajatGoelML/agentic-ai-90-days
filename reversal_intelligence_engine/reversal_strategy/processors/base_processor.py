# ================================
# Signal Processor — Base Contract
# ================================

from domain.models.signal_payload import SignalPayload


class SignalProcessor:
    """
    Abstract base class for all signal processors in the pipeline.

    Each subclass owns exactly one concern and implements process(),
    which receives a SignalPayload, enriches it, and returns it.
    Failures in one processor do not propagate to others.
    """

    name: str = "base"

    def process(self, payload: SignalPayload) -> SignalPayload:
        raise NotImplementedError(
            f"SignalProcessor subclass '{self.__class__.__name__}' "
            f"must implement process()"
        )
