# ETF Implied Volatility, Options Sentiment & Earnings Analysis

**STAT 386 Final Project** — Jillian Baker

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://final-project-386.streamlit.app)

## Project Description

This project builds a custom dataset by combining ETF options chains, price histories, top-fund holdings, earnings calendars, and AI-scored news sentiment for four ETFs that span different investment styles:

| ETF | Focus |
|------|-------|
| **VOO** | S&P 500 broad market |
| **QQQ** | Nasdaq-100 large-cap tech |
| **ARKQ** | ARK autonomous/robotics (thematic, actively managed) |
| **BOTZ** | Global X robotics & AI (thematic, index-based) |

The goal is to investigate two research questions:

1. **Do extreme put/call ratios predict forward returns?** We compute volume- and open-interest-based PCR at the ticker and expiration level, apply threshold signals (PCR > 1.5 bearish, PCR < 0.5 bullish), and test correlations with 1-day and 5-day forward returns.
2. **Does implied-volatility skew correlate with earnings proximity?** We measure IV skew (median OTM put IV minus median ATM put IV) for each ETF and compare it against a weight-normalized days-to-earnings metric derived from each fund's top-10 holdings.

## Interactive Dashboard

An interactive Streamlit app lets you explore the data without running the notebook:

- **Ticker selector** — filter by VOO, QQQ, ARKQ, BOTZ
- **IV Surface** — heatmap of implied volatility by moneyness and days-to-expiry
- **Put/Call Ratio** — summary table and color-coded bar chart with expiration detail
- **Holdings & Earnings** — top-25 holdings with earnings proximity highlighting
- **Price History** — daily close with 20-day SMA and volume

Run locally:

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Or visit the [deployed app](https://final-project-386.streamlit.app).

## Data Sources

- **[yfinance](https://github.com/ranaroussi/yfinance)** — 6-month OHLCV price history and full options chains (strikes, IV, volume, open interest) for all four ETFs. No authentication required.
- **[stockanalysis.com](https://stockanalysis.com)** — Web scraping (verified compliant via `robots.txt`) for:
  - Top-25 holdings and portfolio weights per ETF
  - Next earnings dates for each holding
- **Anthropic Claude API** — AI-powered sentiment scoring of ETF-related news headlines on a 1–5 scale (bearish to bullish), using structured tool-use output for consistency.

All collected data is bundled as CSV files in `etf_iv/data/`, so the full analysis can be reproduced without network access or API keys.

## Methodology

### Data Collection & Cleaning (Sections 1–7)

1. **Scraping compliance** — Fetch and parse `robots.txt`; confirm all target URLs are permitted; enforce 1.5 s delays and a descriptive User-Agent header.
2. **Price history** — 6 months of daily OHLCV via `yfinance`, cleaned for duplicates, missing values, and dtype consistency.
3. **Options chains** — All listed strikes across every expiration, joined with the underlying spot price to compute moneyness (strike / spot). Filtered for liquidity (volume >= 1, open interest >= 10).
4. **Holdings & earnings** — Top-25 holdings scraped from stockanalysis.com; next-earnings dates scraped for each holding ticker.
5. **Sentiment** — News headlines for each ETF scored by Claude with structured tool-use output (1 = very bearish, 5 = very bullish).

### Analysis (Sections 8–9)

- **Put/Call Ratio Analysis (Section 8)** — Aggregate and expiration-level PCR, bucketed by horizon (near <= 30 d, mid 31–90 d, far > 90 d). Pearson and Spearman correlations between PCR and forward returns. Dual-axis time-series plots, bar charts, and scatter plots.
- **IV Skew vs. Earnings Proximity (Section 9)** — Cross-sectional comparison of IV skew across the four ETFs ordered by weighted days-to-earnings. OLS trend line to test the "earnings fear" hypothesis (nearer earnings -> steeper skew). Side-by-side ATM vs. OTM IV visualization.

## Key Findings

- **Broad-market ETFs (VOO, QQQ)** carry structurally higher put/call ratios driven by institutional hedging, making raw PCR levels a poor standalone directional signal for these funds.
- **Thematic ETFs (ARKQ, BOTZ)** have smaller, less liquid options markets where PCR readings are more volatile and potentially more informative.
- **PCR–return correlations** are directionally suggestive but lack statistical power (n = 4 cross-sectional, single snapshot). The expiration-bucketed approach increases observations but cannot establish causality.
- **IV skew** tends to be persistently positive across all ETFs (OTM puts priced above ATM puts), consistent with well-documented demand for crash protection.
- The **earnings proximity** analysis provides directional intuition for the "earnings fear" hypothesis but is limited by the single-snapshot design — a stronger test would require daily IV time series across the earnings window.

See **Section 8** and **Section 9** of the notebook for full visualizations, correlation tables, and detailed interpretation.

## Reproduction Instructions

### Prerequisites

- Python 3.11 or later (required by pandas 3.x)
- Git

### Quick Start (bundled data — no API keys needed)

```bash
git clone https://github.com/jilliangbaker97/Final-Project-386.git
cd Final-Project-386

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
pip install -e .                 # install etf_iv package in editable mode

jupyter notebook final_project.ipynb
```

The notebook defaults to loading pre-collected data from `etf_iv/data/`. Every section works out of the box with no network access.

### Optional: Collect Fresh Data

Each notebook section includes an "Optional: Collect Fresh Data" cell. To use them:

- **Price history & options** — Just run the cells; yfinance requires no API key.
- **Holdings & earnings** — Just run the cells; stockanalysis.com scraping works without authentication.
- **Sentiment scoring** — Requires an Anthropic API key:

```bash
export ANTHROPIC_API_KEY="your-key-here"   # macOS/Linux
set ANTHROPIC_API_KEY=your-key-here        # Windows
```

## Project Structure

```
etf_iv/                    # Installable Python package
  __init__.py              # Public API (21 functions)
  data_collection.py       # Options chains, price history, holdings scraping
  sentiment.py             # Claude-powered headline sentiment scoring
  cleaning.py              # Data cleaning and filtering
  analysis.py              # PCR, forward returns, IV skew, earnings proximity
  data/                    # Bundled CSV datasets
    price_history.csv
    options_chain.csv
    options_with_spot.csv
    options_filtered.csv
    etf_holdings.csv
    earnings_dates.csv
    etf_sentiment.csv
final_project.ipynb        # Main analysis notebook (9 sections)
streamlit_app.py           # Interactive Streamlit dashboard
pyproject.toml             # Package metadata and dependencies
requirements.txt           # Pinned dependency versions
```
