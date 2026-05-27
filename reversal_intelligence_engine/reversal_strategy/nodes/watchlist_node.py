import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from engine.nodes.node_base import (
    Node,
    NodeResult
)

from reversal_strategy.agents.llm_client import token_tracker


class WatchlistNode(Node):

    """
    Persists final investment recommendations to disk and
    produces a structured audit record for each workflow run.

    Writes two files on each run:
    - A dated, incrementally numbered file (e.g. 22_May_26_run_001.json)
    - run_latest.json — always reflects the most recent run
    """

    # Absolute path anchored to this file — works regardless of CWD
    # resolves to: reversal_intelligence_engine/data/outputs/watchlist/
    OUTPUT_DIR = os.path.join(
        os.path.dirname(  # nodes/
        os.path.dirname(  # reversal_strategy/
        os.path.dirname(  # reversal_intelligence_engine/
        os.path.abspath(__file__)))),
        "data", "outputs", "watchlist"
    )

    def run(self, context):

        recommendations = context.state.get(
            "final_recommendations",
            []
        )

        # =====================================================
        # Create output directory
        # =====================================================

        Path(self.OUTPUT_DIR).mkdir(
            parents=True,
            exist_ok=True
        )

        # =====================================================
        # Date + sequential run number -> human-readable filename
        # =====================================================

        now        = datetime.now(timezone.utc)
        date_str   = now.strftime("%d_%b_%y")     # e.g. 22_May_26

        # Derive next run number from the highest existing run number
        # (not file count — avoids gaps when files from other dates exist)
        import re as _re
        existing = list(Path(self.OUTPUT_DIR).glob("*_run_*.json"))
        if existing:
            nums = [int(m.group(1)) for f in existing
                    if (m := _re.search(r'_run_(\d+)\.json$', f.name))]
            run_number = (max(nums) + 1) if nums else 1
        else:
            run_number = 1

        output_file  = f"{self.OUTPUT_DIR}/{date_str}_run_{run_number:03d}.json"
        latest_file  = f"{self.OUTPUT_DIR}/run_latest.json"

        # =====================================================
        # Persist recommendations + token cost
        # =====================================================

        cost_summary = token_tracker.get_summary()

        output_payload = {
            "generated_at": now.isoformat(),
            "run_number": run_number,
            "stocks_analyzed": len(recommendations),
            "token_usage": {
                "model": cost_summary.get("model_used", "N/A"),
                "total_llm_calls": cost_summary.get("total_llm_calls", 0),
                "input_tokens": cost_summary.get("total_input_tokens", 0),
                "output_tokens": cost_summary.get("total_output_tokens", 0),
                "total_tokens": cost_summary.get("total_tokens", 0),
                "estimated_cost_usd": cost_summary.get("total_cost_usd", 0),
            },
            "recommendations": recommendations,
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_payload, f, indent=4, ensure_ascii=False)

        # run_latest.json — always reflects the current run
        shutil.copy(output_file, latest_file)

        print(
            f"\nWatchlist saved : {output_file}"
            f"\nLatest          : {latest_file}"
        )

        # =====================================================
        # Console summary — reversal classification
        # =====================================================

        DECISION_EMOJI = {
            "STRONG_BUY":               "🟢",
            "EARLY_REVERSAL_CANDIDATE": "🔵",
            "GOOD_COMPANY_BAD_PRICE":   "🟡",
            "HIGH_RISK_REVERSAL":       "🟠",
            "AVOID_STRUCTURALLY_WEAK":  "🔴",
        }

        for rec in recommendations:
            symbol     = rec.get("symbol", "?")
            decision   = rec.get("decision", "?")
            confidence = rec.get("confidence", 0)
            news       = rec.get("latest_news", [])
            news_count = len(news)
            label      = DECISION_EMOJI.get(decision, " ")
            rr         = rec.get("risk_reward", {})
            rq         = rec.get("reversal_quality", "")

            print(f"  {label} {symbol:<18} {decision}")
            print(
                f"     Confidence: {confidence}  |  "
                f"News: {news_count}  |  "
                f"R/R: {rr.get('risk_reward_view', 'N/A')}"
            )
            if rq:
                print(f"     Reversal: {rq}")
            for headline in news:
                print(f"     - {headline}")

        # =====================================================
        # Final workflow contract
        # =====================================================

        return NodeResult(
            success=True,
            data={
                "watchlist_output_file": output_file,
                "watchlist_latest_file": latest_file,
                "final_output":          recommendations,
            },
            metadata={
                "recommendation_count": len(recommendations),
                "run_number":           run_number,
            }
        )