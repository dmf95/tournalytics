import pandas as pd
import random
import streamlit as st
import random
import numpy as np
import itertools

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


def generate_league_schedule(tournament_details, debug=False):
    """
    Generate a league schedule considering constraints such as games per player, consoles, fairness,
    and diverse matchups.

    Args:
        tournament_details (dict): Dictionary containing all tournament configuration details.
        debug (bool): If True, outputs debug information to the console/UI.

    Returns:
        list: A schedule of league games.
    """

    # Validate tournament_details and extract necessary fields
    required_keys = ["selected_players", "team_selection", "num_players", "num_consoles", "games_per_player"]
    missing_keys = [key for key in required_keys if key not in tournament_details]
    if missing_keys:
        raise KeyError(f"Missing required keys in tournament_details: {missing_keys}")

    # Extract necessary details
    players = tournament_details["selected_players"]
    teams = tournament_details["team_selection"]
    num_players = tournament_details["num_players"]
    num_consoles = tournament_details["num_consoles"]
    games_per_player = tournament_details["games_per_player"]

    # Debugging: Display tournament details
    if debug:
        st.write("### [DEBUG] Tournament Details")
        st.write("Players:", players)
        st.write("Teams:", teams)
        st.write(f"Num Players: {num_players}, Num Consoles: {num_consoles}, Games Per Player: {games_per_player}")

    # Initialize variables
    schedule = []
    total_league_games = (num_players * games_per_player) // 2
    matchups = list(itertools.combinations(players, 2))  # All unique matchups
    random.shuffle(matchups)  # Randomize matchups for diversity

    # Initialize symmetric matchup count
    matchup_count = {}
    for home, away in matchups:
        matchup_count[(home, away)] = 0
        matchup_count[(away, home)] = 0

    # Tracking variables
    home_away_count = {player: 0 for player in players}
    player_game_count = {player: 0 for player in players}
    game_id = 1
    round_num = 1

    # Generate schedule
    while len(schedule) < total_league_games:
        if debug:
            st.write(f"### [DEBUG] Starting Round {round_num}")
        games_in_round = []
        players_in_round = set()
        used_consoles = set()

        # Iterate over a copy of matchups
        for home, away in matchups[:]:  # Iterate over a copy of the matchups list
            if len(games_in_round) >= num_consoles:
                break

            # Debugging: Validate current pair
            if debug:
                st.write(f"[DEBUG] Evaluating Pair: ({home}, {away})")

            # Skip if players exceed games_per_player or conflict with the current round
            if (
                player_game_count[home] >= games_per_player
                or player_game_count[away] >= games_per_player
                or home in players_in_round
                or away in players_in_round
            ):
                continue

            # Ensure diversity in matchups by minimizing repeat pairings
            if matchup_count[(home, away)] > 0:
                continue

            # Assign console
            console = f"Console {len(used_consoles) + 1}"
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
            player_game_count[home] += 1
            player_game_count[away] += 1
            matchup_count[(home, away)] += 1
            matchup_count[(away, home)] += 1
            game_id += 1

            # Safely remove the matchup
            if (home, away) in matchups:
                matchups.remove((home, away))

        # Add completed round to the schedule
        schedule.extend(games_in_round)
        round_num += 1

        # Re-shuffle remaining matchups to prioritize unused pairs
        matchups = sorted(
            matchups,
            key=lambda x: matchup_count[x],
        )
        random.shuffle(matchups)  # Randomize within the sorted order

    return schedule


def validate_schedule(schedule, tournament_details):
    """
    Validate the schedule against key constraints.

    Args:
        schedule (list): Generated schedule of games.
        tournament_details (dict): Dictionary containing tournament configuration details.

    Returns:
        list: Validation messages indicating issues.
    """
    num_consoles = tournament_details["num_consoles"]
    games_per_player = tournament_details["games_per_player"]

    validation_messages = []

    # Validate no player plays more than once per round
    for round_num in set(game["Round"] for game in schedule):
        players_in_round = set()
        for game in filter(lambda g: g["Round"] == round_num, schedule):
            if game["Home"] in players_in_round or game["Away"] in players_in_round:
                validation_messages.append(f"Round {round_num}: Player conflict detected.")
            players_in_round.add(game["Home"])
            players_in_round.add(game["Away"])

    # Validate no console is used more than once per round
    for round_num in set(game["Round"] for game in schedule):
        consoles_in_round = set()
        for game in filter(lambda g: g["Round"] == round_num, schedule):
            if game["Console"] in consoles_in_round:
                validation_messages.append(f"Round {round_num}: Console conflict detected.")
            consoles_in_round.add(game["Console"])

    # Validate total games per player
    player_game_count = {player: 0 for player in set(p for game in schedule for p in [game["Home"], game["Away"]])}
    for game in schedule:
        player_game_count[game["Home"]] += 1
        player_game_count[game["Away"]] += 1
    for player, count in player_game_count.items():
        if count != games_per_player:
            validation_messages.append(f"Player {player} has {count} games, expected {games_per_player}.")

    return validation_messages


