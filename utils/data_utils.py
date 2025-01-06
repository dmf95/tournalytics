import json
from datetime import datetime, date  
import pandas as pd
import streamlit as st
import os
import sqlalchemy

def load_previous_tournaments():
    if os.path.exists("tournaments.csv"):
        return pd.read_csv("tournaments.csv")
    return pd.DataFrame(columns=["Tournament ID", "Tournament Name", "Status"])

def load_player_data_local(path):
    return pd.read_csv(path)

def save_tournament(tournament_id, tournament_name, standings, results):
    results.to_csv(f"tournament_{tournament_id}_results.csv", index=False)
    standings.to_csv(f"tournament_{tournament_id}_standings.csv", index=False)

    tournaments = load_previous_tournaments()
    tournaments = pd.concat([
        tournaments,
        pd.DataFrame([{"Tournament ID": tournament_id, "Tournament Name": tournament_name, "Status": "Completed"}])
    ])
    tournaments.to_csv("tournaments.csv", index=False)

# Define a custom encoder to handle non-serializable types
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()  # Convert date and datetime to ISO format strings
        return super().default(obj)

def save_tournament_complete(session_state, save_path="", verbose=False):
    """
    Save tournament data to a file or return it as a dictionary.
    """
    required_keys = ["standings", "results", "playoff_results", "selected_tournament_id"]

    # Validate session state keys
    for key in required_keys:
        if key not in session_state or (key == "selected_tournament_id" and not session_state[key]):
            raise ValueError(f"Missing required session state key: {key}")

    tournament_id = session_state.selected_tournament_id
    tournament_metadata = session_state.tournaments.get(tournament_id, {})

    # Enhance the tables with the tournament_id column
    standings = session_state.standings.copy()
    standings["tournament_id"] = tournament_id

    results = session_state.results.copy()
    results["tournament_id"] = tournament_id

    playoff_results = session_state.playoff_results.copy()
    playoff_results["tournament_id"] = tournament_id

    # Log the results as a single dictionary
    tournament_data = {
        "standings": standings.to_dict(orient="records"),
        "results": results.to_dict(orient="records"),
        "playoff_results": playoff_results.to_dict(orient="records"),
        "metadata": tournament_metadata,
    }

    # Save the data to a file if a path is provided
    if save_path:
        timestamp = datetime.now().strftime("%d%m%Y%H%M")
        filename = f"{save_path}/tournament_{tournament_id}_{timestamp}.json"
        try:
            with open(filename, "w") as f:
                json.dump(tournament_data, f, indent=4, cls=CustomJSONEncoder)
            if verbose:
                print(f"Tournament data saved to {filename}")
        except Exception as e:
            raise IOError(f"Failed to save tournament data: {str(e)}")

    return tournament_data


def insert_player_data(data, file_path="assets/players.csv"):
    """
    Insert player data into the players CSV file.

    Parameters:
    - data (list of dict): List of player dictionaries with keys 'first_name', 'last_name', and 'team_name'.
    - file_path (str): Path to the players CSV file (default: "assets/players.csv").
    
    Returns:
    None
    """
    # Ensure the file exists; if not, create it with the appropriate columns
    if not os.path.exists(file_path):
        pd.DataFrame(columns=["first_name", "last_name", "team_name"]).to_csv(file_path, index=False)

    # Load the existing data
    existing_data = pd.read_csv(file_path)

    # Convert the input data to a DataFrame
    new_data = pd.DataFrame(data)

    # Append the new data to the existing data
    updated_data = pd.concat([existing_data, new_data], ignore_index=True)

    # Save the updated data back to the file
    updated_data.to_csv(file_path, index=False)

def insert_new_player_data(new_players):
    """
    Inserts new player data into a database table.
    """
    try:
        # Establish a connection to the database
        engine = sqlalchemy.create_engine("sqlite:///players.db")  # Example with SQLite
        connection = engine.connect()

        # Convert new players (list of dicts) to a DataFrame
        new_data = pd.DataFrame(new_players)

        # Insert new data into the database
        new_data.to_sql("players", con=connection, if_exists="append", index=False)

        # Close the connection
        connection.close()
    except Exception as e:
        raise ValueError(f"Error persisting data to database: {e}")
