import pandas as pd
import random
import streamlit as st
import random
import numpy as np

# Helper Functions
def validate_schedule(schedule):
    """
    Validates the generated schedule to ensure it meets application requirements.
    """
    if not schedule or not isinstance(schedule, list):
        raise ValueError("Invalid schedule: Schedule must be a non-empty list of games.")
    required_keys = {"Game #", "Home", "Away", "Console"}
    if not all(required_keys.issubset(game.keys()) for game in schedule):
        raise ValueError(f"Invalid schedule: Each game must contain keys {required_keys}.")

def set_schedule(schedule):
    """
    Updates the session state with the generated schedule and ensures all dependent keys are initialized.
    """
    validate_schedule(schedule)  # Ensure schedule is valid
    st.session_state["schedule"] = schedule
    st.session_state["results"] = pd.DataFrame(schedule)
    st.session_state["results"]["Home Goals"] = np.nan
    st.session_state["results"]["Away Goals"] = np.nan
    st.session_state["results"]["Home xG"] = np.nan
    st.session_state["results"]["Away xG"] = np.nan
    st.session_state["tournament_ready"] = True


def generate_league_schedule(players, teams, num_consoles, league_format="Play-Everyone"):
    """
    Generate a league schedule considering consoles, minimizing concurrent games.

    Args:
        players (list): List of player names.
        teams (dict): Mapping of players to their teams.
        num_consoles (int): Number of consoles available.
        league_format (str): Format of league games (e.g., "Play-Everyone").

    Returns:
        list: A schedule of league games.
    """
    # Validate league format
    if league_format != "Play-Everyone":
        raise ValueError(f"Unsupported league format: {league_format}")

    # Initialize variables
    schedule = []
    num_players = len(players)
    matchups = [(players[i], players[j]) for i in range(num_players) for j in range(i + 1, num_players)]
    random.shuffle(matchups)  # Randomize matchups for diversity

    home_away_count = {player: 0 for player in players}
    game_id = 1
    round_num = 1

    # Generate schedule
    while matchups:
        games_in_round = []
        players_in_round = set()
        used_consoles = set()

        while len(games_in_round) < num_consoles and matchups:
            home, away = matchups.pop(0)

            # Skip if players are already scheduled in this round
            if home in players_in_round or away in players_in_round:
                matchups.append((home, away))
                continue

            # Assign console
            console = f"Console {len(used_consoles) + 1}"
            if console in used_consoles:
                matchups.append((home, away))
                continue

            used_consoles.add(console)

            # Balance home and away games
            if home_away_count[home] > home_away_count[away]:
                home, away = away, home

            # Add game to the round
            games_in_round.append({
                "Game #": f"Game{game_id:02}",
                "Round": round_num,
                "Home": home,
                "Away": away,
                "Console": console,
                "Home Team": teams[home],
                "Away Team": teams[away],
                "Played": ""  # Placeholder for played status
            })

            # Update state
            players_in_round.update([home, away])
            home_away_count[home] += 1
            game_id += 1

        # Add completed round to the schedule
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

def estimate_tournament_duration(num_players, num_consoles, half_duration, league_format, playoff_format):
    """
    Estimate the total duration of the tournament based on league and playoff formats, considering consoles.

    Args:
        num_players (int): Total number of players in the tournament.
        num_consoles (int): Number of consoles available.
        half_duration (int): Duration of one half in minutes.
        league_format (str): Format of league games (e.g., "Play-Everyone").
        playoff_format (str): Format of playoff games (e.g., "Single-Elimination", "Double-Elimination").

    Returns:
        dict: Breakdown of the estimated tournament duration.
    """
    # Define constants
    game_duration = (half_duration * 2) + 3  # Two halves + 3-minute break

    # League duration calculation
    if league_format == "Play-Everyone":
        # Each team plays every other team once
        total_league_games = num_players * (num_players - 1) // 2
    else:
        raise ValueError(f"Unsupported league format: {league_format}")

    # Calculate league rounds based on consoles
    league_rounds = (total_league_games + num_consoles - 1) // num_consoles  # Ceiling division
    total_league_duration = league_rounds * game_duration

    # Playoff duration calculation
    if playoff_format == "Single-Elimination":
        # Top 6 teams: 4 wildcard games (1 match), 2 semifinals (1 match), 1 final (1 match)
        total_playoff_games = 4 + 2 + 1
        playoff_rounds = (total_playoff_games + num_consoles - 1) // num_consoles  # Ceiling division
    elif playoff_format == "Double-Elimination":
        # Top 6 teams: 4 wildcard games (home/away), 2 semifinals (home/away), 2 finals (home/away)
        # Wildcards (4 games = 2 matchups * 2 rounds)
        wildcard_games = 4
        wildcard_rounds = (wildcard_games + num_consoles - 1) // num_consoles  # Ceiling division

        # Semifinals (4 games = 2 matchups * 2 rounds)
        semifinal_games = 4
        semifinal_rounds = (semifinal_games + num_consoles - 1) // num_consoles  # Ceiling division

        # Finals (2 games = 1 matchup * 2 rounds, single console per game)
        final_games = 2
        final_rounds = final_games  # Each game requires a separate round due to single-console limitation

        total_playoff_games = wildcard_games + semifinal_games + final_games
        playoff_rounds = wildcard_rounds + semifinal_rounds + final_rounds
    else:
        raise ValueError(f"Unsupported playoff format: {playoff_format}")

    # Calculate playoff duration
    total_playoff_duration = playoff_rounds * game_duration

    # Calculate team management time
    team_management_time = num_players * num_consoles * 2  # 2 minutes per team per console

    # Calculate total duration
    total_duration = total_league_duration + total_playoff_duration + team_management_time

    # Convert to hours and minutes
    total_hours = total_duration // 60
    total_minutes = total_duration % 60

    # Output detailed breakdown for debugging or user insights
    breakdown = {
        "total_league_games": total_league_games,
        "total_league_rounds": league_rounds,
        "total_league_duration": total_league_duration,
        "total_playoff_games": total_playoff_games,
        "total_playoff_rounds": playoff_rounds,
        "total_playoff_duration": total_playoff_duration,
        "team_management_time": team_management_time,
        "total_duration_minutes": total_duration,
        "total_hours": total_hours,
        "total_minutes": total_minutes,
    }

    return breakdown



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
