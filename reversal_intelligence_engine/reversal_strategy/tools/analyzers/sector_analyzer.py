"""
Deterministic relative valuation analysis.

Compares a company's PE ratio against the sector median PE to produce
sector-aware valuation intelligence. Uses no LLM calls and makes no
network requests — pure deterministic logic against a reference table.
"""

from typing import Optional
import os

from reversal_strategy.tools.base_tool import BaseTool, ToolResult


# =========================================================
# Sector PE Reference — loaded from config/sector_pe.yaml
# =========================================================
# WHY YAML: sector analysts can update PE bands without
# touching Python code. Zero deployment needed for PE updates.
# =========================================================

def _load_sector_pe_config() -> tuple[dict, dict]:
    """Load sector PE bands from config file. Falls back to defaults if unavailable."""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "infrastructure", "config", "sector_pe.yaml"
    )
    try:
        import yaml
        with open(config_path) as f:
            data = yaml.safe_load(f)
        sectors  = data.get("sectors", {})
        default  = data.get("default", {"median": 20, "low": 12, "high": 30})
        return sectors, default
    except Exception as e:
        print(f"⚠️ Could not load sector_pe.yaml ({e}) — using built-in defaults")
        return _BUILTIN_SECTOR_PE, {"median": 20, "low": 12, "high": 30}


# Hardcoded fallback — used only if YAML is missing
_BUILTIN_SECTOR_PE = {
    "Financial Services": {"median": 16, "low": 10, "high": 22},
    "Banking":            {"median": 14, "low": 8,  "high": 20},
    "Technology":         {"median": 30, "low": 20, "high": 45},
    "Information Technology": {"median": 28, "low": 18, "high": 42},
    "Consumer Cyclical":  {"median": 28, "low": 18, "high": 40},
    "Consumer Defensive": {"median": 35, "low": 25, "high": 50},
    "Healthcare":         {"median": 30, "low": 20, "high": 45},
    "Industrials":        {"median": 22, "low": 14, "high": 32},
    "Basic Materials":    {"median": 18, "low": 10, "high": 28},
    "Chemicals":          {"median": 22, "low": 14, "high": 35},
    "Energy":             {"median": 12, "low": 6,  "high": 18},
    "Utilities":          {"median": 15, "low": 10, "high": 22},
    "Real Estate":        {"median": 18, "low": 10, "high": 28},
    "Communication Services": {"median": 20, "low": 12, "high": 30},
}

SECTOR_PE_REFERENCE, DEFAULT_SECTOR_PE = _load_sector_pe_config()


# =========================================================
# Module-level function (used directly by financial_signal_node)
# =========================================================

def compute_relative_valuation(
    pe_ratio: Optional[float],
    forward_pe: Optional[float],
    sector: Optional[str]
) -> dict:
    """
    Compares company PE against sector median PE range.

    Returns compact relative valuation intelligence:
    {
        "company_pe":            27,
        "sector_median_pe":      24,
        "sector_pe_band":        "18-40",
        "peer_position":         "SLIGHT_PREMIUM",
        "forward_pe_compression": True,
        "valuation_view":        "FAIR_TO_SLIGHTLY_EXPENSIVE"
    }
    """
    if pe_ratio is None:
        return {
            "company_pe":     None,
            "sector_median_pe": None,
            "peer_position":  "UNKNOWN",
            "valuation_view": "INSUFFICIENT_DATA",
        }

    ref    = SECTOR_PE_REFERENCE.get(sector or "", DEFAULT_SECTOR_PE)
    median = ref["median"]
    low    = ref["low"]
    high   = ref["high"]

    ratio = pe_ratio / median if median else 1.0

    if ratio <= 0.75:   peer_position = "DEEP_DISCOUNT"
    elif ratio <= 0.90: peer_position = "DISCOUNT"
    elif ratio <= 1.10: peer_position = "FAIR_VALUE"
    elif ratio <= 1.25: peer_position = "SLIGHT_PREMIUM"
    else:               peer_position = "PREMIUM"

    if pe_ratio <= low:      valuation_view = "UNDERVALUED"
    elif pe_ratio <= median: valuation_view = "ATTRACTIVE"
    elif pe_ratio <= high:   valuation_view = "FAIR_TO_SLIGHTLY_EXPENSIVE"
    else:                    valuation_view = "EXPENSIVE_VS_SECTOR"

    forward_pe_compression = None
    if forward_pe is not None and pe_ratio > 0:
        forward_pe_compression = forward_pe < pe_ratio * 0.85

    return {
        "company_pe":             round(pe_ratio, 1),
        "sector_median_pe":       median,
        "sector_pe_band":         f"{low}-{high}",
        "peer_position":          peer_position,
        "forward_pe_compression": forward_pe_compression,
        "valuation_view":         valuation_view,
    }


# =========================================================
# BaseTool wrapper — for registry + structured ToolResult
# =========================================================

class SectorAnalyzerTool(BaseTool):
    """
    Computes sector-relative PE valuation for a stock.

    input_data keys:
        pe_ratio   (float | None)
        forward_pe (float | None)
        sector     (str   | None)

    Returns ToolResult.data = relative valuation dict.
    """

    name = "sector_analyzer"
    description = (
        "Computes sector-relative PE valuation (UNDERVALUED / ATTRACTIVE / "
        "FAIR_TO_SLIGHTLY_EXPENSIVE / EXPENSIVE_VS_SECTOR) by comparing the "
        "company's PE against a sector median PE reference table. "
        "No LLM calls. No network calls."
    )

    def run(self, input_data: dict) -> ToolResult:
        result = compute_relative_valuation(
            pe_ratio   = input_data.get("pe_ratio"),
            forward_pe = input_data.get("forward_pe"),
            sector     = input_data.get("sector"),
        )
        return ToolResult(
            success=True,
            data=result,
            source=self.name,
        )

