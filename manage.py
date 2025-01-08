import streamlit as st
import pandas as pd
from utils.data_utils import load_player_data_local, insert_new_player_data
import random

# Helper function to generate a unique 9-digit ID
def generate_unique_player_id(existing_ids):
    while True:
        random_id = random.randint(100_000_000, 999_999_999)  # Generate a 9-digit number
        if random_id not in existing_ids:
            return random_id

def to_snake_case(name):
    """
    Converts a name to Snake Case format: First letters capitalized, rest lowercase.
    Example: "john DOE" -> "John Doe"
    """
    return " ".join([word.capitalize() for word in name.split()])

# Load and process player data
if "players" not in st.session_state:
    try:
        # Load players and add "source" column for default players
        loaded_players = load_player_data_local("assets/players.csv")
        loaded_players["source"] = "default"
        st.session_state["players"] = loaded_players
    except Exception as e:
        st.session_state["players"] = None
        st.error(f"Failed to load player data: {e}", icon="❌")


# App Branding
st.markdown(
    """
    <div style='text-align: center; margin-bottom: 20px;'>
        <h2 style='margin-bottom: 0px;'>👤 Manage Players</h2>
        <p style='font-size: 14px; color: #808080;'>Manage existing Tournament Players</p>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown("---")

# Add New Player Section
st.markdown(
    """
    <div style='text-align: center; margin-bottom: 20px;'>
        <h3 style='margin-bottom: 0px;'>➕ Add a New Player</h3>
    </div>
    """,
    unsafe_allow_html=True,
)
with st.form("add_player_form"):
    st.write("Fill out the form to add new players.")
    first_name = st.text_input("First Name", placeholder="Enter first name")
    last_name = st.text_input("Last Name", placeholder="Enter last name")
    submitted = st.form_submit_button("➕ Add Player", use_container_width=True)

    if submitted:
        if first_name and last_name:
            # Process names into Snake Case
            first_name = to_snake_case(first_name)
            last_name = to_snake_case(last_name)

            # Check for duplicate full name
            full_name = f"{first_name} {last_name}"
            existing_players = st.session_state["players"]

            # Check if full_name already exists
            if isinstance(existing_players, list):
                existing_full_names = existing_players
            elif isinstance(existing_players, pd.DataFrame):
                existing_full_names = (
                    existing_players["first_name"] + " " + existing_players["last_name"]
                ).tolist()
            else:
                existing_full_names = []

            if full_name in existing_full_names:
                st.error(f"Player '{full_name}' already exists in current players.", icon="❌")
            else:
                # Add the new player to the session state
                if isinstance(st.session_state["players"], list):
                    st.session_state["players"].append(full_name)
                elif isinstance(st.session_state["players"], pd.DataFrame):
                    # Generate a unique ID for DataFrame case
                    existing_ids = st.session_state["players"]["id"].dropna().tolist()
                    player_id = generate_unique_player_id(existing_ids)

                    new_player = pd.DataFrame(
                        [{
                            "id": player_id,
                            "first_name": first_name,
                            "last_name": last_name,
                            "source": "custom",
                        }]
                    )
                    st.session_state["players"] = pd.concat(
                        [st.session_state["players"], new_player], ignore_index=True
                    )
                else:
                    # Initialize as a list if previously uninitialized
                    st.session_state["players"] = [full_name]

                st.success(f"Player '{full_name}' added successfully!", icon="✅")
        else:
            st.error("First Name and Last Name are required fields.", icon="❌")

# Add divider
st.markdown("---")

# Display Current Players in an Expander
with st.expander("📋 View Current Players", expanded=False):
    # Heading for the section
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 0px;">
            <h3 style="margin: 0; font-size: 1.2em;">🎮 Current Player Roster</h3>
            <p style="color: #aaa; font-size: 0.9em; margin-top: 0px;">
                Review and manage the players in your league.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if isinstance(st.session_state["players"], pd.DataFrame) and not st.session_state["players"].empty:
        # Players stored as a DataFrame
        players_with_source = st.session_state["players"].copy()

        # Ensure "source" column is available and populated
        if "source" not in players_with_source.columns:
            players_with_source["source"] = "default"
        else:
            players_with_source.loc[players_with_source["source"].isnull(), "source"] = "custom"

        # Rename columns for better display
        display_players = players_with_source.rename(
            columns={
                "id": "ID",
                "first_name": "First Name",
                "last_name": "Last Name",
                "source": "Source",
            }
        )

        # Highlight "Custom" players for better UX
        display_players["Source"] = display_players["Source"].apply(
            lambda x: "🛠️ Custom" if x == "custom" else "📦 Default"
        )

        # Display players in an interactive table
        st.dataframe(
            display_players,
            use_container_width=True,
            height=400,
            hide_index=True,
        )

        # User guidance
        st.markdown(
            """
            <div style="text-align: center; margin-top: 10px; color: #aaa; font-size: 0.85em;">
                Tip: Use column headers to sort or search for specific players.
            </div>
            """,
            unsafe_allow_html=True,
        )

    elif isinstance(st.session_state["players"], list) and st.session_state["players"]:
        # Players stored as a list
        st.markdown(
            """
            <style>
            ul.player-list {
                list-style-type: none;
                padding: 0;
                margin: 0;
            }
            ul.player-list li {
                background: #444;
                margin: 5px 0;
                padding: 10px;
                border-radius: 8px;
                color: white;
                font-size: 1em;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<ul class='player-list'>", unsafe_allow_html=True)
        for player in st.session_state["players"]:
            st.markdown(f"<li>🎮 {player}</li>", unsafe_allow_html=True)
        st.markdown("</ul>", unsafe_allow_html=True)

        # User guidance
        st.markdown(
            """
            <div style="text-align: center; margin-top: 10px; color: #aaa; font-size: 0.85em;">
                Tip: Tap on a player name to view their details in the future.
            </div>
            """,
            unsafe_allow_html=True,
        )

    else:
        # No players found
        st.markdown(
            """
            <div style="text-align: center; margin-top: 20px;">
                <p style="color: #aaa; font-size: 1em;">
                    🚨 No players found. Start by adding new players using the form above.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )



# Display Footer
st.markdown("---")
st.markdown(
    "💡 Use this page to manage your player rosters efficiently. Check the current roster above and add new players below."
)
