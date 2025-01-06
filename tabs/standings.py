#-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-
#-- dependencies
#-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-

# main libraries
import streamlit as st
import pandas as pd
import numpy as np
# custom libraries
from utils.tournament_utils import (
    initialize_standings,
    update_standings,
    calculate_outcomes,
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

    # Ensure 'results' exists
    if "results" not in st.session_state:
        st.error("No results available. Please generate a tournament schedule first.", icon="❌")
        return

    # Filter for completed round-robin games
    games_played = st.session_state.results.dropna(subset=["Home Goals", "Away Goals"]).copy()

    # Recalculate standings dynamically based on completed games
    st.session_state.standings = initialize_standings(st.session_state.players, st.session_state.teams)
    st.session_state.standings = update_standings(st.session_state.standings, games_played)

    # Count unique games played for each player (round-robin)
    games_played_count = (
        games_played[["Game #", "Home", "Away"]]
        .melt(id_vars=["Game #"], value_vars=["Home", "Away"], var_name="Role", value_name="Player")
        .groupby("Player")
        .agg(Played=("Game #", "nunique"))
        .reset_index()
    )

    # Calculate Wins, Losses, and Draws dynamically for round-robin
    outcomes = calculate_outcomes(games_played)

    # Merge games played count and outcomes into standings
    standings = st.session_state.standings.merge(games_played_count, on="Player", how="left").fillna({"Played": 0})
    standings = standings.merge(outcomes, on="Player", how="left")

    # Add Playoff Games Played if playoff results exist
    if "playoff_results" in st.session_state and not st.session_state.playoff_results.empty:
        # Filter completed playoff games
        playoff_games_played = st.session_state.playoff_results.dropna(subset=["Home Goals", "Away Goals"]).copy()

        # Count unique playoff games played for each player
        playoff_games_played_count = (
            playoff_games_played[["Game #", "Home", "Away"]]
            .melt(id_vars=["Game #"], value_vars=["Home", "Away"], var_name="Role", value_name="Player")
            .groupby("Player")
            .agg(Playoff_Played=("Game #", "nunique"))
            .reset_index()
        )

        # Merge playoff games played count into standings
        standings = standings.merge(playoff_games_played_count, on="Player", how="left").fillna({"Playoff_Played": 0})
    else:
        # Add a default Playoff_Played column if no playoff games are available
        standings["Playoff_Played"] = 0

    # Map team names and safely handle missing teams
    standings["Team"] = standings["Player"].map(st.session_state.get("teams", {}))

    # Round xG values if the column exists
    if "xG" in standings:
        standings["xG"] = standings["xG"].round(2)

    # Sort standings and reset index
    standings = (
        standings.sort_values(by=["Points", "Wins", "Goals", "xG"], ascending=False)
        .reset_index(drop=True)
        .assign(Rank=lambda df: df.index + 1)  # Add Rank column
    )

    # Reorder and select only the required columns
    columns_to_display = ["Rank", "Team", "Points", "Played", "Wins", "Draws", "Losses", "Goals", "xG"]
    standings = standings.loc[:, [col for col in columns_to_display if col in standings]]

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
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.dataframe(standings, use_container_width=True, hide_index=True)

    # Display the Games Played Table (Round Robin)
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
        # Extract relevant columns and map teams
        teams_mapping = st.session_state.get("teams", {})
        playoff_games_played_summary = (
            playoff_games_played[["Game #", "Match", "Home", "Away", "Home Goals", "Away Goals", "Home xG", "Away xG"]]
            .assign(
                Home_Team=lambda df: df["Home"].map(teams_mapping),
                Away_Team=lambda df: df["Away"].map(teams_mapping),
                Home_xG=lambda df: df["Home xG"].round(2),
                Away_xG=lambda df: df["Away xG"].round(2),
            )
            .loc[:, ["Game #", "Match", "Home_Team", "Away_Team", "Home Goals", "Away Goals", "Home_xG", "Away_xG"]]
        )

        # Adjust index for display
        playoff_games_played_summary.index = playoff_games_played_summary.index + 1

        # Display the data table
        st.dataframe(
            playoff_games_played_summary,
            use_container_width=True,
            hide_index=True,
        )
