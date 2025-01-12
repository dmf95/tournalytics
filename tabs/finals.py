#-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-
#-- dependencies
#-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-

import streamlit as st
import pandas as pd
from utils.tournament_utils import (
    determine_winner,
    validate_playoffs_completion,
    update_playoff_results,
    update_final_matches
    )
from utils.data_utils import save_tournament_complete

#-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-
#-- tournament.py: finals tab (4th)
#-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-

def render():

    # Extract the selected tournament ID and details
    tournament_details = st.session_state["tournaments"][st.session_state["selected_tournament_id"]]
    # Extract necessary details
    players = tournament_details["selected_players"]
    teams = tournament_details["team_selection"]
        
    # Get playoff results
    playoff_results = st.session_state.playoff_results.copy()

    # Ensure semi-finals are completed
    playoffs_complete = validate_playoffs_completion(playoff_results, debug=False)

    # Lock Finals if playoffs not completed
    if not playoffs_complete:
        st.markdown(
            """
            <div style='text-align: center; margin-top: 50px;'>
                <h3 style='margin-bottom: 10px; color: #808080;'>🔒 Locked</h3>
                <p style='font-size: 14px; color: #ccc;'>Complete all ⚔️ Playoff Games to unlock the 🏆 Finals.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Unlock Finals if Playoffs completed
    elif playoffs_complete and ("playoff_results" in st.session_state or st.session_state.playoff_results):

        #...Show button to Generate Finals if not already clicked
        if "generate_finals_clicked" not in st.session_state:
            st.session_state["generate_finals_clicked"] = False

        #...Show button to Generate Finals!
        if not st.session_state["generate_finals_clicked"]:
            # Show button to generate finals bracket
            st.markdown(
                """
                <div style='text-align: center; margin-top: 50px;'>
                    <h3 style='margin-bottom: 10px; color: #808080;'>🔓 Unlocked</h3>
                    <p style='font-size: 14px; color: #ccc;'>⚔️ Playoffs Games Completed! Ready to start the 🏆 Finals.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("🚀 Generate Finals Bracket", key="generate_finals_button", use_container_width=True):
                st.session_state["generate_finals_clicked"] = True
                st.rerun()  # Refresh the app to proceed

        # Only proceed if the finals have been generated
        if st.session_state["generate_finals_clicked"]:
            
            # Determine semi-final winners and update finals
            final_results = update_final_matches(playoff_results)

            # Display finals information
            final_matches = final_results[final_results["Match"].str.contains("Final", na=False)]
            # Add team names and status to playoff results
            final_matches["Home Team"] = final_matches["Home"].map(teams)
            final_matches["Away Team"] = final_matches["Away"].map(teams)
            if final_matches.empty:
                st.info("No finals matches available.", icon="ℹ️")
                return
            # Add status column to indicate match completion
            final_matches["Status"] = final_matches.apply(
                lambda row: "✅" if pd.notna(row["Home Goals"]) and pd.notna(row["Away Goals"]) else "⏳ TBD", axis=1
            )
            # Display finals bracket
            st.markdown("<div style='text-align: center;'><h3>🏆 Finals</h3></div>", unsafe_allow_html=True)
            final_bracket = final_matches[["Game #", "Match", "Home Team", "Away Team", "Console", "Status"]]
            st.dataframe(final_bracket, use_container_width=True, hide_index=True)

            # Check if all finals matches are complete
            if final_matches["Status"].eq("✅").all():
                #-1- save results to firebase
                st.markdown("<div style='text-align: center; margin: 10px;'><h3>💾 Save Tournament Results</h3></div>", unsafe_allow_html=True)
                if st.button("💾 Save Tournament Results", use_container_width=True):
                    with st.spinner("Saving tournament results..."):
                        try:
                            save_tournament_complete(st.session_state, verbose=True)
                            st.success("Tournament results saved successfully! 🎉", icon="✅")
                        except Exception as e:
                            st.error(f"An error occurred: {str(e)}", icon="❌")
                #-2- display the champion
                overall_winner = determine_winner(final_matches)
                winner_team = teams[overall_winner]
                st.markdown(
                    f"""
                    <div style="text-align: center; margin: 5px 0; font-family: Arial, sans-serif;">
                        <h2 style="color: #FFD700; font-size: 1.8em; line-height: 1.1; font-weight: bold;">🎉 {winner_team} 🎉</h2>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.image("assets/_champion.gif", caption=f"{winner_team} ({overall_winner}) is your champion!", use_container_width=True)

            else:
                st.info("Complete all finals matches to determine the champion.", icon="ℹ️")


            # Allow updating results for Finals playoffs games only if Finals are not locked
            st.markdown("---")
            st.markdown(
                """
                <div style="text-align: center; margin-bottom: 0px;">
                    <h3>✏️ Update Match Results</h3>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if final_matches.empty:
                st.info("No finals matches available to update.", icon="ℹ️")
            else:
                # Create a selectbox for finals games
                selected_game = st.selectbox("Select Finals Game to Update", final_matches["Game #"])
                
                if selected_game:
                    # Get the match row for the selected game
                    match_row = final_matches[final_matches["Game #"] == selected_game].iloc[0]
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
                with st.form(key="update_finals_form", clear_on_submit=False):
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
                    submitted = st.form_submit_button(f"✏️ Update {selected_game} (Finals) Results", use_container_width=True)

                    if submitted:
                        # Construct a new result record
                        new_results = {
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
                        updated_results = update_playoff_results(st.session_state.playoff_results, new_results)

                        # Reflect changes in session state
                        st.session_state.playoff_results = updated_results

                        st.success(f"Results updated for Finals {selected_game}.", icon="✅")

            # RESET FINALS BUTTON
            st.markdown("---")  
            st.markdown(
                """
                <div style='text-align: center;'>
                    <strong>Need a Finals mulligan?</strong><br>
                </div>
                """,
                unsafe_allow_html=True,
            )
            # Reset Playoff Bracket
            if st.button("🔄 Reset Finals", use_container_width=True):
                if "generate_finals_clicked" in st.session_state:
                    st.session_state.pop("generate_finals_clicked", None)  # Safely remove finals button state
                st.success("Finals results and state have been cleared!", icon="✅")
                st.rerun()