def initialize_standings(players, teams):
    """
    Initialize standings for the tournament.

    Args:
        players (list): List of players.
        teams (dict): Mapping of players to their teams.

    Returns:
        pd.DataFrame: Initial standings DataFrame.
    """
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

def validate_league_completion(schedule_df, results_df, debug=False):
    """
    Determine if all league matches are complete by comparing the schedule with results.

    Args:
        schedule_df (pd.DataFrame): DataFrame containing the full league fixture list.
        results_df (pd.DataFrame): DataFrame containing the league match history (completed games).
        debug (bool): If True, prints debug information.

    Returns:
        bool: True if all matches in the schedule are complete, False otherwise.
    """
    if schedule_df.empty:
        if debug:
            st.write("[DEBUG] Schedule table is empty.")
        return False

    if results_df.empty:
        if debug:
            st.write("[DEBUG] Results table is empty. No matches have been played.")
        return False

    # Check if all games in the schedule exist in the results
    all_games_exist = set(schedule_df["Game #"]) == set(results_df["Game #"])

    # Check if all results in the completed games have non-null goals
    no_null_values = not results_df[["Home Goals", "Away Goals"]].isnull().any().any()

    if debug:
        st.write(f"[DEBUG] All Scheduled Games Exist in Results: {all_games_exist}")
        st.write(f"[DEBUG] No Null Values in Results: {no_null_values}")

    return all_games_exist and no_null_values

def validate_playoffs_completion(playoff_results, debug=False):
    """
    Validate if all semi-final matches in the playoffs are complete and ensure there are exactly 4 matches.

    Args:
        playoff_results (pd.DataFrame): DataFrame containing playoff results.
        debug (bool): If True, prints debug information.

    Returns:
        bool: True if exactly 4 semi-final matches are complete, False otherwise.
    """
    if playoff_results.empty:
        if debug:
            st.write("[DEBUG] Playoff results table is empty. No matches have been played.")
        return False

    # Filter for semi-final matches
    semi_final_matches = playoff_results[playoff_results["Match"].str.startswith("SF")]

    if semi_final_matches.empty:
        if debug:
            st.write("[DEBUG] No semi-final matches found in playoff results.")
        return False

    # Validate the number of semi-final matches
    if len(semi_final_matches) != 4:
        if debug:
            st.write(f"[DEBUG] Found {len(semi_final_matches)} semi-final matches. Expected: 4.")
        return False

    # Check if all semi-final matches have completed results
    no_null_values = not semi_final_matches[["Home Goals", "Away Goals"]].isnull().any().any()

    if debug:
        st.write(f"[DEBUG] All Semi-Final Matches Have Non-Null Results: {no_null_values}")

    return no_null_values

# Helper function: Safely retrieve session state variables
def get_session_state(key, default=None):
    return st.session_state.get(key, default)

def upsert_results(results, new_result):
    """
    Inserts or updates a game result into the results DataFrame based on 'Game #'.

    Args:
        results (pd.DataFrame): DataFrame containing existing game results.
        new_result (dict): Dictionary containing the new game result.

    Returns:
        pd.DataFrame: Updated results DataFrame.
    """
    # Ensure 'results' is a DataFrame to handle edge cases
    if results is None or results.empty:
        return pd.DataFrame([new_result])

    # Check if the 'Game #' already exists
    if new_result["Game #"] in results["Game #"].values:
        # Update the existing row by aligning new_result keys to DataFrame columns
        idx = results.index[results["Game #"] == new_result["Game #"]].tolist()[0]
        for key, value in new_result.items():
            if key in results.columns:
                results.at[idx, key] = value
    else:
        # Add the new result as a new row
        new_result_df = pd.DataFrame([new_result])
        results = pd.concat([results, new_result_df], ignore_index=True)

    # Ensure no duplicate rows
    return results.drop_duplicates(subset=["Game #"], keep="last").reset_index(drop=True)


