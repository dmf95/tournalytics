import streamlit as st
from utils.auth_utils import authenticate_user, register_user
import re

#-1- Authentication needed: Signin page

if not st.session_state.get("authenticated", False):
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 20px; padding: 10px;">
            <h2 style="font-size: 2.2em; margin-bottom: 0px;">🧑‍💻 Get Started</h2>
            <p style="font-size: 1.1em; color: #808080; max-width: 600px; margin: 0 auto;">
                Sign In or Create an Account
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    # Tab-based layout for Sigin and Signup
    tabs = st.tabs(["Sign In", "Create Account"])

    # Sign In Tab
    with tabs[0]:
        st.subheader("Sign In")
        with st.form("signin_form", clear_on_submit=True):
            identifier = st.text_input("Email or Username", placeholder="Enter your email or username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            login_button = st.form_submit_button("Sign In")

        if login_button:
            if not identifier or not password:
                st.error("Both identifier and password are required.")
            else:
                user_data = authenticate_user(identifier, password)
                if user_data:
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = user_data["username"]
                    st.session_state["role"] = user_data["role"]
                    st.session_state["email"] = user_data.get("email")
                    st.session_state["league_id"] = user_data.get("league_id")
                    st.success(f"Welcome, {user_data['username']}! Redirecting...")
                    st.rerun()
                else:
                    st.error("Invalid identifier or password. Please try again.")

    # Create an Account Tab
    with tabs[1]:
        st.subheader("Create an Account")
        with st.form("signup_form", clear_on_submit=True):
            new_email = st.text_input("Email Address", placeholder="Enter a valid email address")
            new_username = st.text_input("New Username", placeholder="Choose a unique username")
            new_password = st.text_input("New Password", type="password", placeholder="Choose a strong password")
            signup_button = st.form_submit_button("Create an Account")

        if signup_button:
            if not new_email or not new_username or not new_password:
                st.error("Email, username, and password are all required.")
            elif not re.match(r"[^@]+@[^@]+\.[^@]+", new_email):
                st.error("Invalid email address format.")
            elif len(new_password) < 6:
                st.error("Password must be at least 6 characters long.")
            else:
                success, message = register_user(new_email, new_password, new_username, role="user", league_id=None)
                if success:
                    st.success(f"Account created successfully for {new_username}. Please sign in.")
                else:
                    st.error(message)

# Authentication complete: Home page
else:
    # Welcome Section
    st.markdown(
        f"""
        <div style="text-align: center; margin-bottom: 20px;">
            <h2 style="font-size: 2.2em; margin: 0; color: #fff;">Welcome, {st.session_state['username']}! 👋</h2>
            <p style="font-size: 1em; color: #ccc;">Your Tournalytics dashboard</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Feature Cards Section
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 20px;">
            <h3 style="margin: 0; font-size: 1.6em; color: #fff;">✨ Quick Actions</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Feature Cards with Page Links (styled buttons)
    col1, col2 = st.columns(2)

    with col1:
        st.page_link("tournaments.py", label="Start a Tournament", icon="🏆", help="Build or Run a Tournament for your Leagues")
        
    with col2:
        st.page_link("manage.py", label="Manage Leagues", icon="🏟️")


    # Feature Cards with Page Links (styled buttons)
    col3, col4 = st.columns(2)


    with col3:
        st.page_link("stats.py", label="League Records", icon="📊")

    with col4:
        st.page_link("profile.py", label="My Profile", icon="👤")

    # Tips Section
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 20px;">
            <h3 style="margin: 0; font-size: 1.6em; color: #fff;">🔥 Helpful Tips</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Navigation Guidance
    st.markdown(
        """
        <style>
            .navigation-tip {
                margin-top: 20px;
                padding: 15px;
                border: 1px solid #444;
                border-radius: 8px;
                background-color: #222;
                color: #ccc;
                text-align: center;
                font-size: 1em;
            }
            .navigation-tip strong {
                color: #fff;
            }
            .navigation-tip .menu-highlight {
                color: #1E90FF;
            }
        </style>
        <div class="navigation-tip">
            📱 <strong>Tip:</strong> Click the links above to get started.
        </div>
        """,
        unsafe_allow_html=True,
    )

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

    # Log Out Button
    st.markdown("---")
    if st.button("🔓 Log Out", use_container_width=True):
        st.session_state.update(
            {"authenticated": False, "username": None, "role": None, "email": None, "league_id": None}
        )
        st.rerun()

# Footer Section
st.markdown(
    """
    <div style="text-align: center; margin-top: 10px; font-size: 0.85em; color: #777;">
        Built with ❤️ by <strong>Tournalytics</strong> | v1.0.0
    </div>
    """,
    unsafe_allow_html=True,
)