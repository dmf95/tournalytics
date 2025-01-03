import streamlit as st
from utils import (
    generate_tournament_id,
    generate_schedule,
    validate_schedule,
    initialize_standings,
    upsert_results,
    update_standings,
    calculate_outcomes,
    calculate_tournament_duration,
    generate_playoffs_bracket,
    load_previous_tournaments,
    save_tournament,
    load_player_data,
    determine_winner,
)
import pandas as pd
import numpy as np
from tabs import standings, league, playoffs, finals


# Centralized session state initialization
def initialize_session_state():
    defaults = {
        "tournament_id": None,
        "tournament_name": "New Tournament",
        "players": [],
        "teams": {},
        "schedule": None,
        "results": pd.DataFrame(),  # Empty DataFrame
        "standings": None,
        "total_duration": 0,
        "team_management_time": 0,
        "playoff_results": pd.DataFrame(),  # Empty DataFrame
        "completed": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state or st.session_state[key] is None:
            st.session_state[key] = value


def main():
    # Initialize session state
    initialize_session_state()

    # App title
    st.title("🎮 Tournalytics 🎮")

    # Load player data
    players_df = load_player_data()
    player_names = players_df["first_name"] + " " + players_df["last_name"]

    # Tournament Setup
    st.sidebar.header("Tournament Setup")
    st.session_state["tournament_name"] = st.sidebar.text_input("Tournament Name", value=st.session_state["tournament_name"])
    num_players = st.sidebar.slider("Number of Players", min_value=6, max_value=12, value=6)
    num_consoles = st.sidebar.slider("Number of Consoles", min_value=1, max_value=4, value=2)
    half_duration = st.sidebar.slider("Half Duration (minutes)", min_value=4, max_value=6, value=5)

    selected_players = st.sidebar.multiselect("Select Players", player_names, default=player_names[:num_players])
    team_selection = {
        player: st.sidebar.text_input(f"Team for {player}", value=f"Team {player}")
        for player in selected_players
    }

    # Validate player selection
    if len(selected_players) != num_players:
        st.sidebar.error(f"Please select exactly {num_players} players.")
        return

    # Generate tournament schedule
    if st.sidebar.button("Generate Tournament Schedule"):
        st.session_state["tournament_id"] = generate_tournament_id()
        st.session_state["players"] = selected_players
        st.session_state["teams"] = team_selection
        st.session_state["schedule"] = generate_schedule(selected_players, team_selection, num_consoles)
        validation_messages = validate_schedule(st.session_state["schedule"], num_consoles)
        st.session_state["results"] = pd.DataFrame(st.session_state["schedule"])
        st.session_state["results"]["Home Goals"] = np.nan
        st.session_state["results"]["Away Goals"] = np.nan
        st.session_state["results"]["Home xG"] = np.nan
        st.session_state["results"]["Away xG"] = np.nan
        st.session_state["standings"] = initialize_standings(selected_players, team_selection)

        for player, team in team_selection.items():
            st.session_state["standings"].loc[st.session_state["standings"]["Player"] == player, "Team"] = team

        if validation_messages:
            for message in validation_messages:
                st.error(message)
        else:
            st.info("All scheduling validations passed.")

        total_duration, team_management_time = calculate_tournament_duration(
            st.session_state["schedule"], half_duration
        )
        st.session_state["total_duration"] = total_duration
        st.session_state["team_management_time"] = team_management_time

    # Ensure tournament is initialized
    if not st.session_state["tournament_id"]:
        st.sidebar.warning("Please generate a tournament schedule to proceed.")
        return

    # Sidebar tournament details
    st.sidebar.write(f"**Tournament ID**: {st.session_state['tournament_id']}")
    st.sidebar.write(f"**Tournament Name**: {st.session_state['tournament_name']}")
    st.sidebar.write(f"**Total Duration**: {st.session_state['total_duration']} minutes")
    st.sidebar.write(f"**Team Management Time**: {st.session_state['team_management_time']} minutes")

    # Tabs for tournament details
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Standings", "📅 League", "🥊 Playoffs", "🏆 Finals"])

    # League Standings
    with tab1:
        standings.render()

    # Match Schedule
    with tab2:
        league.render()

    # Playoffs
    with tab3:
        playoffs.render()

    # Finals
    with tab4:
        finals.render()

    # Save Tournament
    if st.sidebar.button("Finalize and Save Tournament Statistics"):
        if st.session_state["results"] is not None and not st.session_state["results"].empty:
            save_tournament(
                st.session_state["tournament_id"],
                st.session_state["tournament_name"],
                st.session_state["standings"],
                st.session_state["results"]
            )
            st.session_state["completed"] = True
            st.success("Tournament statistics saved successfully!")
        else:
            st.sidebar.error("Cannot finalize: No results available.")


if __name__ == "__main__":
    main()
