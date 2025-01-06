import streamlit as st
from utils.data_utils import load_player_data_local, insert_new_player_data
import random
import pandas as pd

# Page Configuration for Mobile-First Design
st.set_page_config(
    page_title="Players",
    page_icon="👤",
    layout="centered",  # Optimized for mobile
    initial_sidebar_state="collapsed"
)

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
        <p style='font-size: 14px; color: #808080;'>Manage existing Tournament Players.</p>
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

            if existing_players is not None:
                # Ensure "id" column exists
                if "id" not in existing_players.columns:
                    existing_players["id"] = None  # Initialize "id" column with None

                existing_full_names = (
                    existing_players["first_name"] + " " + existing_players["last_name"]
                ).tolist()
            else:
                existing_full_names = []

            if full_name in existing_full_names:
                st.error(f"Player '{full_name}' already exists in current players.", icon="❌")
            else:
                # Generate a unique ID
                existing_ids = existing_players["id"].dropna().tolist() if existing_players is not None else []
                player_id = generate_unique_player_id(existing_ids)

                # Add the new player with the "custom" source
                new_player = pd.DataFrame(
                    [{
                        "id": player_id,
                        "first_name": first_name,
                        "last_name": last_name,
                        "source": "custom",
                    }]
                )

                if st.session_state["players"] is None or st.session_state["players"].empty:
                    st.session_state["players"] = new_player
                else:
                    st.session_state["players"] = pd.concat(
                        [st.session_state["players"], new_player], ignore_index=True
                    )

                try:
                    insert_new_player_data(new_player.drop(columns=["source"]).to_dict(orient="records"))  # Persist without "source"
                    st.success(f"Player '{full_name}' added successfully with ID {player_id}!", icon="✅")
                except Exception as e:
                    st.error(f"Failed to add player: {e}", icon="❌")
        else:
            st.error("First Name and Last Name are required fields.", icon="❌")


# Add divider
st.markdown("---")

# Display Current Players in an Expander
import pandas as pd

# Display Current Players in an Expander
with st.expander("📋 View Current Players", expanded=False):
    if st.session_state["players"] is not None and not st.session_state["players"].empty:
        # Dynamically add the "source" column within the app
        players_with_source = st.session_state["players"].copy()

        # Add a source column: Default for preloaded, Custom for session-added
        if "source" not in players_with_source.columns:
            players_with_source["source"] = "default"  # Default for all preloaded players
        else:
            # Ensure any new players marked as "custom" are retained
            players_with_source.loc[players_with_source["source"].isnull(), "source"] = "custom"

        # Rename columns for display
        display_players = players_with_source.rename(
            columns={
                "id": "ID",
                "first_name": "First",
                "last_name": "Last",
                "source": "Source",
            }
        )

        # Display the interactive dataframe
        st.dataframe(
            display_players,
            use_container_width=True,
            height=400,
            hide_index=True
        )

        # Provide user guidance
        st.write("🔍 Use column headers to sort or search for specific players.")
    else:
        st.info("No players found. Start by adding a new player!", icon="ℹ️")



# Display Footer
st.markdown("---")
st.markdown(
    "💡 Use this page to manage your player rosters efficiently. Check the current roster above and add new players below."
)
