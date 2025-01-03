import pandas as pd
import numpy as np
import random
import os
import uuid
import plotly.figure_factory as ff
import streamlit as st

# Function to generate a unique tournament ID
def generate_tournament_id():
    return str(uuid.uuid4())[:8]

# Function to generate a round-robin schedule considering consoles, minimizing concurrent games
def generate_schedule(players, teams, num_consoles):
    schedule = []
    num_players = len(players)
    matchups = [(players[i], players[j]) for i in range(num_players) for j in range(i + 1, num_players)]
    random.shuffle(matchups)  # Shuffle to randomize the schedule
    home_away_count = {player: 0 for player in players}
    game_id = 1  # Unique game ID counter
    round_num = 1

    while matchups:
        games_in_round = []
        players_in_round = set()
        used_consoles = set()

        # Attempt to fill the round with up to `num_consoles` games
        while len(games_in_round) < num_consoles and matchups:
            home, away = matchups.pop(0)

            # Ensure no player duplication in the current round
            if home in players_in_round or away in players_in_round:
                matchups.append((home, away))  # Defer to a later round
                continue

            # Assign the next available console
            console = f"Console {len(used_consoles) + 1}"
            if console in used_consoles:
                matchups.append((home, away))  # Defer to a later round
                continue

            used_consoles.add(console)

            # Balance home/away games
            if home_away_count[home] > home_away_count[away]:
                home, away = away, home

            games_in_round.append({
                "Game #": f"Game{game_id}",
                "Round": round_num,
                "Home": home,
                "Away": away,
                "Console": console,
                "Home Team": teams[home],
                "Away Team": teams[away],
                "Played": ""  # Placeholder for played status
            })

            players_in_round.add(home)
            players_in_round.add(away)
            home_away_count[home] += 1
            game_id += 1

        # Add the completed round to the schedule
        schedule.extend(games_in_round)
        round_num += 1

    return schedule

# Function to validate the schedule
def validate_schedule(schedule, num_consoles):
    validation_messages = []

    # Validate no player plays more than once per round
    for round_num in set(game['Round'] for game in schedule):
        players_in_round = set()
        for game in filter(lambda g: g['Round'] == round_num, schedule):
            if game['Home'] in players_in_round or game['Away'] in players_in_round:
                validation_messages.append(f"Round {round_num}: Player conflict detected.")
            players_in_round.add(game['Home'])
            players_in_round.add(game['Away'])

    # Validate no console is used more than once per round
    for round_num in set(game['Round'] for game in schedule):
        consoles_in_round = set()
        for game in filter(lambda g: g['Round'] == round_num, schedule):
            if game['Console'] in consoles_in_round:
                validation_messages.append(f"Round {round_num}: Console conflict detected.")
            consoles_in_round.add(game['Console'])

    # Validate the maximum number of games per round matches the number of consoles
    for round_num in set(game['Round'] for game in schedule):
        games_in_round = list(filter(lambda g: g['Round'] == round_num, schedule))
        if len(games_in_round) > num_consoles:
            validation_messages.append(f"Round {round_num}: Too many games scheduled for available consoles.")

    return validation_messages

# Function to initialize standings
def initialize_standings(players, teams):
    # Ensure all players have teams
    if not all(player in teams for player in players):
        raise ValueError("Some players do not have corresponding teams in the 'teams' dictionary.")

    return pd.DataFrame({
        "Player": players,
        "Team": [teams[player] for player in players],
        "Points": 0,
        "Goals": 0,
        "xG": 0.00,
        "Games Played": 0
    })


# Function to upsert results and avoid duplicates
def upsert_results(results, new_result):
    # Remove duplicates based on Game #
    results = results.drop(results[results["Game #"] == new_result["Game #"]].index)
    # Append the new result
    results = pd.concat([results, pd.DataFrame([new_result])], ignore_index=True)
    return results

