"""Backward-compatible shim — re-exports from the etf_iv package."""

from etf_iv.data_collection import (  # noqa: F401
    get_etf_holdings,
    get_options_chain,
    get_price_history,
)
from etf_iv.sentiment import (  # noqa: F401
    get_etf_headlines,
    get_sentiment_score,
)
from etf_iv.data import (  # noqa: F401
    load_earnings_dates,
    load_etf_holdings,
    load_etf_sentiment,
    load_options_chain,
    load_options_filtered,
    load_price_history,
)
