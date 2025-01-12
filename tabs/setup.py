import streamlit as st
import pandas as pd
from utils.general_utils import generate_unique_id
from utils.data_utils import firestore_get_leagues, create_league_mapping
from utils.tournament_utils import (
    estimate_league_duration, 
    estimate_playoff_duration, 
    estimate_tournament_duration
    )


def update_current_step():
    """Updates the current step based on the progress flags."""
    steps = [
        st.session_state["create_complete"],
        st.session_state["setup_complete"],
        st.session_state["games_complete"],
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
            "games_complete",
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
        st.session_state["games_complete"] = False
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
    if "games_complete" not in st.session_state:
        st.session_state["games_complete"] = False
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
    progress_steps = ["Create", "Setup", "Games", "Players", "Finish"]
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
    tab_create, tab_setup, tab_games, tab_players, tab_finish = st.tabs(
        ["🛠️ 01 Create", "⚙️ 02 Format", "🕹️ 03 Games",  "👤 04 Players",  "🎉 05 Finish"]
    )

    # Create Tab
    with tab_create:
        # Header Section
        st.markdown(
            """
            <div style='text-align: center; margin-bottom: 20px;'>
                <h3 style='margin-bottom: 5px;'>🎮 Create Tournament</h3>
                <p style='font-size: 14px; color: #808080;'>Enter the tournament details to get started.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


        if not st.session_state.get("league_mapping"):
            st.markdown(
                """
                <div style='text-align: center; margin-top: 50px;'>
                    <h3 style='margin-bottom: 10px; color: #808080;'>🔒 Locked</h3>
                    <p style='font-size: 14px; color: #ccc;'>You need to join a 🏟️ League to create a tournament.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:

            # Fetch league names from Firestore
            league_ids = st.session_state['user_data']['league_id']
            league_catalog = st.session_state['league_catalog']
            league_mapping = st.session_state['league_mapping']
            league_names = list(league_mapping.values()) 


            # Layout for Input Fields
            create_col1, create_col2 = st.columns(2, gap="medium")
            create_col3, create_col4 = st.columns(2, gap="medium")

            with create_col1:
                # League Selection Dropdown
                league_name = st.selectbox(
                    "Select League",
                    options=["Select a league"] + league_names,
                    key="select_league",
                    help="Choose the league to associate with this tournament.",
                )

            with create_col2:
                # Tournament Name Input
                tournament_name = st.text_input(
                    "Tournament Name",
                    value=st.session_state["user_data"].get("tournament_name", ""),
                    key="create_tournament_name",
                    placeholder="Enter a unique tournament name",
                    help="Provide a unique name for your tournament.",
                )

            with create_col3:
                # Video Game Selection
                video_game = st.selectbox(
                    "Select Game",
                    ["FC25", "FC24"],
                    key="select_video_game",
                    help="Choose the Video Game you will be playing. Currently, only 'FC25' and 'FC24' are supported.",
                )

            with create_col4:
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
                # Validate Inputs
                if league_name == "Select a league":
                    st.error("You must select a league to associate this tournament.", icon="❌")
                elif not tournament_name.strip():
                    st.error("Tournament Name cannot be empty.", icon="❌")
                elif not event_date:
                    st.error("Event Date must be selected.", icon="❌")
                else:
                    # Update Session State
                    st.session_state.update(
                        {
                            "league_name": league_name,
                            "tournament_name": tournament_name.strip(),
                            "video_game": video_game,
                            "event_date": event_date,
                            "league_id": next(
                                (
                                    key
                                    for key, value in st.session_state["league_mapping"].items()
                                    if value == league_name
                                ),
                                None,
                            ),
                            "create_complete": True,
                        }
                    )
                    st.success(
                        f"Tournament created successfully in {league_name}! Proceed to Setup.",
                        icon="✅",
                    )

            # Add Start Over Button
            render_start_over_button(tab="setup_create")



    # General Setup Tab
    with tab_setup:
        # Header Section
        st.markdown(
            """
            <div style='text-align: center; margin-bottom: 20px;'>
                <h3 style='margin-bottom: 5px;'>⚙️ General Setup</h3>
                <p style='font-size: 14px; color: #808080;'>Define tournament setup settings.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Check if "Create" step is complete
        if not st.session_state.get("create_complete", False):
            st.markdown(
                """
                <div style='text-align: center; margin-top: 50px;'>
                    <h3 style='margin-bottom: 10px; color: #808080;'>🔒 Locked</h3>
                    <p style='font-size: 14px; color: #ccc;'>Complete 🛠️ 01 Create to unlock this tab.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        else:

            # Layout for Setup Options
            setup_col1, setup_col2 = st.columns(2, gap="medium")
            
            # Tiebreaker Metrics Selection
            tiebreakers = st.multiselect(
                "Select Tiebreaker Metrics (in order of priority):",
                options=["Goals For", "xG For", "Wins", "Draws"],
                default=["Goals For", "xG For", "Wins"],
                help="Choose the metrics to break ties on Points, ordered by priority. Points are as follows: W = 3pts, D = 1pt, L = 0pts.",
                key="setup_tiebreakers",
            )

            # League Format Selection
            with setup_col1:
                league_format = st.selectbox(
                    "Select League Format",
                    ["League"],
                    help="Defines the format for the tournament. 'Group' & 'Knockouts' coming soon...",
                    key="setup_league_format"
                )

            # Playoff Format Selection
            with setup_col2:
                playoff_format = st.selectbox(
                    "Select Playoff Format",
                    ["Double-Elimination", "Single-Elimination"],
                    help="Determines playoff structure. Top 6 league teams advance, with the top 2 receiving byes.",
                    key="setup_playoff_format"
                )

            # Layout for Setup Options
            setup_col3, setup_col4 = st.columns(2, gap="medium")

            # Number of Players
            with setup_col3:
                num_players = st.slider(
                    "Number of Players",
                    min_value=6,
                    max_value=20,
                    value=6,
                    key="setup_num_players",
                    help="Choose the total number of players participating in the tournament.",
                )

            # Number of Consoles
            with setup_col4:
                num_consoles = st.slider(
                    "Number of Consoles",
                    min_value=1,
                    max_value=4,
                    value=2,
                    key="setup_num_consoles",
                    help="Specify the number of in-person consoles available for the tournament.",
                )

            # Half Duration
            half_duration = st.slider(
                "Select Half Duration",
                min_value=4,
                max_value=6,
                value=5,
                key="setup_half_duration",
                help="Set the duration (in minutes) for each half of a game.",
            )

            # Proceed Button
            proceed_button = st.button(
                "🚀 Proceed to Games Setup",
                key="proceed_to_games",
                use_container_width=True,
            )

            # Handle Proceed Action
            if proceed_button:
                st.session_state["setup_complete"] = True
                st.session_state["league_format"] = league_format
                st.session_state["playoff_format"] = playoff_format
                st.session_state["tiebreakers"] = tiebreakers
                st.session_state["num_players"] = num_players
                st.session_state["num_consoles"] = num_consoles
                st.session_state["half_duration"] = half_duration
                st.session_state["tournament_type"] = (
                    f'League ({num_players}-Team-{league_format}) '
                    f'Playoffs (6-Team-{playoff_format})'
                )
                st.success(
                    "General Setup completed! Proceed to the next step.", icon="✅"
                )

            # Add Start Over Button
            render_start_over_button(tab="setup_general")


    # Games Tab
    with tab_games:

        # Header Section
        st.markdown(
            """
            <div style='text-align: center; margin-bottom: 20px;'>
                <h3 style='margin-bottom: 5px;'>🕹️ Game Calculations</h3>
                <p style='font-size: 14px; color: #808080;'>Choose how many games each player will play.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not st.session_state.get("setup_complete"):
            st.markdown(
                """
                <div style='text-align: center; margin-top: 50px;'>
                    <h3 style='margin-bottom: 10px; color: #808080;'>🔒 Locked</h3>
                    <p style='font-size: 14px; color: #ccc;'>Complete ⚙️ 02 Setup to unlock this tab.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            # Pre-configured inputs
            num_players = st.session_state.get("num_players", 8)
            num_consoles = st.session_state.get("num_consoles", 2)
            half_duration = st.session_state.get("half_duration", 6)
            playoff_format = st.session_state.get("playoff_format", "Single-Elimination")
            league_format = st.session_state["league_format"]  # Currently only "League" is supported
            target_duration = 200  # Target ~3 hours in minutes

            # Calculate valid and recommended games
            max_games_per_player = num_players - 1
            viable_games = [
                games
                for games in range(1, max_games_per_player + 1)
                if (num_players * games) % 2 == 0  # Ensure all players can play the same number of games
            ]

            # Determine durations and recommended option
            durations = {
                games: estimate_tournament_duration(
                    num_players=num_players,
                    num_consoles=num_consoles,
                    half_duration=half_duration,
                    games_per_player=games,
                    league_format=league_format,
                    playoff_format=playoff_format,
                )
                for games in viable_games
            }
            recommended_games = min(durations, key=lambda x: abs(durations[x]["total_duration"] - target_duration))
            recommended_duration = durations[recommended_games]["total_duration"]

            # Card for Valid Options and Recommended Setup
            st.markdown(
                f"""
                <div style="
                    background-color: #1e1e1e; 
                    border-radius: 8px; 
                    box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.2); 
                    padding: 15px; 
                    margin-bottom: 20px; 
                    color: #f5f5f5; 
                    text-align: center;
                ">
                    <p style="font-size: 14px; color: #fff; margin: 5px 0;">
                        👍 Valid options: {', '.join(map(str, viable_games))}
                    </p>
                    <p style="font-size: 16px; color: #4caf50; margin: 5px 0;">
                        ✨ Recommended: {recommended_games} games per player
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Slider for selecting games per player
            selected_games_per_player = st.slider(
                label="Select Games Per Player",
                min_value=min(viable_games),
                max_value=max(viable_games),
                value=recommended_games,
                step=1,
                key="games_per_player_slider",  # Use a different key for the slider
                help="Slide to select the number of games each player will play.",
            )

            # Validate selected games per player
            if selected_games_per_player not in viable_games:
                st.error("🚫 Invalid selection. Please choose a valid option from the slider.")
            else:
                # Tournament Breakdown Section
                tournament_details = durations[selected_games_per_player]
                league_details = tournament_details["league_details"]
                playoff_details = tournament_details["playoff_details"]
                additional_time = tournament_details["additional_time"]

                with st.expander(label="📊 Game Calculations Breakdown", expanded=False):
                    # Organized and styled breakdown
                    st.markdown(
                        f"""
                        <div style='font-size: 14px; line-height: 1.6; padding: 10px; background-color: #1e1e1e; border-radius: 8px;'>
                            <b>🏆 Total League Games:</b> {league_details["total_league_games"]}<br>
                            <b>⏳ League Rounds:</b> {league_details["league_rounds"]}<br>
                            <b>🏅 League Duration:</b> {league_details["league_duration"] // 60} hours and {league_details["league_duration"] % 60} minutes<br>
                            <b>⚔️ Playoff Duration:</b> {playoff_details["playoff_duration"] // 60} hours and {playoff_details["playoff_duration"] % 60} minutes<br>
                            <b>⏱️ Additional Time:</b> {additional_time} minutes<br>
                            <b>📅 Total Tournament Duration:</b> {tournament_details["total_duration"] // 60} hours and {tournament_details["total_duration"] % 60} minutes<br>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                # Recommendation Feedback
                if selected_games_per_player == recommended_games:
                    st.info(
                        f"✨ Recommended setup selected: {selected_games_per_player} games per player (~{tournament_details['total_duration'] // 60} hours and {tournament_details['total_duration'] % 60} minutes)."
                    )
                else:
                    st.info(
                        f"👍 Valid setup: {selected_games_per_player} games per player (~{tournament_details['total_duration'] // 60} hours and {tournament_details['total_duration'] % 60} minutes)."
                    )

            # Proceed Button
            proceed_button = st.button(
                "🚀 Proceed to Players",
                key="proceed_to_players",
                use_container_width=True,
            )

            if proceed_button:
                if selected_games_per_player in viable_games:
                    st.session_state["games_complete"] = True
                    st.session_state["games_per_player"] = selected_games_per_player
                    st.success("Games Setup completed! Proceed to the next step.", icon="✅")
                else:
                    st.error("Invalid selection. Please fix the input before proceeding.", icon="❌")

            # Add Start Over Button
            render_start_over_button(tab="setup_games")


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

        if not st.session_state.get("games_complete", False):
            st.markdown(
                """
                <div style='text-align: center; margin-top: 50px;'>
                    <h3 style='margin-bottom: 10px; color: #808080;'>🔒 Locked</h3>
                    <p style='font-size: 14px; color: #ccc;'>Complete 🕹️ 03 Games to unlock this tab.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:

            # Initialize players list in session state
            if "players" not in st.session_state:
                st.session_state["players"] = []

            if not st.session_state["players"]:
                try:
                    # Ensure league_id is selected
                    selected_league_id = st.session_state.get("league_id")

                    if not selected_league_id:
                        raise ValueError("No league selected. Please select a league to proceed.")

                    # Fetch league data
                    league_data = league_catalog.get(selected_league_id, {})
                    members = league_data.get("members", {})

                    if not members:
                        st.warning("No members found for the selected league. Please add players.")
                    else:
                        # Populate player data with fallbacks
                        players_data = [
                            {"id": user_id, "username": username or f"Player_{user_id}", "source": "league"}
                            for user_id, username in members.items()
                        ]
                        st.session_state["players"] = players_data

                except Exception as e:
                    st.error(f"Failed to load player data: {e}", icon="❌")
                    return

            # Convert session state players to DataFrame
            players_data = pd.DataFrame(st.session_state["players"])

            # Ensure essential columns exist
            for column, default_value in [("id", None), ("username", "Unknown"), ("source", "league")]:
                if column not in players_data.columns:
                    players_data[column] = default_value

            # Generate player usernames
            player_names = players_data["username"].tolist()
            st.session_state["player_names"] = player_names

            # Player Multiselect
            num_players_required = st.session_state.get("num_players", len(player_names))
            selected_players = st.multiselect(
                "Select Players",
                options=player_names,
                default=player_names[:num_players_required],
            )

            # Validate selected players
            if not selected_players:
                st.error("Please select at least one player.", icon="❌")
            elif len(selected_players) != num_players_required:
                st.error(f"Please select exactly {num_players_required} players.", icon="❌")
            else:
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
                        "team_selection": team_selection,
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

        if not st.session_state.get("players_selected", False):
            st.markdown(
                """
                <div style='text-align: center; margin-top: 50px;'>
                    <h3 style='margin-bottom: 10px; color: #808080;'>🔒 Locked</h3>
                    <p style='font-size: 14px; color: #ccc;'>Complete 👤 04 Players to unlock this tab.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            # Retrieve parameters from session state
            games_per_player = st.session_state["games_per_player"]
            num_players = st.session_state["num_players"]
            num_consoles = st.session_state["num_consoles"]
            half_duration = st.session_state["half_duration"]
            playoff_format = st.session_state["playoff_format"]
            league_format = "League"  # Only "League" supported for now

            # Calculate tournament details using modularized functions
            tournament_details = estimate_tournament_duration(
                num_players=num_players,
                num_consoles=num_consoles,
                half_duration=half_duration,
                games_per_player=games_per_player,
                league_format=league_format,
                playoff_format=playoff_format,
            )

            league_details = tournament_details["league_details"]
            playoff_details = tournament_details["playoff_details"]
            additional_time = tournament_details["additional_time"]
            total_duration = tournament_details["total_duration"]

            # Convert durations to hours and minutes
            league_duration_hm = f"{league_details['league_duration'] // 60} hours and {league_details['league_duration'] % 60} minutes"
            playoff_duration_hm = f"{playoff_details['playoff_duration'] // 60} hours and {playoff_details['playoff_duration'] % 60} minutes"
            total_duration_hm = f"{total_duration // 60} hours and {total_duration % 60} minutes"

            # Collapsible sections for details
            with st.expander("🏆 Tournament Details", expanded=True):
                st.markdown(f"### 🏆 **{st.session_state['tournament_name']}**")
                # Tournament details
                st.write(f"**🏟️ League:** {st.session_state['league_name']}")
                st.write(f"**⚽ Game:** {st.session_state['video_game']}")
                st.write(f"**📅 Date:** {st.session_state['event_date']}")
                st.write(f"**🎯 Type:** {st.session_state['tournament_type']}")
                st.write(f"**🏅 League Format:** {st.session_state['league_format']}")
                st.write(f"**↕️ League Tiebreaker Order:** {st.session_state['tiebreakers']}")
                st.write(f"**⚔️ Playoff Format:** {st.session_state['playoff_format']}")
                st.write(f"**👥 Players:** {num_players}")
                st.write(f"**🎮 Consoles:** {num_consoles}")
                st.write(f"**⏱️ Half Duration:** {half_duration} minutes")
                st.write(f"**🕹️ Games Per Player:** {games_per_player}")

            with st.expander("⏳ Estimated Duration", expanded=False):
                st.markdown(f"#### **⏳ ~ {total_duration_hm}**")
                # League duration details
                st.markdown("**🏅 League Games**")
                st.write(f"- **Total Games:** {league_details['total_league_games']} games, {league_details['league_rounds']} rounds")
                st.write(f"- **Estimated Duration:** ~{league_duration_hm}")
                # Playoff duration details
                st.markdown("**⚔️ Playoff Games**")
                st.write(f"- **Estimated Duration:** ~{playoff_duration_hm}")
                # Additional time
                st.markdown("**⏱️ Additional Time**")
                st.write(f"- **Miscellaneous Time:** ~{additional_time} minutes")

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

            # Save Button Logic
            if save_button:
                tournament_id = generate_unique_id(id_length=12, id_type="uuid")
                st.session_state["tournaments"][tournament_id] = {
                    "tournament_name": st.session_state["tournament_name"],
                    "video_game": st.session_state["video_game"],
                    "league_id": st.session_state["league_id"],
                    "league_name": st.session_state["league_name"],
                    "event_date": st.session_state["event_date"],
                    "league_format": st.session_state["league_format"],
                    "tiebreakers": st.session_state["tiebreakers"],
                    "playoff_format": st.session_state["playoff_format"],
                    "tournament_type": st.session_state["tournament_type"],
                    "num_players":  st.session_state["num_players"],
                    "num_consoles":  st.session_state["num_consoles"],
                    "half_duration": st.session_state["half_duration"],
                    "games_per_player": st.session_state["games_per_player"],
                    "estimated_tournament_duration": total_duration_hm,
                    "estimated_league_duration": league_duration_hm,
                    "estimated_playoff_duration": playoff_duration_hm,
                    "estimated_additional_duration": additional_time,
                    "selected_players": st.session_state["selected_players"],
                    "team_selection": st.session_state["team_selection"],
                }
                st.session_state["selected_tournament_id"] = tournament_id
                st.session_state["tournament_ready"] = True
                st.success(f"Tournament setup saved with ID: {tournament_id}", icon="✅")

            # Add Start Over Button
            render_start_over_button(tab="setup_finish")

