import pandas as pd
import os

def load_previous_tournaments():
    if os.path.exists("tournaments.csv"):
        return pd.read_csv("tournaments.csv")
    return pd.DataFrame(columns=["Tournament ID", "Tournament Name", "Status"])

def save_tournament(tournament_id, tournament_name, standings, results):
    results.to_csv(f"tournament_{tournament_id}_results.csv", index=False)
    standings.to_csv(f"tournament_{tournament_id}_standings.csv", index=False)

    tournaments = load_previous_tournaments()
    tournaments = pd.concat([
        tournaments,
        pd.DataFrame([{"Tournament ID": tournament_id, "Tournament Name": tournament_name, "Status": "Completed"}])
    ])
    tournaments.to_csv("tournaments.csv", index=False)

# Load player data
def load_player_data_local(path):
    return pd.read_csv(path)

import pandas as pd
import os

def insert_player_data(data, file_path="assets/players.csv"):
    """
    Insert player data into the players CSV file.

    Parameters:
    - data (list of dict): List of player dictionaries with keys 'first_name', 'last_name', and 'team_name'.
    - file_path (str): Path to the players CSV file (default: "assets/players.csv").
    
    Returns:
    None
    """
    # Ensure the file exists; if not, create it with the appropriate columns
    if not os.path.exists(file_path):
        pd.DataFrame(columns=["first_name", "last_name", "team_name"]).to_csv(file_path, index=False)

    # Load the existing data
    existing_data = pd.read_csv(file_path)

    # Convert the input data to a DataFrame
    new_data = pd.DataFrame(data)

    # Append the new data to the existing data
    updated_data = pd.concat([existing_data, new_data], ignore_index=True)

    # Save the updated data back to the file
    updated_data.to_csv(file_path, index=False)
