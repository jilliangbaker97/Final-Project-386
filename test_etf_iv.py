"""
pytest test suite for the etf_iv package.
Covers all 21 public functions across 4 modules.

Run from the repo root:
    pytest                     # offline-safe: skips network/API tests
    pytest -v                  # verbose
    pytest -m "not network"    # explicitly exclude network tests
"""

import os
import socket

import pandas as pd
import pytest

import etf_iv

# ---------------------------------------------------------------------------
# Network / API availability (evaluated once at collection time)
# ---------------------------------------------------------------------------

def _has_network() -> bool:
    try:
        socket.setdefaulttimeout(3)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        return True
    except Exception:
        return False

_network_ok = _has_network()

requires_network = pytest.mark.skipif(not _network_ok, reason="no network")
requires_api_key = pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _assert_df(df, *, min_rows: int = 1, required_cols: tuple = ()):
    """Common DataFrame shape/column assertions."""
    assert isinstance(df, pd.DataFrame), f"Expected DataFrame, got {type(df).__name__}"
    if min_rows:
        assert len(df) >= min_rows, f"Expected >= {min_rows} rows, got {len(df)}"
    missing = [c for c in required_cols if c not in df.columns]
    assert not missing, f"Missing columns: {missing}"


# ===========================================================================
# Session fixtures — bundled loaders (always available, no network)
# ===========================================================================

@pytest.fixture(scope="session")
def prices():
    return etf_iv.load_price_history()


@pytest.fixture(scope="session")
def options():
    return etf_iv.load_options_chain()


@pytest.fixture(scope="session")
def options_filtered():
    return etf_iv.load_options_filtered()


@pytest.fixture(scope="session")
def holdings():
    return etf_iv.load_etf_holdings()


@pytest.fixture(scope="session")
def earnings():
    return etf_iv.load_earnings_dates()


@pytest.fixture(scope="session")
def sentiment():
    return etf_iv.load_etf_sentiment()


# ---------------------------------------------------------------------------
# Derived fixtures (offline, built from bundled data)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def cleaned_options(options):
    return etf_iv.clean_options(options)


@pytest.fixture(scope="session")
def filtered_options(cleaned_options):
    return etf_iv.filter_liquidity(cleaned_options, min_volume=1, min_open_interest=10)


@pytest.fixture(scope="session")
def cleaned_holdings(holdings):
    return etf_iv.clean_holdings(holdings)


@pytest.fixture(scope="session")
def cleaned_earnings(earnings):
    return etf_iv.clean_earnings(earnings)


@pytest.fixture(scope="session")
def options_with_moneyness(cleaned_options, prices):
    prices_src = prices[["ticker", "Date", "Close"]].copy()
    return etf_iv.add_spot_and_moneyness(cleaned_options, prices_src)


# ---------------------------------------------------------------------------
# Live-data fixture (skips automatically when offline)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def live_prices():
    if not _network_ok:
        pytest.skip("no network")
    return etf_iv.get_price_history("VOO", "1mo")


# ===========================================================================
# Section 1: Bundled Data Loaders
# ===========================================================================

def test_load_price_history(prices):
    _assert_df(prices, required_cols=["ticker", "Date", "Open", "High", "Low", "Close", "Volume"])
    assert pd.api.types.is_datetime64_any_dtype(prices["Date"]), "Date column is not datetime"
    assert prices["ticker"].nunique() >= 1


def test_load_options_chain(options):
    _assert_df(
        options,
        required_cols=[
            "ticker", "expiration", "contractType", "strike",
            "bid", "ask", "volume", "openInterest", "impliedVolatility",
        ],
    )
    assert pd.api.types.is_datetime64_any_dtype(options["expiration"]), \
        "expiration column is not datetime"


def test_load_options_filtered(options_filtered):
    _assert_df(
        options_filtered,
        required_cols=["ticker", "expiration", "contractType", "strike", "impliedVolatility"],
    )


def test_load_etf_holdings(holdings):
    _assert_df(holdings, required_cols=["holding_ticker", "etf_ticker", "weight_pct"])


def test_load_earnings_dates(earnings):
    _assert_df(earnings, required_cols=["holding_ticker", "earnings_date"])
    assert pd.api.types.is_datetime64_any_dtype(earnings["earnings_date"]), \
        "earnings_date column is not datetime"


def test_load_etf_sentiment(sentiment):
    _assert_df(sentiment, required_cols=["etf_ticker", "sentiment_score"])


# ===========================================================================
# Section 2: Live Data Collection
# ===========================================================================

@requires_network
def test_get_options_chain():
    df = etf_iv.get_options_chain("VOO")
    _assert_df(df, required_cols=["ticker", "expiration", "option_type", "strike"])
    assert set(df["option_type"].unique()).issubset({"call", "put"}), \
        "Unexpected option_type values"


def test_get_options_chain_bad_ticker():
    with pytest.raises(ValueError):
        etf_iv.get_options_chain("")


@requires_network
def test_get_price_history():
    df = etf_iv.get_price_history("VOO", "1mo")
    _assert_df(df, required_cols=["ticker"])
    assert "Close" in df.columns


def test_get_price_history_bad_period():
    with pytest.raises(ValueError):
        etf_iv.get_price_history("VOO", "99y")


@requires_network
def test_get_etf_holdings():
    df = etf_iv.get_etf_holdings("VOO")
    _assert_df(df, required_cols=["ticker", "holding_symbol", "weight_pct"])


@requires_network
def test_get_etf_headlines():
    headlines = etf_iv.get_etf_headlines("VOO", max_articles=3)
    assert isinstance(headlines, list), f"Expected list, got {type(headlines).__name__}"
    assert all(isinstance(h, str) for h in headlines), "Non-string item in headlines"


