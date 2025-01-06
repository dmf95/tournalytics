import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth

# Mock database for authentication
#USER_DATABASE = {
#    "dmf95": {"password": "elephant", "role": "super_admin"},  # Super admin
#    "admin1": {"password": "admin123", "role": "admin"},       # Admin
#    "user1": {"password": "user123", "role": "user"},          # Regular user
#}


# Path to your Firebase Admin SDK key JSON file
FIREBASE_CREDENTIALS_PATH = ".streamlit/firebase-key.json"

# Initialize Firebase
if not firebase_admin._apps:  # Prevent reinitialization
    cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred)


def render_login():
    """Renders the login page."""
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 20px; padding: 10px;">
            <h1 style="font-size: 2.2em; margin-bottom: 0px;">🎮 Tournalytics Login 🎮</h1>
            <p style="font-size: 1.1em; color: #808080; max-width: 600px; margin: 0 auto;">
                Please log in to access the app.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Login form
    with st.form("login_form", clear_on_submit=True):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Log In")

    # Handle login
    if submit_button:
        user = USER_DATABASE.get(username)
        if user and user["password"] == password:
            st.session_state["authenticated"] = True
            st.session_state["username"] = username
            st.session_state["role"] = user["role"]
            st.success(f"Welcome, {username}!")
        else:
            st.error("Invalid username or password.")

def render_home():
    """Render the Home page with mobile-first enhancements."""
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 20px; padding: 10px;">
            <h1 style="font-size: 2.2em; margin-bottom: 0px;">🎮 Tournalytics 🎮</h1>
            <p style="font-size: 1.1em; color: #808080; max-width: 600px; margin: 0 auto;">
                Welcome to the Tournament app.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Feature Overview Section
    st.markdown(
        """
        <div style="margin: 0px 0; padding: 0px;">
            <h2 style="text-align: center; font-size: 1.8em; margin-bottom: 0px;">Features</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )