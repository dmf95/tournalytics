#-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-
#-- dependencies
#-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-

# main libraries
import streamlit as st
import pandas as pd
# custom libraries
from utils.tournament_utils import (
    update_league_game_results,
)

#-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-
#-- tournament.py: league tab (2nd)
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
    
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 0px;">
            <h3>📅 League Schedule</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Extract the selected tournament ID and details
    tournament_details = st.session_state["tournaments"][st.session_state["selected_tournament_id"]]

    # Extract necessary details
    players = tournament_details["selected_players"]
    teams = tournament_details["team_selection"]

    # Generate and update League Schedule DataFrame dynamically
    schedule_df = pd.DataFrame(st.session_state["schedule"])
    schedule_df["Home Team"] = schedule_df["Home"].map(teams)
    schedule_df["Away Team"] = schedule_df["Away"].map(teams)

    # Update the Status column dynamically based on results
    if "results" in st.session_state and not st.session_state["results"].empty:
        results_df = st.session_state["results"]

        # Precompute completed games using valid results
        completed_games = results_df.loc[
            results_df["Home Goals"].notna() & results_df["Away Goals"].notna(), "Game #"
        ].tolist()

        # Map completed games to their statuses
        status_map = {game_id: "✅" for game_id in completed_games}

        # Apply the status mapping with a default value for incomplete games
        schedule_df["Status"] = schedule_df["Game #"].map(status_map).fillna("⏳ TBD")
    else:
        # Default status if no results are available
        schedule_df["Status"] = "⏳ TBD"


    # Display the schedule with dynamic status updates
    st.dataframe(
        schedule_df[["Game #", "Round", "Home Team", "Away Team", "Console", "Status"]],
        use_container_width=True,
    )


    # Render UI for Updating Match Results
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 0px;">
            <h3>✏️ Update Match Results</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Select the game to update
    selected_game = st.selectbox(
        "Select Game to Update",
        st.session_state["results"]["Game #"],
        key="selected_game_dropdown",
    )

    if selected_game:
        # Fetch game details
        game_row = st.session_state["results"].loc[
            st.session_state["results"]["Game #"] == selected_game
        ]

        if not game_row.empty:
            # Safely extract game details
            game_details = game_row.iloc[0]
            home_player = game_details["Home"]
            away_player = game_details["Away"]
            home_team = game_details["Home Team"]
            away_team = game_details["Away Team"]
            console = game_details["Console"]
            round_number = int(game_details["Round"])

            # Display game details in a card
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
                        <span style="margin-right: 8px;">🏠</span> <strong>Home Team:&nbsp;</strong> {home_team}
                    </div>
                    <div style="display: flex; align-items: center; margin-bottom: 10px;">
                        <span style="margin-right: 8px;">✈️</span> <strong>Away Team:&nbsp;</strong> {away_team}
                    </div>
                    <div style="display: flex; align-items: center; margin-bottom: 10px;">
                        <span style="margin-right: 8px;">🕹️</span> <strong>Console:&nbsp;</strong> {console}
                    </div>
                    <div style="display: flex; align-items: center;">
                        <span style="margin-right: 8px;">📅</span> <strong>Round:&nbsp;</strong> {round_number}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Create a form for updating match results
            with st.form(key="update_match_form", clear_on_submit=False):
                col1, col2 = st.columns(2)
                with col1:
                    home_goals = st.number_input(
                        f"Goals for {home_team}", 
                        min_value=0, 
                        step=1, 
                        key=f"home_goals_{selected_game}"
                    )
                    home_xg = st.number_input(
                        f"xG for {home_team}", 
                        min_value=0.0, 
                        step=0.1, 
                        key=f"home_xg_{selected_game}"
                    )
                with col2:
                    away_goals = st.number_input(
                        f"Goals for {away_team}", 
                        min_value=0, 
                        step=1, 
                        key=f"away_goals_{selected_game}"
                    )
                    away_xg = st.number_input(
                        f"xG for {away_team}", 
                        min_value=0.0, 
                        step=0.1, 
                        key=f"away_xg_{selected_game}"
                    )

                # Form submission button
                submitted = st.form_submit_button("✏️ Update League Match Results", use_container_width=True)
                if submitted:
                    # Construct a new result record
                    new_result = {
                        "Game #": selected_game,
                        "Round": round_number,
                        "Home": home_player,
                        "Away": away_player,
                        "Console": console,
                        "Home Team": home_team,
                        "Away Team": away_team,
                        "Played": 1,
                        "Home Goals": home_goals,
                        "Away Goals": away_goals,
                        "Home xG": home_xg,
                        "Away xG": away_xg,
                    }

                    # Update results and standings
                    updated_results, updated_standings = update_league_game_results(
                        results_df=st.session_state["results"],
                        new_result=new_result,
                        players=players,
                        teams=teams
                    )

                    # Update session state with new data
                    st.session_state["results"] = updated_results
                    st.session_state["standings"] = updated_standings

                    st.success(f"Result updated for League {selected_game}.", icon="✅")

        else:
            st.warning("Playoffs are locked. Update Match Results will be available after playoffs are unlocked.", icon="🔒")