import streamlit as st
import pandas as pd
import numpy as np

# Custom libraries
from utils.tournament_utils import (generate_schedule)
from utils.general_utils import initialize_session_state
from utils.data_utils import load_player_data_local
from tabs import (
    setup_render,
    standings_render,
    league_render,
    playoffs_render,
    finals_render,
)



# Set page title and layout
st.set_page_config(
    page_title="Tournaments",
    page_icon="🏆",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <div style="text-align: center; margin-bottom: 20px;">
        <h1>🎮 Tournalytics</h1>
    </div>
    """,
    unsafe_allow_html=True,
)

# Initialize session state
if "player_names" not in st.session_state:
    players_df = load_player_data_local("assets/players.csv")
    st.session_state["player_names"] = players_df["first_name"] + " " + players_df["last_name"]

if "tournaments" not in st.session_state:
    st.session_state["tournaments"] = {}

if "selected_tournament_id" not in st.session_state:
    # Automatically set the first tournament ID if available
    st.session_state["selected_tournament_id"] = next(iter(st.session_state["tournaments"]), None)

if "tournament_ready" not in st.session_state:
    st.session_state["tournament_ready"] = False

# Main Navigation Buttons
col1, col2 = st.columns(2)

with col1:
    setup_button = st.button(
        "🔧 Build a Tournament",
        use_container_width=True,
        key="setup_button",
        help="Set up your tournament step-by-step.",
    )

with col2:
    management_button = st.button(
        "📋 Run a Tournament",
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
        st.warning("No tournaments available. Please set up a tournament first.")
        st.stop()

    st.markdown(
        """
        <div style='text-align: center; margin-bottom: 20px;'>
            <h3 style='margin-bottom: 5px;'>📋 Find your Tournament</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Dropdown to select a tournament
    tournament_ids = list(st.session_state["tournaments"].keys())
    tournament_labels = [
        f"{tid} - {st.session_state['tournaments'][tid]['tournament_name']}"
        for tid in tournament_ids
    ]
    selected_label = st.selectbox(
        "Choose a Tournament",
        tournament_labels,
        key="tournament_selector",
        help="Select a tournament to view its details and proceed.",
    )

    # Extract the selected tournament ID and details
    selected_tournament_id = tournament_ids[tournament_labels.index(selected_label)]
    st.session_state["selected_tournament_id"] = selected_tournament_id
    tournament_details = st.session_state["tournaments"][selected_tournament_id]

    # Tournament Details Section
    with st.expander("🏆 Tournament Details", expanded=True):
        st.write(f"**Name:** {tournament_details['tournament_name']}")
        st.write(f"**Date:** {tournament_details['event_date']}")
        st.write(f"**Type:** {tournament_details['tournament_type']}")
        st.write(f"**Players:** {tournament_details['num_players']}")
        st.write(f"**Consoles:** {tournament_details['num_consoles']}")
        st.write(f"**Half Duration:** {tournament_details['half_duration']} minutes")

    # Players & Teams Section
    with st.expander("👤 Players & Teams", expanded=False):
        for player, team in tournament_details["team_selection"].items():
            st.write(f"- {player}: {team}")

    # Lock the tab if no tournament is selected
    if not st.session_state["selected_tournament_id"]:
        st.markdown(
            """
            <div style='text-align: center; color: orange;'>
                <p>Please select a tournament to proceed.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.stop()

   # Generate Tournament Schedule Section
    if st.button("🚀 Generate Tournament Schedule", key="generate_schedule", use_container_width=True):
        try:
            # Extract necessary details from the selected tournament
            players = tournament_details["selected_players"]
            teams = tournament_details["team_selection"]
            num_consoles = tournament_details["num_consoles"]
            half_duration = tournament_details["half_duration"]

            # Initialize session state for players and teams
            st.session_state["players"] = players
            st.session_state["teams"] = teams

            # Call the generate_schedule function
            schedule = generate_schedule(players, teams, num_consoles)

            # Store schedule and initialize results in session state
            st.session_state["schedule"] = schedule
            st.session_state["results"] = pd.DataFrame(schedule)
            st.session_state["results"]["Home Goals"] = np.nan
            st.session_state["results"]["Away Goals"] = np.nan
            st.session_state["results"]["Home xG"] = np.nan
            st.session_state["results"]["Away xG"] = np.nan

            # Initialize standings
            st.session_state["standings"] = initialize_session_state()

            # Mark tournament as ready
            st.session_state["tournament_ready"] = True  # Ensure it's set to True
            st.success("Tournament schedule generated successfully! Tabs are now unlocked.")

        except KeyError as e:
            st.error(f"Missing required setup information: {e}")
        except Exception as e:
            st.error(f"An error occurred while generating the schedule: {e}")

    # Management Tabs
    if st.session_state.get("tournament_ready"):
        tab1, tab2, tab3, tab4 = st.tabs(
            ["📊 Standings", "📅 League", "🥊 Playoffs", "🏆 Finals"]
        )

        with tab1:
            standings_render()

        with tab2:
            league_render()

        with tab3:
            playoffs_render()

        with tab4:
            finals_render()


        # Floating Action Button for Save
        st.markdown(
            """
            <style>
            .floating-button {
                position: fixed;
                bottom: 20px;
                right: 20px;
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 15px;
                border-radius: 50%;
                font-size: 20px;
                cursor: pointer;
                box-shadow: 0px 4px 6px rgba(0,0,0,0.3);
            }
            .floating-button:hover {
                background-color: #45a049;
            }
            </style>
            <button class="floating-button" onclick="document.querySelector('button.streamlit-button.primary').click();">✔️</button>
            """,
            unsafe_allow_html=True,
        )
