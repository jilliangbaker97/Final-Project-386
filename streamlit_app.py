"""ETF Implied Volatility Explorer — Streamlit Dashboard.

Interactive visualization of options IV surfaces, put/call ratios,
holdings & earnings proximity, and price history for VOO, QQQ, ARKQ, BOTZ.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="ETF IV Explorer",
    page_icon="📊",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Data loading (cached)
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent / "etf_iv" / "data"
TICKERS = ["VOO", "QQQ", "ARKQ", "BOTZ"]


@st.cache_data
def load_options():
    df = pd.read_csv(DATA_DIR / "options_filtered.csv", parse_dates=["expiration"])
    today = pd.Timestamp.today().normalize()
    df["dte"] = (df["expiration"] - today).dt.days
    return df


@st.cache_data
def load_holdings():
    return pd.read_csv(DATA_DIR / "etf_holdings.csv")


@st.cache_data
def load_earnings():
    return pd.read_csv(DATA_DIR / "earnings_dates.csv", parse_dates=["earnings_date"])


@st.cache_data
def load_sentiment():
    return pd.read_csv(DATA_DIR / "etf_sentiment.csv")


@st.cache_data
def load_prices():
    return pd.read_csv(DATA_DIR / "price_history.csv", parse_dates=["Date"])


options = load_options()
holdings = load_holdings()
earnings = load_earnings()
sentiment = load_sentiment()
prices = load_prices()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

st.sidebar.title("ETF IV Explorer")
st.sidebar.markdown("STAT 386 Final Project")

selected = st.sidebar.multiselect(
    "Select ETFs",
    options=TICKERS,
    default=TICKERS,
)

if not selected:
    st.warning("Select at least one ETF from the sidebar.")
    st.stop()

st.sidebar.markdown("---")
st.sidebar.caption(
    "Data is pre-collected and bundled — no API keys required. "
    "See the project README for collection details."
)

# ---------------------------------------------------------------------------
# Helper: compute PCR tables
# ---------------------------------------------------------------------------


def compute_pcr(opts: pd.DataFrame):
    """Return (pcr_ticker, pcr_expiry) DataFrames from options data."""
    agg = (
        opts.groupby(["ticker", "contractType"])[["volume", "openInterest"]]
        .sum()
        .unstack("contractType")
    )
    agg.columns = ["_".join(c) for c in agg.columns]

    pcr_ticker = pd.DataFrame(
        {
            "pcr_volume": agg["volume_put"] / agg["volume_call"],
            "pcr_oi": agg["openInterest_put"] / agg["openInterest_call"],
            "put_volume": agg["volume_put"],
            "call_volume": agg["volume_call"],
            "put_oi": agg["openInterest_put"],
            "call_oi": agg["openInterest_call"],
        }
    ).round(4)

    agg_exp = (
        opts.groupby(["ticker", "expiration", "contractType"])[
            ["volume", "openInterest"]
        ]
        .sum()
        .unstack("contractType")
        .fillna(0)
    )
    agg_exp.columns = ["_".join(c) for c in agg_exp.columns]

    pcr_expiry = pd.DataFrame(
        {
            "pcr_volume": (
                agg_exp["volume_put"]
                / agg_exp["volume_call"].replace(0, np.nan)
            ),
            "pcr_oi": (
                agg_exp["openInterest_put"]
                / agg_exp["openInterest_call"].replace(0, np.nan)
            ),
        }
    ).reset_index()

    today = pd.Timestamp.today().normalize()
    pcr_expiry["days_to_exp"] = (pcr_expiry["expiration"] - today).dt.days
    pcr_expiry["horizon"] = pd.cut(
        pcr_expiry["days_to_exp"],
        bins=[-np.inf, 30, 90, np.inf],
        labels=["near (≤30d)", "mid (31-90d)", "far (>90d)"],
    )
    return pcr_ticker, pcr_expiry


# ---------------------------------------------------------------------------
# Metric cards
# ---------------------------------------------------------------------------

st.title("ETF Implied Volatility Explorer")

opts_sel = options[options["ticker"].isin(selected)]
pcr_ticker, _ = compute_pcr(opts_sel)

cols = st.columns(len(selected))
for i, ticker in enumerate(selected):
    with cols[i]:
        spot = opts_sel.loc[opts_sel["ticker"] == ticker, "spot_price"]
        spot_val = f"${spot.iloc[0]:,.2f}" if len(spot) > 0 else "N/A"

        pcr_val = (
            f"{pcr_ticker.loc[ticker, 'pcr_oi']:.2f}"
            if ticker in pcr_ticker.index
            else "N/A"
        )

        sent_row = sentiment[sentiment["etf_ticker"] == ticker]
        sent_label = sent_row["sentiment_label"].iloc[0] if len(sent_row) > 0 else "N/A"
        num_articles = int(sent_row["num_articles"].iloc[0]) if len(sent_row) > 0 else 0

        st.metric(label=f"{ticker} Spot", value=spot_val)
        st.metric(label="PCR (OI)", value=pcr_val)
        st.metric(label="Sentiment", value=sent_label)
        st.caption(f"Based on {num_articles} article{'s' if num_articles != 1 else ''}")

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab_iv, tab_pcr, tab_hold, tab_price = st.tabs(
    ["IV Surface", "Put/Call Ratio", "Holdings & Earnings", "Price History"]
)

# ---- Tab 1: IV Surface ---------------------------------------------------

with tab_iv:
    contract_type = st.radio(
        "Option type", ["call", "put"], horizontal=True, key="iv_type"
    )

    moneyness_bins = [0.80, 0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15, 1.20]
    moneyness_labels = [
        f"{moneyness_bins[j]:.2f}–{moneyness_bins[j+1]:.2f}"
        for j in range(len(moneyness_bins) - 1)
    ]
    dte_bins = [0, 15, 30, 60, 90, 1000]
    dte_labels = ["1–15d", "16–30d", "31–60d", "61–90d", ">90d"]

    n_tickers = len(selected)
    fig = make_subplots(
        rows=1,
        cols=n_tickers,
        subplot_titles=selected,
        horizontal_spacing=0.05,
    )

    for idx, ticker in enumerate(selected):
        sub = opts_sel[
            (opts_sel["ticker"] == ticker)
            & (opts_sel["contractType"] == contract_type)
        ].copy()

        if len(sub) < 3:
            fig.add_annotation(
                text="Insufficient data",
                xref=f"x{idx+1}" if idx > 0 else "x",
                yref=f"y{idx+1}" if idx > 0 else "y",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=14),
            )
            continue

        sub["m_bin"] = pd.cut(
            sub["moneyness"], bins=moneyness_bins, labels=moneyness_labels
        )
        sub["dte_bin"] = pd.cut(sub["dte"], bins=dte_bins, labels=dte_labels)

        pivot = (
            sub.groupby(["dte_bin", "m_bin"], observed=False)["impliedVolatility"]
            .median()
            .unstack("m_bin")
        )
        pivot = pivot * 100  # display as %

        fig.add_trace(
            go.Heatmap(
                z=pivot.values,
                x=[str(c) for c in pivot.columns],
                y=[str(r) for r in pivot.index],
                colorscale="YlOrRd",
                colorbar=dict(title="IV %") if idx == n_tickers - 1 else None,
                showscale=(idx == n_tickers - 1),
                zmin=0,
                zmax=pivot.values[~np.isnan(pivot.values)].max() if pivot.notna().any().any() else 100,
                hovertemplate="Moneyness: %{x}<br>DTE: %{y}<br>IV: %{z:.1f}%<extra></extra>",
            ),
            row=1,
            col=idx + 1,
        )

    fig.update_layout(
        height=450,
        title_text=f"Implied Volatility Surface ({contract_type.title()}s)",
        margin=dict(t=80),
    )
    st.plotly_chart(fig, use_container_width=True)

# ---- Tab 2: Put/Call Ratio -----------------------------------------------

with tab_pcr:
    pcr_ticker_full, pcr_expiry_full = compute_pcr(opts_sel)

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("Ticker-Level Summary")
        display_pcr = pcr_ticker_full.copy()
        display_pcr.index.name = "ticker"
        st.dataframe(
            display_pcr.style.format(
                {
                    "pcr_volume": "{:.4f}",
                    "pcr_oi": "{:.4f}",
                    "put_volume": "{:,.0f}",
                    "call_volume": "{:,.0f}",
                    "put_oi": "{:,.0f}",
                    "call_oi": "{:,.0f}",
                }
            ),
            use_container_width=True,
        )

    with col_right:
        st.subheader("PCR (OI) by Ticker")
        bar_df = pcr_ticker_full[["pcr_oi"]].reset_index()
        bar_df.columns = ["ticker", "pcr_oi"]
        bar_df["color"] = bar_df["pcr_oi"].apply(
            lambda v: "Bearish (>1.5)" if v > 1.5 else ("Bullish (<0.5)" if v < 0.5 else "Neutral")
        )
        color_map = {
            "Bearish (>1.5)": "#ef4444",
            "Bullish (<0.5)": "#22c55e",
            "Neutral": "#94a3b8",
        }
        fig_bar = px.bar(
            bar_df,
            x="ticker",
            y="pcr_oi",
            color="color",
            color_discrete_map=color_map,
            labels={"pcr_oi": "Put/Call Ratio (OI)", "ticker": ""},
        )
        fig_bar.update_layout(
            showlegend=True,
            legend_title_text="Signal",
            height=350,
            margin=dict(t=30),
        )
        fig_bar.add_hline(y=1.0, line_dash="dash", line_color="gray", annotation_text="PCR=1.0")
        st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("Expiration-Level Detail")
    exp_display = pcr_expiry_full[pcr_expiry_full["ticker"].isin(selected)].copy()
    exp_display["expiration"] = exp_display["expiration"].dt.strftime("%Y-%m-%d")
    exp_display = exp_display.round(4)
    st.dataframe(
        exp_display[["ticker", "expiration", "pcr_volume", "pcr_oi", "days_to_exp", "horizon"]],
        use_container_width=True,
        hide_index=True,
    )

# ---- Tab 3: Holdings & Earnings ------------------------------------------

with tab_hold:
    etf_pick = st.selectbox(
        "Select ETF for holdings detail", selected, key="hold_etf"
    )

    today = pd.Timestamp.today().normalize()

    h = holdings[holdings["etf_ticker"] == etf_pick].copy()
    e = earnings[earnings["etf_ticker"] == etf_pick].copy()

    merged = h.merge(
        e[["holding_ticker", "etf_ticker", "earnings_date"]],
        on=["holding_ticker", "etf_ticker"],
        how="left",
    )
    merged["days_to_earnings"] = (merged["earnings_date"] - today).dt.days
    merged = merged.sort_values("weight_pct", ascending=False).reset_index(drop=True)

    top10 = merged.head(10)
    with_dates = top10.dropna(subset=["days_to_earnings"])
    pct_30 = (
        (with_dates["days_to_earnings"] <= 30).mean() * 100
        if len(with_dates) > 0
        else 0
    )
    pct_60 = (
        (with_dates["days_to_earnings"] <= 60).mean() * 100
        if len(with_dates) > 0
        else 0
    )

    m1, m2, m3 = st.columns(3)
    m1.metric("Holdings shown", len(merged))
    m2.metric("Top-10 w/ earnings ≤30d", f"{pct_30:.0f}%")
    m3.metric("Top-10 w/ earnings ≤60d", f"{pct_60:.0f}%")

    def highlight_earnings(row):
        dte = row.get("days_to_earnings")
        if pd.isna(dte):
            return [""] * len(row)
        if dte <= 30:
            return [f"background-color: rgba(239,68,68,0.15)"] * len(row)
        if dte <= 60:
            return [f"background-color: rgba(234,179,8,0.15)"] * len(row)
        return [""] * len(row)

    display_cols = ["holding_ticker", "company_name", "weight_pct", "earnings_date", "days_to_earnings"]
    display_df = merged[display_cols].copy()
    display_df["earnings_date"] = display_df["earnings_date"].dt.strftime("%Y-%m-%d").fillna("—")
    display_df["days_to_earnings"] = display_df["days_to_earnings"].fillna(-1).astype(int)
    display_df.loc[display_df["days_to_earnings"] == -1, "days_to_earnings"] = None

    styled = display_df.style.apply(highlight_earnings, axis=1).format(
        {"weight_pct": "{:.2f}%"},
        na_rep="—",
    )
    st.dataframe(styled, use_container_width=True, hide_index=True, height=600)
    st.caption("Red = earnings within 30 days · Yellow = within 60 days")

# ---- Tab 4: Price History -------------------------------------------------

with tab_price:
    p = prices[prices["ticker"].isin(selected)].copy()
    p = p.sort_values(["ticker", "Date"])
    p["SMA_20"] = p.groupby("ticker")["Close"].transform(
        lambda s: s.rolling(20, min_periods=1).mean()
    )

    fig_price = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.7, 0.3],
        subplot_titles=["Close Price & 20-Day SMA", "Daily Volume"],
    )

    colors = px.colors.qualitative.Set2
    for i, ticker in enumerate(selected):
        t = p[p["ticker"] == ticker]
        color = colors[i % len(colors)]

        fig_price.add_trace(
            go.Scatter(
                x=t["Date"], y=t["Close"],
                name=f"{ticker}",
                line=dict(color=color, width=2),
                legendgroup=ticker,
            ),
            row=1, col=1,
        )
        fig_price.add_trace(
            go.Scatter(
                x=t["Date"], y=t["SMA_20"],
                name=f"{ticker} SMA20",
                line=dict(color=color, width=1, dash="dot"),
                legendgroup=ticker,
                showlegend=False,
            ),
            row=1, col=1,
        )
        fig_price.add_trace(
            go.Bar(
                x=t["Date"], y=t["Volume"],
                name=f"{ticker} vol",
                marker_color=color,
                opacity=0.5,
                legendgroup=ticker,
                showlegend=False,
            ),
            row=2, col=1,
        )

    fig_price.update_layout(
        height=600,
        margin=dict(t=60),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )
    fig_price.update_yaxes(title_text="Price ($)", row=1, col=1)
    fig_price.update_yaxes(title_text="Volume", row=2, col=1)

    st.plotly_chart(fig_price, use_container_width=True)
