"""
Comprehensive test script for the etf_iv package.
Tests all 21 public functions across 4 modules.
Usage: python test_etf_iv.py
"""

import sys
import traceback
import socket

import pandas as pd

# ---------------------------------------------------------------------------
# Tracking helpers
# ---------------------------------------------------------------------------

results = []

def passed(name, detail=""):
    msg = f"PASS  {name}"
    if detail:
        msg += f"  ({detail})"
    print(msg)
    results.append(("PASS", name))

def failed(name, reason):
    print(f"FAIL  {name}  -- {reason}")
    results.append(("FAIL", name, reason))

def skipped(name, reason):
    print(f"SKIP  {name}  -- {reason}")
    results.append(("SKIP", name))

def assert_df(df, *, min_rows=1, required_cols=()):
    """Common DataFrame shape/column assertions."""
    if not isinstance(df, pd.DataFrame):
        raise AssertionError(f"Expected DataFrame, got {type(df).__name__}")
    if min_rows and len(df) < min_rows:
        raise AssertionError(f"Expected >= {min_rows} rows, got {len(df)}")
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise AssertionError(f"Missing columns: {missing}")


def _has_network():
    try:
        socket.setdefaulttimeout(3)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        return True
    except Exception:
        return False

_network_ok = _has_network()

import etf_iv

# ===========================================================================
# Section 1: Bundled Data Loaders (etf_iv.data — 6 functions)
# ===========================================================================

print("\n" + "=" * 60)
print("SECTION 1: Bundled Data Loaders")
print("=" * 60)

# --- load_price_history ---
df_prices = None
try:
    df_prices = etf_iv.load_price_history()
    assert_df(df_prices,
              required_cols=["ticker", "Date", "Open", "High", "Low", "Close", "Volume"])
    assert pd.api.types.is_datetime64_any_dtype(df_prices["Date"]), "Date not datetime"
    assert df_prices["ticker"].nunique() >= 1, "No tickers found"
    passed("load_price_history", f"{len(df_prices)} rows, {df_prices['ticker'].nunique()} tickers")
except Exception as e:
    failed("load_price_history", str(e))

# --- load_options_chain ---
df_options = None
try:
    df_options = etf_iv.load_options_chain()
    assert_df(df_options,
              required_cols=["ticker", "expiration", "contractType", "strike",
                             "bid", "ask", "volume", "openInterest", "impliedVolatility"])
    assert pd.api.types.is_datetime64_any_dtype(df_options["expiration"]), "expiration not datetime"
    passed("load_options_chain", f"{len(df_options)} rows")
except Exception as e:
    failed("load_options_chain", str(e))

# --- load_options_filtered ---
df_filtered = None
try:
    df_filtered = etf_iv.load_options_filtered()
    assert_df(df_filtered,
              required_cols=["ticker", "expiration", "contractType", "strike",
                             "impliedVolatility"])
    has_spot = "spot_price" in df_filtered.columns
    has_mono = "moneyness" in df_filtered.columns
    passed("load_options_filtered",
           f"{len(df_filtered)} rows; spot_price={has_spot}, moneyness={has_mono}")
except Exception as e:
    failed("load_options_filtered", str(e))

# --- load_etf_holdings ---
df_holdings = None
try:
    df_holdings = etf_iv.load_etf_holdings()
    assert_df(df_holdings,
              required_cols=["holding_ticker", "etf_ticker", "weight_pct"])
    passed("load_etf_holdings", f"{len(df_holdings)} rows")
except Exception as e:
    failed("load_etf_holdings", str(e))

# --- load_earnings_dates ---
df_earnings = None
try:
    df_earnings = etf_iv.load_earnings_dates()
    assert_df(df_earnings,
              required_cols=["holding_ticker", "earnings_date"])
    assert pd.api.types.is_datetime64_any_dtype(df_earnings["earnings_date"]), "earnings_date not datetime"
    passed("load_earnings_dates", f"{len(df_earnings)} rows")
except Exception as e:
    failed("load_earnings_dates", str(e))

# --- load_etf_sentiment ---
df_sentiment = None
try:
    df_sentiment = etf_iv.load_etf_sentiment()
    assert_df(df_sentiment,
              required_cols=["etf_ticker", "sentiment_score"])
    passed("load_etf_sentiment", f"{len(df_sentiment)} rows")
except Exception as e:
    failed("load_etf_sentiment", str(e))


# ===========================================================================
# Section 2: Live Data Collection (5 functions)
# ===========================================================================

