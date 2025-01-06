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
)

#-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-
#-- tournament.py: league tab (2nd)
#-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-

def render():
    # Check if the tournament is ready
    if not st.session_state.get("tournament_ready", False):
        st.warning("Please complete the tournament setup before accessing the league.")
        return

    # Check if the schedule is available
    if "schedule" not in st.session_state or not st.session_state["schedule"]:
        st.warning("Tournament schedule is missing. Generate the schedule first.")
        return
    
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 0px;">
            <h3>📅 League Schedule</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Prepare the schedule DataFrame
    schedule_df = pd.DataFrame(st.session_state["schedule"])
    schedule_df = schedule_df.rename(columns={"Home": "Home Player", "Away": "Away Player"})

    # Map team names to players
    schedule_df["Home Team"] = schedule_df["Home Player"].map(st.session_state["teams"])
    schedule_df["Away Team"] = schedule_df["Away Player"].map(st.session_state["teams"])

    # Add status column for completed games
    schedule_df["Status"] = schedule_df["Game #"].apply(
        lambda game_id: "✅" if not pd.isna(
            st.session_state["results"].loc[st.session_state["results"]["Game #"] == game_id, "Home Goals"]
        ).all() else ""
    )

    # Display the schedule
    schedule_df.index = schedule_df.index + 1
    st.dataframe(
        schedule_df[["Game #", "Round", "Home Team", "Away Team", "Console", "Status"]], 
        use_container_width=True,
        hide_index=True,
        )
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 0px;">
            <h3>✏️ Update Match Results</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    selected_game = st.selectbox(
        "Select Game to Update", 
        st.session_state["results"]["Game #"], 
        key="selected_game_dropdown"
    )
    
    if selected_game:
        # Fetch game details
        game_row = st.session_state["results"][st.session_state["results"]["Game #"] == selected_game]
        # Check if game_row is not empty and fetch details safely
        if not game_row.empty:
            home_team = game_row.get("Home Team", pd.Series(["Unknown Team"])).iloc[0]
            away_team = game_row.get("Away Team", pd.Series(["Unknown Team"])).iloc[0]
            home_player = game_row.get("Home", pd.Series(["Unknown Player"])).iloc[0]
            away_player = game_row.get("Away", pd.Series(["Unknown Player"])).iloc[0]

            home_team_full = f"{home_team} ({home_player})"
            away_team_full = f"{away_team} ({away_player})"
        else:
            home_team_full = "Unknown Team (Unknown Player)"
            away_team_full = "Unknown Team (Unknown Player)"

        # Display match details in a card
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
                transition: transform 0.2s;
            " onmouseover="this.style.transform='scale(1.02)'" onmouseout="this.style.transform='scale(1)'">
                <div style="display: flex; align-items: center; margin-bottom: 10px;">
                    <span style="margin-right: 8px;">🎮</span> <strong>Selected Game #:&nbsp;</strong> {selected_game}
                </div>
                <div style="display: flex; align-items: center; margin-bottom: 10px;">
                    <span style="margin-right: 8px;">🆚</span> <strong>Match Type:&nbsp;</strong> League
                </div>
                <div style="display: flex; align-items: center; margin-bottom: 10px;">
                    <span style="margin-right: 8px;">🏠</span> <strong>Home Team:&nbsp;</strong> {home_team_full}
                </div>
                <div style="display: flex; align-items: center; margin-bottom: 10px;">
                    <span style="margin-right: 8px;">✈️</span> <strong>Away Team:&nbsp;</strong> {away_team_full}
                </div>
                <div style="display: flex; align-items: center; margin-bottom: 10px;">
                    <span style="margin-right: 8px;">🕹️</span> <strong>Console:&nbsp;</strong> {game_row['Console'].values[0]}
                </div>
                <div style="display: flex; align-items: center;">
                    <span style="margin-right: 8px;">📅</span> <strong>Round:&nbsp;</strong> {game_row['Round'].values[0]}
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

        # Add confirmation step before updating
        if st.button("✏️ Update Results", key="update_button",use_container_width=True):
            # Create a new result record
            new_result = {
                "Game #": selected_game,
                "Round": game_row["Round"].values[0],
                "Home": game_row["Home"].values[0],
                "Away": game_row["Away"].values[0],
                "Console": game_row["Console"].values[0],
                "Home Team": home_team,
                "Away Team": away_team,
                "Home Goals": home_goals,
                "Away Goals": away_goals,
                "Home xG": home_xg,
                "Away xG": away_xg,
            }

            # Update session state results
            st.session_state["results"] = upsert_results(st.session_state["results"], new_result)

            # Recalculate standings
            games_played = st.session_state["results"].dropna(subset=["Home Goals", "Away Goals"])
            st.session_state["standings"] = initialize_standings(st.session_state["players"], st.session_state["teams"])
            for _, game in games_played.iterrows():
                st.session_state["standings"] = update_standings(st.session_state["standings"], pd.DataFrame([game]))

            st.success(f"Results updated for {selected_game}", icon="✅") 


