import streamlit as st
from utils.auth_utils import authenticate_user, register_user
import re

# Check authentication state

if not st.session_state.get("authenticated", False):
    st.markdown(
        """
        <div style='text-align: center; margin-bottom: 20px;'>
            <h2 style='margin-bottom: 5px;'>🧑‍💻 Login or Signup</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Tab-based layout for Login and Signup
    tabs = st.tabs(["Log In", "Sign Up"])

    # Log In Tab
    with tabs[0]:
        st.subheader("Log In")
        with st.form("login_form", clear_on_submit=True):
            identifier = st.text_input("Email or Username", placeholder="Enter your email or username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            login_button = st.form_submit_button("Log In")

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

    # Sign Up Tab
    with tabs[1]:  # Sign Up tab
        st.subheader("Sign Up")
        with st.form("signup_form", clear_on_submit=True):
            new_email = st.text_input("Email Address", placeholder="Enter a valid email address")
            new_username = st.text_input("New Username", placeholder="Choose a unique username")
            new_password = st.text_input("New Password", type="password", placeholder="Choose a strong password")
            signup_button = st.form_submit_button("Sign Up")

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
                    st.success(f"Account created successfully for {new_username}. Please log in.")
                else:
                    st.error(message)

else:
    # Show user details if authenticated
    st.markdown(
        f"""
        <div style="text-align: center; margin-bottom: 20px;">
            <h2>Welcome, {st.session_state['username']}!</h2>
            <p style='font-size: 1em; color: #808080;'>Here are your account details.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(f"**Username:** {st.session_state['username']}")
    st.markdown(f"**Email:** {st.session_state.get('email', 'Not Available')}")
    st.markdown(f"**Role:** {st.session_state['role']}")
    st.markdown(f"**League ID:** {st.session_state.get('league_id', 'None')}")

    # Log Out Button
    if st.button("Log Out", use_container_width=True):
        st.session_state.update({"authenticated": False, "username": None, "role": None, "email": None, "league_id": None})
        st.rerun()