print("\n" + "=" * 60)
print("SECTION 2: Live Data Collection")
print("=" * 60)

# --- get_options_chain (live) ---
df_live_opts = None
if not _network_ok:
    skipped("get_options_chain", "no network")
else:
    try:
        df_live_opts = etf_iv.get_options_chain("VOO")
        assert_df(df_live_opts,
                  required_cols=["ticker", "expiration", "option_type", "strike"])
        assert set(df_live_opts["option_type"].unique()).issubset({"call", "put"}), \
            "unexpected option_type values"
        passed("get_options_chain", f"{len(df_live_opts)} rows")
    except Exception as e:
        failed("get_options_chain", str(e))

# --- get_options_chain: ValueError on bad ticker ---
try:
    etf_iv.get_options_chain("")
    failed("get_options_chain_bad_ticker", "expected ValueError, got none")
except ValueError:
    passed("get_options_chain_bad_ticker", "ValueError raised on empty ticker")
except Exception as e:
    failed("get_options_chain_bad_ticker", f"expected ValueError, got {type(e).__name__}: {e}")

# --- get_price_history (live) ---
df_live_prices = None
if not _network_ok:
    skipped("get_price_history", "no network")
else:
    try:
        df_live_prices = etf_iv.get_price_history("VOO", "1mo")
        assert_df(df_live_prices, required_cols=["ticker"])
        assert "Close" in df_live_prices.columns, "Close column missing"
        passed("get_price_history", f"{len(df_live_prices)} rows (DatetimeIndex)")
    except Exception as e:
        failed("get_price_history", str(e))

# --- get_price_history: ValueError on bad period ---
try:
    etf_iv.get_price_history("VOO", "99y")
    failed("get_price_history_bad_period", "expected ValueError, got none")
except ValueError:
    passed("get_price_history_bad_period", "ValueError raised on invalid period")
except Exception as e:
    failed("get_price_history_bad_period", f"expected ValueError, got {type(e).__name__}: {e}")

# --- get_etf_holdings (live) ---
if not _network_ok:
    skipped("get_etf_holdings", "no network")
else:
    try:
        df_live_hold = etf_iv.get_etf_holdings("VOO")
        assert_df(df_live_hold,
                  required_cols=["ticker", "holding_symbol", "weight_pct"])
        passed("get_etf_holdings", f"{len(df_live_hold)} holdings")
    except ValueError as e:
        # Yahoo Finance frequently changes their HTML structure; a 404 or
        # missing-table error is a real scraping failure, not a code bug per se.
        failed("get_etf_holdings",
               f"Yahoo Finance scraping failed (site may have changed layout): {e}")
    except Exception as e:
        failed("get_etf_holdings", str(e))

# --- get_etf_headlines (live) ---
if not _network_ok:
    skipped("get_etf_headlines", "no network")
else:
    try:
        headlines = etf_iv.get_etf_headlines("VOO", max_articles=3)
        assert isinstance(headlines, list), f"Expected list, got {type(headlines).__name__}"
        assert all(isinstance(h, str) for h in headlines), "Non-string in headlines"
        if len(headlines) == 0:
            # yfinance news API changed structure (article["content"]["title"]
            # instead of article["title"]). The function returns [] silently.
            failed("get_etf_headlines",
                   "KNOWN BUG: returned 0 headlines — yfinance news API changed "
                   "to nested structure (article['content']['title']); "
                   "get_etf_headlines() checks article.get('title') which is now None")
        else:
            passed("get_etf_headlines", f"{len(headlines)} headlines")
    except Exception as e:
        failed("get_etf_headlines", str(e))

# --- get_sentiment_score: SKIPPED (requires ANTHROPIC_API_KEY) ---
skipped("get_sentiment_score", "requires ANTHROPIC_API_KEY — skipped per instructions")


# ===========================================================================
# Section 3: Data Cleaning (6 functions)
# ===========================================================================

print("\n" + "=" * 60)
print("SECTION 3: Data Cleaning")
print("=" * 60)

# --- clean_prices ---
# clean_prices expects a DataFrame with a DatetimeIndex (as returned by
# get_price_history). The bundled CSV (load_price_history) has Date as a
# regular column, so passing it triggers a known bug: reset_index() adds an
# integer 'index' column, which is then renamed to 'Date', creating a
# duplicate 'Date' column that causes pd.to_datetime to fail.
cleaned_prices = None
if df_live_prices is not None:
    # Use the live DatetimeIndex DataFrame (correct input format)
    try:
        cleaned_prices = etf_iv.clean_prices(df_live_prices)
        assert_df(cleaned_prices, required_cols=["ticker", "Date", "Close"])
        assert pd.api.types.is_datetime64_any_dtype(cleaned_prices["Date"]), "Date not datetime"
        passed("clean_prices", f"{len(cleaned_prices)} rows (live DatetimeIndex input)")
    except Exception as e:
        failed("clean_prices", str(e))
