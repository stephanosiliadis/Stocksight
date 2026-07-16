# Import third party packages.
import streamlit as st

# Import local packages.
from src.utils.news_fetcher import fetch_google_news


def render_news_panel(ticker: str) -> None:
    """
    Render a panel displaying top news articles for a ticker.

    Args:
        ticker: Stock ticker symbol.
    """
    st.subheader(f"📰 News & Articles for {ticker}")

    # Fetch articles with caching
    articles = fetch_google_news(ticker, max_results=3)

    if not articles:
        st.info("No recent news articles found. Please try again later.")
        return

    for idx, article in enumerate(articles, 1):
        with st.container(border=True):
            # Title as clickable link
            st.markdown(
                f"**[{article['title']}]({article['url']})**",
                unsafe_allow_html=False,
            )

            # Metadata in smaller text
            col1, col2 = st.columns(2)
            with col1:
                st.caption(f"📌 {article['source']}")
            with col2:
                st.caption(f"📅 {article['date']}")
