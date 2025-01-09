import streamlit as st
import pandas as pd
from utils.data_utils import load_player_data_local, insert_new_player_data
import random
from firebase_admin import firestore
from utils.auth_utils import create_league_metadata

def to_snake_case(name):
    """
    Converts a name to Snake Case format: First letters capitalized, rest lowercase.
    Example: "john DOE" -> "John Doe"
    """
    return " ".join([word.capitalize() for word in name.split()])



st.markdown(
    """
    <div style="text-align: center; margin-bottom: 20px;">
        <h2>🎮 Manage Leagues 🎮</h2>
    </div>
    """,
    unsafe_allow_html=True,
)

# Initialize session state
if "player_names" not in st.session_state:
    players_df = load_player_data_local("assets/players.csv")
    st.session_state["player_names"] = players_df["first_name"] + " " + players_df["last_name"]

if "tournaments" not in st.session_state:
    st.session_state["tournaments"] = {}

if "selected_tab" not in st.session_state:
    st.session_state["selected_tab"] = "Create League"  # Default tab

if "selected_tournament_id" not in st.session_state:
    # Automatically set the first tournament ID if available
    st.session_state["selected_tournament_id"] = next(iter(st.session_state["tournaments"]), None)

if "tournament_ready" not in st.session_state:
    st.session_state["tournament_ready"] = False

if "expander_open" not in st.session_state:
    st.session_state["expander_open"] = True  # Start with the expander open

# Firestore setup (assuming Firebase Admin SDK is initialized elsewhere)
db = firestore.client()

# Main Navigation Buttons
col1, col2, col3 = st.columns(3)

# Determine user role
user_role = st.session_state.role

# Show buttons but disable unavailable options
with col1:
    setup_button = st.button(
        "🖌️ Create League",
        use_container_width=True,
        key="create_leagues_button",
        help="Set up your tournament step-by-step.",
        disabled=user_role != "super_admin",
    )
    if setup_button:
        st.session_state["selected_tab"] = "Create League"

with col2:
    management_button = st.button(
        "🎮 Manage Leagues",
        use_container_width=True,
        key="manage_leagues_button",
        help="Manage your tournament after setup is complete.",
        disabled=user_role not in ["super_admin", "admin"],
    )
    if management_button:
        st.session_state["selected_tab"] = "Manage Leagues"

with col3:
    search_button = st.button(
        "🔍 Search Leagues",
        use_container_width=True,
        key="search_leagues_button",
        help="Search for leagues and their details.",
    )
    if search_button:
        st.session_state["selected_tab"] = "Search Leagues"

# Handle tab selection
selected_tab = st.session_state["selected_tab"]

