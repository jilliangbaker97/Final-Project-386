# CLAUDE.md

## Project Overview

**etf-iv** -- STAT 386 Final Project analyzing ETF implied volatility, options data, sentiment, and earnings.

Analyzes four ETFs: **VOO, QQQ, ARKQ, BOTZ**. Research questions:
- Do extreme put/call ratios predict forward returns?
- Does implied volatility skew correlate with earnings proximity?

## Tech Stack

- Python 3.11+ (pandas 3.x requires it)
- yfinance for market data, BeautifulSoup + lxml for web scraping
- Anthropic Claude API for sentiment analysis (requires `ANTHROPIC_API_KEY` env var)
- Jupyter notebook for analysis, matplotlib/seaborn for visualization

## Project Structure

```
etf_iv/                    # Reusable Python package
  __init__.py              # Public API exports (21 functions: 6 loaders + 5 collection + 6 cleaning + 4 analysis)
  data_collection.py       # Options chains, price history, holdings scraping
  sentiment.py             # Claude-powered headline sentiment scoring (tool use)
  cleaning.py              # Data cleaning: prices, options, liquidity, moneyness, holdings, earnings
  analysis.py              # Derived metrics: PCR, forward returns, IV skew, earnings proximity
  data/                    # Bundled dataset (ships with package)
    __init__.py            # load_* functions using importlib.resources
    price_history.csv      # 6-month OHLCV for VOO, QQQ, ARKQ, BOTZ
    options_chain.csv      # Full options chains (cleaned)
    options_with_spot.csv  # Options with spot price and moneyness
    options_filtered.csv   # Liquidity-filtered options (volume >= 1, OI >= 10)
    etf_holdings.csv       # Top 25 holdings per ETF from stockanalysis.com
    earnings_dates.csv     # Next earnings dates for holdings
    etf_sentiment.csv      # Claude-scored news sentiment (1-5 scale)
data_collection.py         # Backward-compatible shim re-exporting from etf_iv
final_project.ipynb        # Main analysis notebook (103 cells, 9 sections)
pyproject.toml             # Package metadata and dependencies
requirements.txt           # Pinned dependencies for reproducibility
```

## Dual-Mode Data Access

The notebook supports two paths for every dataset:

- **Default (bundled):** `etf_iv.load_price_history()` etc. — works instantly, no network or API keys needed. Data lives in `etf_iv/data/*.csv` and ships with the package.
- **Fresh collection:** `etf_iv.get_price_history()` etc. — fetches live data from yfinance, stockanalysis.com, or Anthropic. Requires network; sentiment requires `ANTHROPIC_API_KEY`.

Each notebook section has a "Load bundled" cell followed by "Optional: Collect Fresh Data" cells.

## Setup & Run

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pip install -e .           # Install etf_iv in editable mode
jupyter notebook final_project.ipynb
```

## Code Conventions

- Snake_case for functions and columns
- NumPy-style docstrings with Parameters/Returns/Raises/Examples
- Functions return pandas DataFrames; raise ValueError on bad input
- Logging via `logging.getLogger(__name__)`
- Polite scraping: User-Agent headers, robots.txt checks, 15s timeout
- DataFrames copied before mutation

## No Test Suite

Validation is done inline in notebook cells. No pytest or unittest setup exists.

## Key External Dependencies

- **yfinance** -- no auth needed (used by live collection functions)
- **Anthropic API** -- needs `ANTHROPIC_API_KEY` in environment (only for fresh sentiment scoring)
- **stockanalysis.com** -- scraped for holdings and earnings dates (only for fresh collection)
- **None required for bundled data** -- `etf_iv.data.load_*()` functions work offline
