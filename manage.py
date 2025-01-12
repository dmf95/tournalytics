import streamlit as st
import pandas as pd
from utils.data_utils import (
    create_league_mapping,
    firestore_get_leagues,
    firestore_get_all_users,
    firestore_add_league,
    firestore_get_all_leagues,
    firestore_get_user,
    firestore_update_league_admins,
    firestore_add_players_to_league,
    firestore_remove_players_from_league,
    firestore_batch_update_users,
    filter_users_by_role
)
from utils.auth_utils import create_league_metadata
import firebase_admin
from firebase_admin import firestore
import time

# Initialize Firebase app if not already initialized
if not firebase_admin._apps:
    firebase_admin.initialize_app()

# Initialize Firestore client
db = firestore.client()

# Helper Functions
def to_snake_case(name):
    """
    Converts a name to Snake Case format: First letters capitalized, rest lowercase.
    Example: "john DOE" -> "John Doe"
    """
    return " ".join([word.capitalize() for word in name.split()])


# Main Code
st.markdown(
    """
    <div style="text-align: center; margin-bottom: 20px;">
        <h2>🏟️ League Portal 🏟️</h2>
    </div>
    """,
    unsafe_allow_html=True,
)

# Initialize Session State Defaults
if "tournaments" not in st.session_state:
    st.session_state["tournaments"] = {}

if "selected_tab" not in st.session_state:
    st.session_state["selected_tab"] = "Create League"

if "expander_open" not in st.session_state:
    st.session_state["expander_open"] = True


# Main Navigation Buttons
col1, col2, col3 = st.columns(3)
user_role = st.session_state.get("role", "user")

# Fetch all users once and cache them in session state
if "all_users" not in st.session_state:
    st.session_state["all_users"] = firestore_get_all_users()


# Initialize 'all_leagues' in session_state if not already present
if 'all_leagues' not in st.session_state:
    st.session_state['all_leagues'] = firestore_get_all_leagues()

# Helper function to fetch user ID
def fetch_user_id():
    """Retrieve the user ID based on email if not already in session state."""
    if "user_id" not in st.session_state or not st.session_state["user_id"]:
        user_email = st.session_state.get("email")
        if not user_email:
            st.error("Email not found in session state. Please log in again.", icon="❌")
            st.stop()
        try:
            user_doc = db.collection("users").where("email", "==", user_email).get()
            if user_doc:
                st.session_state["user_id"] = user_doc[0].id
            else:
                st.error("Failed to retrieve user ID. Please reauthenticate.", icon="❌")
                st.stop()
        except Exception as e:
            st.error(f"Error retrieving user ID: {e}", icon="❌")
            st.stop()

fetch_user_id()
creator_id = st.session_state["user_id"]

# Use cached users for filtering
all_users = st.session_state["all_users"]
admins = filter_users_by_role(all_users, ["admin", "super_admin"])
players = filter_users_by_role(all_users, ["user"])


# Show buttons but disable unavailable options
with col1:
    setup_button = st.button(
        "🧙 Create League",
        use_container_width=True,
        key="create_leagues_button",
        help="Set up your tournament step-by-step.",
        disabled=user_role != "super_admin",
    )
    if setup_button:
        st.session_state["selected_tab"] = "Create League"

with col2:
    management_button = st.button(
        "👥 Manage Leagues",
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

# Create League Section
if selected_tab == "Create League" and user_role == "super_admin":
    st.markdown(
        """
        <div style='text-align: center; margin-bottom: 20px;'>
            <h2>🖌️ Create a League</h2>
            <p style='font-size: 14px; color: #808080;'>Set up your new league, assign admins, and establish a super admin.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Use session state to track submission status
    if "league_submission_result" not in st.session_state:
        st.session_state["league_submission_result"] = None

    # Create League Form
    with st.form("add_league_form"):
        league_name = st.text_input("League Name", placeholder="Enter league name")
        league_type = st.selectbox("League Type", ["Private", "Public"], index=0)

        if admins:
            selected_admins = st.multiselect(
                "Assign Admins",
                options=list(admins.keys()),
                format_func=lambda x: f"{admins[x]['username']} ({admins[x]['role']})",
            )
        else:
            st.warning("No users available to assign as admins. Please add admins or super admins.")
            selected_admins = []

        submitted = st.form_submit_button("➕ Create League", use_container_width=True)

        if submitted:
            # Validate league name and admin assignment
            if not league_name or not selected_admins:
                st.error("League Name and Admin assignment are required.", icon="❌")
            else:
                # Ensure the creator is included in the admin list
                if creator_id not in selected_admins:
                    selected_admins.append(creator_id)  # Ensure creator is always an admin

                # Validate roles: ensure exactly one super admin, which is the creator
                super_admins = [admin for admin in selected_admins if admins.get(admin, {}).get("role") == "super_admin"]
                if len(super_admins) != 1 or super_admins[0] != creator_id:
                    st.error("Each league must have exactly one super admin, which is the creator.", icon="❌")
                else:
                    # Check if a league with the same name already exists
                    try:
                        existing_leagues = db.collection("leagues").where("league_name", "==", league_name).get()
                        if existing_leagues:
                            st.error(f"A league with the name '{league_name}' already exists. Please choose a different name.", icon="❌")
                        else:
                            # Attempt to create the league
                            try:
                                created_league = firestore_add_league(
                                    league_name=league_name,
                                    league_type=league_type,
                                    created_by=creator_id,
                                    admins=selected_admins,
                                    super_admin=creator_id,
                                )
                                if created_league.get("success"):
                                    # Update session state
                                    new_league_id = created_league["league_id"]
                                    st.session_state["all_leagues"][new_league_id] = {
                                        "league_name": league_name,
                                        "league_type": league_type,
                                        "created_by": creator_id,
                                        "admins": selected_admins,
                                        "super_admin": creator_id,
                                        "members": [],  # No members initially
                                        "created_at": "Just now",  # Placeholder for Firestore's SERVER_TIMESTAMP
                                    }
                                    st.success(f"League '{league_name}' created successfully!", icon="✅")
                                else:
                                    st.error(created_league.get("message", "Unexpected issue while creating the league."), icon="❌")
                            except Exception as e:
                                st.error(f"Error creating league: {e}", icon="❌")
                    except Exception as e:
                        st.error(f"Error checking for existing leagues: {e}", icon="❌")

    st.markdown("---")

    # Leagues Overview Section
    st.markdown(
        """
        <div style='text-align: center; margin-bottom: 20px;'>
            <h3>📋 Manage League Admins</h3>
            <p style='font-size: 14px; color: #808080;'>Easily view leagues and manage their admin associations.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Use cached leagues and users
    leagues = st.session_state.get("all_leagues", {})
    users = st.session_state.get("all_users", {})

    if leagues:
        # Display leagues in a collapsible table
        st.markdown("#### Leagues Overview")
        with st.expander("📋 View Existing Leagues", expanded=False):
            # Prepare league data for display
            league_data = [
                {
                    "League Name": league.get("league_name", "Unknown"),
                    "League Type": league.get("league_type", "Unknown").capitalize(),
                    "Super Admin": users.get(league.get("super_admin", ""), {}).get("username", "Unassigned"),
                    "Admins": ", ".join(
                        [users.get(admin, {}).get("username", "Unknown") for admin in league.get("admins", [])]
                    ),
                    "Created At": league.get("created_at", "N/A"),
                }
                for league in leagues.values()
            ]
            st.dataframe(pd.DataFrame(league_data), use_container_width=True)

        st.markdown("---")
        st.markdown("#### Manage League Admins")

        # Select League to Manage
        selected_league_id = st.selectbox(
            "Select League to Manage",
            options=list(leagues.keys()),
            format_func=lambda x: leagues[x].get("league_name", "Unknown"),
        )

        if selected_league_id:
            selected_league = leagues[selected_league_id]
            current_admins = selected_league.get("admins", [])
            current_super_admin = selected_league.get("super_admin", "")

            st.markdown(
                f"""
                <div style="
                    border: 1px solid #444; 
                    border-radius: 8px; 
                    padding: 16px; 
                    margin-bottom: 16px; 
                    background-color: #222;">
                    <h4 style="margin: 0; color: #fff;">🏆 League Details</h4>
                    <p style="color: #ddd;"><strong>League Name:</strong> {selected_league.get('league_name', 'Unknown')}</p>
                    <p style="color: #ddd;"><strong>League Type:</strong> {selected_league.get('league_type', 'Unknown').capitalize()}</p>
                    <p style="color: #ddd;"><strong>Super Admin:</strong> {users.get(current_super_admin, {}).get('username', 'Unassigned')}</p>
                    <p style="color: #ddd;"><strong>Current Admins:</strong> {", ".join([users.get(admin, {}).get("username", "Unknown") for admin in current_admins])}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Update Admin Associations
            selected_new_admins = st.multiselect(
                "Add or Remove Admins",
                options=list(users.keys()),
                format_func=lambda x: f"{users[x]['username']} ({users[x]['role']})",
                default=current_admins,
            )

            if st.button("Update Admins"):
                try:
                    # Ensure the super admin remains in the admin list
                    if current_super_admin not in selected_new_admins:
                        st.error("The super admin cannot be removed from the admin list.", icon="❌")
                    else:
                        # Only update if there are changes
                        if set(current_admins) != set(selected_new_admins):
                            result = firestore_update_league_admins(selected_league_id, selected_new_admins)
                            if result["success"]:
                                # Update local session state for immediate feedback
                                selected_league["admins"] = selected_new_admins
                                st.session_state["all_leagues"][selected_league_id] = selected_league
                                st.success(result["message"], icon="✅")
                            else:
                                st.error(result["message"], icon="❌")
                        else:
                            st.info("No changes detected in the admin list.", icon="ℹ️")
                except Exception as e:
                    st.error(f"Error updating admins: {e}", icon="❌")
    else:
        st.warning("No leagues found for your account. Please create a league first.")





elif selected_tab == "Manage Leagues" and user_role in ["super_admin", "admin"]:
    st.markdown(
        """
        <div style='text-align: center; margin-bottom: 20px;'>
            <h2 style='margin-bottom: 0px;'>👥 Manage Leagues</h2>
            <p style='font-size: 14px; color: #808080;'>View and update league details, and manage player associations.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Fetch leagues and filter by current user
    leagues_ref = db.collection("leagues").get()
    leagues = {
        league.id: league.to_dict() for league in leagues_ref
        if st.session_state.user_id in league.to_dict().get("admins", [])
        or league.to_dict().get("super_admin") == st.session_state.user_id
    }

    # Fetch all users from Firestore
    try:
        users_ref = db.collection("users").get()
        users = {user.id: user.to_dict() for user in users_ref}
    except Exception as e:
        st.error(f"Error fetching users: {e}", icon="❌")
        users = {}

    if leagues and users:
        # Select a league to manage
        selected_league_id = st.selectbox(
            "Select League",
            options=list(leagues.keys()),
            format_func=lambda x: leagues[x]["league_name"],
        )

        if selected_league_id:
            selected_league = leagues[selected_league_id]
            current_admins = selected_league.get("admins", [])
            current_super_admin = selected_league.get("super_admin")
            current_members = selected_league.get("members", []) or []

            # Display league details in a mobile-friendly card
            with st.container():
                st.markdown(
                    f"""
                    <div style="
                        border: 1px solid #444;
                        border-radius: 8px;
                        padding: 16px;
                        margin-bottom: 16px;
                        background-color: #222;
                        color: #fff;
                    ">
                        <h4 style="margin: 0;">🏆 <strong>{selected_league.get('league_name', 'Unknown')}</strong></h4>
                        <hr style="border: none; border-top: 1px solid #555; margin: 8px 0;">
                        <p><strong>League Type:</strong> {selected_league.get('league_type', 'Unknown').capitalize()}</p>
                        <p><strong>Creator:</strong> {users.get(current_super_admin, {}).get('username', 'Unassigned')}</p>
                        <p><strong>Admins:</strong> {", ".join([users.get(admin, {}).get("username", "Unknown") for admin in current_admins]) if current_admins else "No admins assigned."}</p>
                        <p><strong>Players in League:</strong> {len(current_members)}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Display Current Players
            with st.expander("👥 View Current Players", expanded=False):
                if current_members:
                    for player_id in current_members:
                        player_data = users.get(player_id, {})
                        st.markdown(
                            f"**{player_data.get('username', 'Unknown')}** - {player_data.get('email', 'N/A')}"
                        )
                else:
                    st.markdown("No players assigned to this league.")

            # Add Players Section
            with st.expander("➕ Add Players to League", expanded=False):
                # Filter available players (those not already in the league)
                available_players = [
                    user_id for user_id, user_data in users.items()
                    if selected_league_id not in (user_data.get("league_id", []) or [])
                ]

                # Multiselect to choose players to add
                selected_new_players = st.multiselect(
                    "Select Players to Add",
                    options=available_players,
                    format_func=lambda x: f"{users[x]['username']} ({users[x]['email']})",
                )

                if st.button("Add Players"):
                    if not selected_new_players:
                        st.warning("No players selected. Please select players to add.", icon="⚠️")
                    else:
                        try:
                            # Cache current members for Firestore writes
                            league_ref = db.collection("leagues").document(selected_league_id)
                            league_data = league_ref.get().to_dict()
                            current_members = league_data.get("members", {})
                            
                            # Ensure `current_members` is a dictionary
                            if isinstance(current_members, list):
                                current_members = {player_id: "" for player_id in current_members}  # Default empty names

                            current_members_set = set(current_members.keys())

                            # Identify duplicates and new players
                            selected_players_set = set(selected_new_players)
                            duplicates = selected_players_set & current_members_set
                            valid_new_players = selected_players_set - current_members_set

                            if duplicates:
                                duplicate_names = [users[player_id]["username"] for player_id in duplicates]
                                st.warning(
                                    f"The following players are already in the league and will not be added: {', '.join(duplicate_names)}",
                                    icon="⚠️",
                                )

                            if not valid_new_players:
                                st.warning("No new players to add. All selected players are already in the league.", icon="ℹ️")
                            else:
                                # Prepare Firestore updates
                                batch = db.batch()
                                update_log = {}

                                # Update league members
                                for player_id in valid_new_players:
                                    user_data = users[player_id]
                                    user_name = user_data.get("username", "Unknown User")
                                    current_members[player_id] = user_name
                                    update_log[player_id] = user_name

                                # Add batch updates for league members
                                batch.update(league_ref, {"members": current_members})

                                # Update user league memberships
                                for player_id in valid_new_players:
                                    user_ref = db.collection("users").document(player_id)
                                    user_league_list = users[player_id].get("league_id", [])
                                    user_league_list.append(selected_league_id)
                                    batch.update(user_ref, {"league_id": user_league_list})

                                # Commit the batch
                                batch.commit()

                                # Update session state
                                st.session_state["all_leagues"][selected_league_id]["members"] = current_members

                                st.success("Players successfully added to the league!", icon="✅")
                                st.write("The following players were added:")
                                for user_id, username in update_log.items():
                                    st.write(f"- {username} (ID: {user_id})")

                        except Exception as e:
                            st.error(f"Error adding players to league: {e}", icon="❌")


            # Remove Players Section
            with st.expander("➖ Remove Players from League", expanded=False):
                try:
                    # Cache current members for Firestore writes
                    league_ref = db.collection("leagues").document(selected_league_id)
                    league_data = league_ref.get().to_dict()
                    current_members = league_data.get("members", {})

                    # Ensure `current_members` is a dictionary
                    if isinstance(current_members, list):
                        current_members = {player_id: "" for player_id in current_members}  # Default empty names

                    if not current_members:
                        st.info("No players currently in this league.", icon="ℹ️")
                    else:
                        selected_remove_players = st.multiselect(
                            "Select Players to Remove",
                            options=current_members.keys(),
                            format_func=lambda x: f"{users.get(x, {}).get('username', 'Unknown')} ({users.get(x, {}).get('email', 'N/A')})",
                        )

                        if st.button("Remove Players"):
                            if not selected_remove_players:
                                st.warning("No players selected. Please select players to remove.", icon="⚠️")
                            else:
                                try:
                                    current_members_set = set(current_members.keys())

                                    # Identify players to remove
                                    selected_remove_set = set(selected_remove_players)
                                    valid_remove_players = selected_remove_set & current_members_set

                                    if not valid_remove_players:
                                        st.warning("None of the selected players are currently in the league.", icon="⚠️")
                                    else:
                                        # Prepare Firestore updates
                                        batch = db.batch()
                                        update_log = []

                                        # Update league members
                                        for player_id in valid_remove_players:
                                            current_members.pop(player_id, None)
                                            update_log.append(users.get(player_id, {}).get("username", "Unknown User"))

                                        # Add batch update for league members
                                        batch.update(league_ref, {"members": current_members})

                                        # Update user league memberships
                                        for player_id in valid_remove_players:
                                            user_ref = db.collection("users").document(player_id)
                                            user_league_list = users.get(player_id, {}).get("league_id", [])
                                            if selected_league_id in user_league_list:
                                                user_league_list.remove(selected_league_id)
                                                batch.update(user_ref, {"league_id": user_league_list})

                                        # Commit the batch
                                        batch.commit()

                                        # Update session state
                                        st.session_state["all_leagues"][selected_league_id]["members"] = current_members

                                        st.success("Players successfully removed from the league!", icon="✅")
                                        st.write("The following players were removed:")
                                        for username in update_log:
                                            st.write(f"- {username}")

                                except Exception as e:
                                    st.error(f"Error removing players from league: {e}", icon="❌")
                except Exception as e:
                    st.error(f"Error fetching league data: {e}", icon="❌")



    else:
        if not leagues:
            st.warning("No leagues found for your account.")
        if not users:
            st.warning("No users found in the system. Please ensure users exist in the database.")


elif selected_tab == "Search Leagues":
    st.markdown(
        """
        <div style='text-align: center; margin-bottom: 20px;'>
            <h2 style='margin-bottom: 0px;'>🔍 Search Leagues</h2>
            <p style='font-size: 14px; color: #808080;'>Find leagues, view details, and join public leagues.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Initialize refresh-related session state variables
    if "last_refresh_time" not in st.session_state:
        st.session_state["last_refresh_time"] = 0
    if "all_leagues" not in st.session_state:
        st.session_state["all_leagues"] = firestore_get_all_leagues()

    # Refresh Button with Cooldown
    cooldown = 60  # Cooldown in seconds
    can_refresh = time.time() - st.session_state["last_refresh_time"] >= cooldown

    if st.button("🔄 Refresh Leagues", disabled=not can_refresh, use_container_width=True):
        if can_refresh:
            st.session_state["all_leagues"] = firestore_get_all_leagues()
            st.session_state["last_refresh_time"] = time.time()
            st.success("Leagues refreshed successfully!", icon="✅")
        else:
            remaining_time = cooldown - int(time.time() - st.session_state["last_refresh_time"])
            st.warning(f"Please wait {remaining_time} seconds before refreshing again.", icon="⏳")

    # Fetch current user details
    current_user_data = firestore_get_user(st.session_state.user_id)
    user_leagues = current_user_data.get("league_id", [])
    leagues = st.session_state["all_leagues"]

    if not leagues:
        st.warning("No leagues available. Please try again later.")
        st.stop()

    # Section: Leagues the User Belongs To
    with st.expander("🎮 Your Leagues", expanded=False):
        if not leagues or not user_leagues:  # Handle empty `leagues` or `user_leagues`
            st.info("You are not currently a member of any leagues.")
        else:
            user_league_data = {
                league_id: league_data
                for league_id, league_data in leagues.items()
                if league_id in user_leagues
            }

            if user_league_data:  # Check if `user_league_data` has entries
                for league_id, league_data in user_league_data.items():
                    st.markdown(
                        f"""
                        <div style="
                            border: 1px solid #444;
                            border-radius: 8px;
                            padding: 16px;
                            margin-bottom: 16px;
                            background-color: #222;
                            color: #fff;
                        ">
                            <h4 style="margin: 0;">🏆 <strong>{league_data['league_name']}</strong></h4>
                            <p style="margin: 8px 0;"><strong>League Type:</strong> {league_data['league_type'].capitalize()}</p>
                            <p style="margin: 8px 0;"><strong>Members:</strong> {len(league_data.get('members', []))}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            else:
                st.info("You are not currently a member of any leagues.")


    st.markdown("---")

    # Section: Public Leagues
    with st.expander("🌐 Browse Public Leagues", expanded=True):
        st.markdown(
            """
            <div style='text-align: center; margin-bottom: 10px;'>
                <h4 style='margin-bottom: 0px;'>➕ Join a Public League</h4>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Ensure `user_leagues` is initialized as an empty list if it is None
        user_leagues = user_leagues or []

        # Check if `leagues` exists and is not empty
        if not leagues:
            st.info("No public leagues are available at the moment.")
        else:
            # Enhanced Filtering Logic
            public_leagues = {
                league_id: league_data
                for league_id, league_data in leagues.items()
                if league_data.get("league_type", "").lower() == "public"  # Handle case sensitivity
                and league_id not in user_leagues
            }

            if public_leagues:
                selected_league_id = st.selectbox(
                    "Select a Public League to Join",
                    options=list(public_leagues.keys()),
                    format_func=lambda x: public_leagues[x]["league_name"],
                )

                if selected_league_id:
                    league_data = public_leagues[selected_league_id]

                    # Display league details in a card
                    st.markdown(
                        f"""
                        <div style="
                            border: 1px solid #444;
                            border-radius: 8px;
                            padding: 16px;
                            margin-bottom: 16px;
                            background-color: #222;
                            color: #fff;
                        ">
                            <h4 style="margin: 0;">🏆 <strong>{league_data['league_name']}</strong></h4>
                            <p style="margin: 8px 0;"><strong>League Type:</strong> {league_data['league_type'].capitalize()}</p>
                            <p style="margin: 8px 0;"><strong>Members:</strong> {len(league_data.get('members', []))}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    # Join button
                    if st.button(f"Join {league_data['league_name']}", key=f"join_{selected_league_id}"):
                        try:
                            # Check if the user is already in the league
                            if selected_league_id in user_leagues:
                                st.info(f"You are already a member of {league_data['league_name']}.", icon="ℹ️")
                                st.stop()

                            # Add the league to the user's `league_id` list
                            updated_user_leagues = user_leagues.copy() if isinstance(user_leagues, list) else []
                            updated_user_leagues.append(selected_league_id)

                            firestore_batch_update_users(
                                {st.session_state.user_id: {"league_id": updated_user_leagues}}
                            )

                            # Add the user to the league's `members` list
                            result = firestore_add_players_to_league(selected_league_id, [st.session_state.user_id])

                            if result["success"]:
                                # Update session state and success message
                                st.session_state["user_data"]["league_id"] = updated_user_leagues
                                st.success(f"You have joined {league_data['league_name']}!", icon="✅")
                            else:
                                st.error(result["message"], icon="❌")
                        except Exception as e:
                            st.error(f"Error joining league: {e}", icon="❌")
            else:
                st.info("No public leagues available for you to join.", icon="ℹ️")

else:
    st.warning("No leagues found.")