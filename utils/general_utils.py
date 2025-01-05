import uuid
import streamlit as st
import pandas as pd

def generate_tournament_id():
    return str(uuid.uuid4())[:8]

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
