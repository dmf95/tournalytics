import streamlit as st
import pandas as pd
from utils.general_utils import generate_tournament_id

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
        # Clear relevant session state variables
        st.session_state.clear()

        # Reinitialize necessary session state variables
        st.session_state["tournaments"] = {}
        st.session_state["create_complete"] = False
        st.session_state["setup_complete"] = False
        st.session_state["players_selected"] = False
        st.session_state["finish_generated"] = False
        st.session_state["current_step"] = 0
        st.session_state["active_tab"] = "🛠️ 01 Create"

        # Rerun the script
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

    # Create Tab
    with tab_create:
        st.markdown(
            """
            <div style='text-align: center; margin-bottom: 20px;'>
                <h3 style='margin-bottom: 5px;'>🎮 Create Tournament</h3>
                <p style='font-size: 14px; color: #555;'>Enter the tournament details to get started.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Tournament Name Input
        st.session_state["tournament_name"] = st.text_input(
            "Tournament Name",
            value=st.session_state.get("tournament_name", ""),
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
            if not st.session_state["tournament_name"]:
                st.error("Tournament Name cannot be empty.", icon="❌")
            elif not event_date:
                st.error("Event Date must be selected.", icon="❌")
            else:
                st.session_state["create_complete"] = True
                st.session_state["event_date"] = event_date
                st.success("Tournament created successfully! Proceed to Setup.", icon="✅") 

        # Add Start Over Button
        render_start_over_button(tab='setup_create')

    # General Setup Tab
    with tab_setup:
        st.markdown(
            """
            <div style='text-align: center; margin-bottom: 20px;'>
                <h3 style='margin-bottom: 5px;'>⚙️ General Setup</h3>
                <p style='font-size: 14px; color: #555;'>Define tournament setup settings.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not st.session_state["create_complete"]:
            st.warning(
                "Complete the Create step first to unlock this tab.", icon="🔒"
            )
        else:
            
            tournament_type = st.selectbox(
                "Select Tournament Type",
                ["Round Robin", "Single Elimination", "Double Elimination"],
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
                st.session_state["tournament_type"] = tournament_type
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
                <p style='font-size: 14px; color: #555;'>Select players and assign teams.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not st.session_state["setup_complete"]:
            st.warning(
                "Complete the General Setup step first to unlock this tab.", icon="🔒"
            )
        else:

            player_names = st.session_state["player_names"]
            selected_players = st.multiselect(
                "Select Players", player_names, default=player_names[:st.session_state["num_players"]]
            )
            if len(selected_players) != st.session_state["num_players"]:
                st.error(f"Please select exactly {st.session_state['num_players']} players.")
            else:
                team_selection = {
                    player: st.text_input(f"Team for {player}", value=f"Team {player}")
                    for player in selected_players
                }

                # Proceed Button with Icon
                proceed_button = st.button(
                    "🚀 Proceed to Finish",
                    key="proceed_to_finish",
                    use_container_width=True,
                )

                # Logic for Proceed Button
                if proceed_button:
                    st.session_state["players_selected"] = True
                    st.session_state["selected_players"] = selected_players
                    st.session_state["team_selection"] = team_selection
                    st.success("Player Setup completed! Proceed to the Finish.", icon="✅")

            # Add Start Over Button
            render_start_over_button(tab='setup_players')

    # Finish Tab
    with tab_finish:
        st.markdown(
            """
            <div style='text-align: center; margin-bottom: 20px;'>
                <h3 style='margin-bottom: 5px;'>🎉 Finish Tournament Setup</h3>
                <p style='font-size: 14px; color: #555;'>Save your Tournament setup.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if not st.session_state["players_selected"]:
            st.warning("Complete the Player Selection step first to unlock this tab.")
        else:
            # Collapsible sections for details
            with st.expander("🏆 Tournament Details", expanded=True):
                st.write(f"**Name**: {st.session_state['tournament_name']}")
                st.write(f"**Date**: {st.session_state['event_date']}")
                st.write(f"**Type**: {st.session_state['tournament_type']}")
                st.write(f"**Players**: {st.session_state['num_players']}")
                st.write(f"**Consoles**: {st.session_state['num_consoles']}")
                st.write(f"**Half Duration**: {st.session_state['half_duration']} minutes")

            with st.expander("👤 Players & Teams", expanded=False):
                for player, team in st.session_state["team_selection"].items():
                    st.write(f"- {player}: {team}")

            # Save Tournament Setup Button
            save_button = st.button(
                "💾 Save Tournament Setup", 
                key="save_tournament_setup",
                use_container_width=True,
                )
            if save_button:
                tournament_id = generate_tournament_id()
                st.session_state["tournaments"][tournament_id] = {
                    "tournament_name": st.session_state["tournament_name"],
                    "event_date": st.session_state["event_date"],
                    "tournament_type": st.session_state["tournament_type"],
                    "num_players": st.session_state["num_players"],
                    "num_consoles": st.session_state["num_consoles"],
                    "half_duration": st.session_state["half_duration"],
                    "selected_players": st.session_state["selected_players"],
                    "team_selection": st.session_state["team_selection"],
                }
                st.success(f"Tournament setup saved with ID: {tournament_id}",icon="✅") 

            # Add Start Over Button
            render_start_over_button(tab='setup_finish')

