# Import standard library packages.
import logging
import xml.etree.ElementTree as ET

# Import third party packages.
import requests
import streamlit as st

logger = logging.getLogger(__name__)


@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_google_news(ticker: str, max_results: int = 3) -> list[dict]:
    """
    Fetch top news articles from Google News RSS feed for a ticker.

    Uses Google News RSS feed which is more reliable than web scraping.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL').
        max_results: Maximum number of articles to return.

    Returns:
        A list of dictionaries with keys: title, url, source, date.
        Returns empty list if fetch fails.
    """
    try:
        # Google News RSS feed for stock-specific ticker search
        # Include "stock" keyword to filter for financial/trading news
        search_query = f"{ticker} stock"
        url = f"https://news.google.com/rss/search?q={search_query}"

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # Parse RSS XML
        root = ET.fromstring(response.content)

        # Define namespace for RSS
        ns = {"content": "http://purl.org/rss/1.0/modules/content/"}

        articles = []

        # Extract items from RSS feed
        for item in root.findall(".//item"):
            if len(articles) >= max_results:
                break

            try:
                # Extract title
                title_elem = item.find("title")
                title = title_elem.text if title_elem is not None else "Unknown Title"

                # Filter for stock/finance-related articles
                title_lower = title.lower()
                stock_keywords = [
                    "stock",
                    "share",
                    "trade",
                    "market",
                    "price",
                    "earning",
                    "revenue",
                    "investor",
                    "financial",
                    "fund",
                    "sec",
                    "ipo",
                    "dividend",
                ]
                if not any(kw in title_lower for kw in stock_keywords):
                    continue

                # Extract link
                link_elem = item.find("link")
                link = link_elem.text if link_elem is not None else ""

                if not link:
                    continue

                # Extract source from description
                description_elem = item.find("description")
                description = (
                    description_elem.text if description_elem is not None else ""
                )

                # Google News RSS format: "Description - Source"
                # Extract source name from description
                source = "News Source"
                if description:
                    # Look for source in format: "text - Source Name"
                    if " - " in description:
                        parts = description.split(" - ")
                        source = parts[-1].strip()
                        # Clean up any HTML tags
                        source = source.replace("<br>", "").replace("</br>", "").strip()
                    elif "<br>" in description:
                        # Sometimes source is after <br> tag
                        parts = description.split("<br>")
                        if len(parts) > 1:
                            potential_source = parts[-1].strip().replace("</br>", "")
                            if potential_source and not potential_source.startswith(
                                "<"
                            ):
                                source = potential_source

                # Extract date/publication time
                pub_date_elem = item.find("pubDate")
                date_str = (
                    pub_date_elem.text if pub_date_elem is not None else "Unknown"
                )
                # Format date more readably (remove timezone info for display)
                if date_str != "Unknown":
                    # Keep only the readable date part
                    date_str = date_str.split("+")[0].split("GMT")[0].strip()

                articles.append(
                    {
                        "title": title,
                        "url": link,
                        "source": source,
                        "date": date_str,
                    }
                )

            except Exception as e:
                logger.debug(f"Error parsing article: {e}")
                continue

        return articles

    except requests.RequestException as e:
        logger.error(f"Failed to fetch news for {ticker}: {e}")
        return []
    except ET.ParseError as e:
        logger.error(f"Failed to parse RSS feed for {ticker}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching news for {ticker}: {e}")
        return []
