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
    create_bracket_visualization,
    plot_bracket,
    load_previous_tournaments,
    save_tournament,
    load_player_data,
)
import pandas as pd
import numpy as np
import re  # Import regex for extracting numbers

def main():
    st.title("🎮 Tournalytics 🎮")

    # Load player data
    players_df = load_player_data()
    player_names = players_df["first_name"] + " " + players_df["last_name"]

    # Tournament Setup
    st.sidebar.header("Tournament Setup")
    tournament_name = st.sidebar.text_input("Tournament Name", value="New Tournament")
    num_players = st.sidebar.slider("Number of Players", min_value=6, max_value=12, value=6)
    num_consoles = st.sidebar.slider("Number of Consoles", min_value=1, max_value=4, value=2)
    half_duration = st.sidebar.slider("Half Duration (minutes)", min_value=4, max_value=6, value=5)

    selected_players = st.sidebar.multiselect("Select Players", player_names, default=player_names[:num_players])
    team_selection = {
        player: st.sidebar.text_input(f"Team for {player}", value=f"Team {player}")
        for player in selected_players
    }

    if len(selected_players) != num_players:
        st.sidebar.error(f"Please select exactly {num_players} players.")
        return

    if st.sidebar.button("Generate Tournament Schedule"):
        st.session_state.tournament_id = generate_tournament_id()
        st.session_state.tournament_name = tournament_name
        st.session_state.players = selected_players
        st.session_state.teams = team_selection
        st.session_state.schedule = generate_schedule(st.session_state.players, st.session_state.teams, num_consoles)
        validation_messages = validate_schedule(st.session_state.schedule, num_consoles)
        st.session_state.results = pd.DataFrame(st.session_state.schedule)
        st.session_state.results["Home Goals"] = np.nan
        st.session_state.results["Away Goals"] = np.nan
        st.session_state.results["Home xG"] = np.nan
        st.session_state.results["Away xG"] = np.nan

        # Corrected call to initialize_standings
        st.session_state.standings = initialize_standings(st.session_state.players, st.session_state.teams)

        for player, team in team_selection.items():
            st.session_state.standings.loc[st.session_state.standings["Player"] == player, "Team"] = team
        st.session_state.completed = False

        if validation_messages:
            for message in validation_messages:
                st.error(message)
        else:
            st.info("All scheduling validations passed.")

        total_duration, team_management_time = calculate_tournament_duration(st.session_state.schedule, half_duration)
        st.session_state.total_duration = total_duration
        st.session_state.team_management_time = team_management_time



    if "tournament_id" not in st.session_state:
        st.sidebar.warning("Please generate a tournament schedule to proceed.")
        return

    st.sidebar.write(f"**Tournament ID**: {st.session_state.tournament_id}")
    st.sidebar.write(f"**Tournament Name**: {st.session_state.tournament_name}")

    st.sidebar.write(f"**Total Tournament Duration**: {st.session_state.total_duration} minutes (+ {st.session_state.team_management_time} minutes for team management)")

    with st.sidebar.expander("View Previous Tournaments"):
        previous_tournaments = load_previous_tournaments()
        if not previous_tournaments.empty:
            st.dataframe(previous_tournaments)
        else:
            st.write("No previous tournaments found.")

    tab1, tab2, tab3 = st.tabs(["📊 Standings", "📅 League", "🏆 Playoffs"])

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
            playoff_games_played_summary = playoff_games_played[["Game #", "Home", "Away", "Home Goals", "Away Goals", "Home xG", "Away xG"]]
            playoff_games_played_summary["Home xG"] = playoff_games_played_summary["Home xG"].round(2)
            playoff_games_played_summary["Away xG"] = playoff_games_played_summary["Away xG"].round(2)
            
            # Reset index to start from 1 for display
            playoff_games_played_summary.index = playoff_games_played_summary.index + 1

            st.dataframe(
                playoff_games_played_summary,
                use_container_width=True
            )



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
        st.header("Playoffs Bracket")

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
                # Generate playoff games only once
                st.session_state.playoff_results = pd.DataFrame(generate_playoffs_bracket(ranked_standings, last_game_id))
                st.session_state.playoff_results["Home Goals"] = np.nan
                st.session_state.playoff_results["Away Goals"] = np.nan
                st.session_state.playoff_results["Home xG"] = np.nan
                st.session_state.playoff_results["Away xG"] = np.nan

            # Display playoff results
            st.subheader("Playoff Bracket Details")
            st.dataframe(
                st.session_state.playoff_results[["Game #", "Round", "Home", "Away", "Console", "Home Goals", "Away Goals", "Home xG", "Away xG"]],
                use_container_width=True,
            )

            # Allow updating results for playoff games
            st.subheader("Update Playoff Match Results")
            selected_game = st.selectbox("Select Game to Update", st.session_state.playoff_results["Game #"])

            if selected_game:
                # Get match details
                match_row = st.session_state.playoff_results[st.session_state.playoff_results["Game #"] == selected_game].iloc[0]
                home_team = match_row["Home"]
                away_team = match_row["Away"]

                st.write(f"**Home Team**: {home_team}")
                st.write(f"**Away Team**: {away_team}")

                # Input fields for match results
                home_goals = st.number_input(f"Goals for {home_team}", min_value=0, step=1, key=f"home_goals_{selected_game}")
                away_goals = st.number_input(f"Goals for {away_team}", min_value=0, step=1, key=f"away_goals_{selected_game}")
                home_xg = st.number_input(f"xG for {home_team}", min_value=0.0, step=0.1, key=f"home_xg_{selected_game}")
                away_xg = st.number_input(f"xG for {away_team}", min_value=0.0, step=0.1, key=f"away_xg_{selected_game}")

                if st.button("Update Playoff Match Results"):
                    # Update results in the playoff bracket
                    st.session_state.playoff_results.loc[st.session_state.playoff_results["Game #"] == selected_game, ["Home Goals", "Away Goals", "Home xG", "Away xG"]] = [
                        home_goals, away_goals, home_xg, away_xg
                    ]

                    # Recalculate standings dynamically after playoff results are updated
                    if "standings" in st.session_state:
                        playoff_games_played = st.session_state.playoff_results.dropna(subset=["Home Goals", "Away Goals"]).copy()
                        st.session_state.standings = update_standings(st.session_state.standings, playoff_games_played)

                    st.success(f"Results updated for {selected_game}")

            # Plot the updated playoffs bracket
            st.subheader("Updated Bracket Visualization")
            bracket_plot = plot_bracket(st.session_state.playoff_results)
            st.plotly_chart(bracket_plot)


    if st.sidebar.button("Finalize and Save Tournament Statistics"):
        if st.session_state.results["Home Goals"].isnull().any() or st.session_state.results["Away Goals"].isnull().any():
            st.sidebar.error("Cannot finalize: Not all match results have been entered.")
        else:
            save_tournament(
                st.session_state.tournament_id,
                st.session_state.tournament_name,
                standings,
                st.session_state.results
            )
            st.session_state.completed = True
            st.success("Tournament statistics saved successfully!")

if __name__ == "__main__":
    main()
