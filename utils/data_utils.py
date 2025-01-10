## Libraries

import json
from datetime import datetime, date  
import pandas as pd
import streamlit as st
import os
import sqlalchemy
import firebase_admin
from firebase_admin import firestore
from datetime import datetime

## Configs

# Initialize Firebase app if not already initialized
if not firebase_admin._apps:
    firebase_admin.initialize_app()

## Functions

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

def firestore_get_leagues(league_ids):
    """
    Fetch league data for a list of league IDs from Firestore.

    Args:
        league_ids (list): List of league IDs.

    Returns:
        dict: A dictionary with league IDs as keys and their corresponding attributes as values.
    """
    db = firestore.client()
    league_data = {}
    try:
        for league_id in league_ids:
            doc_ref = db.collection("leagues").document(league_id)
            doc = doc_ref.get()
            if doc.exists:
                league_data[league_id] = doc.to_dict()  # Fetch all attributes
            else:
                league_data[league_id] = {"error": "League not found"}
    except Exception as e:
        st.error(f"Error fetching league data: {e}")
    return league_data

def create_league_mapping(league_catalog):
    """
    Create a league mapping with league_id as the key and league_name as the value.

    Args:
        league_catalog (dict): Dictionary with league_ids as keys and their corresponding attributes as values.

    Returns:
        dict: A dictionary with league_ids as keys and league_names as values.
    """
    league_mapping = {}
    for league_id, league_data in league_catalog.items():
        # Extract league_name if it exists, otherwise use a default value
        league_name = league_data.get("league_name", "Unknown League")
        league_mapping[league_id] = league_name
    return league_mapping


# Define a custom encoder to handle non-serializable types
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()  # Convert date and datetime to ISO format strings
        return super().default(obj)

def save_tournament_complete_local(session_state, save_path="", verbose=False):
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
    tournament_metadata["tournament_id"] = tournament_id

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


import json
from datetime import date, datetime
from firebase_admin import firestore


def make_serializable(obj):
    """
    Convert non-serializable objects to serializable ones.
    Handles date, datetime, and other custom types.
    """
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()  # Convert to ISO 8601 string
    return obj  # Return as-is for serializable objects


def validate_session_state_keys(session_state, required_keys):
    """
    Validate that all required keys are present in the session_state.
    """
    for key in required_keys:
        if key not in session_state or (key == "selected_tournament_id" and not session_state[key]):
            raise ValueError(f"Missing required session state key: {key}")


def extract_and_validate_tournament_metadata(session_state, tournament_id):
    """
    Extract tournament metadata from session_state and validate its structure.
    """
    tournaments_raw = session_state.get("tournaments", {})

    # Ensure tournaments is a dictionary
    if isinstance(tournaments_raw, dict):
        tournaments = tournaments_raw
    elif isinstance(tournaments_raw, str):
        try:
            tournaments = json.loads(tournaments_raw)  # Deserialize if stored as JSON string
        except json.JSONDecodeError:
            raise ValueError("The 'tournaments' in session_state is not a valid JSON string.")
    else:
        raise ValueError("'tournaments' in session_state must be a dictionary or a valid JSON string.")

    # Retrieve metadata for the selected tournament
    tournament_metadata = tournaments.get(tournament_id, {})

    if not isinstance(tournament_metadata, dict):
        raise ValueError(f"Invalid tournament metadata for ID {tournament_id}.")

    # Add the tournament_id to the metadata
    tournament_metadata["tournament_id"] = tournament_id
    return {key: make_serializable(value) for key, value in tournament_metadata.items()}


def enhance_dataframe_with_tournament_id(dataframe, tournament_id):
    """
    Add a tournament_id column to a DataFrame.
    """
    dataframe = dataframe.copy()
    dataframe["tournament_id"] = tournament_id
    return dataframe.to_dict(orient="records")


def save_tournament_complete(session_state, verbose=False):
    """
    Save tournament data to Firestore under the tournaments/ collection.
    """
    # Firestore client
    db = firestore.client()

    # Validate required keys
    required_keys = ["standings", "results", "playoff_results", "selected_tournament_id"]
    validate_session_state_keys(session_state, required_keys)

    # Extract tournament_id and metadata
    tournament_id = session_state.get("selected_tournament_id")
    if not tournament_id:
        raise ValueError("The selected tournament ID is missing or not set in session_state.")

    tournament_metadata = extract_and_validate_tournament_metadata(session_state, tournament_id)

    # Enhance dataframes with tournament_id
    standings = enhance_dataframe_with_tournament_id(session_state.final_standings, tournament_id)
    results = enhance_dataframe_with_tournament_id(session_state.results, tournament_id)
    playoff_results = enhance_dataframe_with_tournament_id(session_state.playoff_results, tournament_id)

    # Prepare tournament data for saving
    tournament_data = {
        "standings": standings,
        "results": results,
        "playoff_results": playoff_results,
        "metadata": tournament_metadata,
    }

    # Save to Firestore
    try:
        doc_ref = db.collection("tournaments").document(tournament_id)
        doc_ref.set(tournament_data)  # Write tournament data to Firestore

        if verbose:
            print(f"Tournament data saved successfully to Firestore for ID: {tournament_id}")
    except Exception as e:
        raise RuntimeError(f"Failed to save tournament data to Firestore: {e}")

    return tournament_id
