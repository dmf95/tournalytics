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
    determine_winner,
    get_session_state,
    sort_standings,
    validate_league_completion,
    update_playoff_results
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

    # Ensure results DataFrame exists and is valid
    if "results" not in st.session_state or st.session_state.results.empty:
        st.warning("No results available. Please complete the League stage first.", icon="🔒")
        return

    # Extract the selected tournament ID and details
    tournament_details = st.session_state["tournaments"][st.session_state["selected_tournament_id"]]

    # Extract necessary details
    players = tournament_details["selected_players"]
    teams = tournament_details["team_selection"]

    # Display League Schedule
    league_schedule = pd.DataFrame(st.session_state["schedule"])

    # Check if league games are complete
    games_played = st.session_state.results.dropna(subset=["Home Goals", "Away Goals"]).copy()
    league_match_history = games_played[
        ["Game #", "Home Team", "Away Team", "Home Goals", "Away Goals", "Home xG", "Away xG"]
    ]
    league_match_history["Home xG"] = league_match_history["Home xG"].round(2)
    league_match_history["Away xG"] = league_match_history["Away xG"].round(2)
    league_match_history.index = league_match_history.index + 1
    league_complete = validate_league_completion(league_schedule, league_match_history,  debug=False)

    # Display locked message if league is incomplete
    if not league_complete:
        st.markdown(
            """
            <div style='text-align: center; margin-top: 50px;'>
                <h3 style='margin-bottom: 10px; color: #808080;'>🔒 Locked</h3>
                <p style='font-size: 14px; color: #ccc;'>Complete all 🏅 League Games to unlock ⚔️ Playoffs.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # Handle playoff_results safely
    if league_complete and ("playoff_results" not in st.session_state or st.session_state.playoff_results.empty):
        playoff_results = pd.DataFrame()  # Placeholder for playoff results

        # Add safeguard: "Generate Playoffs Bracket" button
        if "generate_playoffs_clicked" not in st.session_state:
            st.session_state["generate_playoffs_clicked"] = False

        if not st.session_state["generate_playoffs_clicked"]:
            # Show button to generate playoffs
            st.markdown(
                """
                <div style='text-align: center; margin-top: 50px;'>
                    <h3 style='margin-bottom: 10px; color: #808080;'>🔓 Unlocked</h3>
                    <p style='font-size: 14px; color: #ccc;'>🏅 League Games Completed! Ready to start the ⚔️ Playoffs.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("🚀 Generate Playoffs Bracket", key="generate_playoffs_button", use_container_width=True):
                st.session_state["generate_playoffs_clicked"] = True
                st.rerun()  # Refresh the app to proceed with generation

        else:
            # Generate playoff bracket if league is complete and button was clicked
            try:
                team_to_player = {team: player for player, team in teams.items()}

                league_match_history = st.session_state.results.dropna(subset=["Home Goals", "Away Goals"]).copy()
                league_standings =  st.session_state.standings

                # Map players to the league_standings based on the Team column
                league_standings["Player"] = league_standings["Team"].map(team_to_player)

                # Rearrange columns to include Player
                league_standings = league_standings[["Rank", "Player", "Team", "Points", "Wins", "Draws", "Losses", "Goals", "xG"]]
                league_standings["xG"] = league_standings["xG"].round(2)

                # Determine the starting Game ID for playoffs
                last_game_id = (
                    st.session_state.results["Game #"]
                    .str.extract(r'(\d+)')[0]  # Extract the numeric part
                    .astype(float)  # Convert to float for handling NaNs
                    .max()
                )
                last_game_id = int(last_game_id) if not pd.isna(last_game_id) else 0

                # Generate the playoff bracket
                playoff_bracket = generate_playoffs_bracket(
                    tournament_details=tournament_details,
                    standings=st.session_state.standings,
                    last_game_id=last_game_id,
                    debug=True  # Enable debugging
                )
                st.session_state["playoff_results"] = pd.DataFrame(playoff_bracket)
                st.session_state["playoff_results"][["Home Goals", "Away Goals", "Home xG", "Away xG"]] = np.nan
                st.success("Playoffs bracket generated successfully!", icon="✅")
                st.rerun()
            except ValueError as e:
                st.error(f"Failed to generate playoffs: {e}", icon="❌")
                return
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}", icon="❌")
                return
    else:
        
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
        playoff_results["Home Team"] = playoff_results["Home"].map(teams)
        playoff_results["Away Team"] = playoff_results["Away"].map(teams)
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


        # Allow updating results for playoff games only if playoffs are not locked
        if league_complete and not playoff_results.empty:
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
                    home_player = match_row["Home"]
                    away_player = match_row["Away"]
                    home_team = match_row["Home Team"]
                    away_team = match_row["Away Team"]
                    round_number = match_row["Round"]
                    match_type = match_row["Match"]
                    console = match_row["Console"]
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
                                <span style="margin-right: 8px;">🆚</span> <strong>Match Type:&nbsp;</strong> {match_type}
                            </div>
                            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                                <span style="margin-right: 8px;">🕹️</span> <strong>Console:&nbsp;</strong> {console}
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

                # Create a form for updating playoff results
                with st.form(key="update_playoff_form", clear_on_submit=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        home_goals = st.number_input(
                            f"Goals for {home_team}",
                            min_value=0,
                            step=1,
                            key=f"home_goals_{selected_game}",
                        )
                        home_xg = st.number_input(
                            f"xG for {home_team}",
                            min_value=0.0,
                            step=0.1,
                            key=f"home_xg_{selected_game}",
                        )
                    with col2:
                        away_goals = st.number_input(
                            f"Goals for {away_team}",
                            min_value=0,
                            step=1,
                            key=f"away_goals_{selected_game}",
                        )
                        away_xg = st.number_input(
                            f"xG for {away_team}",
                            min_value=0.0,
                            step=0.1,
                            key=f"away_xg_{selected_game}",
                        )

                    # Submit button for the form
                    submitted = st.form_submit_button("✏️ Update Playoff Match Results", use_container_width=True)

                    if submitted:
                        # Construct a new result record
                        new_result = {
                            "Game #": selected_game,
                            "Round": int(round_number),
                            "Home": home_player,
                            "Away": away_player,
                            "Console": console,
                            "Match": match_type,
                            "Home Team": home_team,
                            "Away Team": away_team,
                            "Played": 1,
                            "Home Goals": home_goals,
                            "Away Goals": away_goals,
                            "Home xG": home_xg,
                            "Away xG": away_xg,
                        }

                        # Update playoff results
                        updated_results = update_playoff_results(playoff_results, new_result)

                        # Reflect changes in session state
                        st.session_state["playoff_results"] = updated_results

                        st.success(f"Result updated for Playoff {selected_game}.", icon="✅")
                    
            # RESET PLAYOFFS BUTTON
            st.markdown("---")  
            st.markdown(
                """
                <div style='text-align: center;'>
                    <strong>Need a playoff mulligan?</strong><br>
                </div>
                """,
                unsafe_allow_html=True,
            )
            # Reset Playoff Bracket
            if st.button("🔄 Reset Playoffs", use_container_width=True):
                if "playoff_results" in st.session_state:
                    st.session_state.pop("playoff_results", None) 
                if "generate_playoffs_clicked" in st.session_state:
                    st.session_state.pop("generate_playoffs_clicked", None)
                if "generate_finals_clicked" in st.session_state:
                    st.session_state.pop("generate_finals_clicked", None)


                st.success("Playoff results cache has been cleared!", icon="✅")
                st.rerun()
        else:
            st.warning("Playoffs are locked. Update Match Results will be available after playoffs are unlocked.", icon="🔒")