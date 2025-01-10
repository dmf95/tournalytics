import streamlit as st
import firebase_admin
from firebase_admin import firestore
from utils.data_utils import firestore_get_leagues, create_league_mapping

# Initialize Firebase app if not already initialized
if not firebase_admin._apps:
    firebase_admin.initialize_app()

# Function to display user account details
def display_account_details(username, email, role, league_names):
    st.markdown(
        f"""
        <div style="text-align: center; margin-bottom: 20px;">
            <h2>Welcome, {username}! 👋</h2>
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
                <li>📧 <strong>Email:</strong> {email or "Not Available"}</li>
                <li>🛡️ <strong>Role:</strong> {role or "Not Available"}</li>
                <li>🏅 <strong>Leagues:</strong> {", ".join(league_names)}</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Function to display navigation tips
def display_navigation_tip():
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

# Main Logic
if st.session_state.get("authenticated", False):
    # Fetch league IDs and names from user data
    league_ids = st.session_state["user_data"].get("league_ids", [])
    if league_ids:
        try:
            # Fetch league names and create mapping
            league_catalog = firestore_get_leagues(league_ids)
            league_mapping = create_league_mapping(league_catalog)
            league_names = list(league_mapping.values())

            # Display account details
            display_account_details(
                username=st.session_state.get("username", "User"),
                email=st.session_state.get("email", "Not Available"),
                role=st.session_state.get("role", "Not Available"),
                league_names=league_names,
            )

            # Display navigation tips
            display_navigation_tip()

        except Exception as e:
            st.error(f"Error fetching league details: {e}", icon="❌")
    else:
        st.warning("No leagues are associated with your account. Please join a league to continue.", icon="ℹ️")
else:
    st.error("You are not authenticated. Please log in to access this page.", icon="❌")

# Divider
st.markdown("---")

# Log Out Button
if st.button("Log Out", use_container_width=True):
    st.session_state.update(
        {
            "authenticated": False,
            "username": None,
            "role": None,
            "email": None,
            "league_id": None,
            "league_mapping": None,
            "league_names": None,
        }
    )
    st.rerun()
