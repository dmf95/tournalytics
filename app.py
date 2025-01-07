import streamlit as st
from utils.auth_utils import authenticate_user

# Set page configuration (centralized, only called once)
st.set_page_config(
    page_title="Tournalytics", 
    page_icon="🎮", 
    layout="centered",
    initial_sidebar_state="collapsed"
    )

# Initialize session state for authentication
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "username" not in st.session_state:
    st.session_state["username"] = None
if "role" not in st.session_state:
    st.session_state["role"] = None

# Define pages using st.Page
pages = {
    "Home": st.Page("home.py", title="Home", icon="🎮", default=True),
    "Account": st.Page("login.py", title="Account", icon="🧑‍💻"),
    "Tournaments": st.Page("tournaments.py", title="Tournaments", icon="🏆"),
    "Players": st.Page("players.py", title="Players", icon="👤"),
    "Stats": st.Page("stats.py", title="Stats", icon="📊"),
}

# Authentication and Navigation
if st.session_state["authenticated"]:
    # Display user info and logout option
    st.sidebar.markdown(f"**Logged in as:** {st.session_state['username']} ({st.session_state['role']})")
    if st.sidebar.button("Log Out"):
        # Reset session state and rerun the app
        st.session_state["authenticated"] = False
        st.session_state["username"] = None
        st.session_state["role"] = None
        st.rerun()

    # Define role-based navigation
    role_pages = {
        "super_admin": {
            "Main": [pages["Home"]],
            "Features": [pages["Account"], pages["Tournaments"], pages["Players"], pages["Stats"]],
        },
        "admin": {
            "Main": [pages["Home"]],
            "Features": [pages["Account"], pages["Tournaments"], pages["Players"]],
        },
        "user": {
            "Main": [pages["Home"]],
            "Features": [pages["Account"], pages["Stats"]],
        },
    }

    # Get pages based on user role
    navigation_structure = role_pages.get(st.session_state["role"])
    if navigation_structure:
        pg = st.navigation(navigation_structure)
    else:
        st.error("Unknown role. Please contact support.")
        st.stop()
else:
    # Not authenticated: Restrict to Account page
    pg = st.navigation(
        {
            "Authentication": [pages["Account"]],
        }
    )

# Run the selected page
pg.run()
