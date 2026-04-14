# ETF Implied Volatility, Options Sentiment & Earnings Analysis

**STAT 386 Final Project** — Jillian Baker

---

This project builds a custom dataset by combining ETF options chains, price
histories, top-fund holdings, earnings calendars, and AI-scored news
sentiment for four ETFs spanning different investment styles: **VOO**,
**QQQ**, **ARKQ**, and **BOTZ**.

Two research questions drive the analysis:

1. Do extreme put/call ratios predict short-term forward returns?
2. Does implied-volatility skew correlate with earnings proximity of top holdings?

---

## Links

| | |
|---|---|
| 🚀 [Streamlit App](https://final-project-386.streamlit.app) | Interactive dashboard — explore IV surfaces, put/call ratios, holdings, and price history |
| 📓 [Full Analysis Notebook](analysis.html) | Complete 9-section Jupyter notebook with all code and visualizations |
| 📄 [Technical Report](report.md) | Written summary of methodology, findings, and limitations |
| 📖 [Tutorial](tutorial.md) | Step-by-step guide to installing and using the `etf_iv` package |
| 🔧 [API Documentation](api/etf_iv.html) | Auto-generated function reference for all 21 package functions |
| 💻 [GitHub Repository](https://github.com/jilliangbaker97/Final-Project-386) | Source code, data, and notebook |

---

## Project Overview

### Data Sources

- **yfinance** — 6-month OHLCV price history and full options chains
- **stockanalysis.com** — Top-25 holdings and next earnings dates (scraped with robots.txt compliance)
- **Anthropic Claude API** — AI-scored news sentiment on a 1–5 scale

### Package

The `etf_iv` Python package exposes 21 functions for data collection,
cleaning, and analysis. All collected data is bundled as CSV files so the
full analysis runs without any network access or API keys.

```bash
pip install -e .
```

```python
from etf_iv import load_options_filtered, compute_iv_skew

options = load_options_filtered()
skew    = compute_iv_skew(options)
print(skew)
```

### Key Findings

- Broad-market ETFs (VOO, QQQ) carry structurally high put/call ratios
  from institutional hedging, making raw PCR a poor standalone directional
  signal for these funds.
- IV skew is persistently positive across all four ETFs, consistent with
  sustained demand for crash protection.
- ETFs whose top holdings have nearer earnings tend to show steeper IV
  skews, offering directional support for the "earnings fear" hypothesis —
  though the single-snapshot design limits statistical power.

---

*Built with Python, yfinance, Streamlit, and the Anthropic Claude API.*