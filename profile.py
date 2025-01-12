import streamlit as st
import firebase_admin
from utils.data_utils import firestore_get_leagues, create_league_mapping, firestore_get_user
import time

# Initialize Firebase app if not already initialized
if not firebase_admin._apps:
    firebase_admin.initialize_app()

def display_account_details(username, email, role, league_names):
    """
    Display user account details in a styled card.
    """
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
                <li>🏅 <strong>Leagues:</strong> {", ".join(league_names) if league_names else "None"}</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def display_navigation_tip():
    """
    Display a navigation tip for the user.
    """
    st.markdown(
        """
        <style>
            .navigation-tip {
                margin-top: 20px;
                padding: 15px;
                border: 1px solid #444;
                border-radius: 8px;
                background-color: #222;
                color: #ddd;
                text-align: center;
                font-size: 1.1em;
            }
            .navigation-tip strong {
                color: #fff;
            }
            .navigation-tip .menu-highlight {
                color: #1E90FF;
            }
        </style>
        <div class="navigation-tip">
            📱 <strong>Tip:</strong> Tap the <span class="menu-highlight">> Menu</span> (top-left) to access pages like 
            <strong>🏆Tournaments</strong>, <strong>🏟️Manage League</strong>, & <strong>📊League Records</strong>.
        </div>
        """,
        unsafe_allow_html=True,
    )

def sync_user_leagues():
    """
    Sync user's leagues from Firestore to session state.
    Ensures user data is refreshed before syncing leagues.
    """
    try:
        # Refresh user data from Firestore
        user_data = firestore_get_user(st.session_state["user_id"])
        st.session_state["user_data"] = user_data  # Update session state with refreshed user data

        league_ids = user_data.get("league_id", [])
        if league_ids:
            # Fetch league data and update session state
            league_catalog = firestore_get_leagues(league_ids)
            league_mapping = create_league_mapping(league_catalog)
            league_names = list(league_mapping.values())

            st.session_state.update(
                {
                    "league_catalog": league_catalog,
                    "league_mapping": league_mapping,
                    "league_names": league_names,
                }
            )
        else:
            # Clear league data if no leagues are associated
            st.session_state.update(
                {
                    "league_catalog": None,
                    "league_mapping": None,
                    "league_names": [],
                }
            )
    except Exception as e:
        st.error(f"Error syncing league data: {e}", icon="❌")



# Main Logic
if st.session_state.get("authenticated", False):
    # Sync leagues if not already in session state
    if "league_mapping" not in st.session_state:
        sync_user_leagues()

    # Display account details
    display_account_details(
        username=st.session_state.get("username", "User"),
        email=st.session_state.get("email", "Not Available"),
        role=st.session_state.get("role", "Not Available"),
        league_names=st.session_state.get("league_names", []),
    )

    # Initialize session state variables for cooldown
    if "last_refresh_time" not in st.session_state:
        st.session_state["last_refresh_time"] = 0

    # Define cooldown period (in seconds)
    cooldown_period = 60

    # Check if cooldown period has elapsed
    current_time = time.time()
    time_since_last_click = current_time - st.session_state["last_refresh_time"]

    if time_since_last_click < cooldown_period:
        st.warning(f"Please wait {int(cooldown_period - time_since_last_click)} seconds before refreshing again.", icon="⏳")
        button_disabled = True
    else:
        button_disabled = False


    # Sync Button (optional manual refresh)
    if st.button("🔄 Refresh League Data", use_container_width=True, disabled=button_disabled):
        try:
            sync_user_leagues()  # Refresh both user data and leagues
            st.success("League data refreshed successfully!", icon="✅")
            st.session_state["last_refresh_time"] = time.time()  # Update last click time
        except Exception as e:
            st.error(f"Error refreshing league data: {e}", icon="❌")


    # Display navigation tips
    display_navigation_tip()

# Divider
st.markdown("---")

# Log Out Button
if st.button("🚪 Log Out", use_container_width=True):
    # Clear the entire session state
    for key in list(st.session_state.keys()):
        del st.session_state[key]

    # Optionally set default states (if needed after clearing)
    st.session_state.update(
        {
            "authenticated": False,  # Ensure user is logged out
        }
    )

    # Rerun the app to refresh the UI
    st.rerun()
