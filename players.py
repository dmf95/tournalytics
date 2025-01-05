import streamlit as st
from utils.data_utils import load_player_data_local, insert_player_data


# App branding
st.title("🏃 Player Management 🏃")
st.subheader("Manage player rosters efficiently")

# Display existing players
st.markdown("---")
st.subheader("Current Players")
try:
    players = load_player_data_local()
    if not players.empty:
        st.dataframe(players, use_container_width=True)
    else:
        st.info("No players found. Start by adding a new player!")
except Exception as e:
    st.error(f"Failed to load player data: {e}")

# Add new player
st.markdown("---")
st.subheader("Add a New Player")
with st.form("add_player_form"):
    first_name = st.text_input("First Name", placeholder="Enter first name")
    last_name = st.text_input("Last Name", placeholder="Enter last name")
    team_name = st.text_input("Team Name", placeholder="Enter team name")
    submitted = st.form_submit_button("Add Player")

    if submitted:
        if first_name and last_name:
            try:
                data = [{"first_name": first_name, "last_name": last_name, "team_name": team_name}]
                insert_player_data(data)
                st.success(f"Player '{first_name} {last_name}' added successfully!")
            except Exception as e:
                st.error(f"Failed to add player: {e}")
        else:
            st.error("First Name and Last Name are required fields.")

# Footer branding
st.markdown("---")
st.write("💡 Use this page to manage players and their respective teams efficiently.")