elif not _network_ok:
    skipped("clean_prices", "no network to get DatetimeIndex input")
else:
    skipped("clean_prices", "live price data unavailable")

# --- clean_prices: known bug with bundled CSV input ---
if df_prices is not None:
    try:
        etf_iv.clean_prices(df_prices)
        passed("clean_prices_csv_path", "no error on bundled CSV path (bug may be fixed)")
    except ValueError as e:
        if "duplicate keys" in str(e):
            failed("clean_prices_csv_path",
                   "KNOWN BUG: reset_index() creates duplicate 'Date' column "
                   "when input already has Date as a regular column (not DatetimeIndex). "
                   f"Error: {e}")
        else:
            failed("clean_prices_csv_path", str(e))
    except Exception as e:
        failed("clean_prices_csv_path", str(e))

# --- clean_prices: ValueError on empty DataFrame ---
try:
    etf_iv.clean_prices(pd.DataFrame())
    failed("clean_prices_empty", "expected ValueError, got none")
except ValueError:
    passed("clean_prices_empty", "ValueError raised on empty input")
except Exception as e:
    failed("clean_prices_empty", f"expected ValueError, got {type(e).__name__}: {e}")

# --- clean_options ---
cleaned_opts = None
try:
    if df_options is None:
        raise RuntimeError("df_options not loaded; skipping clean_options test")
    cleaned_opts = etf_iv.clean_options(df_options)
    assert_df(cleaned_opts,
              required_cols=["ticker", "expiration", "contractType", "strike",
                             "impliedVolatility"])
    assert cleaned_opts["strike"].notna().all(), "NaN strikes after cleaning"
    assert cleaned_opts["impliedVolatility"].notna().all(), "NaN IV after cleaning"
    passed("clean_options", f"{len(cleaned_opts)} rows retained")
except Exception as e:
    failed("clean_options", str(e))

# --- clean_options: ValueError on empty DataFrame ---
try:
    etf_iv.clean_options(pd.DataFrame())
    failed("clean_options_empty", "expected ValueError, got none")
except ValueError:
    passed("clean_options_empty", "ValueError raised on empty input")
except Exception as e:
    failed("clean_options_empty", f"expected ValueError, got {type(e).__name__}: {e}")

# --- filter_liquidity ---
filtered_opts = None
try:
    source = cleaned_opts if cleaned_opts is not None else df_options
    if source is None:
        raise RuntimeError("No options DataFrame available for filter_liquidity")
    filtered_opts = etf_iv.filter_liquidity(source, min_volume=1, min_open_interest=10)
    assert_df(filtered_opts)
    if "volume" in filtered_opts.columns and "openInterest" in filtered_opts.columns:
        vol_ok = (filtered_opts["volume"].fillna(0) >= 1).all()
        oi_ok = (filtered_opts["openInterest"].fillna(0) >= 10).all()
        assert vol_ok, "Some rows have volume < 1"
        assert oi_ok, "Some rows have OI < 10"
    passed("filter_liquidity", f"{len(filtered_opts)} rows after filter")
except Exception as e:
    failed("filter_liquidity", str(e))

# --- add_spot_and_moneyness ---
# Uses the bundled prices (all 4 tickers) so the ticker set matches options.
opts_with_mono = None
try:
    opts_src = cleaned_opts if cleaned_opts is not None else df_options
    # Always use bundled prices here: already has ticker, Date, Close for all 4 ETFs
    if df_prices is None:
        raise RuntimeError("Bundled prices not loaded")
    prices_src = df_prices[["ticker", "Date", "Close"]].copy()
    if opts_src is None:
        raise RuntimeError("No options DataFrame available")
    opts_with_mono = etf_iv.add_spot_and_moneyness(opts_src, prices_src)
    assert_df(opts_with_mono, required_cols=["spot_price", "moneyness", "dte"])
    assert opts_with_mono["spot_price"].notna().any(), "All spot_price are NaN"
    assert opts_with_mono["moneyness"].notna().any(), "All moneyness are NaN"
    passed("add_spot_and_moneyness",
           f"{len(opts_with_mono)} rows, spot range "
           f"[{opts_with_mono['spot_price'].min():.2f}, "
           f"{opts_with_mono['spot_price'].max():.2f}]")
