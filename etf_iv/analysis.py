"""
Analytical computations for ETF options data.

Functions in this module derive metrics from cleaned DataFrames produced by
:mod:`etf_iv.cleaning`.  They do not perform raw data fetching or cleaning.
"""

import logging

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Put / Call Ratios
# ---------------------------------------------------------------------------


def compute_put_call_ratios(
    options: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compute put/call ratios by ticker and by ticker-expiration.

    Parameters
    ----------
    options : pd.DataFrame
        Cleaned options with ``ticker``, ``expiration``, ``contractType``,
        ``volume``, and ``openInterest``.

    Returns
    -------
    pcr_ticker : pd.DataFrame
        Index = ticker.  Columns: ``pcr_volume``, ``pcr_oi``,
        ``put_volume``, ``call_volume``, ``put_oi``, ``call_oi``.
    pcr_expiry : pd.DataFrame
        Columns: ``ticker``, ``expiration``, ``pcr_volume``, ``pcr_oi``,
        ``days_to_exp``, ``horizon`` (near / mid / far).
    """
    # --- Aggregate by ticker ---
    agg = (
        options.groupby(["ticker", "contractType"])[["volume", "openInterest"]]
        .sum()
        .unstack("contractType")
    )
    agg.columns = ["_".join(c) for c in agg.columns]

    pcr_ticker = pd.DataFrame({
        "pcr_volume":  agg["volume_put"] / agg["volume_call"],
        "pcr_oi":      agg["openInterest_put"] / agg["openInterest_call"],
        "put_volume":  agg["volume_put"],
        "call_volume": agg["volume_call"],
        "put_oi":      agg["openInterest_put"],
        "call_oi":     agg["openInterest_call"],
    }).round(4)

    # --- By ticker × expiration ---
    agg_exp = (
        options.groupby(["ticker", "expiration", "contractType"])[
            ["volume", "openInterest"]
        ]
        .sum()
        .unstack("contractType")
        .fillna(0)
    )
    agg_exp.columns = ["_".join(c) for c in agg_exp.columns]

    pcr_expiry = pd.DataFrame({
        "pcr_volume": (
            agg_exp["volume_put"]
            / agg_exp["volume_call"].replace(0, np.nan)
        ),
        "pcr_oi": (
            agg_exp["openInterest_put"]
            / agg_exp["openInterest_call"].replace(0, np.nan)
        ),
    }).reset_index()

    today = pd.Timestamp.today().normalize()
    pcr_expiry["days_to_exp"] = (pcr_expiry["expiration"] - today).dt.days
    pcr_expiry["horizon"] = pd.cut(
        pcr_expiry["days_to_exp"],
        bins=[-np.inf, 30, 90, np.inf],
        labels=["near (≤30d)", "mid (31-90d)", "far (>90d)"],
    )

    log.info(
        "compute_put_call_ratios: %d tickers, %d expiry rows.",
        len(pcr_ticker), len(pcr_expiry),
    )
    return pcr_ticker, pcr_expiry


# ---------------------------------------------------------------------------
# Forward Returns
# ---------------------------------------------------------------------------


def compute_forward_returns(
    prices: pd.DataFrame,
    windows: list[int] | None = None,
) -> pd.DataFrame:
    """Add forward-return columns to a price DataFrame.

    Parameters
    ----------
    prices : pd.DataFrame
        Cleaned price history with ``ticker``, ``Date``, ``Close``.
    windows : list[int], optional
        Look-ahead windows in trading days.  Default ``[1, 5]``.

    Returns
    -------
    pd.DataFrame
        Copy of *prices* with new columns ``fwd_{n}d`` for each window.
    """
    if windows is None:
        windows = [1, 5]

    df = prices.sort_values(["ticker", "Date"]).reset_index(drop=True)

    for n in windows:
        df[f"fwd_{n}d"] = (
            df.groupby("ticker")["Close"].pct_change(n).shift(-n)
        )

    log.info("compute_forward_returns: windows=%s, %d rows.", windows, len(df))
    return df


# ---------------------------------------------------------------------------
# IV Skew
# ---------------------------------------------------------------------------


def compute_iv_skew(
    options: pd.DataFrame,
    dte_range: tuple[int, int] = (15, 60),
    atm_range: tuple[float, float] = (0.97, 1.03),
    otm_range: tuple[float, float] = (0.85, 0.97),
) -> pd.DataFrame:
    """Compute implied-volatility skew per ETF.

    IV Skew = median(OTM put IV) - median(ATM put IV), restricted to puts
    within the specified DTE window.

    Parameters
    ----------
    options : pd.DataFrame
        Must contain ``ticker``, ``contractType``, ``impliedVolatility``,
        ``moneyness``, and ``dte``.
    dte_range : tuple[int, int]
        (min, max) days to expiration, inclusive.
    atm_range : tuple[float, float]
        (lo, hi) moneyness bounds for ATM puts, inclusive.
    otm_range : tuple[float, float]
        (lo, hi) moneyness bounds for OTM puts. Lower inclusive, upper
        exclusive.

    Returns
    -------
    pd.DataFrame
        Index = ticker.  Columns: ``atm_iv``, ``otm_iv``, ``iv_skew``,
        ``n_atm``, ``n_otm``.
    """
    dte_lo, dte_hi = dte_range
    atm_lo, atm_hi = atm_range
    otm_lo, otm_hi = otm_range

    puts = options[
        (options["contractType"] == "put")
        & (options["dte"].between(dte_lo, dte_hi))
    ].copy()

    puts["bucket"] = np.where(
        puts["moneyness"].between(atm_lo, atm_hi),
        "ATM",
        np.where(
            puts["moneyness"].between(otm_lo, otm_hi, inclusive="left"),
            "OTM",
            "other",
        ),
    )
    puts = puts[puts["bucket"].isin(["ATM", "OTM"])]

    rows = []
    for ticker in sorted(options["ticker"].unique()):
        t_puts = puts[puts["ticker"] == ticker]
        atm = t_puts.loc[t_puts["bucket"] == "ATM", "impliedVolatility"]
        otm = t_puts.loc[t_puts["bucket"] == "OTM", "impliedVolatility"]

        atm_iv = atm.median() if len(atm) > 0 else np.nan
        otm_iv = otm.median() if len(otm) > 0 else np.nan
        iv_skew = (
            otm_iv - atm_iv
            if pd.notna(atm_iv) and pd.notna(otm_iv)
            else np.nan
        )

        rows.append({
            "ticker": ticker,
            "atm_iv": atm_iv,
            "otm_iv": otm_iv,
            "iv_skew": iv_skew,
            "n_atm": len(atm),
            "n_otm": len(otm),
        })

    result = pd.DataFrame(rows).set_index("ticker")
    log.info("compute_iv_skew: %d tickers.", len(result))
    return result


# ---------------------------------------------------------------------------
# Earnings Proximity
# ---------------------------------------------------------------------------


def compute_earnings_proximity(
    holdings: pd.DataFrame,
    earnings: pd.DataFrame,
    today: pd.Timestamp | None = None,
    top_n: int = 10,
) -> pd.DataFrame:
    """Weight-normalized earnings proximity metrics per ETF.

    Parameters
    ----------
    holdings : pd.DataFrame
        Cleaned holdings with ``holding_ticker``, ``etf_ticker``,
        ``weight_pct``.
    earnings : pd.DataFrame
        Cleaned earnings with ``holding_ticker``, ``etf_ticker``,
        ``earnings_date``.
    today : pd.Timestamp, optional
        Reference date.  Defaults to today.
    top_n : int
        Number of largest holdings (by weight) to consider per ETF.

    Returns
    -------
    pd.DataFrame
        Index = ticker.  Columns: ``weighted_dte_earnings``,
        ``pct_within_30d``, ``pct_within_60d``, ``n_holdings_with_dates``.
    """
    if today is None:
        today = pd.Timestamp.today().normalize()

    hold_earn = holdings.merge(
        earnings[["holding_ticker", "etf_ticker", "earnings_date"]],
        on=["holding_ticker", "etf_ticker"],
        how="left",
    )
    hold_earn["days_to_earnings"] = (
        (hold_earn["earnings_date"] - today).dt.days
    )
    hold_earn["days_to_earnings"] = hold_earn["days_to_earnings"].clip(lower=0)

    rows = []
    for etf in sorted(holdings["etf_ticker"].unique()):
        sub = (
            hold_earn[hold_earn["etf_ticker"] == etf]
            .nlargest(top_n, "weight_pct")
        )
        valid = sub.dropna(subset=["days_to_earnings"])

        if valid.empty:
            rows.append({
                "ticker": etf,
                "weighted_dte_earnings": np.nan,
                "pct_within_30d": np.nan,
                "pct_within_60d": np.nan,
                "n_holdings_with_dates": 0,
            })
            continue

        w = valid["weight_pct"]
        d = valid["days_to_earnings"]
        w_norm = w / w.sum()

        rows.append({
            "ticker": etf,
            "weighted_dte_earnings": (w_norm * d).sum(),
            "pct_within_30d": (d <= 30).mean() * 100,
            "pct_within_60d": (d <= 60).mean() * 100,
            "n_holdings_with_dates": len(valid),
        })

    result = pd.DataFrame(rows).set_index("ticker")
    log.info("compute_earnings_proximity: %d ETFs.", len(result))
    return result
