"""Pre-collected ETF dataset bundled with the etf_iv package.

Loader functions return pandas DataFrames from the CSV files shipped
inside this package.  No network access or API keys required.

To collect fresh data instead, use the live collection functions in
:mod:`etf_iv.data_collection` and :mod:`etf_iv.sentiment`.
"""

from __future__ import annotations

from importlib.resources import files

import pandas as pd

_DATA = files("etf_iv.data")


def _read(name: str, **kwargs) -> pd.DataFrame:
    """Read a bundled CSV by filename."""
    with (_DATA / name).open() as f:
        return pd.read_csv(f, **kwargs)


def load_price_history() -> pd.DataFrame:
    """Load bundled 6-month price history for VOO, QQQ, ARKQ, BOTZ.

    Returns
    -------
    pd.DataFrame
        Columns: ticker, Date, Open, High, Low, Close, Volume.
    """
    return _read("price_history.csv", parse_dates=["Date"])


def load_options_chain() -> pd.DataFrame:
    """Load bundled options chain (cleaned, all expirations).

    Returns
    -------
    pd.DataFrame
        Columns: ticker, expiration, contractType, strike, bid, ask,
        volume, openInterest, impliedVolatility.
    """
    return _read("options_chain.csv", parse_dates=["expiration"])


def load_options_filtered() -> pd.DataFrame:
    """Load bundled liquidity-filtered options with spot and moneyness.

    Returns
    -------
    pd.DataFrame
        Filtered options (volume >= 1, OI >= 10) with spot_price and
        moneyness columns.
    """
    return _read("options_filtered.csv", parse_dates=["expiration"])


def load_etf_holdings() -> pd.DataFrame:
    """Load bundled ETF top holdings scraped from stockanalysis.com.

    Returns
    -------
    pd.DataFrame
        Columns: holding_ticker, company_name, weight_pct, etf_ticker.
    """
    return _read("etf_holdings.csv")


def load_earnings_dates() -> pd.DataFrame:
    """Load bundled earnings dates for ETF holdings.

    Returns
    -------
    pd.DataFrame
        Columns: holding_ticker, etf_ticker, earnings_date.
    """
    return _read("earnings_dates.csv", parse_dates=["earnings_date"])


def load_etf_sentiment() -> pd.DataFrame:
    """Load bundled ETF news sentiment scores.

    Returns
    -------
    pd.DataFrame
        Columns: etf_ticker, num_articles, sentiment_score, sentiment_label.
    """
    return _read("etf_sentiment.csv")