# Centralized Function for Updating Results
def update_league_game_results(results_df, new_result, players, teams):
    """
    Update the results DataFrame with new game results and recalculate standings.

    Args:
        results_df (pd.DataFrame): Current results DataFrame.
        new_result (dict): Dictionary containing the new game result to update.
        players (list): List of players in the tournament.
        teams (dict): Dictionary mapping players to teams.

    Returns:
        tuple: Updated results DataFrame and standings DataFrame.
    """
    # Update results
    updated_results = upsert_results(results_df, new_result)

    # Recalculate standings in a batch
    games_played = updated_results.dropna(subset=["Home Goals", "Away Goals"])
    updated_standings = initialize_standings(players, teams)

    if not games_played.empty:
        updated_standings = update_standings(updated_standings, games_played)

    return updated_results, updated_standings

def update_playoff_results(results_df, new_result):
    """
    Update the playoff results DataFrame with new game results.

    Args:
        results_df (pd.DataFrame): Current playoff results DataFrame.
        new_result (dict): Dictionary containing the new game result to update.

    Returns:
        pd.DataFrame: Updated playoff results DataFrame.
    """
    # Update results using the existing upsert_results logic
    updated_results = upsert_results(results_df, new_result)

    # Update the Status column
    updated_results["Status"] = updated_results["Game #"].apply(
        lambda game_id: "✅"
        if not updated_results.loc[
            updated_results["Game #"] == game_id, ["Home Goals", "Away Goals"]
        ].isna().any().any()
        else "⏳ TBD"
    )

    return updated_results

def update_final_matches(playoff_results):
    """
    Updates the finals matches with the winners of the semi-final matches.

    Args:
        playoff_results (pd.DataFrame): DataFrame containing playoff results.

    Returns:
        pd.DataFrame: Updated playoff_results with finals matches updated.
    """
    # Extract semi-final matches
    sf1_matches = playoff_results[playoff_results["Match"].str.startswith("SF1")]
    sf2_matches = playoff_results[playoff_results["Match"].str.startswith("SF2")]

    # Determine winners for semi-finals
    sf1_win = determine_winner(sf1_matches) if not sf1_matches.dropna(subset=["Home Goals", "Away Goals"]).empty else None
    sf2_win = determine_winner(sf2_matches) if not sf2_matches.dropna(subset=["Home Goals", "Away Goals"]).empty else None

    if sf1_win and sf2_win:
        # Find and update final matches with winners
        final_matches = playoff_results["Match"].str.startswith("Final")
        playoff_results.loc[final_matches, ["Home", "Away"]] = playoff_results.loc[
            final_matches, ["Home", "Away"]
        ].replace({"Winner SF1": sf1_win, "Winner SF2": sf2_win})

        # Update session state
        st.session_state.playoff_results = playoff_results.copy()
    else:
        st.warning("One or both semi-final matches are incomplete. Complete the matches to update finals.")

    return playoff_results

# Update Standings: Calculate points, goals, and xG dynamically
def update_standings(standings, results):
    """
    Updates the standings DataFrame based on game results.
    """
    standings = standings.set_index("Player").assign(Points=0, Goals=0, xG=0.0, Games_Played=0)

    for _, row in results.iterrows():
        if pd.isna(row["Home Goals"]) or pd.isna(row["Away Goals"]):
            continue  # Skip incomplete games

        home, away = row["Home"], row["Away"]
        home_goals, away_goals = int(row["Home Goals"]), int(row["Away Goals"])
        home_xg, away_xg = float(row["Home xG"]), float(row["Away xG"])

        for team, goals, xg, points in [
            (home, home_goals, home_xg, 3 if home_goals > away_goals else 1 if home_goals == away_goals else 0),
            (away, away_goals, away_xg, 3 if away_goals > home_goals else 1 if home_goals == away_goals else 0),
        ]:
            if team in standings.index:
                standings.loc[team, ["Goals", "xG", "Games_Played"]] += [goals, xg, 1]
                standings.loc[team, "Points"] += points

    return standings.reset_index()

# Calculate Outcomes: Wins, Losses, and Draws
def calculate_outcomes(results, players):
    """
    Calculates wins, losses, and draws for all players based on game results.
    """
    outcomes = pd.DataFrame({"Player": players}).assign(Wins=0, Losses=0, Draws=0)

    for _, game in results.iterrows():
        home, away = game["Home"], game["Away"]
        home_goals, away_goals = int(game["Home Goals"]), int(game["Away Goals"])

        if home_goals > away_goals:
            outcomes.loc[outcomes["Player"] == home, "Wins"] += 1
            outcomes.loc[outcomes["Player"] == away, "Losses"] += 1
        elif away_goals > home_goals:
            outcomes.loc[outcomes["Player"] == away, "Wins"] += 1
            outcomes.loc[outcomes["Player"] == home, "Losses"] += 1
        else:
            outcomes.loc[outcomes["Player"].isin([home, away]), "Draws"] += 1

    return outcomes