if selected_tab == "Create League" and user_role == "super_admin":
    st.markdown(
        """
        <div style='text-align: center; margin-bottom: 20px;'>
            <h2 style='margin-bottom: 0px;'>🖌️ Create a League</h2>
            <p style='font-size: 14px; color: #808080;'>Set up your new league, assign admins, and establish a super admin.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Ensure user_id exists in session state
    if "user_id" not in st.session_state or not st.session_state["user_id"]:
        try:
            # Example: Retrieve user_id from Firebase based on email (assumes email is stored in session_state)
            user_email = st.session_state.get("email")
            if user_email:
                user_doc = db.collection("users").where("email", "==", user_email).get()
                if user_doc:
                    st.session_state["user_id"] = user_doc[0].id
                else:
                    st.error("Failed to retrieve user ID. Please reauthenticate.", icon="❌")
                    st.stop()
            else:
                st.error("Email not found in session state. Please log in again.", icon="❌")
                st.stop()
        except Exception as e:
            st.error(f"Error retrieving user ID: {e}", icon="❌")
            st.stop()

    creator_id = st.session_state["user_id"]

    # Fetch available admins (both admins and super admins)
    users_ref = db.collection("users").where("role", "in", ["admin", "super_admin"]).get()
    users = {user.id: user.to_dict() for user in users_ref}

    # Use session state to track submission status
    if "league_submission_result" not in st.session_state:
        st.session_state["league_submission_result"] = None

    with st.form("add_league_form"):
        league_name = st.text_input("League Name", placeholder="Enter league name")
        league_type = st.selectbox("League Type", ["Private", "Public"], index=0)

        if users:
            # Select multiple admins
            selected_admins = st.multiselect(
                "Assign Admins",
                options=list(users.keys()),
                format_func=lambda x: f"{users[x]['username']} ({users[x]['role']})",
            )
        else:
            st.warning("No users available to assign as admins. Please add admins or super admins.")
            selected_admins = []

        submitted = st.form_submit_button("➕ Create League", use_container_width=True)

        if submitted:
            if league_name and selected_admins:
                if creator_id not in selected_admins:
                    selected_admins.append(creator_id)

                # Validate roles: exactly one super admin, which is the creator
                super_admins = [
                    admin for admin in selected_admins if admin in users and users[admin]["role"] == "super_admin"
                ]
                if len(super_admins) != 1 or super_admins[0] != creator_id:
                    st.error("Each league must have exactly one super admin, which is the creator.", icon="❌")
                else:
                    # Create the league metadata
                    created_league = create_league_metadata(
                        league_name,
                        league_type,
                        created_by=creator_id,
                    )
                    if created_league["success"]:
                        # Add admins and super admin to the league
                        league_id = created_league["league_id"]
                        db.collection("leagues").document(league_id).update({
                            "admins": selected_admins,
                            "super_admin": creator_id,
                        })
                        st.session_state["league_submission_result"] = created_league
                    else:
                        st.error(created_league["message"], icon="❌")
            else:
                st.error("League Name and Admin assignment are required.", icon="❌")

    if st.session_state["league_submission_result"]:
        if st.session_state["league_submission_result"]["success"]:
            st.success(st.session_state["league_submission_result"]["message"], icon="✅")
        else:
            st.error(st.session_state["league_submission_result"]["message"], icon="❌")

    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; margin-bottom: 20px;'>
            <h3 style='margin-bottom: 0px;'>📋 Manage League Admins</h3>
            <p style='font-size: 14px; color: #808080;'>Easily view leagues and manage their admin associations.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Fetch leagues and users
    leagues_ref = db.collection("leagues").get()
    leagues = {league.id: league.to_dict() for league in leagues_ref}
    users_ref = db.collection("users").where("role", "in", ["admin", "super_admin"]).get()
    users = {user.id: user.to_dict() for user in users_ref}

    if leagues:
        # Display leagues in collapsible cards
        st.markdown("#### Leagues Overview")
        with st.expander("📋 View Existing Leagues", expanded=False):
            leagues_ref = db.collection("leagues").get()
            leagues = {league.id: league.to_dict() for league in leagues_ref}

            if leagues:
                leagues_data = [
                    {
                        "League Name": league_data.get("league_name", "Unknown"),
                        "League Type": league_data.get("league_type", "Unknown").capitalize(),
                        "Super Admin": users.get(league_data.get("super_admin"), {}).get("username", "Unassigned"),
                        "Admins": ", ".join(
                            [users.get(admin, {}).get("username", "Unknown") for admin in league_data.get("admins", [])]
                        ),
                        "Created At": league_data.get("created_at", "N/A"),
                    }
                    for league_data in leagues.values()
                ]
                leagues_df = pd.DataFrame(leagues_data)

                st.dataframe(
                    leagues_df,
                    use_container_width=True,
                )
            else:
                st.warning("No leagues found.")



        st.markdown("---")
        st.markdown("#### Manage League Admins")

        # Select league to manage
        selected_league_id = st.selectbox(
            "Select League to Manage",
            options=list(leagues.keys()),
            format_func=lambda x: leagues[x]["league_name"],
        )

        if selected_league_id:
            selected_league = leagues[selected_league_id]
            current_admins = selected_league.get("admins", [])
            current_super_admin = selected_league.get("super_admin")

            # Display current league details in a card-style layout optimized for dark theme
            st.markdown(
                f"""
                <div style="
                    border: 1px solid #444; 
                    border-radius: 8px; 
                    padding: 16px; 
                    margin-bottom: 16px; 
                    background-color: #222; 
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.5);
                ">
                    <h4 style="margin: 0; color: #fff;">🏆 League Details</h4>
                    <hr style="border: none; border-top: 1px solid #444; margin: 8px 0;">
                    <p style="color: #ddd;"><strong>League Name:</strong> {selected_league.get('league_name', 'Unknown')}</p>
                    <p style="color: #ddd;"><strong>League Type:</strong> {selected_league.get('league_type', 'Unknown').capitalize()}</p>
                    <p style="color: #ddd;"><strong>Super Admin:</strong> {users.get(current_super_admin, {}).get('username', 'Unassigned')}</p>
                    <p style="color: #ddd;"><strong>Current Admins:</strong> {", ".join([users.get(admin, {}).get("username", "Unknown") for admin in current_admins]) if current_admins else "No admins assigned."}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )



            # Update admin associations
            st.markdown("#### Update Admin Associations")
            selected_new_admins = st.multiselect(
                "Add or Remove Admins",
                options=list(users.keys()),
                format_func=lambda x: f"{users[x]['username']} ({users[x]['role']})",
                default=current_admins,
            )

            if st.button("Update Admins"):
                try:
                    # Ensure the super admin remains unchanged
                    if current_super_admin not in selected_new_admins:
                        st.error("The super admin cannot be removed from the admin list.", icon="❌")
                    else:
                        # Update league admins in Firestore
                        db.collection("leagues").document(selected_league_id).update({
                            "admins": selected_new_admins,
                        })
                        st.success("Admins updated successfully!", icon="✅")
                        # Refresh the page or data after update
                except Exception as e:
                    st.error(f"Error updating admins: {e}", icon="❌")
    else:
        st.warning("No leagues found. Please create a league first.")





