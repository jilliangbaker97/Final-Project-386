"""
Data-cleaning helpers for ETF options, price history, holdings, and earnings.

Each function accepts a raw DataFrame (as returned by the data-collection
layer or read from CSV) and returns a cleaned copy.  Input DataFrames are
never mutated.
"""

import logging

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Price history
# ---------------------------------------------------------------------------

_PRICE_COLS = ["ticker", "Date", "Open", "High", "Low", "Close", "Volume"]


def clean_prices(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize a raw price-history DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Raw output from :func:`get_price_history` (DatetimeIndex) or a CSV
        reload.  Must contain at least ``ticker``, ``Date`` (or index), and
        ``Close``.

    Returns
    -------
    pd.DataFrame
        Columns limited to ``ticker, Date, Open, High, Low, Close, Volume``
        with correct dtypes, tz-naive dates, and sorted by
        ``[ticker, Date]``.

    Raises
    ------
    ValueError
        If the input is empty or essential columns are missing.
    """
    if df.empty:
        raise ValueError("clean_prices: input DataFrame is empty.")

    if "Date" not in df.columns:
        df = df.reset_index()
        df = df.rename(columns={"index": "Date"})

    cols = [c for c in _PRICE_COLS if c in df.columns]
    missing = {"ticker", "Date", "Close"} - set(cols)
    if missing:
        raise ValueError(f"clean_prices: missing required columns {missing}.")
    df = df[cols].copy()

    df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
    for col in ("Open", "High", "Low", "Close", "Volume"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.sort_values(["ticker", "Date"]).reset_index(drop=True)
    log.info("clean_prices: %d rows, %d tickers.", len(df), df["ticker"].nunique())
    return df


# ---------------------------------------------------------------------------
# Options chain
# ---------------------------------------------------------------------------

_OPTION_COLS = [
    "ticker", "expiration", "contractType", "strike", "bid", "ask",
    "volume", "openInterest", "impliedVolatility",
]


def clean_options(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize a raw options-chain DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Raw output from :func:`get_options_chain`.  The column
        ``option_type`` is renamed to ``contractType`` if present.

    Returns
    -------
    pd.DataFrame
        Columns limited to the canonical set, correct dtypes, rows with
        missing ``strike`` or ``impliedVolatility`` dropped, sorted by
        ``[ticker, expiration, contractType, strike]``.

    Raises
    ------
    ValueError
        If the input is empty or essential columns are missing.
    """
    if df.empty:
        raise ValueError("clean_options: input DataFrame is empty.")

    df = df.copy()
    df = df.rename(columns={"option_type": "contractType"})

    cols = [c for c in _OPTION_COLS if c in df.columns]
    required = {"ticker", "expiration", "contractType", "strike", "impliedVolatility"}
    missing = required - set(cols)
    if missing:
        raise ValueError(f"clean_options: missing required columns {missing}.")
    df = df[cols]

    df["expiration"] = pd.to_datetime(df["expiration"])
    for col in ("strike", "bid", "ask", "volume", "openInterest", "impliedVolatility"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    before = len(df)
    df = df.dropna(subset=["strike", "impliedVolatility"])
    dropped = before - len(df)
    if dropped:
        log.info("clean_options: dropped %d rows with missing strike/IV.", dropped)

    df = df.sort_values(
        ["ticker", "expiration", "contractType", "strike"]
    ).reset_index(drop=True)
    log.info("clean_options: %d rows retained.", len(df))
    return df


# ---------------------------------------------------------------------------
# Liquidity filter
# ---------------------------------------------------------------------------


def filter_liquidity(
    df: pd.DataFrame,
    min_volume: int = 1,
    min_open_interest: int = 10,
) -> pd.DataFrame:
    """Remove illiquid option contracts.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned options DataFrame with ``volume`` and ``openInterest``.
    min_volume : int
        Minimum trade volume (inclusive).  Default ``1``.
    min_open_interest : int
        Minimum open interest (inclusive).  Default ``10``.

    Returns
    -------
    pd.DataFrame
        Filtered copy with reset index.
    """
    df = df.copy()
    mask = (
        (df["volume"].fillna(0) >= min_volume)
        & (df["openInterest"].fillna(0) >= min_open_interest)
    )
    result = df[mask].reset_index(drop=True)
    log.info(
        "filter_liquidity: %d -> %d rows (dropped %d).",
        len(df), len(result), len(df) - len(result),
    )
    return result


# ---------------------------------------------------------------------------
# Spot price join + moneyness + DTE
# ---------------------------------------------------------------------------


def add_spot_and_moneyness(
    options: pd.DataFrame,
    prices: pd.DataFrame,
) -> pd.DataFrame:
    """Merge latest spot price onto options and compute moneyness and DTE.

    Parameters
    ----------
    options : pd.DataFrame
        Cleaned options with ``ticker``, ``strike``, ``expiration``.
    prices : pd.DataFrame
        Cleaned price history with ``ticker``, ``Date``, ``Close``.

    Returns
    -------
    pd.DataFrame
        Options augmented with ``spot_price``, ``moneyness``
        (strike / spot), and ``dte`` (days to expiration from today).

    Raises
    ------
    ValueError
        If any ticker in *options* has no matching price data.
    """
    spot = (
        prices.sort_values("Date")
        .groupby("ticker", as_index=False)
        .last()[["ticker", "Close"]]
        .rename(columns={"Close": "spot_price"})
    )

    result = options.merge(spot, on="ticker", how="left")

    unmatched = result["spot_price"].isna().sum()
    if unmatched:
        bad = result.loc[result["spot_price"].isna(), "ticker"].unique()
        raise ValueError(
            f"add_spot_and_moneyness: no price data for tickers {list(bad)}."
        )

    result["moneyness"] = (result["strike"] / result["spot_price"]).round(4)

    today = pd.Timestamp.today().normalize()
    result["dte"] = (result["expiration"] - today).dt.days

    log.info("add_spot_and_moneyness: added spot, moneyness, dte to %d rows.", len(result))
    return result


# ---------------------------------------------------------------------------
# Holdings
# ---------------------------------------------------------------------------


def clean_holdings(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names and types for ETF holdings.

    Handles both the package output (``holding_symbol``, ``ticker``) and the
    notebook convention (``holding_ticker``, ``etf_ticker``).

    Parameters
    ----------
    df : pd.DataFrame
        Raw holdings data.

    Returns
    -------
    pd.DataFrame
        Columns normalized to ``holding_ticker``, ``etf_ticker``,
        ``holding_name`` (if present), ``weight_pct`` (float).

    Raises
    ------
    ValueError
        If the input is empty.
    """
    if df.empty:
        raise ValueError("clean_holdings: input DataFrame is empty.")

    df = df.copy()

    # Normalize column names to notebook convention
    rename_map = {}
    if "holding_symbol" in df.columns and "holding_ticker" not in df.columns:
        rename_map["holding_symbol"] = "holding_ticker"
    if "ticker" in df.columns and "etf_ticker" not in df.columns:
        rename_map["ticker"] = "etf_ticker"
    if rename_map:
        df = df.rename(columns=rename_map)

    df["weight_pct"] = pd.to_numeric(df["weight_pct"], errors="coerce")

    # Drop rows with empty or missing holding tickers
    df = df[df["holding_ticker"].notna() & (df["holding_ticker"] != "")]
    df = df.reset_index(drop=True)

    log.info("clean_holdings: %d rows.", len(df))
    return df


# ---------------------------------------------------------------------------
# Earnings dates
# ---------------------------------------------------------------------------


def clean_earnings(df: pd.DataFrame) -> pd.DataFrame:
    """Parse and filter earnings-date data.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain ``holding_ticker`` and ``earnings_date``.

    Returns
    -------
    pd.DataFrame
        Rows with exchange-prefixed tickers (containing ``":"`` or ``"/"``)
        removed; ``earnings_date`` parsed to datetime (unparseable → NaT
        retained so callers can see coverage gaps).
    """
    if df.empty:
        raise ValueError("clean_earnings: input DataFrame is empty.")

    df = df.copy()
    df["earnings_date"] = pd.to_datetime(df["earnings_date"], errors="coerce")

    # Filter out exchange-prefixed tickers (e.g. "TLV: ESLT", "AAPL/B")
    mask = ~df["holding_ticker"].str.contains(r"[:/]", na=False)
    removed = (~mask).sum()
    if removed:
        log.info("clean_earnings: removed %d exchange-prefixed tickers.", removed)
    df = df[mask].reset_index(drop=True)

    log.info("clean_earnings: %d rows (%d with dates).",
             len(df), df["earnings_date"].notna().sum())
    return df