# Sort Standings: Dynamically sort based on tiebreakers
def sort_standings(
            standings, 
            tiebreakers, 
            column_mapping = {"Goals For": "Goals", "xG For": "xG", "Wins": "Wins", "Draws": "Draws"}
    ):
    """
    Sorts standings dynamically based on primary metrics and tiebreakers.
    """
    primary_metric = "Points"
    sorting_order = [primary_metric] + [column_mapping.get(metric, metric) for metric in tiebreakers]

    return (
        standings.sort_values(by=sorting_order, ascending=[False] * len(sorting_order))
        .reset_index(drop=True)
        .assign(Rank=lambda df: df.index + 1)
    )


def estimate_league_duration(num_players, num_consoles, half_duration, games_per_player, league_format):
    """
    Estimate the total league duration based on the number of players, consoles, game duration, and league format.

    Args:
        num_players (int): Total number of players in the tournament.
        num_consoles (int): Number of consoles available.
        half_duration (int): Duration of one half of a game in minutes.
        games_per_player (int): Number of games each player will play in the league phase.
        league_format (str): Format of the league ("League", "Group", or "Knockouts").

    Returns:
        dict: League duration details, including total league games, rounds, and duration.
    """
    if league_format != "League":
        raise NotImplementedError(f"League format '{league_format}' is not yet supported.")

    total_league_games = (num_players * games_per_player) // 2
    game_duration = (half_duration * 2) + 3  # Two halves + break
    league_rounds = (total_league_games + num_consoles - 1) // num_consoles
    league_duration = league_rounds * game_duration

    return {
        "league_duration": league_duration,
        "total_league_games": total_league_games,
        "league_rounds": league_rounds,
        "game_duration": game_duration,
    }

def estimate_playoff_duration(num_players, num_consoles, game_duration, playoff_format):
    """
    Estimate the total playoff duration based on the number of players, consoles, game duration, and playoff format.

    Args:
        num_players (int): Total number of players in the tournament.
        num_consoles (int): Number of consoles available.
        game_duration (int): Duration of one game in minutes.
        playoff_format (str): Format of the playoffs ("Single-Elimination" or "Double-Elimination").

    Returns:
        dict: Playoff duration details, including total playoff games, rounds, and duration.
    """
    if playoff_format == "Single-Elimination":
        total_playoff_games = 4 + 2 + 1
        playoff_rounds = (total_playoff_games + num_consoles - 1) // num_consoles
    elif playoff_format == "Double-Elimination":
        wildcard_games = 4
        semifinal_games = 4
        final_games = 2
        total_playoff_games = wildcard_games + semifinal_games + final_games
        playoff_rounds = (
            (wildcard_games + num_consoles - 1) // num_consoles +
            (semifinal_games + num_consoles - 1) // num_consoles +
            final_games
        )
    else:
        raise ValueError(f"Unsupported playoff format: {playoff_format}")

    return {
        "playoff_duration": playoff_rounds * game_duration,
        "total_playoff_games": total_playoff_games,
        "playoff_rounds": playoff_rounds,
    }


def estimate_tournament_duration(num_players, num_consoles, half_duration, games_per_player, league_format, playoff_format, misc_time=2):
    """
    Estimate the total duration of the tournament, including league, playoff phases, and additional time for miscellaneous activities.

    Args:
        num_players (int): Total number of players in the tournament.
        num_consoles (int): Number of consoles available.
        half_duration (int): Duration of one half of a game in minutes.
        games_per_player (int): Number of games each player will play in the league phase.
        league_format (str): Format of the league ("League", "Group", or "Knockouts").
        playoff_format (str): Format of the playoffs ("Single-Elimination" or "Double-Elimination").
        misc_time (int): Number of extra minutes per round as a buffer

    Returns:
        dict: A breakdown of the tournament's total duration, league duration, playoff duration, and additional time.
    """
    league_details = estimate_league_duration(
        num_players=num_players,
        num_consoles=num_consoles,
        half_duration=half_duration,
        games_per_player=games_per_player,
        league_format=league_format,
    )

    playoff_details = estimate_playoff_duration(
        num_players=num_players,
        num_consoles=num_consoles,
        game_duration=league_details["game_duration"],
        playoff_format=playoff_format,
    )

    additional_time = (league_details["league_rounds"] + playoff_details["playoff_rounds"]) * misc_time

    total_duration = league_details["league_duration"] + playoff_details["playoff_duration"] + additional_time

    return {
        "total_duration": total_duration,
        "league_details": league_details,
        "playoff_details": playoff_details,
        "additional_time": additional_time,
    }


