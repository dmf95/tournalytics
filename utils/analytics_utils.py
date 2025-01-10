import pandas as pd
import os

def calculate_basic_analysis(results_df):
    """
    Perform advanced analysis on tournament results for mobile-first analytics.

    Args:
        results_df (pd.DataFrame): DataFrame containing tournament results.

    Returns:
        dict: A dictionary with keys "kpi_summary", "overall", "win_rates", and "matchups".
    """
    analysis = {}

    # KPI Summary
    total_games = len(results_df)
    total_goals = results_df["Home Goals"].sum() + results_df["Away Goals"].sum()
    avg_goals_per_game = total_goals / total_games if total_games else 0

    analysis["kpi_summary"] = {
        "total_games": total_games,
        "total_goals": total_goals,
        "avg_goals_per_game": avg_goals_per_game,
    }

    # Overall Performance
    overall_performance = (
        results_df.melt(
            id_vars=["Game #"],
            value_vars=["Home", "Away"],
            var_name="Role",
            value_name="Player",
        )
        .merge(
            results_df[["Game #", "Home Goals", "Away Goals", "Home xG", "Away xG"]],
            on="Game #",
        )
        .assign(
            Goals=lambda df: df.apply(
                lambda row: row["Home Goals"] if row["Role"] == "Home" else row["Away Goals"], axis=1
            ),
            Opponent_Goals=lambda df: df.apply(
                lambda row: row["Away Goals"] if row["Role"] == "Home" else row["Home Goals"], axis=1
            ),
            xG_For=lambda df: df.apply(
                lambda row: row["Home xG"] if row["Role"] == "Home" else row["Away xG"], axis=1
            ),
            xG_Against=lambda df: df.apply(
                lambda row: row["Away xG"] if row["Role"] == "Home" else row["Home xG"], axis=1
            ),
            Wins=lambda df: (df["Goals"] > df["Opponent_Goals"]).astype(int),
            Draws=lambda df: (df["Goals"] == df["Opponent_Goals"]).astype(int),
            Losses=lambda df: (df["Goals"] < df["Opponent_Goals"]).astype(int),
        )
        .groupby("Player", as_index=False)
        .agg(
            Games=("Game #", "nunique"),
            Wins=("Wins", "sum"),
            Draws=("Draws", "sum"),
            Losses=("Losses", "sum"),
            Goals_For=("Goals", "sum"),
            Goals_Against=("Opponent_Goals", "sum"),
            xG_For=("xG_For", "sum"),
            xG_Against=("xG_Against", "sum"),
        )
        .assign(Points=lambda df: df["Wins"] * 3 + df["Draws"])
    )

    analysis["overall"] = overall_performance

    # Win Rates
    analysis["win_rates"] = overall_performance.assign(
        Win_Rate=lambda df: (df["Wins"] / df["Games"]).fillna(0).round(2)
    )["Player Win_Rate".split()]

    # Frequent Matchups
    matchups = (
        results_df[["Home", "Away", "Home Goals", "Away Goals"]]
        .groupby(["Home", "Away"], as_index=False)
        .agg(Games=("Home", "count"), Total_Goals=("Home Goals", "sum"))
    )
    analysis["matchups"] = matchups

    return analysis

def calculate_playoff_ranks(df):
    # Assign numeric round values for ranking (lower is better)
    round_order = {"Final": 1, "SF1": 2, "SF2": 2, "WC1": 3, "WC2": 3}
    df['round_numeric'] = df['Round'].map(round_order)

    # Calculate total goals scored for each player
    total_goals = (
        pd.concat([
            df[['Home', 'Home Goals']].rename(columns={'Home': 'Player', 'Home Goals': 'Goals'}),
            df[['Away', 'Away Goals']].rename(columns={'Away': 'Player', 'Away Goals': 'Goals'})
        ])
        .groupby('Player', as_index=False)['Goals']
        .sum()
    )

    # Calculate total xG for each player
    total_xg = (
        pd.concat([
            df[['Home', 'Home xG']].rename(columns={'Home': 'Player', 'Home xG': 'xG'}),
            df[['Away', 'Away xG']].rename(columns={'Away': 'Player', 'Away xG': 'xG'})
        ])
        .groupby('Player', as_index=False)['xG']
        .sum()
    )

    # Count games played by each player
    games_played = (
        pd.concat([
            df[['Home']].rename(columns={'Home': 'Player'}),
            df[['Away']].rename(columns={'Away': 'Player'})
        ])
        .groupby('Player', as_index=False)
        .size()
        .rename(columns={'size': 'Games Played'})
    )

    # Determine the best round each player participated in
    best_round = (
        pd.concat([
            df[['Home', 'Round']].rename(columns={'Home': 'Player'}),
            df[['Away', 'Round']].rename(columns={'Away': 'Player'})
        ])
        .groupby('Player', as_index=False)['Round']
        .min()
    )

    # Calculate goals for and against for each player
    goals_for = (
        pd.concat([
            df[['Home', 'Home Goals']].rename(columns={'Home': 'Player', 'Home Goals': 'Goals For'}),
            df[['Away', 'Away Goals']].rename(columns={'Away': 'Player', 'Away Goals': 'Goals For'})
        ])
        .groupby('Player', as_index=False)['Goals For']
        .sum()
    )

    goals_against = (
        pd.concat([
            df[['Home', 'Away Goals']].rename(columns={'Home': 'Player', 'Away Goals': 'Goals Against'}),
            df[['Away', 'Home Goals']].rename(columns={'Away': 'Player', 'Home Goals': 'Goals Against'})
        ])
        .groupby('Player', as_index=False)['Goals Against']
        .sum()
    )

    # Merge all metrics into a single DataFrame
    ranking_data = total_goals.merge(total_xg, on='Player')
    ranking_data = ranking_data.merge(games_played, on='Player')
    ranking_data = ranking_data.merge(best_round, on='Player')
    ranking_data = ranking_data.merge(goals_for, on='Player')
    ranking_data = ranking_data.merge(goals_against, on='Player')
    
    # Add round progression information
    ranking_data = ranking_data.merge(
        pd.concat([
            df[['Home', 'round_numeric']].rename(columns={'Home': 'Player'}),
            df[['Away', 'round_numeric']].rename(columns={'Away': 'Player'})
        ])
        .groupby('Player', as_index=False)['round_numeric']
        .min(),
        on='Player'
    )

    # Sort players by round_numeric (progression) and total goals (descending)
    ranking_data.sort_values(by=['round_numeric', 'Goals'], ascending=[True, False], inplace=True)

    # Assign ranks
    ranking_data['Rank'] = range(1, len(ranking_data) + 1)

    return ranking_data[['Rank', 'Player', 'Goals', 'xG', 'Goals For', 'Goals Against', 'Games Played', 'Round', 'round_numeric']]
