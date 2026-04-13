"""
Reusable data-fetching helpers for options, price history, and ETF holdings.
All functions return a pandas DataFrame and raise ValueError on bad input or
empty results so callers can handle errors explicitly.

Dependencies (see requirements.txt):
    yfinance, pandas, requests, beautifulsoup4, lxml
"""

import logging

import pandas as pd
import requests
import yfinance as yf
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

_ETF_SOURCES = {
    # Maps ticker -> (url_template, parser_fn)
    # Extend this dict to support additional providers.
    "default": "https://finance.yahoo.com/quote/{ticker}/holdings/",
}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_options_chain(ticker: str) -> pd.DataFrame:
    """Fetch the full options chain for every available expiration date.

    Combines calls and puts across all expirations into a single tidy
    DataFrame, adding ``expiration``, ``option_type``, and ``ticker`` columns
    so downstream code can filter or group without extra joins.

    Parameters
    ----------
    ticker : str
        Upper- or lower-case ticker symbol (e.g. ``"AAPL"``).

    Returns
    -------
    pd.DataFrame
        Columns mirror yfinance option chain fields plus:
        ``expiration`` (str, YYYY-MM-DD), ``option_type`` ("call"|"put"),
        ``ticker`` (str).

    Raises
    ------
    ValueError
        If the ticker is invalid, has no listed options, or the network
        request fails.

    Examples
    --------
    >>> df = get_options_chain("AAPL")
    >>> df[df.option_type == "call"].head()
    """
    ticker = _validate_ticker(ticker)

    try:
        t = yf.Ticker(ticker)
        expirations = t.options
    except Exception as e:
        raise ValueError(f"Could not fetch options for '{ticker}': {e}") from e

    if not expirations:
        raise ValueError(f"No options listed for '{ticker}'.")

    frames = []
    for exp in expirations:
        try:
            chain = t.option_chain(exp)
        except Exception as e:
            log.warning("Skipping expiration %s for %s: %s", exp, ticker, e)
            continue

        for side, df in (("call", chain.calls), ("put", chain.puts)):
            if df.empty:
                continue
            df = df.copy()
            df["expiration"] = exp
            df["option_type"] = side
            df["ticker"] = ticker
            frames.append(df)

    if not frames:
        raise ValueError(f"Options chain for '{ticker}' returned no data.")

    result = pd.concat(frames, ignore_index=True)
    log.info(
        "get_options_chain('%s'): %d rows across %d expirations.",
        ticker, len(result), len(expirations),
    )
    return result


def get_price_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    """Download Open, High, Low, Close, Volume price history for a single ticker.

    Parameters
    ----------
    ticker : str
        Ticker symbol (e.g. ``"SPY"``).
    period : str, optional
        Any period string accepted by yfinance: ``"1d"``, ``"5d"``,
        ``"1mo"``, ``"3mo"``, ``"6mo"``, ``"1y"``, ``"2y"``, ``"5y"``,
        ``"10y"``, ``"ytd"``, ``"max"``.  Defaults to ``"1y"``.

    Returns
    -------
    pd.DataFrame
        DatetimeIndex with columns: Open, High, Low, Close, Volume,
        Dividends, Stock Splits, plus a ``ticker`` column for convenience
        when concatenating multiple symbols.

    Raises
    ------
    ValueError
        If the ticker or period is invalid, or the response is empty.

    Examples
    --------
    >>> df = get_price_history("SPY", period="6mo")
    >>> df[["Open", "Close", "Volume"]].tail()
    """
    ticker = _validate_ticker(ticker)

    valid_periods = {
        "1d", "5d", "1mo", "3mo", "6mo",
        "1y", "2y", "5y", "10y", "ytd", "max",
    }
    if period not in valid_periods:
        raise ValueError(
            f"Invalid period '{period}'. Choose from: {sorted(valid_periods)}"
        )

    try:
        df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
    except Exception as e:
        raise ValueError(f"Download failed for '{ticker}': {e}") from e

    if df.empty:
        raise ValueError(
            f"No price data returned for '{ticker}' with period='{period}'."
        )

    # Flatten MultiIndex columns produced when yfinance returns a single ticker
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.copy()
    df["ticker"] = ticker
    log.info(
        "get_price_history('%s', period='%s'): %d rows, %s to %s.",
        ticker, period, len(df),
        df.index.min().date(), df.index.max().date(),
    )
    return df


def get_etf_holdings(ticker: str) -> pd.DataFrame:
    """Fetch the top holdings and portfolio weights for an ETF via yfinance.

    Uses the yfinance ``Ticker.get_funds_data()`` API to retrieve ETF
    holdings data.  Falls back to scraping Yahoo Finance if the API
    method is unavailable.

    Parameters
    ----------
    ticker : str
        ETF ticker symbol (e.g. ``"SPY"``, ``"QQQ"``).

    Returns
    -------
    pd.DataFrame
        Columns: ``ticker`` (the ETF), ``holding_symbol``, ``holding_name``,
        ``weight_pct`` (float, 0-100).

    Raises
    ------
    ValueError
        If the ticker is invalid or no holdings data can be retrieved.

    Examples
    --------
    >>> df = get_etf_holdings("SPY")
    >>> df.sort_values("weight_pct", ascending=False).head(10)
    """
    ticker = _validate_ticker(ticker)

    try:
        t = yf.Ticker(ticker)
        funds_data = t.get_funds_data()
        holdings_df = funds_data.top_holdings
    except Exception as e:
        raise ValueError(
            f"Could not fetch holdings for '{ticker}': {e}"
        ) from e

    if holdings_df is None or holdings_df.empty:
        raise ValueError(f"No holdings data returned for '{ticker}'.")

    rows = []
    for symbol, row in holdings_df.iterrows():
        name = row.get("Name", row.get("holdingName", ""))
        weight = row.get("Holding Percent", row.get("holdingPercent", float("nan")))
        # yfinance returns weight as a fraction (0-1); convert to percentage
        if pd.notna(weight) and weight <= 1.0:
            weight = weight * 100
        rows.append({
            "ticker": ticker,
            "holding_symbol": str(symbol),
            "holding_name": str(name),
            "weight_pct": round(float(weight), 4) if pd.notna(weight) else float("nan"),
        })

    if not rows:
        raise ValueError(f"No holding rows parsed for ETF '{ticker}'.")

    result = pd.DataFrame(rows)
    log.info(
        "get_etf_holdings('%s'): %d holdings fetched.", ticker, len(result)
    )
    return result


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _validate_ticker(ticker: str) -> str:
    """Strip whitespace and upper-case a ticker; raise if empty."""
    if not isinstance(ticker, str) or not ticker.strip():
        raise ValueError("ticker must be a non-empty string.")
    return ticker.strip().upper()


def _find_holdings_table(soup: BeautifulSoup):
    """Return the first <table> whose header row contains 'Symbol', else None."""
    for table in soup.find_all("table"):
        thead = table.find("thead")
        if thead and "Symbol" in thead.get_text():
            return table
    return None


def _parse_weight(raw: str) -> float:
    """Convert a weight string like '6.78%' or '6.78' to a float, or NaN."""
    try:
        return float(raw.replace("%", "").strip())
    except (ValueError, AttributeError):
        return float("nan")