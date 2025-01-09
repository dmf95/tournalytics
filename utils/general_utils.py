import uuid
import streamlit as st
import pandas as pd
import random


def generate_unique_id(existing_ids=None, id_length=9, id_type='numeric'):
    """
    Generates a unique ID not present in the existing_ids collection.

    Parameters:
        existing_ids (set or list, optional): A collection of existing IDs to avoid duplicates. Default is None.
        id_length (int): The length of the ID to be generated (applies to numeric type).
        id_type (str): Type of ID to generate - 'numeric' or 'uuid'.

    Returns:
        str: A unique ID.
    """
    # Ensure existing_ids is a set for efficient lookups
    if existing_ids is None:
        existing_ids = set()
    elif not isinstance(existing_ids, set):
        existing_ids = set(existing_ids)

    while True:
        if id_type == 'numeric':
            # Generate a numeric ID with the specified length
            random_id = ''.join([str(random.randint(0, 9)) for _ in range(id_length)])
        elif id_type == 'uuid':
            # Generate a UUID-based ID with the specified length
            random_id = str(uuid.uuid4())[:id_length]
        else:
            raise ValueError("Invalid id_type. Choose 'numeric' or 'uuid'.")

        # Check uniqueness
        if random_id not in existing_ids:
            return random_id
        

def initialize_session_state():
    defaults = {
        "tournament_id": None,
        "tournament_name": "New Tournament",
        "players": [],
        "teams": {},
        "schedule": None,
        "results": pd.DataFrame(),
        "standings": None,
        "total_duration": 0,
        "team_management_time": 0,
        "playoff_results": pd.DataFrame(),
        "completed": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state or st.session_state[key] is None:
            st.session_state[key] = value
