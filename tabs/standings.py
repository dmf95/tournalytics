#-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-
#-- dependencies
#-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-

# main libraries
import streamlit as st
import pandas as pd
# custom libraries
from utils.tournament_utils import (
    initialize_standings,
    update_standings,
    calculate_outcomes,
    get_session_state,
    sort_standings
)

#-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-
#-- tournament.py: standings tab (1st)
#-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-

def render():
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 0px;">
            <h3>📊 League Standings</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Check if results exist
    if "results" not in st.session_state or st.session_state.results.empty:
        st.error("No results available. Please generate a tournament schedule first.", icon="❌")
        return

    # Filter completed games
    games_played = st.session_state.results.dropna(subset=["Home Goals", "Away Goals"])

    # Extract the selected tournament ID and details
    tournament_details = st.session_state["tournaments"][st.session_state["selected_tournament_id"]]

    # Extract necessary details
    players = tournament_details["selected_players"]
    teams = tournament_details["team_selection"]

    # Initialize standings and update based on results
    standings = initialize_standings(players, teams)
    standings = update_standings(standings, games_played)

    # Calculate Wins, Losses, and Draws
    if not games_played.empty:
        outcomes = calculate_outcomes(games_played, players)
    else:
        # Create an empty outcomes DataFrame with required columns if no games have been played
        outcomes = pd.DataFrame({"Player": players, "Wins": 0, "Losses": 0, "Draws": 0})

    # Merge outcomes and count games played
    standings = (
        standings.merge(outcomes, on="Player", how="left")
        .fillna({"Wins": 0, "Losses": 0, "Draws": 0})  # Ensure default values for empty outcomes
        .assign(Played=lambda df: df["Games_Played"] + df.get("Playoff_Played", 0))
    )

    # Add playoff games if available
    if "playoff_results" in st.session_state and not st.session_state.playoff_results.empty:
        playoff_games = st.session_state.playoff_results.dropna(subset=["Home Goals", "Away Goals"])
        playoff_counts = (
            playoff_games[["Game #", "Home", "Away"]]
            .melt(id_vars=["Game #"], value_vars=["Home", "Away"], var_name="Role", value_name="Player")
            .groupby("Player")
            .agg(Playoff_Played=("Game #", "nunique"))
            .reset_index()
        )
        standings = standings.merge(playoff_counts, on="Player", how="left").fillna({"Playoff_Played": 0})
    else:
        standings["Playoff_Played"] = 0

    # Sort standings and apply rankings
    standings = sort_standings(standings, get_session_state("tiebreakers", []))
    
    # Display final standings
    columns_to_display = ["Rank", "Team", "Points", "Played", "Wins", "Draws", "Losses", "Goals", "xG"]
    standings = standings.loc[:, [col for col in columns_to_display if col in standings]]
    st.session_state["final_standings"] = standings


    # Display the updated standings table
    st.markdown(
        """
        <style>
        .styled-table {
            font-size: 14px;
            font-family: Arial, sans-serif;
            margin: auto;
            width: 100%;
            border-collapse: collapse;
        }
        .styled-table th, .styled-table td {
            text-align: center;
            padding: 8px;
        }
        .tiebreaker-note {
            text-align: center;
            margin: 5px auto 20px auto;
            font-size: 0.8em;
            color: #808080;
            font-family: Arial, sans-serif;
            word-wrap: break-word;
            line-height: 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Display a centered note about the tiebreakers used
    if "tiebreakers" in st.session_state:
        tiebreakers = st.session_state.get("tiebreakers", [])
        tiebreaker_note = (
            f"<strong>Order:</strong> Points (Primary)"
            + (", " + ", ".join(tiebreakers) if tiebreakers else " (No additional tiebreakers selected).")
        )
        st.markdown(
            f"""
            <div class="tiebreaker-note">
                {tiebreaker_note}
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Display the standings table
    st.dataframe(standings, use_container_width=True, hide_index=True)

    # Update session state with the standings
    st.session_state.standings = standings


    # Display the Games Played Table (League)
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 0px;">
            <h3>🏅 League Match History</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )
    games_played_summary = games_played[["Game #", "Home Team", "Away Team", "Home Goals", "Away Goals", "Home xG", "Away xG"]]
    games_played_summary["Home xG"] = games_played_summary["Home xG"].round(2)
    games_played_summary["Away xG"] = games_played_summary["Away xG"].round(2)
    games_played_summary.index = games_played_summary.index + 1

    st.dataframe(
        games_played_summary,
        use_container_width=True,
        hide_index=True,
    )

    # Display the Games Played Table (Playoffs)
    if "playoff_results" in st.session_state and not st.session_state.playoff_results.empty:
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 0px;">
                <h3>⚔️ Playoff Match History</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )
        # Extract relevant columns, map teams, round xG, and rename columns
        playoff_games_played_summary = (
            playoff_games[["Game #", "Match", "Home", "Away", "Home Goals", "Away Goals", "Home xG", "Away xG"]]
            .assign(
                Home=lambda df: df["Home"].map(teams),  # Map teams to 'Home'
                Away=lambda df: df["Away"].map(teams),  # Map teams to 'Away'
            )
            .rename(
                columns={
                    "Home": "Home Team",  # Rename 'Home' to 'Home Team'
                    "Away": "Away Team",  # Rename 'Away' to 'Away Team'
                }
            )
            .loc[:, [
                "Game #", "Match", "Home Team", "Away Team", 
                "Home Goals", "Away Goals", 
                "Home xG", "Away xG"
            ]]
        )

        # Round xG values directly after selection
        playoff_games_played_summary["Home xG"] = playoff_games_played_summary["Home xG"].round(2)
        playoff_games_played_summary["Away xG"] = playoff_games_played_summary["Away xG"].round(2)

        # Adjust index for display
        playoff_games_played_summary.index = playoff_games_played_summary.index + 1

        # Display the data table
        st.dataframe(
            playoff_games_played_summary,
            use_container_width=True,
            hide_index=True,
        )
