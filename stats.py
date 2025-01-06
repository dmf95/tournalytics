import streamlit as st
from utils.analytics import get_tournament_stats

# Set page configuration
st.set_page_config(page_title="Tournament Stats", page_icon="📈", layout="wide")

# Page content
st.title("📈 Previous Tournament Stats 📈")
st.subheader("Analyze performance and uncover insights from past tournaments.")

# Fetch and display stats
st.markdown("---")
try:
    stats = get_tournament_stats() or {"overall": None, "win_rates": None, "matchups": None}

    # Overall performance stats
    if stats.get("overall") is not None and not stats["overall"].empty:
        st.subheader("🏆 Overall Performance")
        st.dataframe(stats["overall"], use_container_width=True)
    else:
        st.info("No overall performance data available.", icon="ℹ️")

    # Player win rates
    if stats.get("win_rates") is not None and not stats["win_rates"].empty:
        st.subheader("💪 Player Win Rates")
        st.dataframe(stats["win_rates"], use_container_width=True)
    else:
        st.info("No player win rate data available.", icon="ℹ️")

    # Frequent matchups
    if stats.get("matchups") is not None and not stats["matchups"].empty:
        st.subheader("🤼 Frequent Matchups")
        st.dataframe(stats["matchups"], use_container_width=True)
    else:
        st.info("No matchup data available.", icon="ℹ️")

except Exception as e:
    st.error(f"Failed to fetch tournament stats: {e}", icon="❌")

# Footer branding
st.markdown("---")
st.write("💡 Use this page to review past tournaments and improve your strategies.")
