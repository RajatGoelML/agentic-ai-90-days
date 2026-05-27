from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class StockDTO:
    symbol: str
    price: float = 0.0
    volume: float = 0.0
    sector: str = ""
    industry: str = ""
    category: str = ""
    source_table: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)