from utils import (
    initialize_standings,
    update_standings,
    calculate_outcomes,
)
import streamlit as st
import pandas as pd
import numpy as np


def render():
  st.header("League Standings")

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

  # Add team names to standings
  standings["Team"] = standings["Player"].map(st.session_state.teams)

  # Round xG values in standings
  standings["xG"] = standings["xG"].round(2)

  # Sort standings by Points, Wins, Draws, Goals, and xG
  standings = standings.sort_values(by=["Points", "Wins", "Goals", "xG"], ascending=False).reset_index(drop=True)

  # Reorder: Player, Team, Points, Played, Playoff_Played, Wins, Draws, Goals, xG
  standings = standings[["Player", "Team", "Points", "Played", "Wins", "Draws", "Goals", "xG"]]
  ranked_standings = standings.sort_values(by=["Points", "Wins", "Goals", "xG"], ascending=False).reset_index(drop=True)

  # Reset index to start from 1 for display
  standings.index = standings.index + 1
  standings.index.name = "Rank"

  # Display the updated standings table
  st.dataframe(standings, use_container_width=True)

  # Display the Games Played Table (Round Robin)
  st.subheader("League Games Played")
  games_played_summary = games_played[["Game #", "Home", "Away", "Home Goals", "Away Goals", "Home xG", "Away xG"]]
  games_played_summary["Home xG"] = games_played_summary["Home xG"].round(2)
  games_played_summary["Away xG"] = games_played_summary["Away xG"].round(2)
  
  # Reset index to start from 1 for display
  games_played_summary.index = games_played_summary.index + 1

  st.dataframe(
      games_played_summary,
      use_container_width=True
  )

  # Display the Games Played Table (Playoffs)
  if "playoff_results" in st.session_state and not st.session_state.playoff_results.empty:
      st.subheader("Playoff Games Played")
      playoff_games_played_summary = playoff_games_played[["Game #", "Match", "Home", "Away", "Home Goals", "Away Goals", "Home xG", "Away xG"]]
      playoff_games_played_summary["Home xG"] = playoff_games_played_summary["Home xG"].round(2)
      playoff_games_played_summary["Away xG"] = playoff_games_played_summary["Away xG"].round(2)
      
      # Reset index to start from 1 for display
      playoff_games_played_summary.index = playoff_games_played_summary.index + 1

      st.dataframe(
          playoff_games_played_summary,
          use_container_width=True
      )