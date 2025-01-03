from utils import (
    generate_playoffs_bracket,
)
import streamlit as st
import pandas as pd
import numpy as np

# Playoffs (tab3)
def render():

  # Reset Playoff Bracket
  if st.button("Reset Playoff Games"):
      if "playoff_results" in st.session_state:
          del st.session_state["playoff_results"]
      st.success("Playoff results cache has been cleared!")

  # Ensure results DataFrame exists and is valid
  if "results" not in st.session_state or st.session_state.results.empty:
      st.warning("No results available. Please complete the round-robin stage first.")
      st.stop()

  # Determine the starting Game ID for playoffs
  if "Game #" in st.session_state.results.columns and not st.session_state.results["Game #"].isnull().all():
      last_game_id = (
          st.session_state.results["Game #"]
          .str.extract(r'(\d+)')[0]  # Extract the numeric part
          .astype(float)  # Convert to float for handling NaNs
          .max()  # Get the max value
      )
      last_game_id = int(last_game_id) if not pd.isna(last_game_id) else 0
  else:
      last_game_id = 0  # Default value if no games exist in round-robin

  # Check if all matches in the round-robin are complete
  all_round_robin_complete = st.session_state.results.dropna(subset=["Home Goals", "Away Goals"]).shape[0] == st.session_state.results.shape[0]

  if not all_round_robin_complete:
      st.warning("Playoffs are locked until all round-robin matches are completed.")
  else:
      # Generate or fetch playoff results
      if "playoff_results" not in st.session_state:
          # Generate playoff bracket and initialize result columns
          st.session_state.playoff_results = pd.DataFrame(
              generate_playoffs_bracket(ranked_standings, last_game_id)
          )
          st.session_state.playoff_results[["Home Goals", "Away Goals", "Home xG", "Away xG"]] = np.nan

      # Copy playoff results for processing
      playoff_results = st.session_state.playoff_results.copy()

      #TODO: Display the playoff results for debugging
      #st.subheader("Playoff Bracket")
      #st.dataframe(playoff_results)

      # Helper function to determine winner based on cumulative goals and xG
      def determine_winner(matches):
          # Calculate cumulative goals for the home player
          home_player = matches.iloc[0]["Home"]
          home_goals = matches[matches["Home"] == home_player]["Home Goals"].sum()
          away_goals = matches[matches["Away"] == home_player]["Away Goals"].sum()
          total_home_player_goals = home_goals + away_goals

          # Calculate cumulative goals for the away player
          away_player = matches.iloc[0]["Away"]
          home_goals = matches[matches["Home"] == away_player]["Home Goals"].sum()
          away_goals = matches[matches["Away"] == away_player]["Away Goals"].sum()
          total_away_player_goals = home_goals + away_goals

          # Compare cumulative goals
          if total_home_player_goals > total_away_player_goals:
              return home_player
          elif total_away_player_goals > total_home_player_goals:
              return away_player
          else:  # Tie-breaker: Use cumulative xG
              home_xg = matches[matches["Home"] == home_player]["Home xG"].sum()
              away_xg = matches[matches["Away"] == home_player]["Away xG"].sum()
              total_home_player_xg = home_xg + away_xg

              home_xg = matches[matches["Home"] == away_player]["Home xG"].sum()
              away_xg = matches[matches["Away"] == away_player]["Away xG"].sum()
              total_away_player_xg = home_xg + away_xg

              return home_player if total_home_player_xg > total_away_player_xg else away_player


      # Determine winners for WC1 and WC2
      wc1_matches = playoff_results[playoff_results["Match"].str.startswith("WC1")]
      wc2_matches = playoff_results[playoff_results["Match"].str.startswith("WC2")]

      wc1_win = determine_winner(wc1_matches) if not wc1_matches.dropna(subset=["Home Goals", "Away Goals"]).empty else None
      wc2_win = determine_winner(wc2_matches) if not wc2_matches.dropna(subset=["Home Goals", "Away Goals"]).empty else None

      # Update semi-final matches with wildcard winners
      if wc1_win and wc2_win:
          semi_final_matches = playoff_results["Match"].str.startswith("SF")
          playoff_results.loc[semi_final_matches, ["Home", "Away"]] = (
              playoff_results.loc[semi_final_matches, ["Home", "Away"]]
              .replace({"Winner WC2": wc2_win, "Winner WC1": wc1_win})
          )

          # Write back updated playoff results to session state
          st.session_state.playoff_results = playoff_results.copy()

      # Add team names and status to playoff results
      playoff_results["Home Team"] = playoff_results["Home"].map(st.session_state.teams)
      playoff_results["Away Team"] = playoff_results["Away"].map(st.session_state.teams)
      playoff_results["Status"] = playoff_results["Game #"].apply(
          lambda game_id: "✅" if not pd.isna(
              playoff_results.loc[playoff_results["Game #"] == game_id, "Home Goals"]
          ).all() else ""
      )

      # Display playoff results with consistent attributes
      playoff_bracket = playoff_results[["Game #", "Match", "Home Team", "Away Team", "Console", "Status"]]
      st.subheader("Wildcard Games")
      st.dataframe(
          playoff_bracket[playoff_bracket["Match"].str.contains("WC", na=False)],
          use_container_width=True,
      )

      st.subheader("Semifinals")
      st.dataframe(
          playoff_bracket[playoff_bracket["Match"].str.contains("SF", na=False)],
          use_container_width=True,
      )

      # Allow updating results for playoff games
      st.subheader("Update Playoff Match Results")

      # Filter games to exclude "Finals"
      non_finals_matches = playoff_results[~playoff_results["Match"].str.contains("Final", na=False)]
      
      # Create a selectbox for only non-"Finals" games
      selected_game = st.selectbox("Select Game to Update", non_finals_matches["Game #"])

      if selected_game:
          # Get the match row for the selected game
          match_row = playoff_results[playoff_results["Game #"] == selected_game].iloc[0]
          home_team = match_row["Home"]
          away_team = match_row["Away"]

          st.write(f"**Home Team**: {home_team}")
          st.write(f"**Away Team**: {away_team}")

          # Input fields for updating results
          home_goals = st.number_input(f"Goals for {home_team}", min_value=0, step=1, key=f"home_goals_{selected_game}")
          away_goals = st.number_input(f"Goals for {away_team}", min_value=0, step=1, key=f"away_goals_{selected_game}")
          home_xg = st.number_input(f"xG for {home_team}", min_value=0.0, step=0.1, key=f"home_xg_{selected_game}")
          away_xg = st.number_input(f"xG for {away_team}", min_value=0.0, step=0.1, key=f"away_xg_{selected_game}")

          # Button to update match results
          if st.button("Update Playoff Match Results", key=f"update_results_{selected_game}"):
              # Locate the row to update in the DataFrame
              idx = st.session_state.playoff_results[st.session_state.playoff_results["Game #"] == selected_game].index[0]

              # Update the DataFrame with new values
              st.session_state.playoff_results.at[idx, "Home Goals"] = home_goals
              st.session_state.playoff_results.at[idx, "Away Goals"] = away_goals
              st.session_state.playoff_results.at[idx, "Home xG"] = home_xg
              st.session_state.playoff_results.at[idx, "Away xG"] = away_xg

              # Update the status column
              st.session_state.playoff_results["Status"] = st.session_state.playoff_results["Game #"].apply(
                  lambda game_id: "✅" if not pd.isna(
                      st.session_state.playoff_results.loc[
                          st.session_state.playoff_results["Game #"] == game_id, "Home Goals"
                      ]
                  ).all() else ""
              )

              st.success(f"Results updated for Game #{selected_game}")

              #TODO Debug: Display updated playoff results
              #st.dataframe(st.session_state.playoff_results)