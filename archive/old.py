import streamlit as st
from utils import (
    generate_tournament_id,
    generate_schedule,
    validate_schedule,
    initialize_standings,
    upsert_results,
    update_standings,
    calculate_outcomes,
    calculate_tournament_duration,
    generate_playoffs_bracket,
    load_previous_tournaments,
    save_tournament,
    load_player_data,
    determine_winner,
)
import pandas as pd
import numpy as np


# Centralized session state initialization
def initialize_session_state():
    defaults = {
        "tournament_id": None,
        "tournament_name": "New Tournament",
        "players": [],
        "teams": {},
        "schedule": None,
        "results": pd.DataFrame(),  # Empty DataFrame
        "standings": None,
        "total_duration": 0,
        "team_management_time": 0,
        "playoff_results": pd.DataFrame(),  # Empty DataFrame
        "completed": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state or st.session_state[key] is None:
            st.session_state[key] = value

def main():
    # Initialize session state
    initialize_session_state()

    # App title
    st.title("🎮 Tournalytics 🎮")

    # Load player data
    players_df = load_player_data()
    player_names = players_df["first_name"] + " " + players_df["last_name"]

    # Tournament Setup
    st.sidebar.header("Tournament Setup")
    st.session_state["tournament_name"] = st.sidebar.text_input("Tournament Name", value=st.session_state["tournament_name"])
    num_players = st.sidebar.slider("Number of Players", min_value=6, max_value=12, value=6)
    num_consoles = st.sidebar.slider("Number of Consoles", min_value=1, max_value=4, value=2)
    half_duration = st.sidebar.slider("Half Duration (minutes)", min_value=4, max_value=6, value=5)

    selected_players = st.sidebar.multiselect("Select Players", player_names, default=player_names[:num_players])
    team_selection = {
        player: st.sidebar.text_input(f"Team for {player}", value=f"Team {player}")
        for player in selected_players
    }

    # Validate player selection
    if len(selected_players) != num_players:
        st.sidebar.error(f"Please select exactly {num_players} players.")
        return

    # Generate tournament schedule
    if st.sidebar.button("Generate Tournament Schedule"):
        st.session_state["tournament_id"] = generate_tournament_id()
        st.session_state["players"] = selected_players
        st.session_state["teams"] = team_selection
        st.session_state["schedule"] = generate_schedule(selected_players, team_selection, num_consoles)
        validation_messages = validate_schedule(st.session_state["schedule"], num_consoles)
        st.session_state["results"] = pd.DataFrame(st.session_state["schedule"])
        st.session_state["results"]["Home Goals"] = np.nan
        st.session_state["results"]["Away Goals"] = np.nan
        st.session_state["results"]["Home xG"] = np.nan
        st.session_state["results"]["Away xG"] = np.nan
        st.session_state["standings"] = initialize_standings(selected_players, team_selection)

        for player, team in team_selection.items():
            st.session_state["standings"].loc[st.session_state["standings"]["Player"] == player, "Team"] = team

        if validation_messages:
            for message in validation_messages:
                st.error(message)
        else:
            st.info("All scheduling validations passed.")

        total_duration, team_management_time = calculate_tournament_duration(
            st.session_state["schedule"], half_duration
        )
        st.session_state["total_duration"] = total_duration
        st.session_state["team_management_time"] = team_management_time

    # Ensure tournament is initialized
    if not st.session_state["tournament_id"]:
        st.sidebar.warning("Please generate a tournament schedule to proceed.")
        return

    # Sidebar tournament details
    st.sidebar.write(f"**Tournament ID**: {st.session_state['tournament_id']}")
    st.sidebar.write(f"**Tournament Name**: {st.session_state['tournament_name']}")
    st.sidebar.write(f"**Total Duration**: {st.session_state['total_duration']} minutes")
    st.sidebar.write(f"**Team Management Time**: {st.session_state['team_management_time']} minutes")

    # Tabs for tournament details
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Standings", "📅 League", "🥊 Playoffs", "🏆 Finals"])

    # League Standings
    with tab1:
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


    # Match Schedule
    with tab2:
        st.header("Match Schedule")

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

    with tab3:
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



    with tab4:
        if "playoff_results" not in st.session_state:
            st.warning("Playoffs have not been generated yet.")
            st.stop()

        playoff_results = st.session_state.playoff_results.copy()

        # Check semi-final completion
        semi_final_matches = playoff_results[playoff_results["Match"].str.startswith("SF")]
        if semi_final_matches["Home Goals"].isna().any() or semi_final_matches["Away Goals"].isna().any():
            st.warning("Finals are locked until all semi-final matches are completed.")
            st.stop()

        # Determine winners for SF1 and SF2
        sf1_matches = playoff_results[playoff_results["Match"].str.startswith("SF1")]
        sf2_matches = playoff_results[playoff_results["Match"].str.startswith("SF2")]

        sf1_win = determine_winner(sf1_matches) if not sf1_matches.dropna(subset=["Home Goals", "Away Goals"]).empty else None
        sf2_win = determine_winner(sf2_matches) if not sf2_matches.dropna(subset=["Home Goals", "Away Goals"]).empty else None


        # Update final matches with semi-final winners
        if sf1_win and sf2_win:
            final_matches = playoff_results["Match"].str.startswith("Final")
            playoff_results.loc[final_matches, ["Home", "Away"]] = (
                playoff_results.loc[final_matches, ["Home", "Away"]]
                .replace({"Winner SF1": sf1_win, "Winner SF2": sf2_win})
            )
            
            # Write back updated playoff results to session state
            st.session_state.playoff_results = playoff_results.copy()
        
        # Display Finals
        final_matches = playoff_results[playoff_results["Match"].str.contains("Final", na=False)]
        if final_matches.empty:
            st.info("No finals matches available.")
        else:
            # Check if all finals games are complete
            if not final_matches["Home Goals"].isna().any() and not final_matches["Away Goals"].isna().any():
                # Determine the overall winner
                overall_winner = determine_winner(final_matches)
                winner_team = st.session_state.teams[overall_winner]

                # Display winner message and GIF under the header
                st.markdown(f"### 🏆 Congratulations to **{winner_team}**! 🏆")
                st.image("assets/_champion.gif", caption=f"{winner_team} is the champion!")

            # Add team names and status to playoff results
            final_matches["Home Team"] = final_matches["Home"].map(st.session_state.teams)
            final_matches["Away Team"] = final_matches["Away"].map(st.session_state.teams)
            final_matches["Status"] = final_matches["Game #"].apply(
                lambda game_id: "✅" if not pd.isna(
                    final_matches.loc[final_matches["Game #"] == game_id, "Home Goals"]
                ).all() else ""
            )

            # Display playoff results with consistent attributes
            st.subheader("Finals")
            final_bracket = final_matches[["Game #", "Match", "Home Team", "Away Team", "Console", "Status"]]
            st.dataframe(
                final_bracket[final_bracket["Match"].str.contains("Final", na=False)],
                use_container_width=True,
            )

            # Allow updating results for finals games
            st.subheader("Update Finals Match Results")
            selected_final_game = st.selectbox("Select Finals Game to Update", final_matches["Game #"])

            if selected_final_game:
                match_row = final_matches[final_matches["Game #"] == selected_final_game].iloc[0]
                home_team = match_row["Home"]
                away_team = match_row["Away"]

                st.write(f"**Home Team**: {home_team}")
                st.write(f"**Away Team**: {away_team}")

                home_goals = st.number_input(f"Goals for {home_team}", min_value=0, step=1, key=f"home_goals_final_{selected_final_game}")
                away_goals = st.number_input(f"Goals for {away_team}", min_value=0, step=1, key=f"away_goals_final_{selected_final_game}")
                home_xg = st.number_input(f"xG for {home_team}", min_value=0.0, step=0.1, key=f"home_xg_final_{selected_final_game}")
                away_xg = st.number_input(f"xG for {away_team}", min_value=0.0, step=0.1, key=f"away_xg_final_{selected_final_game}")

                if st.button("Update Finals Match Results"):
                    st.session_state.playoff_results.loc[
                        st.session_state.playoff_results["Game #"] == selected_final_game,
                        ["Home Goals", "Away Goals", "Home xG", "Away xG"]
                    ] = [home_goals, away_goals, home_xg, away_xg]

                    st.success(f"Results updated for Finals Game {selected_final_game}")

    # Save Tournament
    if st.sidebar.button("Finalize and Save Tournament Statistics"):
        if st.session_state["results"] is not None and not st.session_state["results"].empty:
            save_tournament(
                st.session_state["tournament_id"],
                st.session_state["tournament_name"],
                st.session_state["standings"],
                st.session_state["results"]
            )
            st.session_state["completed"] = True
            st.success("Tournament statistics saved successfully!")
        else:
            st.sidebar.error("Cannot finalize: No results available.")


if __name__ == "__main__":
    main()