except Exception as e:
    failed("add_spot_and_moneyness", str(e))

# --- add_spot_and_moneyness: ValueError on unmatched ticker ---
try:
    prices_src = cleaned_prices if cleaned_prices is not None else df_prices
    if prices_src is None:
        skipped("add_spot_and_moneyness_bad_ticker", "no prices DataFrame available")
    else:
        bad_opts = pd.DataFrame({
            "ticker": ["XYZZY"],
            "expiration": [pd.Timestamp("2025-12-31")],
            "contractType": ["call"],
            "strike": [100.0],
            "impliedVolatility": [0.3],
        })
        etf_iv.add_spot_and_moneyness(bad_opts, prices_src)
        failed("add_spot_and_moneyness_bad_ticker", "expected ValueError, got none")
except ValueError:
    passed("add_spot_and_moneyness_bad_ticker", "ValueError raised for unmatched ticker")
except Exception as e:
    failed("add_spot_and_moneyness_bad_ticker", f"expected ValueError, got {type(e).__name__}: {e}")

# --- clean_holdings ---
cleaned_hold = None
try:
    if df_holdings is None:
        raise RuntimeError("df_holdings not loaded")
    cleaned_hold = etf_iv.clean_holdings(df_holdings)
    assert_df(cleaned_hold, required_cols=["holding_ticker", "etf_ticker", "weight_pct"])
    assert pd.to_numeric(cleaned_hold["weight_pct"], errors="coerce").notna().any(), \
        "weight_pct not numeric"
    assert (cleaned_hold["holding_ticker"] != "").all(), "Empty holding_ticker after clean"
    passed("clean_holdings", f"{len(cleaned_hold)} rows")
except Exception as e:
    failed("clean_holdings", str(e))

# --- clean_holdings: ValueError on empty DataFrame ---
try:
    etf_iv.clean_holdings(pd.DataFrame())
    failed("clean_holdings_empty", "expected ValueError, got none")
except ValueError:
    passed("clean_holdings_empty", "ValueError raised on empty input")
except Exception as e:
    failed("clean_holdings_empty", f"expected ValueError, got {type(e).__name__}: {e}")

# --- clean_earnings ---
cleaned_earn = None
try:
    if df_earnings is None:
        raise RuntimeError("df_earnings not loaded")
    cleaned_earn = etf_iv.clean_earnings(df_earnings)
    assert_df(cleaned_earn, required_cols=["holding_ticker", "earnings_date"])
    has_bad = cleaned_earn["holding_ticker"].str.contains(r"[:/]", na=False).any()
    assert not has_bad, "Exchange-prefixed tickers remain after clean_earnings"
    passed("clean_earnings",
           f"{len(cleaned_earn)} rows after removing exchange-prefixed tickers")
except Exception as e:
    failed("clean_earnings", str(e))

# --- clean_earnings: ValueError on empty DataFrame ---
try:
    etf_iv.clean_earnings(pd.DataFrame())
    failed("clean_earnings_empty", "expected ValueError, got none")
except ValueError:
    passed("clean_earnings_empty", "ValueError raised on empty input")
except Exception as e:
    failed("clean_earnings_empty", f"expected ValueError, got {type(e).__name__}: {e}")


# ===========================================================================
# Section 4: Analysis (4 functions)
# ===========================================================================

print("\n" + "=" * 60)
print("SECTION 4: Analysis")
print("=" * 60)

# --- compute_put_call_ratios ---
try:
    opts_for_pcr = filtered_opts if filtered_opts is not None else cleaned_opts
    if opts_for_pcr is None:
        opts_for_pcr = df_options
    if opts_for_pcr is None:
        raise RuntimeError("No options DataFrame available for PCR test")
    pcr_ticker, pcr_expiry = etf_iv.compute_put_call_ratios(opts_for_pcr)
    assert isinstance(pcr_ticker, pd.DataFrame), "pcr_ticker not a DataFrame"
    assert isinstance(pcr_expiry, pd.DataFrame), "pcr_expiry not a DataFrame"
    assert_df(pcr_ticker, required_cols=["pcr_volume", "pcr_oi"])
    assert_df(pcr_expiry,
              required_cols=["ticker", "expiration", "pcr_volume", "pcr_oi",
                             "days_to_exp", "horizon"])
    passed("compute_put_call_ratios",
           f"pcr_ticker: {len(pcr_ticker)} rows, pcr_expiry: {len(pcr_expiry)} rows")
