# Technical Report: ETF Implied Volatility, Options Sentiment & Earnings Analysis

**STAT 386 Final Project** — Jillian Baker & Golden Huang

---

## Motivation

Options markets encode forward-looking information that price history alone
cannot capture. When traders buy puts aggressively, they are paying for
downside protection — and that collective behavior shows up in two
measurable signals: the **put/call ratio (PCR)** and **implied volatility
skew**. This project asks whether those signals contain meaningful
information about future returns and earnings risk for four ETFs that span
different investment styles:

| ETF  | Focus                                        |
| ---- | -------------------------------------------- |
| VOO  | S&P 500 broad market                         |
| QQQ  | Nasdaq-100 large-cap tech                    |
| ARKQ | ARK autonomous & robotics (actively managed) |
| BOTZ | Global X robotics & AI (index-based)         |

Two research questions guided the analysis:

1. **Do extreme put/call ratios predict short-term forward returns?**
2. **Does implied-volatility skew correlate with earnings proximity of top holdings?**

---

## Data Collection

All data was collected in a reproducible, compliance-conscious pipeline:

**Price history** — Six months of daily OHLCV data for all four ETFs via
the `yfinance` library. Data was cleaned for duplicates, missing values,
and dtype consistency.

**Options chains** — Full listed strikes across every expiration date,
fetched via `yfinance`. Each contract was joined with the underlying spot
price to compute moneyness (strike / spot). Contracts with fewer than 1
trade in volume or fewer than 10 in open interest were dropped as
illiquid.

**Holdings and earnings** — Top-25 holdings and their portfolio weights
were scraped from stockanalysis.com for each ETF. Next earnings dates were
scraped for each individual holding ticker. Scraping compliance was
verified via `robots.txt` before any requests were made, and a 1.5-second
delay was enforced between requests.

**News sentiment** — Recent headlines for each ETF were retrieved via
`yfinance` and scored on a 1–5 scale (1 = very bearish, 5 = very bullish)
using the Anthropic Claude API with structured tool-use output for
consistency.

All collected data is bundled as CSV files inside the `etf_iv` package so
the full analysis can be reproduced without any network access or API keys.

---

## Methodology

### Put/Call Ratio Analysis

The put/call ratio was computed two ways for each ETF:

- **Aggregate PCR** — total put volume divided by total call volume across
  all expirations, as well as the same ratio using open interest instead of
  volume.
- **Expiration-bucketed PCR** — a separate PCR computed for each individual
  expiration date, bucketed into near (≤30 days), mid (31–90 days), and far
  (>90 days) horizons. This increases the number of observations beyond the
  four-ticker cross-section.

Threshold-based signals were applied: PCR > 1.5 was labeled bearish and
PCR < 0.5 was labeled bullish. Forward returns of 1 day and 5 days were
computed from price history using percentage change with a forward shift.
Pearson and Spearman correlations were then computed between PCR and
forward returns.

### IV Skew vs. Earnings Proximity

IV skew was defined as the difference between median OTM put implied
volatility and median ATM put implied volatility:

> **IV Skew = median(OTM Put IV) − median(ATM Put IV)**

ATM puts were defined as moneyness in [0.97, 1.03] and OTM puts as
moneyness in [0.85, 0.97). The analysis was restricted to options with
15–60 days to expiration to capture the earnings-window premium while
avoiding ultra-short-dated noise.

Earnings proximity was measured as a **weight-normalized days-to-earnings**
metric: for each ETF's top-10 holdings, the days until each holding reports
earnings were averaged using the holding's portfolio weight as the weight.
This gives heavier-weighted constituents more influence on the proximity
score. An OLS trend line was fit to test whether ETFs with nearer earnings
exhibit steeper skews.

---

## Key Findings

### Put/Call Ratio

Broad-market ETFs (VOO, QQQ) carry structurally higher put/call ratios
driven by institutional hedging activity. This means that a raw PCR reading
of 1.5 or higher for these funds reflects normal hedging behavior rather
than genuine bearish sentiment — making PCR a poor standalone directional
signal for large index ETFs.

Thematic ETFs (ARKQ, BOTZ) have smaller, less liquid options markets.
Their PCR readings are more volatile and potentially more informative on a
relative basis, but are also more susceptible to distortion from a small
number of large trades.

Pearson and Spearman correlations between PCR and forward returns were
directionally suggestive but lacked statistical power given only four
cross-sectional observations. The expiration-bucketed approach increased
observations but could not establish causality.

### IV Skew

IV skew was persistently positive across all four ETFs, meaning OTM puts
were consistently priced above ATM puts. This is consistent with
well-documented demand for crash protection in equity options markets.

The cross-sectional comparison of IV skew against weighted days-to-earnings
provided directional support for the "earnings fear" hypothesis — ETFs
whose top holdings report sooner tend to show steeper skews. However, with
only four data points this relationship cannot be established statistically.
A stronger test would require daily IV snapshots tracked across the earnings
window for each holding.

---

## Limitations

- **Single snapshot design** — yfinance provides a current options chain,
  not a historical time series of IV or PCR. This means we cannot observe
  how these signals evolved before past price moves.
- **Small cross-sectional n** — With only four ETFs, all correlations are
  illustrative rather than statistically conclusive.
- **Holdings staleness** — ETF holdings are scraped at a single point in
  time and may not reflect intraday rebalancing.
- **Confounding factors** — ETFs differ in sector composition, average
  market cap, liquidity, and recent volatility, all of which affect options
  pricing independently of earnings proximity or sentiment.

---

## Reproducibility

All data is bundled with the package. To reproduce the full analysis:

```bash
git clone https://github.com/jilliangbaker97/Final-Project-386.git
cd Final-Project-386
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt && pip install -e .
jupyter notebook final_project.ipynb
```

See the [Tutorial](tutorial.html) for full setup instructions and the
[API Documentation](api/etf_iv.html) for function references.

---

## Links

- [Streamlit App](https://final-project-386.streamlit.app)
- [GitHub Repository](https://github.com/jilliangbaker97/Final-Project-386)
- [Tutorial](https://jilliangbaker97.github.io/Final-Project-386/tutorial.html)
- [API Documentation](https://jilliangbaker97.github.io/Final-Project-386/reference/index.html)
