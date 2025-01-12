"""
Utility functions for Tournalytics project.
"""

from .auth_utils import authenticate_user, create_user_metadata
from .data_utils import (
    firestore_get_leagues,
    firestore_get_all_leagues,
    firestore_add_league,
    firestore_update_league_admins,
    firestore_add_players_to_league,
    firestore_remove_players_from_league,
    firestore_get_user,
    firestore_get_all_users,
    firestore_batch_update_users,
    create_league_mapping,
    filter_users_by_role
)
from .general_utils import initialize_session_state, generate_unique_id
from .tournament_utils import (
    generate_league_schedule,
    upsert_results,
    update_standings,
    calculate_outcomes,
    estimate_league_duration,
    estimate_playoff_duration,
    estimate_tournament_duration,
    generate_playoffs_bracket,
    determine_winner,
    validate_league_completion,
    validate_playoffs_completion,
    update_league_game_results,
    update_playoff_results,
    update_final_matches

)