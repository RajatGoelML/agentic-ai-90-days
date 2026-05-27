# ================================
# Signal Processor — News Fetch & Classification
# ================================

from reversal_strategy.tools.data_fetchers import fetch_latest_stock_news
from reversal_strategy.tools.classifiers import classify_news_headlines
from reversal_strategy.processors.base_processor import SignalProcessor


class NewsProcessor(SignalProcessor):
    """
    Fetches the latest news headlines for a stock and classifies
    them into bullish, bearish, and net sentiment buckets.

    This is the only processor that makes external network calls.
    Isolating it here ensures that a news fetch timeout or failure
    does not affect valuation, profitability, or technical signals.
    """

    name = "news"

    def process(self, payload):

        latest_news = fetch_latest_stock_news(
            stock_symbol=payload.symbol
        )
        payload.latest_news = latest_news

        payload.news_sentiment = classify_news_headlines(
            symbol=payload.symbol,
            sector=payload.sector or "",
            headlines=latest_news
        )

        return payload

