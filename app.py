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
    "Tournaments": st.Page("tournaments.py", title="Tournaments", icon="🏆"),
    "Manage": st.Page("manage.py", title="Manage Leagues", icon="🏟️"),
    "Profile": st.Page("profile.py", title="My Profile", icon="🧑‍💻"),
    "Stats": st.Page("stats.py", title="League Records", icon="📊"),
}

# Authentication and Navigation
if st.session_state.get("authenticated", False):
    # Display user info and logout option
    st.sidebar.markdown(f"**Logged in as:** {st.session_state.get('username', 'Unknown')} ({st.session_state.get('role', 'Unknown')})")
    if st.sidebar.button("Log Out"):
        # Clear all session state variables
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        # Optionally, reset specific defaults if needed
        st.session_state["authenticated"] = False
        
        # Rerun the app to reflect the changes
        st.rerun()

    # Define role-based navigation
    role_pages = {
        "super_admin": {
            "Main": [pages["Home"]],
            "Features": [pages["Tournaments"], pages["Manage"], pages["Profile"], pages["Stats"]],
        },
        "admin": {
            "Main": [pages["Home"]],
            "Features": [pages["Tournaments"], pages["Profile"], pages["Manage"], pages["Stats"]],
        },
        "user": {
            "Main": [pages["Home"]],
            "Features": [pages["Tournaments"], pages["Profile"], pages["Manage"], pages["Stats"]],
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
            "Home": [pages["Home"]],
        }
    )

# Run the selected page
pg.run()
