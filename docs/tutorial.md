# Tutorial: ETF Implied Volatility Explorer

This tutorial walks you through installing the `etf_iv` package and using it
to explore ETF options data, holdings, and news sentiment — with and without
network access.

---

## Prerequisites

- Python 3.11 or later
- Git

---

## 1. Clone the Repository

```bash
git clone https://github.com/jilliangbaker97/Final-Project-386.git
cd Final-Project-386
```

---

## 2. Create a Virtual Environment and Install

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
pip install -e .                 # installs the etf_iv package in editable mode
```

---

## 3. Using the Bundled Dataset (No API Keys Needed)

All data is pre-collected and bundled with the package. You can load any
dataset with a single import — no network access or API keys required.

```python
from etf_iv import (
    load_price_history,
    load_options_filtered,
    load_etf_holdings,
    load_earnings_dates,
    load_etf_sentiment,
)

# 6-month daily price history for VOO, QQQ, ARKQ, BOTZ
prices = load_price_history()
print(prices.head())
#    ticker       Date    Open    High     Low   Close     Volume
# 0    ARKQ 2024-10-01  ...

# Liquidity-filtered options chain with moneyness and spot price
options = load_options_filtered()
print(options.shape)
# (4823, 11)

# Top holdings per ETF
holdings = load_etf_holdings()
print(holdings[holdings["etf_ticker"] == "QQQ"].head(3))

# Earnings dates for each holding
earnings = load_earnings_dates()

# Claude-scored news sentiment (1=very bearish, 5=very bullish)
sentiment = load_etf_sentiment()
print(sentiment)
#   etf_ticker  num_articles  sentiment_score sentiment_label
# 0        VOO            10                4        Positive
```

---

## 4. Cleaning Raw Data

If you collect fresh data, the cleaning module standardizes it for analysis.

```python
from etf_iv import clean_prices, clean_options, filter_liquidity, add_spot_and_moneyness

# Clean a raw price DataFrame from yfinance
clean_px = clean_prices(raw_prices)

# Clean a raw options chain and apply liquidity filters
clean_opts = clean_options(raw_options)
filtered   = filter_liquidity(clean_opts, min_volume=1, min_open_interest=10)

# Join spot prices and compute moneyness (strike / spot) and DTE
enriched = add_spot_and_moneyness(filtered, clean_px)
print(enriched[["ticker", "strike", "spot_price", "moneyness", "dte"]].head())
```

---

## 5. Running Analysis Functions

```python
from etf_iv import (
    compute_put_call_ratios,
    compute_iv_skew,
    compute_earnings_proximity,
    compute_forward_returns,
)

options  = load_options_filtered()
prices   = load_price_history()
holdings = load_etf_holdings()
earnings = load_earnings_dates()

# Put/Call Ratios — returns (ticker-level, expiration-level) DataFrames
pcr_ticker, pcr_expiry = compute_put_call_ratios(options)
print(pcr_ticker[["pcr_volume", "pcr_oi"]])

# IV Skew — OTM put IV minus ATM put IV for each ETF
skew = compute_iv_skew(options)
print(skew[["atm_iv", "otm_iv", "iv_skew"]])

# Earnings Proximity — weight-normalized days until top holdings report
proximity = compute_earnings_proximity(holdings, earnings)
print(proximity[["weighted_dte_earnings", "pct_within_30d"]])

# Forward Returns — 1-day and 5-day returns from price history
returns = compute_forward_returns(prices)
print(returns[["fwd_1d", "fwd_5d"]].tail())
```

---

## 6. Collecting Fresh Data (Optional)

You can re-collect live data using yfinance and stockanalysis.com scraping.
No API key is needed for price history, options, or holdings.

```python
from etf_iv import get_price_history, get_options_chain, get_etf_holdings

prices  = get_price_history("QQQ", period="6mo")
options = get_options_chain("QQQ")
holding = get_etf_holdings("QQQ")
```

### Fresh Sentiment Scores (Requires Anthropic API Key)

```bash
export ANTHROPIC_API_KEY="sk-ant-..."   # macOS/Linux
set ANTHROPIC_API_KEY=sk-ant-...        # Windows
```

```python
from etf_iv import get_etf_headlines, get_sentiment_score

headlines = get_etf_headlines("ARKQ", max_articles=10)
score     = get_sentiment_score("ARKQ", headlines)
print(f"ARKQ sentiment: {score}/5")
```

---

## 7. Running the Streamlit App Locally

```bash
streamlit run streamlit_app.py
```

Then open `http://localhost:8501` in your browser. The app loads the bundled
dataset automatically — no API keys or network access needed.

Or visit the [live deployed app](https://final-project-386.streamlit.app).

---

## 8. Running the Full Analysis Notebook

```bash
jupyter notebook final_project.ipynb
```

The notebook is organized into 9 sections. Each section loads bundled data
by default, with optional "Collect Fresh Data" cells you can run separately.

| Section | Content                                 |
| ------- | --------------------------------------- |
| 1       | Scraping compliance check               |
| 2       | Price history collection & cleaning     |
| 3       | Options chain collection & cleaning     |
| 4       | Spot price join & moneyness             |
| 5       | Liquidity filtering                     |
| 6       | ETF holdings scraping                   |
| 7       | Earnings dates scraping                 |
| 8       | News sentiment scoring (Claude API)     |
| 9       | Put/Call ratio analysis & visualization |
| 10      | IV skew vs. earnings proximity analysis |

---

## Project Structure

```
etf_iv/                    # Installable Python package
  __init__.py              # Public API (21 functions)
  data_collection.py       # Options chains, price history, holdings scraping
  sentiment.py             # Claude-powered headline sentiment scoring
  cleaning.py              # Data cleaning and filtering
  analysis.py              # PCR, forward returns, IV skew, earnings proximity
  data/                    # Bundled CSV datasets
docs/                      # GitHub Pages website
  index.md                 # Landing page with project links
  tutorial.md              # This tutorial
  report.md                # Technical report
  api/                     # Auto-generated API documentation (pdoc)
final_project.ipynb        # Main analysis notebook
streamlit_app.py           # Interactive Streamlit dashboard
requirements.txt           # Pinned dependency versions
pyproject.toml             # Package metadata
test_etf_iv.py             # Pytest test suite
```

---

## Links

- [Streamlit App](https://final-project-386.streamlit.app)
- [GitHub Repository](https://github.com/jilliangbaker97/Final-Project-386)
- [API Documentation](api/etf_iv.html)