def update_standings(standings, results):
    standings = standings.set_index("Player")
    standings["Points"] = 0
    standings["Goals"] = 0
    standings["xG"] = 0.0
    standings["Games Played"] = 0

    for _, row in results.iterrows():
        if pd.isna(row["Home Goals"]) or pd.isna(row["Away Goals"]):
            continue

        home = row["Home"]
        away = row["Away"]
        home_goals = int(row["Home Goals"])
        away_goals = int(row["Away Goals"])
        home_xg = float(row["Home xG"])
        away_xg = float(row["Away xG"])

        # Update goals, xG, and games played
        standings.at[home, "Goals"] += home_goals
        standings.at[away, "Goals"] += away_goals
        standings.at[home, "xG"] += home_xg
        standings.at[away, "xG"] += away_xg
        standings.at[home, "Games Played"] += 1
        standings.at[away, "Games Played"] += 1

        # Award points
        if home_goals > away_goals:
            standings.at[home, "Points"] += 3
        elif away_goals > home_goals:
            standings.at[away, "Points"] += 3
        else:  # Tie
            standings.at[home, "Points"] += 1
            standings.at[away, "Points"] += 1

    return standings.reset_index().sort_values(by=["Points", "Goals", "xG"], ascending=False)

# Calculate Wins, Losses, and Draws dynamically
def calculate_outcomes(games):
    outcomes = pd.DataFrame({"Player": st.session_state.players})
    outcomes["Wins"] = 0
    outcomes["Losses"] = 0
    outcomes["Draws"] = 0

    for _, game in games.iterrows():
        home = game["Home"]
        away = game["Away"]
        home_goals = int(game["Home Goals"])
        away_goals = int(game["Away Goals"])

        if home_goals > away_goals:  # Home wins
            outcomes.loc[outcomes["Player"] == home, "Wins"] += 1
            outcomes.loc[outcomes["Player"] == away, "Losses"] += 1
        elif away_goals > home_goals:  # Away wins
            outcomes.loc[outcomes["Player"] == away, "Wins"] += 1
            outcomes.loc[outcomes["Player"] == home, "Losses"] += 1
        else:  # Draw
            outcomes.loc[outcomes["Player"] == home, "Draws"] += 1
            outcomes.loc[outcomes["Player"] == away, "Draws"] += 1

    return outcomes

# Function to calculate tournament duration
def calculate_tournament_duration(schedule, half_duration):
    game_duration = (half_duration * 2) + 3  # Two halves + 3-minute break
    total_games = len(schedule)
    total_duration = total_games * game_duration

    # Calculate team management time
    num_teams = len(set([game["Home"] for game in schedule] + [game["Away"] for game in schedule]))
    num_consoles = len(set([game["Console"] for game in schedule]))
    team_management_time = num_teams * num_consoles * 2  # 2 minutes per team per console

    return total_duration, team_management_time