def generate_playoffs_bracket(tournament_details, standings, last_game_id, debug=False):
    """
    Generate a playoffs bracket based on league standings and tournament details.

    Args:
        tournament_details (dict): Dictionary containing tournament configuration details.
        standings (pd.DataFrame): Standings DataFrame, ranked by tournament tiebreakers.
        last_game_id (int): The last game ID from the league stage to continue numbering.
        debug (bool): Whether to enable debug output.

    Returns:
        list: A playoffs bracket as a list of dictionaries.
    """
    # Extract parameters from tournament details
    playoff_format = tournament_details["playoff_format"]
    num_consoles = tournament_details["num_consoles"]

    # Sort standings for ranking
    ranked_standings = standings.reset_index(drop=True)
    ranked_standings.index += 1  # Start index from 1
    ranked_standings.index.name = "Rank"

    if debug:
        print("[DEBUG] Ranked Standings:")
        print(ranked_standings)

    # Ensure there are enough players for playoffs
    if ranked_standings.shape[0] < 6:
        raise ValueError("Not enough players to generate a playoffs bracket (minimum 6 required).")

    # Extract top-ranked players for wildcard and semifinals
    top_two = ranked_standings.iloc[:2]["Player"].tolist()
    wildcard_players = ranked_standings.iloc[2:6][["Player"]].reset_index()

    # Initialize variables
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
            "Played": ""  # Placeholder for played status
        }

    # Wildcard matches: 3rd vs. 6th and 4th vs. 5th
    wildcard_matchups = [
        (wildcard_players.loc[0, "Player"], wildcard_players.loc[3, "Player"]),  # 3rd vs. 6th
        (wildcard_players.loc[1, "Player"], wildcard_players.loc[2, "Player"])   # 4th vs. 5th
    ]

    round_number = 1
    for i, (home, away) in enumerate(wildcard_matchups):
        # First leg
        bracket.append(add_fixture(
            home=home,
            away=away,
            match=f"WC{i+1}",
            round_number=round_number,
            console=f"Console {i % num_consoles + 1}",
            game_id=current_game_id
        ))
        current_game_id += 1

        # Second leg (reverse fixture)
        bracket.append(add_fixture(
            home=away,
            away=home,
            match=f"WC{i+1}",
            round_number=round_number + 1,
            console=f"Console {i % num_consoles + 1}",
            game_id=current_game_id
        ))
        current_game_id += 1

    # Semifinals: Top 2 vs. Wildcard winners
    semifinal_matchups = [
        (top_two[0], "Winner WC2"),
        (top_two[1], "Winner WC1")
    ]
    round_number += 2
    for i, (home, away) in enumerate(semifinal_matchups):
        # First leg
        bracket.append(add_fixture(
            home=home,
            away=away,
            match=f"SF{i+1}",
            round_number=round_number,
            console=f"Console {i % num_consoles + 1}",
            game_id=current_game_id
        ))
        current_game_id += 1

        # Second leg (reverse fixture)
        bracket.append(add_fixture(
            home=away,
            away=home,
            match=f"SF{i+1}",
            round_number=round_number + 1,
            console=f"Console {i % num_consoles + 1}",
            game_id=current_game_id
        ))
        current_game_id += 1

    # Finals: SF1 winner vs. SF2 winner
    final_match = ("Winner SF1", "Winner SF2")
    round_number += 2
    bracket.append(add_fixture(
        home=final_match[0],
        away=final_match[1],
        match="Final",
        round_number=round_number,
        console="Console 1",
        game_id=current_game_id
    ))
    current_game_id += 1

    # Second leg (reverse fixture)
    bracket.append(add_fixture(
        home=final_match[1],
        away=final_match[0],
        match="Final",
        round_number=round_number + 1,
        console="Console 1",
        game_id=current_game_id
    ))

    if debug:
        print("[DEBUG] Generated Playoff Bracket:")
        for game in bracket:
            print(game)

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
