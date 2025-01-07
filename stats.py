import streamlit as st
from utils.analytics_utils import get_tournament_stats

# Page content
st.markdown(
    """
    <div style='text-align: center; margin-bottom: 20px;'>
        <h2 style='margin-bottom: 5px;'>📈 Tournament Stats</h2>
        <p style='font-size: 14px; color: #808080;'>Analyze performance and uncover insights from past tournaments..</p>
    </div>
    """,
    unsafe_allow_html=True,
)
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
st.write("💡 Page is Under Construction! In the future, you can use this page to review past tournaments and improve your strategies.")
