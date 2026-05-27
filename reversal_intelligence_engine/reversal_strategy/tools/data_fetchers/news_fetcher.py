"""
Fetches recent news headlines for a given stock symbol
via the SearchAPI Google News engine.

Requires the SEARCHAPI_API_KEY environment variable.
Returns an empty list gracefully if the key is absent or
if all retry attempts fail. No LLM calls are made.
"""

import os
import time
import requests
import urllib3

from dotenv import load_dotenv

from reversal_strategy.tools.base_tool import BaseTool, ToolResult

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

# =========================================================
# Constants
# =========================================================

_SEARCH_API_URL = "https://www.searchapi.io/api/v1/search"
_DEFAULT_LIMIT   = 5
_MAX_RETRIES     = 3


# =========================================================
# Module-level function (used directly by financial_signal_node)
# =========================================================

def fetch_latest_stock_news(
    stock_symbol: str,
    limit: int = _DEFAULT_LIMIT
) -> list:
    """
    Fetches recent news headlines for a stock.
    Returns a list of headline strings (empty list on failure).

    Retry policy: exponential backoff — 1s, 2s, 4s between attempts.
    """
    search_api_key = os.getenv("SEARCHAPI_API_KEY")
    if not search_api_key:
        print(f"[NewsFetcher] SEARCHAPI_API_KEY not set — skipping news for {stock_symbol}")
        return []

    params = {
        "engine":  "google_news",
        "q":       f"{stock_symbol} stock news",
        "api_key": search_api_key,
    }

    last_error = None

    for attempt in range(_MAX_RETRIES):
        try:
            response = requests.get(
                _SEARCH_API_URL,
                params=params,
                timeout=20,
                verify=False,
            )
            data = response.json()

            news_results = data.get(
                "news_results",
                data.get("organic_results", [])
            )

            headlines = [
                item["title"]
                for item in news_results[:limit]
                if item.get("title")
            ]

            if headlines:
                print(f"[NewsFetcher] Fetched {len(headlines)} headlines for {stock_symbol}")
            else:
                print(f"[NewsFetcher] No news results returned for {stock_symbol}")

            return headlines

        except Exception as e:
            last_error = e
            wait = 2 ** attempt
            print(f"[NewsFetcher] Attempt {attempt + 1}/{_MAX_RETRIES} failed for {stock_symbol}: {e}")
            if attempt < _MAX_RETRIES - 1:
                time.sleep(wait)

    print(f"[NewsFetcher] Exhausted {_MAX_RETRIES} retries for {stock_symbol}: {last_error}")
    return []


# =========================================================
# BaseTool wrapper — for registry + structured ToolResult
# =========================================================

class NewsFetcherTool(BaseTool):
    """
    Fetches live stock news headlines from SearchAPI.

    input_data keys:
        symbol (str)        — stock ticker, e.g. "KOTAKBANK.NS"
        limit  (int, opt)   — max headlines to return (default 5)

    Returns ToolResult.data = list[str] of headlines.
    """

    name = "news_fetcher"
    description = (
        "Fetches recent stock news headlines from Google News via SearchAPI. "
        "Returns a list of headline strings. No LLM calls."
    )

    def run(self, input_data: dict) -> ToolResult:
        symbol = input_data.get("symbol")
        limit  = input_data.get("limit", _DEFAULT_LIMIT)

        if not symbol:
            return ToolResult(
                success=False,
                data=[],
                error="symbol is required",
                source=self.name,
            )

        headlines = fetch_latest_stock_news(symbol, limit=limit)
        return ToolResult(
            success=True,
            data=headlines,
            source=self.name,
        )