@requires_api_key
def test_get_sentiment_score():
    score = etf_iv.get_sentiment_score(["Markets rally on positive economic data."])
    assert isinstance(score, (int, float)), "Expected numeric sentiment score"
    assert 1 <= score <= 5, f"Score {score} outside expected 1–5 range"


# ===========================================================================
# Section 3: Data Cleaning
# ===========================================================================

def test_clean_prices_empty():
    with pytest.raises(ValueError):
        etf_iv.clean_prices(pd.DataFrame())


@requires_network
def test_clean_prices(live_prices):
    cleaned = etf_iv.clean_prices(live_prices)
    _assert_df(cleaned, required_cols=["ticker", "Date", "Close"])
    assert pd.api.types.is_datetime64_any_dtype(cleaned["Date"]), "Date not datetime"


def test_clean_options(cleaned_options):
    _assert_df(
        cleaned_options,
        required_cols=["ticker", "expiration", "contractType", "strike", "impliedVolatility"],
    )
    assert cleaned_options["strike"].notna().all(), "NaN strikes after cleaning"
    assert cleaned_options["impliedVolatility"].notna().all(), "NaN IV after cleaning"


def test_clean_options_empty():
    with pytest.raises(ValueError):
        etf_iv.clean_options(pd.DataFrame())


def test_filter_liquidity(filtered_options):
    _assert_df(filtered_options)
    if "volume" in filtered_options.columns:
        assert (filtered_options["volume"].fillna(0) >= 1).all(), "Row with volume < 1"
    if "openInterest" in filtered_options.columns:
        assert (filtered_options["openInterest"].fillna(0) >= 10).all(), "Row with OI < 10"


def test_add_spot_and_moneyness(options_with_moneyness):
    _assert_df(options_with_moneyness, required_cols=["spot_price", "moneyness", "dte"])
    assert options_with_moneyness["spot_price"].notna().any(), "All spot_price are NaN"
    assert options_with_moneyness["moneyness"].notna().any(), "All moneyness are NaN"


def test_add_spot_and_moneyness_bad_ticker(prices):
    bad_opts = pd.DataFrame({
        "ticker": ["XYZZY"],
        "expiration": [pd.Timestamp("2025-12-31")],
        "contractType": ["call"],
        "strike": [100.0],
        "impliedVolatility": [0.3],
    })
    with pytest.raises(ValueError):
        etf_iv.add_spot_and_moneyness(bad_opts, prices)


def test_clean_holdings(cleaned_holdings):
    _assert_df(cleaned_holdings, required_cols=["holding_ticker", "etf_ticker", "weight_pct"])
    assert pd.to_numeric(cleaned_holdings["weight_pct"], errors="coerce").notna().any(), \
        "weight_pct is not numeric"
    assert (cleaned_holdings["holding_ticker"] != "").all(), "Empty holding_ticker after clean"


def test_clean_holdings_empty():
    with pytest.raises(ValueError):
        etf_iv.clean_holdings(pd.DataFrame())


def test_clean_earnings(cleaned_earnings):
    _assert_df(cleaned_earnings, required_cols=["holding_ticker", "earnings_date"])
    has_bad = cleaned_earnings["holding_ticker"].str.contains(r"[:/]", na=False).any()
    assert not has_bad, "Exchange-prefixed tickers remain after clean_earnings"


def test_clean_earnings_empty():
    with pytest.raises(ValueError):
        etf_iv.clean_earnings(pd.DataFrame())


# ===========================================================================
# Section 4: Analysis
# ===========================================================================

def test_compute_put_call_ratios(filtered_options):
    pcr_ticker, pcr_expiry = etf_iv.compute_put_call_ratios(filtered_options)
    assert isinstance(pcr_ticker, pd.DataFrame)
    assert isinstance(pcr_expiry, pd.DataFrame)
    _assert_df(pcr_ticker, required_cols=["pcr_volume", "pcr_oi"])
    _assert_df(
        pcr_expiry,
        required_cols=["ticker", "expiration", "pcr_volume", "pcr_oi", "days_to_exp", "horizon"],
    )


def test_compute_forward_returns(prices):
    fwd = etf_iv.compute_forward_returns(prices, windows=[1, 5])
    _assert_df(fwd, required_cols=["ticker", "Date", "Close", "fwd_1d", "fwd_5d"])


def test_compute_forward_returns_custom_windows(prices):
    fwd = etf_iv.compute_forward_returns(prices, windows=[10, 21])
    assert "fwd_10d" in fwd.columns, "fwd_10d column missing"
    assert "fwd_21d" in fwd.columns, "fwd_21d column missing"


def test_compute_iv_skew(options_with_moneyness):
    skew = etf_iv.compute_iv_skew(options_with_moneyness)
    assert isinstance(skew, pd.DataFrame)
    _assert_df(skew, required_cols=["atm_iv", "otm_iv", "iv_skew", "n_atm", "n_otm"])


def test_compute_earnings_proximity(cleaned_holdings, cleaned_earnings):
    earnings = cleaned_earnings.copy()
    if "etf_ticker" not in earnings.columns and "ticker" in earnings.columns:
        earnings = earnings.rename(columns={"ticker": "etf_ticker"})
    ep = etf_iv.compute_earnings_proximity(
        cleaned_holdings,
        earnings,
        today=pd.Timestamp("2025-04-13"),
        top_n=10,
    )
    assert isinstance(ep, pd.DataFrame)
    _assert_df(
        ep,
        required_cols=[
            "weighted_dte_earnings", "pct_within_30d",
            "pct_within_60d", "n_holdings_with_dates",
        ],
    )
