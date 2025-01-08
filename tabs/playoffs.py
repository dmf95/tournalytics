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
    upsert_results,
    update_standings,
    generate_playoffs_bracket,
    calculate_outcomes,
    determine_winner
)

#-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-
#-- tournament.py: playoffs tab (3rd)
#-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-

def render():
    # Check if the tournament is ready
    if not st.session_state.get("tournament_ready", False):
        st.warning("Please complete the tournament setup before accessing the league.", icon="🔒")
        return

    # Check if the schedule is available
    if "schedule" not in st.session_state or not st.session_state["schedule"]:
        st.warning("Tournament schedule is missing. Generate the schedule first.", icon="🔒")
        return

    # Reset Playoff Bracket
    #if st.button("Reset Playoff Games"):
    #    if "playoff_results" in st.session_state:
    #        del st.session_state["playoff_results"]
    #    st.success("Playoff results cache has been cleared!")

    # Ensure results DataFrame exists and is valid
    if "results" not in st.session_state or st.session_state.results.empty:
        st.warning("No results available. Please complete the round-robin stage first.", icon="🔒")
        st.stop()

    # Handle playoff_results safely
    if "playoff_results" not in st.session_state or st.session_state.playoff_results.empty:
        st.warning("Playoffs have not been generated yet.", icon="🔒")
        playoff_results = pd.DataFrame()  # Assign an empty DataFrame as a fallback
    else:
        playoff_results = st.session_state.playoff_results.copy()


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


    #######################################

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
    if not playoff_results.empty:
        # Filter completed playoff games
        playoff_games_played = playoff_results.dropna(subset=["Home Goals", "Away Goals"]).copy()

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

    ########################################

    # Check if all matches in the round-robin are complete
    league_complete = st.session_state.results.dropna(subset=["Home Goals", "Away Goals"]).shape[0] == st.session_state.results.shape[0]
    # Reorder: Player, Team, Points, Played, Playoff_Played, Wins, Draws, Goals, xG
    standings = standings[["Player", "Team", "Points", "Played", "Wins", "Draws", "Goals", "xG"]]
    ranked_standings = standings.sort_values(by=["Points", "Goals", "xG", "Wins"], ascending=False).reset_index(drop=True)

    if not league_complete:
        #st.warning("Playoffs are locked until all round-robin matches are completed.",icon="🔒")
        print("Playoffs are locked until all round-robin matches are completed.")
    else:
        # Generate or fetch playoff results
        if "playoff_results" not in st.session_state or st.session_state["playoff_results"].empty:
            # Generate playoff bracket and initialize result columns
            playoff_bracket = generate_playoffs_bracket(ranked_standings, last_game_id)

            #  Convert to DataFrame if necessary
            if isinstance(playoff_bracket, list):
                playoff_bracket = pd.DataFrame(playoff_bracket)

            # Ensure the "Match" column is added if missing
            if "Match" not in playoff_bracket.columns:
                playoff_bracket["Match"] = [f"WC{i+1}" for i in range(len(playoff_bracket))]  # Example placeholder values

            st.session_state.playoff_results = pd.DataFrame(playoff_bracket)
            st.session_state.playoff_results[["Home Goals", "Away Goals", "Home xG", "Away xG"]] = np.nan

        # Copy playoff results for processing
        playoff_results = st.session_state.playoff_results.copy()
        
        # TODO: Display the playoff results for debugging
        # st.subheader("Playoff Bracket")
        #st.dataframe(playoff_bracket)

        # Ensure the "Match" column exists before accessing it
        if "Match" not in playoff_results.columns:
            st.error("The 'Match' column is missing from the playoff results. Please check the data generation process.", icon="❌")
            return

        # Safely access "Match" column
        wc1_matches = playoff_results[playoff_results["Match"].str.startswith("WC1")]
        wc2_matches = playoff_results[playoff_results["Match"].str.startswith("WC2")]

        # Determine winners for WC1 and WC2
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
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 0px;">
                <h3>🥊 Wildcard Games</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.dataframe(
            playoff_bracket[playoff_bracket["Match"].str.contains("WC", na=False)],
            use_container_width=True,
            hide_index=True,
        )
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 0px;">
                <h3>⚔️ Semifinals</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.dataframe(
            playoff_bracket[playoff_bracket["Match"].str.contains("SF", na=False)],
            use_container_width=True,
            hide_index=True,
        )

        # Determine the starting Game ID for playoffs
        all_round_robin_complete = st.session_state.results.dropna(subset=["Home Goals", "Away Goals"]).shape[0] == st.session_state.results.shape[0]

        # Allow updating results for playoff games only if playoffs are not locked
        if all_round_robin_complete and not playoff_results.empty:
            st.markdown("---")
            st.markdown(
                """
                <div style="text-align: center; margin-bottom: 0px;">
                    <h3>✏️ Update Match Results</h3>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Check if playoff_results exists and ensure the "Match" column exists
            if "Match" not in playoff_results.columns:
                st.error("The 'Match' column is missing from playoff results. Please check the data generation process.", icon="❌")
                return

            # Safely access non-finals matches
            non_finals_matches = playoff_results[~playoff_results["Match"].str.contains("Final", na=False)]

            if non_finals_matches.empty:
                st.info("No non-finals matches available to update.", icon="ℹ️")
            else:
                # Create a selectbox for non-finals games
                selected_game = st.selectbox("Select Game to Update", non_finals_matches["Game #"])
                
                if selected_game:
                    # Get the match row for the selected game
                    match_row = playoff_results[playoff_results["Game #"] == selected_game].iloc[0]
                    home_team = match_row["Home Team"]
                    away_team = match_row["Away Team"]
                    home_team_full = (
                        f"""{match_row.get("Home Team", "Unknown Team")} ({match_row.get("Home", "Unknown Player")})"""
                    )
                    away_team_full = (
                        f"""{match_row.get("Away Team", "Unknown Team")} ({match_row.get("Away", "Unknown Player")})"""
                    )
                    # Display match details in a styled card
                    st.markdown(
                        f"""
                        <div style="
                            background-color: rgba(255, 255, 255, 0.1); 
                            border: 1px solid rgba(255, 255, 255, 0.2); 
                            padding: 15px; 
                            border-radius: 10px; 
                            margin-bottom: 20px; 
                            text-align: left; 
                            color: #ffffff;
                            font-size: 1.1em;
                            line-height: 1.6;
                        ">
                            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                                <span style="margin-right: 8px;">🎮</span> <strong>Selected Game #:&nbsp;</strong> {selected_game}
                            </div>
                            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                                <span style="margin-right: 8px;">🆚</span> <strong>Match Type:&nbsp;</strong> {match_row["Match"]}
                            </div>
                            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                                <span style="margin-right: 8px;">🕹️</span> <strong>Console:&nbsp;</strong> {match_row["Console"]}
                            </div>
                            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                                <span style="margin-right: 8px;">🏠</span> <strong>Home Team:&nbsp;</strong> {home_team_full}
                            </div>
                            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                                <span style="margin-right: 8px;">✈️</span> <strong>Away Team:&nbsp;</strong> {away_team_full}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    # Compact inputs for match results
                    col1, col2 = st.columns(2)
                    with col1:
                        home_goals = st.number_input(
                            f"Goals for {home_team}", min_value=0, step=1, key=f"home_goals_{selected_game}"
                        )
                    with col2:
                        home_xg = st.number_input(
                            f"xG for {home_team}", min_value=0.0, step=0.1, key=f"home_xg_{selected_game}"
                        )

                    col3, col4 = st.columns(2)
                    with col3:
                        away_goals = st.number_input(
                            f"Goals for {away_team}", min_value=0, step=1, key=f"away_goals_{selected_game}"
                        )
                    with col4:
                        away_xg = st.number_input(
                            f"xG for {away_team}", min_value=0.0, step=0.1, key=f"away_xg_{selected_game}"
                        )

                    # Button to update match results
                    if st.button("✏️ Update Playoff Match Results", key=f"update_results_{selected_game}", use_container_width=True):
                        # Locate the row to update in the DataFrame
                        idx = st.session_state.playoff_results[
                            st.session_state.playoff_results["Game #"] == selected_game
                        ].index[0]

                        # Update the DataFrame with new values
                        st.session_state.playoff_results.at[idx, "Home Goals"] = home_goals
                        st.session_state.playoff_results.at[idx, "Away Goals"] = away_goals
                        st.session_state.playoff_results.at[idx, "Home xG"] = home_xg
                        st.session_state.playoff_results.at[idx, "Away xG"] = away_xg

                        # Update the status column
                        st.session_state.playoff_results["Status"] = st.session_state.playoff_results["Game #"].apply(
                            lambda game_id: "✅"
                            if not pd.isna(
                                st.session_state.playoff_results.loc[
                                    st.session_state.playoff_results["Game #"] == game_id, "Home Goals"
                                ]
                            ).all()
                            else ""
                        )

                        st.success(f"Results updated for {selected_game}", icon="✅")
        else:
            st.warning("Playoffs are locked. Update Match Results will be available after playoffs are unlocked.", icon="🔒")

