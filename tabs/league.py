from utils import (
    initialize_standings,
    upsert_results,
    update_standings,

)
import streamlit as st
import pandas as pd
import numpy as np

# League (tab2)
def render():
    st.header("League Schedule")

    schedule_df = pd.DataFrame(st.session_state.schedule)
    schedule_df = schedule_df.rename(columns={"Home": "Home Player", "Away": "Away Player"})

    # Add team names to the schedule
    schedule_df["Home Team"] = schedule_df["Home Player"].map(st.session_state.teams)
    schedule_df["Away Team"] = schedule_df["Away Player"].map(st.session_state.teams)

    # Add status column for completed games
    schedule_df["Status"] = schedule_df["Game #"].apply(
        lambda game_id: "✅" if not pd.isna(
            st.session_state.results.loc[st.session_state.results["Game #"] == game_id, "Home Goals"]
        ).all() else ""
    )

    schedule_df.index = schedule_df.index + 1

    st.dataframe(schedule_df[["Game #", "Round", "Home Team", "Away Team", "Console", "Status"]], use_container_width=True)

    st.subheader("Update Match Results")
    selected_game = st.selectbox("Select Game to Update", st.session_state.results["Game #"])

    if selected_game:
        game_row = st.session_state.results[st.session_state.results["Game #"] == selected_game]
        home_team = game_row["Home Team"].values[0]
        away_team = game_row["Away Team"].values[0]

        st.write(f"**Home Team**: {home_team}")
        st.write(f"**Away Team**: {away_team}")

        home_goals = st.number_input(f"Goals for {home_team}", min_value=0, step=1, key=f"home_goals_{selected_game}")
        away_goals = st.number_input(f"Goals for {away_team}", min_value=0, step=1, key=f"away_goals_{selected_game}")
        home_xg = st.number_input(f"Expected Goals (xG) for {home_team}", min_value=0.0, step=0.1, key=f"home_xg_{selected_game}")
        away_xg = st.number_input(f"Expected Goals (xG) for {away_team}", min_value=0.0, step=0.1, key=f"away_xg_{selected_game}")

        if st.button("Update Results"):
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
                "Away xG": away_xg
            }

            st.session_state.results = upsert_results(st.session_state.results, new_result)

            # Update standings dynamically based on games played
            games_played = st.session_state.results.dropna(subset=["Home Goals", "Away Goals"])
            st.session_state.standings = initialize_standings(st.session_state.players, st.session_state.teams)
            for _, game in games_played.iterrows():
                st.session_state.standings = update_standings(st.session_state.standings, pd.DataFrame([game]))

            st.success(f"Results updated for {selected_game}")