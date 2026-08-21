from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

import requests

# This is the first service in the app needing a genuinely new external
# data source rather than another yfinance endpoint. Built against
# NewsAPI.org's documented /v2/everything endpoint specifically --
# https://newsapi.org/docs/endpoints/everything -- since it's a
# well-documented, widely-used news API with a free tier suitable for
# prototyping. Getting a NEWS_API_KEY requires actually signing up there
# (or swapping this for a different provider); this service can't do
# that step for you, but is otherwise ready to use the moment a key is
# configured.
_NEWS_API_URL = "https://newsapi.org/v2/everything"

_ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_API_VERSION = "2023-06-01"
_DEFAULT_MODEL = "claude-sonnet-4-6"

# Hard ceiling on how many headlines get sent for sentiment scoring per
# call -- bounds cost/latency/prompt size the same way
# MarketSummaryService bounds its response length, and keeps one bad
# batch from blocking on an unbounded number of headlines.
_MAX_HEADLINES = 10


@dataclass
class HeadlineSentiment:
    """One headline and its scored sentiment."""

    headline: str
    url: str
    published_at: str
    sentiment: str  # "positive" | "negative" | "neutral"
    score: float  # -1.0 (bearish) to +1.0 (bullish)


@dataclass
class SentimentSummary:
    """
    Aggregated sentiment across a ticker's recent headlines.

    Attributes:
        ticker: The ticker searched.
        headlines: Per-headline sentiment, in the order the news API
            returned them (most recent first).
        overall_sentiment: Majority label across `headlines`.
        overall_score: Mean of every headline's score.
    """

    ticker: str
    headlines: list[HeadlineSentiment] = field(default_factory=list)
    overall_sentiment: str = "neutral"
    overall_score: float = 0.0


class SentimentService:
    """
    Fetches recent news headlines for a ticker and scores their
    sentiment.

    Isolated, opt-in add-on, same as MarketSummaryService: needs BOTH
    NEWS_API_KEY and ANTHROPIC_API_KEY configured (via Streamlit secrets
    or the environment) to do anything. If either is missing,
    serve_sentiment() returns None -- AnalysisService/AnalysisResult have
    no knowledge of this service, and a missing key or an outage on
    either API can never break core stock analysis.

    Sentiment scoring batches every fetched headline into a SINGLE
    Anthropic API call (asking for one JSON sentiment object per
    headline) rather than one call per headline -- fewer round trips,
    lower latency and cost, same per-headline granularity in the result.
    """

    def __init__(self, model: str = _DEFAULT_MODEL) -> None:
        self._news_api_key = self._get_config("NEWS_API_KEY")
        self._anthropic_api_key = self._get_config("ANTHROPIC_API_KEY")
        self._model = model

    def serve_sentiment(self, ticker: str) -> SentimentSummary | None:
        """
        Fetch recent headlines for `ticker` and score their sentiment.

        Returns:
            SentimentSummary, or None if either API key is missing, the
            news fetch fails or returns nothing, or sentiment scoring
            fails entirely -- never raises.
        """
        if not self._news_api_key or not self._anthropic_api_key:
            return None

        articles = self._fetch_headlines(ticker)
        if not articles:
            return None

        scored = self._score_sentiment([a["title"] for a in articles])
        if scored is None:
            return None

        headlines = [
            HeadlineSentiment(
                headline=article["title"],
                url=article.get("url", ""),
                published_at=article.get("publishedAt", ""),
                sentiment=item.get("sentiment", "neutral"),
                score=float(item.get("score", 0.0)),
            )
            for article, item in zip(articles, scored)
        ]

        return SentimentSummary(
            ticker=ticker,
            headlines=headlines,
            overall_sentiment=self._majority_label(headlines),
            overall_score=(
                sum(h.score for h in headlines) / len(headlines) if headlines else 0.0
            ),
        )

    def _fetch_headlines(self, ticker: str) -> list[dict]:
        """
        Fetch recent headlines mentioning `ticker` from NewsAPI.org.

        Returns:
            List of article dicts (NewsAPI.org's own shape: "title",
            "url", "publishedAt", ...), or [] on any failure.
        """
        try:
            response = requests.get(
                _NEWS_API_URL,
                headers={"X-Api-Key": self._news_api_key},
                params={
                    "q": ticker,
                    "sortBy": "publishedAt",
                    "language": "en",
                    "pageSize": _MAX_HEADLINES,
                },
                timeout=15,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception:
            return []

        articles = payload.get("articles", [])
        # Defensive: only keep articles that actually have a title --
        # NewsAPI.org occasionally returns "[Removed]" placeholder
        # articles for takedowns, which aren't useful to score.
        return [
            article
            for article in articles[:_MAX_HEADLINES]
            if article.get("title") and article["title"] != "[Removed]"
        ]

    def _score_sentiment(self, headlines: list[str]) -> list[dict] | None:
        """
        Score a batch of headlines' financial sentiment via one
        Anthropic API call.

        Returns:
            List of {"sentiment": ..., "score": ...} dicts, same length
            and order as `headlines`, or None if the call or the
            response's JSON parsing fails, or the returned array's
            length doesn't match the input (a malformed response isn't
            trustworthy enough to zip against the headlines positionally).
        """
        prompt = self._build_sentiment_prompt(headlines)

        try:
            response = requests.post(
                _ANTHROPIC_API_URL,
                headers={
                    "x-api-key": self._anthropic_api_key,
                    "anthropic-version": _ANTHROPIC_API_VERSION,
                    "content-type": "application/json",
                },
                json={
                    "model": self._model,
                    "max_tokens": 1024,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            text = "".join(
                block.get("text", "")
                for block in payload.get("content", [])
                if block.get("type") == "text"
            )
            parsed = json.loads(text)
        except Exception:
            return None

        if not isinstance(parsed, list) or len(parsed) != len(headlines):
            return None

        return parsed

    def _build_sentiment_prompt(self, headlines: list[str]) -> str:
        """Build the batched sentiment-classification prompt."""
        numbered = "\n".join(f"{i + 1}. {h}" for i, h in enumerate(headlines))
        return (
            "Classify the financial sentiment of each numbered headline "
            "below as one of: positive, negative, neutral (from the "
            "perspective of the company/stock it concerns).\n\n"
            "Respond with ONLY a JSON array, no other text, no markdown "
            "code fences. One object per headline, in the same order, "
            'each with exactly two keys: "sentiment" (one of '
            '"positive"/"negative"/"neutral") and "score" (a float from '
            "-1.0 to 1.0, negative meaning bearish, positive meaning "
            "bullish).\n\n"
            f"Headlines:\n{numbered}\n"
        )

    @staticmethod
    def _majority_label(headlines: list[HeadlineSentiment]) -> str:
        """Most common sentiment label across the batch, defaulting to neutral."""
        if not headlines:
            return "neutral"

        counts = {"positive": 0, "negative": 0, "neutral": 0}
        for headline in headlines:
            counts[headline.sentiment] = counts.get(headline.sentiment, 0) + 1

        return max(counts, key=counts.get)

    @staticmethod
    def _get_config(key: str) -> str | None:
        """Streamlit secrets first, then environment -- same pattern as
        NotificationService and MarketSummaryService."""
        try:
            import streamlit as st

            if key in st.secrets:
                return str(st.secrets[key])
        except Exception:
            pass

        return os.environ.get(key)
