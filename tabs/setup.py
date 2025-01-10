import streamlit as st
import pandas as pd
from utils.general_utils import generate_unique_id
from utils.data_utils import load_player_data_local, firestore_get_leagues, create_league_mapping
from utils.tournament_utils import estimate_tournament_duration


def update_current_step():
    """Updates the current step based on the progress flags."""
    steps = [
        st.session_state["create_complete"],
        st.session_state["setup_complete"],
        st.session_state["players_selected"],
        st.session_state["finish_generated"],
    ]
    st.session_state["current_step"] = sum(steps)

def render_start_over_button(tab):
    """
    Renders a "Start Over" button to reset the tournament setup process.
    """
    # Divider and Text
    st.markdown("---")  # Divider
    st.markdown(
        """
        <div style='text-align: center;'>
            <strong>Not satisfied with the setup?</strong><br>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Button
    start_over_button = st.button("🔄 Start Over", key=f"start_over_{tab}", use_container_width=True)
    
    # Logic for Reset
    if start_over_button:
        # Clear only tournament-related session state variables
        keys_to_clear = [
            "tournament_name",
            "league_name",
            "league_id",
            "event_date",
            "league_format",
            "playoff_format",
            "tournament_type",
            "num_players",
            "num_consoles",
            "half_duration",
            "players_selected",
            "selected_players",
            "team_selection",
            "create_complete",
            "setup_complete",
            "finish_generated",
            "current_step",
            "active_tab",
            "tournament_ready",
        ]
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        # Reinitialize necessary session state variables
        st.session_state["tournaments"] = {}
        st.session_state["create_complete"] = False
        st.session_state["setup_complete"] = False
        st.session_state["players_selected"] = False
        st.session_state["finish_generated"] = False
        st.session_state["current_step"] = 0
        st.session_state["active_tab"] = "🛠️ 01 Create"

        # Rerun the script
        st.success("Setup has been reset. You can start over!", icon="🔄")
        st.rerun()

def render():
    # Initialize session state for progress tracking
    if "create_complete" not in st.session_state:
        st.session_state["create_complete"] = False
    if "setup_complete" not in st.session_state:
        st.session_state["setup_complete"] = False
    if "players_selected" not in st.session_state:
        st.session_state["players_selected"] = False
    if "finish_generated" not in st.session_state:
        st.session_state["finish_generated"] = False
    if "current_step" not in st.session_state:
        st.session_state["current_step"] = 0
    if "tournaments" not in st.session_state:
        st.session_state["tournaments"] = {}  # Initialize tournaments storage
    if "player_names" not in st.session_state:
        st.session_state["player_names"] = [f"Player {i}" for i in range(1, 13)]  # Default players
    if "num_consoles" not in st.session_state:
        st.session_state["num_consoles"] = 2  # Default value
    if "half_duration" not in st.session_state:
        st.session_state["half_duration"] = 5  # Default value

    # Define progress steps and calculate progress
    progress_steps = ["Create", "Setup", "Players", "Finish"]
    update_current_step()
    progress_percentage = int(
        ((st.session_state["current_step"] + 1) / len(progress_steps)) * 100
    )
    progress_percentage = min(max(progress_percentage, 0), 100)  # Ensure bounded values

    # Render Progress Bar
    st.markdown(
        """
        <style>
        .progress-bar-container {
            background-color: #f5f5f5;
            border: 1px solid #ddd;
            border-radius: 5px;
            width: 100%;
            height: 20px;
            margin-bottom: 20px;
        }
        .progress-bar {
            background-color: #4CAF50;
            height: 100%;
            border-radius: 5px;
            transition: width 0.4s ease;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    step_label = (
        f"Step {st.session_state['current_step'] + 1} of {len(progress_steps)}: {progress_steps[st.session_state['current_step']]}"
        if st.session_state["current_step"] < len(progress_steps)
        else "Complete"
    )
    st.markdown(
        f"""
        <div class="progress-bar-container">
            <div class="progress-bar" style="width: {progress_percentage}%;"></div>
        </div>
        <div style="text-align:center; margin-top:-15px; font-size:14px;">
            {step_label}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Tabs for Setup
    tab_create, tab_setup, tab_players, tab_finish = st.tabs(
        ["🛠️ 01 Create", "⚙️ 02 Setup", "👤 03 Players", "🎉 04 Finish"]
    )

    # Check if user has league_ids
    if st.session_state['user_data'].get("league_ids", []):
        # Fetch league names from Firestore
        league_ids = st.session_state['user_data']['league_ids']
        league_catalog = firestore_get_leagues(league_ids)
        league_mapping = create_league_mapping(league_catalog)
        
        # Store the league mapping in session state
        st.session_state['league_mapping'] = league_mapping
        st.session_state['leagues_catalog'] = league_catalog

        # Store only league names in user_data if needed
        st.session_state['user_data']['league_names'] = list(league_mapping.values())

        # Create Tab
        with tab_create:
            st.markdown(
                """
                <div style='text-align: center; margin-bottom: 20px;'>
                    <h3 style='margin-bottom: 5px;'>🎮 Create Tournament</h3>
                    <p style='font-size: 14px; color: #808080;'>Enter the tournament details to get started.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # League Selection Dropdown
            st.session_state["league_name"]  = st.selectbox(
                "Select League",
                options=["Select a league"] + st.session_state['user_data']['league_names'],
                key="select_league",
                help="Choose the league to associate with this tournament.",
            )

            # Tournament Name Input
            st.session_state["tournament_name"] = st.text_input(
                "Tournament Name",
                value=st.session_state['user_data'].get("tournament_name", ""),
                key="create_tournament_name",
                placeholder="Enter a unique tournament name",
            )

            # Event Date Input
            event_date = st.date_input(
                "Event Date",
                key="create_event_date",
                help="Select the date of the tournament.",
            )

            # Proceed Button with Icon
            proceed_button = st.button(
                "🚀 Proceed to Setup",
                key="proceed_to_setup",
                use_container_width=True,
            )

            # Logic for Proceed Button
            if proceed_button:
                if st.session_state.get("league_name") == "Select a league":
                    st.error("You must select a league to associate this tournament.", icon="❌")
                elif not st.session_state["tournament_name"]:
                    st.error("Tournament Name cannot be empty.", icon="❌")
                elif not event_date:
                    st.error("Event Date must be selected.", icon="❌")
                else:
                    st.session_state["league_id"] = next(
                        (key for key, value in st.session_state['league_mapping'].items() if value == st.session_state["league_name"]), 
                        None
                    )
                    st.session_state["create_complete"] = True
                    st.session_state["event_date"] = event_date
                    st.success(f"Tournament created successfully in {st.session_state.get('league_name')}! Proceed to Setup.", icon="✅")


            # Add Start Over Button
            render_start_over_button(tab="setup_create")
    else:
        # If no league_id, lock the page
        st.markdown(
            """
            <div style='text-align: center; margin-top: 50px;'>
                <h3 style='margin-bottom: 10px; color: #808080;'>🔒 Locked</h3>
                <p style='font-size: 14px; color: #ccc;'>You need to join a league to create a tournament.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


    # General Setup Tab
    with tab_setup:
        st.markdown(
            """
            <div style='text-align: center; margin-bottom: 20px;'>
                <h3 style='margin-bottom: 5px;'>⚙️ General Setup</h3>
                <p style='font-size: 14px; color: #808080;'>Define tournament setup settings.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not st.session_state["create_complete"]:
            st.warning(
                "Complete the Create step first to unlock this tab.", icon="🔒"
            )
        else:
            
            # Tournament Type
            league_format = st.selectbox(
                "Select League Format",
                ["Play-Everyone"],
                help="Choose how league games are scheduled. Currently, the default is 'Play-Everyone,' where each team plays all others once.",
            )

            # Playoff Format
            playoff_format = st.selectbox(
                "Select Playoff Format",
                ["Double-Elimination", "Single-Elimination"],
                help="Decide how playoff games are structured. The top 6 league teams advance to playoffs: top 2 receive byes, and the next 4 compete in wildcard games.",
            )

            col1, col2 = st.columns(2, gap="medium")

            with col1:
                st.session_state["num_players"] = st.slider(
                    "Number of Players",
                    min_value=6,
                    max_value=12,
                    value=6,
                    key="setup_num_players",
                )

            with col2:
                st.session_state["num_consoles"] = st.slider(
                    "Number of Consoles",
                    min_value=1,
                    max_value=4,
                    value=2,
                    key="setup_num_consoles",
                )

            st.session_state["half_duration"] = st.slider(
                "Select Half Duration",
                min_value=4,
                max_value=6,
                value=5,
                key="setup_half_duration",
            )

            # Proceed Button
            proceed_button = st.button(
                "🚀 Proceed to Player Setup",
                key="proceed_to_players",
                use_container_width=True,
            )

            if proceed_button:
                st.session_state["setup_complete"] = True
                st.session_state["league_format"] = league_format
                st.session_state["playoff_format"] = playoff_format
                st.session_state["tournament_type"] =  f'League ({st.session_state["num_players"]}-Team-{league_format}) Playoffs (6-Team-{playoff_format})'
                st.success(
                    "General Setup completed! Proceed to the next step.", icon="✅"
                )


            # Add Start Over Button
            render_start_over_button(tab='setup_general')


    # Player Selection
    with tab_players:
        st.markdown(
            """
            <div style='text-align: center; margin-bottom: 20px;'>
                <h3 style='margin-bottom: 5px;'>👤 Player Setup</h3>
                <p style='font-size: 14px; color: #808080;'>Select players and assign teams.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not st.session_state.get("setup_complete", False):
            st.warning(
                "Complete the General Setup step first to unlock this tab.", icon="🔒"
            )
        else:
            # Load and process player data
            if "players" not in st.session_state or st.session_state["players"] is None:
                try:
                    # Ensure league_id is selected and members are available
                    selected_league_id = st.session_state.get("league_id")
                    if not selected_league_id:
                        raise ValueError("No league selected. Please select a league to proceed.")

                    # Fetch league data
                    league_data = league_catalog.get(selected_league_id)
                    if not league_data or "members" not in league_data:
                        raise ValueError("No members found for the selected league.")

                    # Extract player data from the league's members dictionary
                    members = league_data["members"]  # e.g., {"user_id": "username"}
                    players_data = [{"id": user_id, "username": username, "source": "league"} for user_id, username in members.items()]
                    st.session_state["players"] = players_data
                except Exception as e:
                    st.session_state["players"] = None
                    st.error(f"Failed to load player data: {e}", icon="❌")

            # Handle case where player data is missing
            if not st.session_state.get("players"):
                st.error("No players available. Please add players to the league.", icon="❌")
                return

            # Process player data
            players_data = pd.DataFrame(st.session_state["players"])
            # Ensure essential columns exist
            for column, default_value in [("id", None), ("source", "league")]:
                if column not in players_data.columns:
                    players_data[column] = default_value

            # Generate and store player usernames
            player_names = players_data["username"].tolist()
            st.session_state["player_names"] = player_names

            # Player Multiselect
            selected_players = st.multiselect(
                "Select Players",
                options=player_names,
                default=player_names[: st.session_state.get("num_players", len(player_names))],
            )

            # Validate selected players
            num_players_required = st.session_state.get("num_players", len(player_names))
            if len(selected_players) != num_players_required:
                st.error(f"Please select exactly {num_players_required} players.", icon="❌")
                return

            # Assign teams dynamically
            team_selection = {
                player: st.text_input(f"Team for {player}", value=f"Team {player.split()[0]}")
                for player in selected_players
            }

            # Proceed Button with Logic
            if st.button("🚀 Proceed to Finish", key="proceed_to_finish", use_container_width=True):
                st.session_state.update({
                    "players_selected": True,
                    "selected_players": selected_players,
                    "team_selection": team_selection
                })
                st.success("Player Setup completed! Proceed to the Finish.", icon="✅")

            # Add Start Over Button
            render_start_over_button(tab="setup_players")


    # Finish Tab
    with tab_finish:
        st.markdown(
            """
            <div style='text-align: center; margin-bottom: 20px;'>
                <h3 style='margin-bottom: 5px;'>🎉 Finish Tournament Setup</h3>
                <p style='font-size: 14px; color: #808080;'>Save your Tournament setup.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if not st.session_state["players_selected"]:
            st.warning("Complete the Player Selection step first to unlock this tab.", icon="🔒")
        else:
            # Estimate tournament duration
            duration_breakdown = estimate_tournament_duration(
                num_players=st.session_state["num_players"],
                num_consoles=st.session_state["num_consoles"],
                half_duration=st.session_state["half_duration"],
                league_format=st.session_state["league_format"],
                playoff_format=st.session_state["playoff_format"],
            )
            # Collapsible sections for details
            with st.expander("🏆 Tournament Details", expanded=True):
                st.markdown(f"### 🏆 **{st.session_state['tournament_name']}**")
                # Tournament details
                st.write(f"**🏟️ League:** {st.session_state['league_name']}")
                st.write(f"**📅 Date:** {st.session_state['event_date']}")
                st.write(f"**🎯 Type:** {st.session_state['tournament_type']}")
                st.write(f"**🏅 League Format:** {st.session_state['league_format']}")
                st.write(f"**⚔️ Playoff Format:** {st.session_state['playoff_format']}")
                st.write(f"**👥 Players:** {st.session_state['num_players']}")
                st.write(f"**🎮 Consoles:** {st.session_state['num_consoles']}")
                st.write(f"**⏱️ Half Duration:** {st.session_state['half_duration']} minutes")

            with st.expander("⏳ Estimated Duration", expanded=False):
                st.markdown(f"#### **⏳ ~Est: {duration_breakdown['total_hours']} hours & {duration_breakdown['total_minutes']} minutes**")
                # League duration details
                st.markdown("**🏅 League Games**")
                st.write(f"- **Total Games:** {duration_breakdown['total_league_games']} across {duration_breakdown['total_league_rounds']} rounds")
                st.write(f"- **Estimated Duration:** ~{duration_breakdown['total_league_duration']} minutes")
                # Playoff duration details
                st.markdown("**⚔️ Playoff Games**")
                st.write(f"- **Total Games:** {duration_breakdown['total_playoff_games']} across {duration_breakdown['total_playoff_rounds']} rounds")
                st.write(f"- **Estimated Duration:** ~{duration_breakdown['total_playoff_duration']} minutes")
                # Additional time
                st.markdown("**⏱️ Additional Time**")
                st.write(f"- **Team Management Time:** ~{duration_breakdown['team_management_time']} minutes")


            with st.expander("👤 Players & Teams", expanded=False):
                st.markdown(f"### 👤**Player Teams**")
                for player, team in st.session_state["team_selection"].items():
                    st.write(f"- {player}: {team}")

            # Save Tournament Setup Button
            save_button = st.button(
                "💾 Save Tournament Setup", 
                key="save_tournament_setup",
                use_container_width=True,
                )

            if save_button:
                tournament_id = generate_unique_id(id_length = 12, id_type='uuid')
                st.session_state["tournaments"][tournament_id] = {
                    "tournament_name": st.session_state["tournament_name"],
                    "league_id": st.session_state["league_id"],
                    "league_name": st.session_state["league_name"],
                    "event_date": st.session_state["event_date"],
                    "league_format": st.session_state["league_format"],
                    "playoff_format": st.session_state["playoff_format"],
                    "tournament_type": st.session_state["tournament_type"],
                    "num_players": st.session_state["num_players"],
                    "num_consoles": st.session_state["num_consoles"],
                    "half_duration": st.session_state["half_duration"],
                    "selected_players": st.session_state["selected_players"],
                    "team_selection": st.session_state["team_selection"],
                            }
                st.session_state["selected_tournament_id"] = tournament_id
                st.session_state["tournament_ready"] = True
                st.success(f"Tournament setup saved with ID: {tournament_id}",icon="✅") 

            # Add Start Over Button
            render_start_over_button(tab='setup_finish')

