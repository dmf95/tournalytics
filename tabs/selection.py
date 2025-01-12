#-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-
#-- dependencies
#-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-

# main libraries
import streamlit as st
import pandas as pd
import numpy as np
# custom libraries
from utils.tournament_utils import (
    generate_league_schedule, 
    estimate_tournament_duration, 
    validate_schedule,
    initialize_standings,
)
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

    # Retrieve parameters from session state
    games_per_player = tournament_details["games_per_player"]
    num_players = tournament_details["num_players"]
    num_consoles = tournament_details["num_consoles"]
    half_duration = tournament_details["half_duration"]
    playoff_format = tournament_details["playoff_format"]
    league_format = tournament_details["league_format"]
    team_selection = tournament_details["team_selection"]

    # Calculate tournament details using modularized functions
    tournament_duration_details = estimate_tournament_duration(
        num_players=num_players,
        num_consoles=num_consoles,
        half_duration=half_duration,
        games_per_player=games_per_player,
        league_format=league_format,
        playoff_format=playoff_format,
    )

    league_details = tournament_duration_details["league_details"]
    playoff_details = tournament_duration_details["playoff_details"]
    additional_time = tournament_duration_details["additional_time"]
    total_duration = tournament_duration_details["total_duration"]

    # Convert durations to hours and minutes
    league_duration_hm = f"{league_details['league_duration'] // 60} hours and {league_details['league_duration'] % 60} minutes"
    playoff_duration_hm = f"{playoff_details['playoff_duration'] // 60} hours and {playoff_details['playoff_duration'] % 60} minutes"
    total_duration_hm = f"{total_duration // 60} hours and {total_duration % 60} minutes"

    # Collapsible sections for details
    with st.expander("🏆 Tournament Details", expanded=True):
        st.markdown(f"### 🏆 **{tournament_details['tournament_name']}**")
        # Tournament details
        st.write(f"**🏟️ League:** {tournament_details['league_name']}")
        st.write(f"**⚽ Game:** {tournament_details['video_game']}")
        st.write(f"**📅 Date:** {tournament_details['event_date']}")
        st.write(f"**🎯 Type:** {tournament_details['tournament_type']}")
        st.write(f"**🏅 League Format:** {tournament_details['league_format']}")
        st.write(f"**↕️ League Tiebreaker Order:** {tournament_details['tiebreakers']}")
        st.write(f"**⚔️ Playoff Format:** {tournament_details['playoff_format']}")
        st.write(f"**👥 Players:** {tournament_details['num_players']}")
        st.write(f"**🎮 Consoles:** {tournament_details['num_consoles']}")
        st.write(f"**⏱️ Half Duration:** {tournament_details['half_duration']} minutes")
        st.write(f"**🕹️ Games Per Player:** {tournament_details['games_per_player']}")

    with st.expander("⏳ Estimated Duration", expanded=False):
        st.markdown(f"#### **⏳ ~ {total_duration_hm}**")
        # League duration details
        st.markdown("**🏅 League Games**")
        st.write(f"- **Total Games:** {league_details['total_league_games']} games, {league_details['league_rounds']} rounds")
        st.write(f"- **Estimated Duration:** ~{league_duration_hm}")
        # Playoff duration details
        st.markdown("**⚔️ Playoff Games**")
        st.write(f"- **Estimated Duration:** ~{playoff_duration_hm}")
        # Additional time
        st.markdown("**⏱️ Additional Time**")
        st.write(f"- **Miscellaneous Time:** ~{additional_time} minutes")

    with st.expander("👤 Players & Teams", expanded=False):
        st.markdown(f"### 👤**Player Teams**")
        for player, team in st.session_state["team_selection"].items():
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
            # Validate required fields in tournament_details
            required_keys = ["selected_players", "team_selection", "num_consoles", "games_per_player"]
            for key in required_keys:
                if key not in tournament_details:
                    raise KeyError(f"Missing required field in tournament details: '{key}'")

            # Generate the league schedule
            schedule = generate_league_schedule(tournament_details)

            # Validate the generated schedule
            validation_messages = validate_schedule(schedule, tournament_details)
            if validation_messages:
                st.error("Validation errors detected in the generated schedule:")
                for msg in validation_messages:
                    st.error(f"- {msg}")
                raise ValueError("Schedule validation failed.")

            # Prepare results and standings
            results_df = pd.DataFrame(schedule)
            results_df["Home Goals"] = np.nan
            results_df["Away Goals"] = np.nan
            results_df["Home xG"] = np.nan
            results_df["Away xG"] = np.nan

            # Extract necessary details
            players = tournament_details["selected_players"]
            teams = tournament_details["team_selection"]
            standings_df = initialize_standings(players, teams)

            # Store results and standings in session state
            st.session_state["schedule"] = schedule
            st.session_state["results"] = results_df
            st.session_state["standings"] = standings_df

            # Mark the tournament as ready
            st.session_state["tournament_ready"] = True
            st.success("Tournament schedule generated successfully! Tabs are now unlocked.", icon="✅")

        except KeyError as e:
            st.error(f"Missing required setup information: {e}", icon="❌")
        except ValueError as e:
            st.error(f"Validation failed: {e}", icon="❌")
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}", icon="❌")