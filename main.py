# Import third party packages.
import streamlit as st

# Import local packages.
from src.pages import (
    backtesting,
    comparison,
    dashboard,
    portfolio,
    settings,
    stock_analysis,
    watchlists,
)


def main() -> None:
    """
    Entry point and page navigation.

    Previously this just called stock_analysis.show() directly, so no
    other page module -- including the new Portfolio page -- was ever
    reachable in the running app, no matter how complete its own code
    was. st.navigation()/st.Page() is Streamlit's built-in multi-page
    mechanism: each page keeps its own show()-style function, and this
    is the one place that wires them all into a visible sidebar.

    default=True stays on Stock Analysis so the app's landing page is
    unchanged from before this existed. Each st.Page() is given an
    explicit url_path: every page module names its entry point show(),
    so without an explicit url_path Streamlit infers the same "show"
    pathname for all of them and refuses to start.
    """
    st.set_page_config(
        page_title="Stocksight",
        page_icon="📈",
        layout="wide",
    )

    pages = [
        st.Page(
            stock_analysis.show,
            title="Stock Analysis",
            icon="📈",
            url_path="stock-analysis",
            default=True,
        ),
        st.Page(portfolio.show, title="Portfolio", icon="💼", url_path="portfolio"),
        st.Page(dashboard.show, title="Dashboard", icon="🏠", url_path="dashboard"),
        st.Page(comparison.show, title="Comparison", icon="🔍", url_path="comparison"),
        st.Page(
            backtesting.show, title="Backtesting", icon="🧪", url_path="backtesting"
        ),
        st.Page(watchlists.show, title="Watchlists", icon="⭐", url_path="watchlists"),
        st.Page(settings.show, title="Settings", icon="⚙️", url_path="settings"),
    ]

    navigation = st.navigation(pages)
    navigation.run()


if __name__ == "__main__":
    main()