# Function to generate playoffs bracket
def generate_playoffs_bracket(standings, last_game_id):
    """
    Generate a playoffs bracket based on league standings.
    """

    # Sort standings for ranking
    ranked_standings = (
        standings
        .sort_values(by=["Points", "Goals", "xG"], ascending=False)
        .reset_index(drop=True)
    )
    ranked_standings.index += 1  # Start index from 1
    ranked_standings.index.name = "Rank"

    # Ensure there are enough players for playoffs
    if ranked_standings.shape[0] < 6:
        raise ValueError("Not enough players to generate a playoffs bracket.")

    # Extract top 2 players (semifinals) and next 4 players (wildcard matches)
    top_two = ranked_standings.iloc[:2]["Player"].tolist()
    wildcard_players = ranked_standings.iloc[2:6].reset_index()[["Rank", "Player"]]  # Extract Rank and Player

    # Initialize game IDs and bracket
    current_game_id = last_game_id + 1
    bracket = []

    # Helper function to generate fixtures
    def add_fixture(home, away, match, round_number, console, game_id):
        return {
            "Game #": f"Game{game_id}",
            "Round": round_number,
            "Home": home,
            "Away": away,
            "Console": console,
            "Match": match,
        }

    # Determine wildcard matchups: 3rd vs. 6th and 4th vs. 5th
    wc1_home = wildcard_players.loc[wildcard_players["Rank"] == 3, "Player"].values[0]
    wc1_away = wildcard_players.loc[wildcard_players["Rank"] == 6, "Player"].values[0]
    wc2_home = wildcard_players.loc[wildcard_players["Rank"] == 4, "Player"].values[0]
    wc2_away = wildcard_players.loc[wildcard_players["Rank"] == 5, "Player"].values[0]

    wildcard_matches = [
        {"Home": wc1_home, "Away": wc1_away, "Match": "WC1"},  # 3rd vs. 6th
        {"Home": wc2_home, "Away": wc2_away, "Match": "WC2"},  # 4th vs. 5th
    ]

    # Create home-and-away fixtures for wildcard matches
    round_number = 1
    for match in wildcard_matches:
        # First leg
        bracket.append(add_fixture(
            home=match["Home"],
            away=match["Away"],
            match=match["Match"],
            round_number=round_number,
            console=f"Console {1 if len(bracket) % 2 == 0 else 2}",
            game_id=current_game_id,
        ))
        current_game_id += 1

        # Second leg (reverse fixture)
        bracket.append(add_fixture(
            home=match["Away"],
            away=match["Home"],
            match=match["Match"],
            round_number=round_number + 1,
            console=f"Console {1 if len(bracket) % 2 == 0 else 2}",
            game_id=current_game_id,
        ))
        current_game_id += 1

    # Semifinals: 1st vs. WC2 winner, 2nd vs. WC1 winner
    semifinal_matches = [
        {"Home": top_two[0], "Away": "Winner WC2", "Match": "SF1"},
        {"Home": top_two[1], "Away": "Winner WC1", "Match": "SF2"},
    ]
    for match in semifinal_matches:
        round_number += 1
        bracket.append(add_fixture(
            home=match["Home"],
            away=match["Away"],
            match=match["Match"],
            round_number=round_number,
            console=f"Console {1 if len(bracket) % 2 == 0 else 2}",
            game_id=current_game_id,
        ))
        current_game_id += 1

        # Second leg (reverse fixture)
        bracket.append(add_fixture(
            home=match["Away"],
            away=match["Home"],
            match=match["Match"],
            round_number=round_number + 1,
            console=f"Console {1 if len(bracket) % 2 == 0 else 2}",
            game_id=current_game_id,
        ))
        current_game_id += 1

    # Finals: SF1 winner vs. SF2 winner
    final_match = {"Home": "Winner SF1", "Away": "Winner SF2", "Match": "Final"}
    round_number += 1
    bracket.append(add_fixture(
        home=final_match["Home"],
        away=final_match["Away"],
        match=final_match["Match"],
        round_number=round_number,
        console="Console 1",
        game_id=current_game_id,
    ))
    current_game_id += 1

    # Second leg (reverse fixture)
    bracket.append(add_fixture(
        home=final_match["Away"],
        away=final_match["Home"],
        match=final_match["Match"],
        round_number=round_number + 1,
        console="Console 1",
        game_id=current_game_id,
    ))

    # Debug: Display the generated bracket
    print("Generated Bracket:")
    for b in bracket:
        print(b)

    return bracket


# Function to create a bracket visualization
def create_bracket_visualization(bracket):
    rounds = ["Wildcard", "Semifinals", "Finals"]
    data = []
    for round_name in rounds:
        for match in bracket.get(round_name, []):
            data.append([round_name, match["Match"], match["Home"], match["Away"]])
    bracket_df = pd.DataFrame(data, columns=["Round", "Match", "Home", "Away"])
    return bracket_df

# Function to plot the bracket
def plot_bracket(bracket_df):
    fig = ff.create_table(bracket_df)
    return fig

# Function to load previous tournaments
def load_previous_tournaments():
    if os.path.exists("tournaments.csv"):
        return pd.read_csv("tournaments.csv")
    return pd.DataFrame(columns=["Tournament ID", "Tournament Name", "Status"])

# Function to save a tournament
def save_tournament(tournament_id, tournament_name, standings, results):
    results.to_csv(f"tournament_{tournament_id}_results.csv", index=False)
    standings.to_csv(f"tournament_{tournament_id}_standings.csv", index=False)
    if not os.path.exists("tournaments.csv"):
        pd.DataFrame({"Tournament ID": [], "Tournament Name": [], "Status": []}).to_csv("tournaments.csv", index=False)
    tournaments = pd.read_csv("tournaments.csv")
    tournaments = pd.concat([tournaments, pd.DataFrame([{"Tournament ID": tournament_id, "Tournament Name": tournament_name, "Status": "Completed"}])], ignore_index=True)
    tournaments.to_csv("tournaments.csv", index=False)

# Load player data
def load_player_data():
    return pd.read_csv("assets/players.csv")
