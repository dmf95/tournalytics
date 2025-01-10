import streamlit as st
import firebase_admin
from firebase_admin import firestore
from utils.data_utils import firestore_get_leagues

# Initialize Firebase app if not already initialized
if not firebase_admin._apps:
    firebase_admin.initialize_app()


# Fetch league names if authenticated
if st.session_state.get("authenticated", False):
    league_ids = st.session_state.get("league_id", [])
    league_names = firestore_get_leagues(league_ids)
    st.session_state["league_names"] = league_names

    # Show user details with updated league names
    st.markdown(
        f"""
        <div style="text-align: center; margin-bottom: 20px;">
            <h2>Welcome, {st.session_state['username']}! 👋</h2>
            <p style='font-size: 1em; color: #808080;'>Here are your account details</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div style="margin-bottom: 20px; padding: 15px; border: 1px solid #444; border-radius: 8px; background-color: #222;">
            <h4 style="margin: 0; color: #fff;">👤 Account Details</h4>
            <ul style="list-style: none; padding: 0; margin: 10px 0 0; color: #ccc;">
                <li>📧 <strong>Email:</strong> {st.session_state.get('email', 'Not Available')}</li>
                <li>🛡️ <strong>Role:</strong> {st.session_state['role']}</li>
                <li>🏅 <strong>Leagues:</strong> {", ".join(st.session_state.get('league_names', []))}</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )
# Navigation guidance
st.markdown(
    """
    <style>
        .navigation-tip {
            margin-top: 20px;
            padding: 15px;
            border: 1px solid #444; /* Adjust border color for dark theme */
            border-radius: 8px;
            background-color: #222; /* Dark background */
            color: #ddd; /* Light text color for contrast */
            text-align: center;
            font-size: 1.1em;
        }
        .navigation-tip strong {
            color: #fff; /* Highlighted text in white */
        }
        .navigation-tip .menu-highlight {
            color: #1E90FF; /* Blue for menu text */
        }
    </style>
    <div class="navigation-tip">
        📱 <strong>Tip:</strong> Tap the <span class="menu-highlight">> Menu</span> (top-left) to access pages like 
        <strong>🏆Tournaments</strong>, <strong>🏟️Manage League</strong>, & <strong>📊League Records</strong>.
    </div>
    """,
    unsafe_allow_html=True,
)


st.markdown("---")

# Log Out Button
if st.button("Log Out", use_container_width=True):
    st.session_state.update(
        {"authenticated": False, "username": None, "role": None, "email": None, "league_id": None}
    )
    st.rerun()

