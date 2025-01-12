import streamlit as st

# Custom libraries
from tabs import (
    setup_render,
    selection_render,
    standings_render,
    league_render,
    playoffs_render,
    finals_render,
)


st.markdown(
    """
    <div style="text-align: center; margin-bottom: 20px;">
        <h2>🎮 Tournalytics 🎮</h2>
    </div>
    """,
    unsafe_allow_html=True,
)

if "players" not in st.session_state:
    st.session_state["players"]  = []

# Initialize session state
if "tournaments" not in st.session_state:
    st.session_state["tournaments"] = {}

if "selected_tournament_id" not in st.session_state:
    # Automatically set the first tournament ID if available
    st.session_state["selected_tournament_id"] = next(iter(st.session_state["tournaments"]), None)

if "tournament_ready" not in st.session_state:
    st.session_state["tournament_ready"] = False

if "expander_open" not in st.session_state:
    st.session_state["expander_open"] = True  # Start with the expander open

# Main Navigation Buttons
col1, col2 = st.columns(2)

with col1:
    setup_button = st.button(
        "🛠️ Build a Tournament",
        use_container_width=True,
        key="setup_button",
        help="Set up your tournament step-by-step.",
    )

with col2:
    management_button = st.button(
        "🎮 Run a Tournament",
        use_container_width=True,
        key="management_button",
        help="Manage your tournament after setup is complete.",
    )

# Determine Active Section
if "active_section" not in st.session_state:
    st.session_state["active_section"] = "Tournament Setup"

if setup_button:
    st.session_state["active_section"] = "Tournament Setup"

if management_button:
    st.session_state["active_section"] = "Tournament Management"

# Render Active Section
if st.session_state["active_section"] == "Tournament Setup":
    setup_render()

elif st.session_state["active_section"] == "Tournament Management":
    if not st.session_state["tournaments"]:
        st.markdown(
            """
            <div style='text-align: center; margin-top: 50px;'>
                <h3 style='margin-bottom: 10px; color: #808080;'>🔒 Locked</h3>
                <p style='font-size: 14px; color: #ccc;'>No Tournament available. Please complete 🛠️ Build a Tournament first.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.stop()

    # Management Tabs
    if st.session_state.get("tournament_ready"):
        tab1, tab2, tab3, tab4, tab5 = st.tabs(
            ["▶️ Start", "📊 Standings", "🏅 League", "⚔️ Playoffs", "🏆 Finals"]
)

    # Render each tab
    with tab1:
        selection_render()

    with tab2:
        standings_render()

    with tab3:
        league_render()

    with tab4:
        playoffs_render()

    with tab5:
        finals_render()