elif selected_tab == "Manage Leagues" and user_role in ["super_admin", "admin"]:
    st.markdown(
        """
        <div style='text-align: center; margin-bottom: 20px;'>
            <h2 style='margin-bottom: 0px;'>🎮 Manage Leagues</h2>
            <p style='font-size: 14px; color: #808080;'>Update league details and associations.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    leagues_ref = db.collection("leagues").get()
    players_ref = db.collection("players").get()

    leagues = {league.id: league.to_dict() for league in leagues_ref}
    players = {player.id: player.to_dict() for player in players_ref}

    if leagues and players:
        selected_league = st.selectbox("Select League", options=list(leagues.keys()), format_func=lambda x: leagues[x]["league_name"])
        selected_players = st.multiselect(
            "Select Players to Associate", 
            options=list(players.keys()), 
            format_func=lambda x: f"{players[x]['first_name']} {players[x]['last_name']}"
        )

        if st.button("Update Associations"):
            for player_id in selected_players:
                db.collection("players").document(player_id).update({"league_id": selected_league})
            st.success("Player-League associations updated successfully!", icon="✅")
    else:
        st.warning("No leagues or players found.")

elif selected_tab == "Search Leagues" and user_role in ["super_admin", "admin"]:
    st.markdown(
        """
        <div style='text-align: center; margin-bottom: 20px;'>
            <h2 style='margin-bottom: 0px;'>🔍 Search Leagues</h2>
            <p style='font-size: 14px; color: #808080;'>Find leagues and view their details.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    leagues_ref = db.collection("leagues").get()
    leagues = {league.id: league.to_dict() for league in leagues_ref}

    if leagues:
        search_query = st.text_input("Search for a League", placeholder="Enter league name")
        if search_query:
            filtered_leagues = {k: v for k, v in leagues.items() if search_query.lower() in v["league_name"].lower()}
            for league_id, league_data in filtered_leagues.items():
                st.markdown(f"**{league_data['league_name']}** - Type: {league_data['league_type']}")
        else:
            for league_id, league_data in leagues.items():
                st.markdown(f"**{league_data['league_name']}** - Type: {league_data['league_type']}")
    else:
        st.warning("No leagues found.")
