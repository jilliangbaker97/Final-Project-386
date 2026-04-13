"""Sentiment analysis helpers using Anthropic Claude and yfinance news."""

from __future__ import annotations

import anthropic
import yfinance as yf

_DEFAULT_MODEL = "claude-sonnet-4-6"

_SENTIMENT_TOOL = {
    "name": "record_sentiment",
    "description": "Record the overall sentiment score for ETF news headlines.",
    "input_schema": {
        "type": "object",
        "properties": {
            "sentiment_score": {
                "type": "integer",
                "description": (
                    "Overall sentiment: "
                    "1 = Very Negative, 2 = Negative, 3 = Neutral, "
                    "4 = Positive, 5 = Very Positive"
                ),
                "minimum": 1,
                "maximum": 5,
            }
        },
        "required": ["sentiment_score"],
    },
}

SCORE_LABELS: dict[int, str] = {
    1: "Very Negative",
    2: "Negative",
    3: "Neutral",
    4: "Positive",
    5: "Very Positive",
}


def get_etf_headlines(ticker: str, max_articles: int = 10) -> list[str]:
    """Fetch up to *max_articles* recent news headlines for *ticker* via yfinance.

    Parameters
    ----------
    ticker : str
        ETF or stock ticker symbol (e.g. ``"QQQ"``).
    max_articles : int, optional
        Maximum number of headlines to return.  Defaults to ``10``.

    Returns
    -------
    list[str]
        Headline strings, potentially empty if no news is available.
    """
    t = yf.Ticker(ticker)
    articles = t.news or []
    headlines: list[str] = []
    for article in articles[:max_articles]:
        # yfinance may nest title under "content" or at top level
        content = article.get("content") or {}
        title = (
            content.get("title")
            or article.get("title")
            or article.get("headline", "")
        )
        if title:
            headlines.append(title)
    return headlines


def get_sentiment_score(
    ticker: str,
    headlines: list[str],
    *,
    model: str = _DEFAULT_MODEL,
    client: anthropic.Anthropic | None = None,
) -> int:
    """Score recent ETF news headlines on a 1-5 sentiment scale using Claude.

    Uses Anthropic **tool use** with ``tool_choice`` to guarantee a structured
    integer response.

    Parameters
    ----------
    ticker : str
        ETF ticker for context in the prompt.
    headlines : list[str]
        News headlines to evaluate.
    model : str, optional
        Anthropic model identifier.  Defaults to Claude Sonnet.
    client : anthropic.Anthropic, optional
        Pre-configured client.  If ``None``, a new client is created (reads
        ``ANTHROPIC_API_KEY`` from the environment).

    Returns
    -------
    int
        Sentiment score from 1 (very negative) to 5 (very positive).
    """
    if not headlines:
        return 3  # neutral when no data

    if client is None:
        client = anthropic.Anthropic()

    prompt = (
        f"You are a financial analyst. Given these recent news headlines about "
        f"the {ticker} ETF, rate the overall market sentiment on a scale of "
        f"1 (very negative) to 5 (very positive). Use the record_sentiment "
        f"tool to return your score.\n\n"
        + "\n".join(f"- {h}" for h in headlines)
    )

    response = client.messages.create(
        model=model,
        max_tokens=64,
        tools=[_SENTIMENT_TOOL],
        tool_choice={"type": "tool", "name": "record_sentiment"},
        messages=[{"role": "user", "content": prompt}],
    )

    for block in response.content:
        if block.type == "tool_use":
            return int(block.input["sentiment_score"])

    return 3  # fallback: neutral
