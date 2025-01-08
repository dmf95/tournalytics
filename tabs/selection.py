#-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-
#-- dependencies
#-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-

# main libraries
import streamlit as st
import pandas as pd
import numpy as np
# custom libraries
from utils.tournament_utils import generate_league_schedule, estimate_tournament_duration
from utils.general_utils import initialize_session_state

#-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-
#-- tournament.py: finals tab (1st)
#-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-

def render():
    st.markdown(
    """
    <div style="text-align: center; margin-bottom: 20px;">
      <h3>📋 Find your Tournament</h3>
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

    # Estimate tournament duration
    duration_breakdown = estimate_tournament_duration(
        num_players=st.session_state["num_players"],
        num_consoles=st.session_state["num_consoles"],
        half_duration=st.session_state["half_duration"],
        league_format=st.session_state["league_format"],
        playoff_format=st.session_state["playoff_format"],
    )

    #-1-tournament details expander
    with st.expander("🏆 Tournament Details", expanded=False):
        # Tournament details
        st.markdown(f"### 🏆 **{st.session_state['tournament_name']}**")
        # Tournament details
        st.write(f"**📅 Date:** {tournament_details['event_date']}")
        st.write(f"**🎯 Type:** {tournament_details['tournament_type']}")
        st.write(f"**🏅 League Format:** {tournament_details['league_format']}")
        st.write(f"**⚔️ Playoff Format:** {tournament_details['playoff_format']}")
        st.write(f"**👥 Players:** {tournament_details['num_players']}")
        st.write(f"**🎮 Consoles:** {tournament_details['num_consoles']}")
        st.write(f"**⏱️ Half Duration:** {tournament_details['half_duration']} minutes")

    #-2-estimated duration expander
    with st.expander("⏳ Estimated Duration", expanded=False):
        # Divider for duration section
        st.markdown(f"#### **⏳ ~Est: {duration_breakdown['total_hours']} hours & {duration_breakdown['total_minutes']} minutes**")
        # League duration details
        st.markdown("**🏅 League Games**")
        st.write(f"- **Total Games:** {duration_breakdown['total_league_games']} across {duration_breakdown['total_league_rounds']} rounds")
        st.write(f"- **Estimated Duration:** ~{duration_breakdown['total_league_duration']} minutes")
        # Playoff duration details
        st.markdown("**⚔️ Playoff Games**")
        st.write(f"- **Total Games:** {duration_breakdown['total_playoff_games']} across {duration_breakdown['total_playoff_rounds']} rounds")
        st.write(f"- **Estimated Duration:** ~{duration_breakdown['total_playoff_duration']} minutes")
        # Additional time
        st.markdown("**⏱️ Additional Time**")
        st.write(f"- **Team Management Time:** ~{duration_breakdown['team_management_time']} minutes")

    #-3-players and team selection expander
    with st.expander("👤 Players & Teams", expanded=False):
        st.markdown(f"### 👤**Player Teams**")
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
            schedule = generate_league_schedule(players, teams, num_consoles)

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
            st.success("Tournament schedule generated successfully! Tabs are now unlocked.", icon="✅")

        except KeyError as e:
            st.error(f"Missing required setup information: {e}", icon="❌")
        except Exception as e:
            st.error(f"An error occurred while generating the schedule: {e}", icon="❌")