except Exception as e:
    failed("compute_put_call_ratios", str(e))

# --- compute_forward_returns ---
# Use bundled prices for richer data (500 rows across 4 tickers)
try:
    prices_src = df_prices if df_prices is not None else cleaned_prices
    if prices_src is None:
        raise RuntimeError("No prices DataFrame available")
    fwd = etf_iv.compute_forward_returns(prices_src, windows=[1, 5])
    assert_df(fwd, required_cols=["ticker", "Date", "Close", "fwd_1d", "fwd_5d"])
    passed("compute_forward_returns",
           f"{len(fwd)} rows with fwd_1d, fwd_5d columns")
except Exception as e:
    failed("compute_forward_returns", str(e))

# --- compute_forward_returns with custom windows ---
try:
    prices_src = df_prices if df_prices is not None else cleaned_prices
    if prices_src is None:
        raise RuntimeError("No prices DataFrame available")
    fwd2 = etf_iv.compute_forward_returns(prices_src, windows=[10, 21])
    assert "fwd_10d" in fwd2.columns and "fwd_21d" in fwd2.columns, \
        "Custom window columns missing"
    passed("compute_forward_returns_custom_windows",
           "fwd_10d and fwd_21d columns present")
except Exception as e:
    failed("compute_forward_returns_custom_windows", str(e))

# --- compute_iv_skew ---
try:
    # Prefers opts_with_mono (has moneyness + dte from add_spot_and_moneyness).
    # Fallback: df_filtered has moneyness but not dte; we compute dte from expiration.
    opts_for_skew = opts_with_mono
    if opts_for_skew is None and df_filtered is not None:
        opts_for_skew = df_filtered.copy()
        if "dte" not in opts_for_skew.columns:
            today = pd.Timestamp.today().normalize()
            opts_for_skew["dte"] = (
                pd.to_datetime(opts_for_skew["expiration"]) - today
            ).dt.days
    if opts_for_skew is None:
        raise RuntimeError("No options-with-moneyness DataFrame available")
    missing_cols = [c for c in ["moneyness", "dte"] if c not in opts_for_skew.columns]
    if missing_cols:
        raise RuntimeError(f"Missing columns for iv_skew after preparation: {missing_cols}")
    skew = etf_iv.compute_iv_skew(opts_for_skew)
    assert isinstance(skew, pd.DataFrame), "Expected DataFrame"
    assert_df(skew, required_cols=["atm_iv", "otm_iv", "iv_skew", "n_atm", "n_otm"])
    passed("compute_iv_skew",
           f"{len(skew)} tickers; iv_skew range "
           f"[{skew['iv_skew'].min():.4f}, {skew['iv_skew'].max():.4f}]")
except Exception as e:
    failed("compute_iv_skew", str(e))

# --- compute_earnings_proximity ---
try:
    h = cleaned_hold if cleaned_hold is not None else df_holdings
    e = cleaned_earn if cleaned_earn is not None else df_earnings
    if h is None or e is None:
        raise RuntimeError("Holdings or earnings not available")
    if "etf_ticker" not in e.columns and "ticker" in e.columns:
        e = e.rename(columns={"ticker": "etf_ticker"})
    ep = etf_iv.compute_earnings_proximity(
        h, e,
        today=pd.Timestamp("2025-04-13"),
        top_n=10,
    )
    assert isinstance(ep, pd.DataFrame), "Expected DataFrame"
    assert_df(ep, required_cols=["weighted_dte_earnings", "pct_within_30d",
                                  "pct_within_60d", "n_holdings_with_dates"])
    passed("compute_earnings_proximity", f"{len(ep)} ETFs in result")
except Exception as e:
    failed("compute_earnings_proximity", str(e))
    traceback.print_exc()


# ===========================================================================
# Summary
# ===========================================================================

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)

n_pass = sum(1 for r in results if r[0] == "PASS")
n_fail = sum(1 for r in results if r[0] == "FAIL")
n_skip = sum(1 for r in results if r[0] == "SKIP")

print(f"Total: {len(results)}  |  PASS: {n_pass}  |  FAIL: {n_fail}  |  SKIP: {n_skip}")

if n_fail:
    print("\nFailed tests:")
    for r in results:
        if r[0] == "FAIL":
            print(f"  - {r[1]}: {r[2]}")

sys.exit(0 if n_fail == 0 else 1)
