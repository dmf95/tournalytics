#-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-
#-- dependencies
#-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, date
import json
from utils.tournament_utils import determine_winner
from utils.data_utils import save_tournament_complete, CustomJSONEncoder, save_tournament_complete_local
import json
#-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-
#-- tournament.py: finals tab (4th)
#-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-


def render():
    # Validate session state
    if "playoff_results" not in st.session_state or st.session_state.playoff_results.empty:
        st.markdown(
            """
            <div style='text-align: center; margin-top: 50px;'>
                <h3 style='margin-bottom: 10px; color: #808080;'>🔒 Locked</h3>
                <p style='font-size: 14px; color: #ccc;'>Complete all Playoff Games to unlock the Finals Matchup.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.stop()

    playoff_results = st.session_state.playoff_results.copy()

    # Ensure semi-finals are completed
    validate_semi_final_completion(playoff_results)

    # Determine semi-final winners and update finals
    update_final_matches(playoff_results)

    # Display finals information
    final_matches = playoff_results[playoff_results["Match"].str.contains("Final", na=False)]
    if final_matches.empty:
        st.info("No finals matches available.", icon="ℹ️")
        return

    display_final_matches(final_matches)


# Helper: Validate semi-final completion
def validate_semi_final_completion(playoff_results):
    semi_final_matches = playoff_results[playoff_results["Match"].str.startswith("SF")]
    if semi_final_matches["Home Goals"].isna().any() or semi_final_matches["Away Goals"].isna().any():
        st.markdown(
            """
            <div style='text-align: center; margin-top: 50px;'>
                <h3 style='margin-bottom: 10px; color: #808080;'>🔒 Locked</h3>
                <p style='font-size: 14px; color: #ccc;'>Complete all Playoff Games to unlock the Finals Matchup.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.stop()

# Helper: Update final matches
def update_final_matches(playoff_results):
    sf1_matches = playoff_results[playoff_results["Match"].str.startswith("SF1")]
    sf2_matches = playoff_results[playoff_results["Match"].str.startswith("SF2")]

    sf1_win = determine_winner(sf1_matches) if not sf1_matches.dropna(subset=["Home Goals", "Away Goals"]).empty else None
    sf2_win = determine_winner(sf2_matches) if not sf2_matches.dropna(subset=["Home Goals", "Away Goals"]).empty else None

    if sf1_win and sf2_win:
        final_matches = playoff_results["Match"].str.startswith("Final")
        playoff_results.loc[final_matches, ["Home", "Away"]] = (
            playoff_results.loc[final_matches, ["Home", "Away"]]
            .replace({"Winner SF1": sf1_win, "Winner SF2": sf2_win})
        )
        st.session_state.playoff_results = playoff_results.copy()

# Helper: Display finals
def display_final_matches(final_matches):
    # Add team names and status
    final_matches["Home Team"] = final_matches["Home"].map(st.session_state.teams)
    final_matches["Away Team"] = final_matches["Away"].map(st.session_state.teams)
    final_matches["Status"] = final_matches["Game #"].apply(
        lambda game_id: "✅" if not pd.isna(
            final_matches.loc[final_matches["Game #"] == game_id, "Home Goals"]
        ).all() else ""
    )

    # Display finals bracket
    st.markdown("<div style='text-align: center;'><h3>🏆 Finals</h3></div>", unsafe_allow_html=True)
    final_bracket = final_matches[["Game #", "Match", "Home Team", "Away Team", "Console", "Status"]]
    st.dataframe(final_bracket, use_container_width=True, hide_index=True)

    # Display champion if all finals are completed
    if not final_matches["Home Goals"].isna().any() and not final_matches["Away Goals"].isna().any():
        #handle_results_saving_local()
        handle_results_saving()
        display_champion(final_matches)

    st.markdown("---")
    handle_results_update(final_matches)

# Helper: Display champion
def display_champion(final_matches):
    overall_winner = determine_winner(final_matches)
    winner_team = st.session_state.teams[overall_winner]
    st.markdown(
        f"""
        <div style="text-align: center; margin: 5px 0; font-family: Arial, sans-serif;">
            <h2 style="color: #FFD700; font-size: 1.8em; line-height: 1.1; font-weight: bold;">🎉 {winner_team} 🎉</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.image("assets/_champion.gif", caption=f"{winner_team} are the champions!", use_container_width=True)

# Helper: Save results
"""
def handle_results_saving_local():
    st.markdown("<div style='text-align: center; margin: 10px;'><h3>💾 Save Tournament Results</h3></div>", unsafe_allow_html=True)
    if st.button("💾 Save Tournament Results", use_container_width=True):
        with st.spinner("Saving tournament results..."):
            try:
                path = 'assets/'
                save_tournament_complete_local(st.session_state, path, verbose=True)
                st.success("Tournament results saved successfully! 🎉", icon="✅")
            except Exception as e:
                st.error(f"An error occurred: {str(e)}", icon="❌")
"""
# Helper: Save results
def handle_results_saving():
    st.markdown("<div style='text-align: center; margin: 10px;'><h3>💾 Save Tournament Results</h3></div>", unsafe_allow_html=True)
    if st.button("💾 Save Tournament Results", use_container_width=True):
        with st.spinner("Saving tournament results..."):
            try:
                save_tournament_complete(st.session_state, verbose=True)
                st.success("Tournament results saved successfully! 🎉", icon="✅")
            except Exception as e:
                st.error(f"An error occurred: {str(e)}", icon="❌")

# Helper: Update results
def handle_results_update(final_matches):
    st.markdown("<div style='text-align: center;'><h3>✏️ Update Finals Match Results</h3></div>", unsafe_allow_html=True)
    selected_game = st.selectbox("Select Finals Game to Update", final_matches["Game #"])

    if selected_game:
        match_row = final_matches[final_matches["Game #"] == selected_game].iloc[0]
        home_team = match_row["Home Team"]
        away_team = match_row["Away Team"]
        display_match_details(selected_game, match_row, home_team, away_team)
        update_match_results(selected_game, home_team, away_team)

# Helper: Display match details
def display_match_details(selected_game, match_row, home_team, away_team):
    st.markdown(
        f"""
        <div style="background-color: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); 
                    padding: 15px; border-radius: 10px; margin-bottom: 20px; text-align: left; 
                    color: #ffffff; font-size: 1.1em; line-height: 1.6;">
            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                🎮 <strong>Game #:</strong> {selected_game}
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                🆚 <strong>Match Type:</strong> {match_row["Match"]}
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                🕹️ <strong>Console:</strong> {match_row["Console"]}
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                🏠 <strong>Home Team:</strong> {home_team}
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                ✈️ <strong>Away Team:</strong> {away_team}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Helper: Update match results
def update_match_results(selected_game, home_team, away_team):
    col1, col2 = st.columns(2)
    with col1:
        home_goals = st.number_input(f"Goals for {home_team}", min_value=0, step=1, key=f"home_goals_{selected_game}")
    with col2:
        home_xg = st.number_input(f"xG for {home_team}", min_value=0.0, step=0.1, key=f"home_xg_{selected_game}")

    col3, col4 = st.columns(2)
    with col3:
        away_goals = st.number_input(f"Goals for {away_team}", min_value=0, step=1, key=f"away_goals_{selected_game}")
    with col4:
        away_xg = st.number_input(f"xG for {away_team}", min_value=0.0, step=0.1, key=f"away_xg_{selected_game}")

    if st.button(f"✏️ Update Match Results ({selected_game})", use_container_width=True):
        idx = st.session_state.playoff_results[st.session_state.playoff_results["Game #"] == selected_game].index[0]
        st.session_state.playoff_results.at[idx, "Home Goals"] = home_goals
        st.session_state.playoff_results.at[idx, "Away Goals"] = away_goals
        st.session_state.playoff_results.at[idx, "Home xG"] = home_xg
        st.session_state.playoff_results.at[idx, "Away xG"] = away_xg
        st.success(f"Results updated for Game #{selected_game}", icon="✅")
