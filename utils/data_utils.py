## Libraries
import json
import os
from datetime import datetime, date
import pandas as pd
import sqlalchemy
import streamlit as st
import firebase_admin
from firebase_admin import firestore

# Initialize Firestore client
if not firebase_admin._apps:
    firebase_admin.initialize_app()

db = firestore.client()


# --- FIRESTORE READ/WRITE FUNCTIONS ---
@st.cache_data(ttl=600)
def firestore_get_leagues(league_ids):
    """
    Fetch data for multiple league IDs using batch reads.
    """
    try:
        doc_refs = [db.collection("leagues").document(league_id) for league_id in league_ids]
        docs = db.get_all(doc_refs)
        return {
            doc.id: doc.to_dict() if doc.exists else {"error": "League not found"}
            for doc in docs
        }
    except Exception as e:
        st.error(f"Error fetching league data: {e}")
        return {}


@st.cache_data(ttl=600)
def firestore_get_all_users():
    """
    Fetch all users from Firestore.
    """
    try:
        users_ref = db.collection("users").get()
        return {user.id: user.to_dict() for user in users_ref}
    except Exception as e:
        st.error(f"Error fetching all users: {e}")
        return {}

@st.cache_data(ttl=600)
def firestore_get_all_leagues():
    """
    Fetch all leagues from Firestore.
    """
    try:
        leagues_ref = db.collection("leagues").get()
        return {league.id: league.to_dict() for league in leagues_ref}
    except Exception as e:
        st.error(f"Error fetching all leagues: {e}")
        return {}


def firestore_add_league(league_name, league_type, created_by, admins, super_admin):
    """
    Add a new league to Firestore with its metadata, admins, and super admin.
    """
    try:
        league_ref = db.collection("leagues").document()
        league_data = {
            "league_name": league_name,
            "league_type": league_type,
            "created_by": created_by,
            "admins": admins,
            "super_admin": super_admin,
            "created_at": firestore.SERVER_TIMESTAMP,  # Adds creation timestamp
        }
        league_ref.set(league_data)
        return {"success": True, "league_id": league_ref.id}
    except Exception as e:
        return {"success": False, "message": str(e)}


def firestore_update_league_admins(league_id, new_admins):
    """
    Updates the list of admins for a given league in Firestore.

    Args:
        league_id (str): The ID of the league to update.
        new_admins (list): The updated list of admin user IDs.

    Returns:
        dict: A dictionary indicating success or failure with a message.
    """
    try:
        league_ref = db.collection("leagues").document(league_id)
        league_ref.update({"admins": new_admins})
        return {"success": True, "message": "Admins updated successfully."}
    except Exception as e:
        return {"success": False, "message": str(e)}


def firestore_add_players_to_league(league_id, player_ids):
    """
    Add multiple players to a league in Firestore, ensuring no duplicates.
    
    Args:
        league_id (str): The ID of the league.
        player_ids (list): A list of player IDs to add.

    Returns:
        dict: A success flag and a message.
    """
    try:
        league_ref = db.collection("leagues").document(league_id)
        league_data = league_ref.get().to_dict()

        if not league_data:
            return {"success": False, "message": f"League with ID {league_id} not found."}

        # Ensure 'members' is treated as a list
        current_members = league_data.get("members", [])
        if not isinstance(current_members, list):
            current_members = []

        # Add new members and remove duplicates
        new_members = list(set(current_members + player_ids))
        league_ref.update({"members": new_members})

        return {"success": True, "message": "Players added successfully."}
    except Exception as e:
        return {"success": False, "message": f"Error adding players to league: {e}"}


    except Exception as e:
        # Log and return the error message
        error_message = f"Error adding players to league: {e}"
        st.error(error_message)
        return {"success": False, "message": error_message}



def firestore_remove_players_from_league(league_id, player_ids):
    """
    Remove multiple players from a league in Firestore.
    """
    try:
        league_ref = db.collection("leagues").document(league_id)
        current_members = league_ref.get().to_dict().get("members", [])
        updated_members = [player for player in current_members if player not in player_ids]
        league_ref.update({"members": updated_members})
        return {"success": True, "message": "Players removed successfully."}
    except Exception as e:
        st.error(f"Error removing players from league: {e}")
        return {"success": False, "message": str(e)}


def firestore_get_user(user_id):
    """
    Fetch a single user's data by their ID.
    """
    try:
        user_doc = db.collection("users").document(user_id).get()
        if user_doc.exists:
            return user_doc.to_dict()
        else:
            return {"error": "User not found"}
    except Exception as e:
        st.error(f"Error fetching user data: {e}")
        return {}


def firestore_batch_update_users(user_updates):
    """
    Batch update user data in Firestore.
    """
    try:
        batch = db.batch()
        for user_id, updates in user_updates.items():
            user_ref = db.collection("users").document(user_id)
            batch.update(user_ref, updates)
        batch.commit()
        return {"success": True, "message": "Batch update completed successfully."}
    except Exception as e:
        st.error(f"Error in batch updating users: {e}")
        return {"success": False, "message": str(e)}


def firestore_query_tournaments_by_league(league_id):
    """
    Query Firestore for tournaments associated with a specific league.

    Args:
        league_id (str): The ID of the league to filter tournaments by.

    Returns:
        list: A list of dictionaries representing the tournaments for the given league.
    """
    db = firestore.client()
    try:
        # Query the tournaments collection filtered by league_id
        tournaments_ref = db.collection("tournaments").where("metadata.league_id", "==", league_id).stream()
        
        # Parse the query results
        tournaments = [doc.to_dict() for doc in tournaments_ref]
        
        return tournaments
    except Exception as e:
        # Log error and return an empty list
        print(f"Error querying tournaments by league: {e}")
        return []



# --- FIRESTORE FUNCTIONS, SAVE TOURNAMENT ---


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

# --- DATA MANIPULATION FUNCTIONS ---

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

def filter_users_by_role(users, roles):
    """
    Filter users locally by roles.

    Args:
        users (dict): All users fetched from Firestore.
        roles (list): List of roles to filter by.

    Returns:
        dict: Filtered users by roles.
    """
    return {user_id: user_data for user_id, user_data in users.items() if user_data.get("role") in roles}
