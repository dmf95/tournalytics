import streamlit as st
import pandas as pd
from utils.analytics_utils import calculate_basic_analysis, calculate_playoff_ranks
from utils.data_utils import create_league_mapping, firestore_query_tournaments_by_league
from utils.tournament_utils import sort_standings

# Page Header: Mobile-First Design
st.markdown(
    """
    <div style='text-align: center; margin-bottom: 20px;'>
        <h2>📈 Tournament Stats</h2>
        <p style='font-size: 14px; color: #808080;'>Analyze your performance and gain insights from past tournaments.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Check if user has league_ids
league_ids = st.session_state['user_data'].get("league_id", [])
if not league_ids or not st.session_state.get("league_mapping"):
    st.error("No leagues are associated with your account.", icon="❌")
else:
    # League Selection Dropdown
    league_mapping = st.session_state['league_mapping']
    selected_league_id = st.selectbox(
        "Select a League to View Stats",
        options=league_ids,
        format_func=lambda x: league_mapping.get(x, "Unknown League"),
    )

    # Fetch Tournaments for Selected League
    @st.cache_data(ttl=600)
    def fetch_tournaments_by_league(league_id):
        return firestore_query_tournaments_by_league(league_id)

    filtered_tournaments = st.session_state.get(f"tournaments_{selected_league_id}")
    if not filtered_tournaments:
        filtered_tournaments = fetch_tournaments_by_league(selected_league_id)
        st.session_state[f"tournaments_{selected_league_id}"] = filtered_tournaments

    if not filtered_tournaments:
        st.info("No tournaments found for the selected league.", icon="ℹ️")
    else:
        # Tournament Selection
        tournament_names = {
            t["metadata"]["tournament_id"]: t["metadata"].get("tournament_name", "Unnamed Tournament")
            for t in filtered_tournaments
        }
        selected_tournament_id = st.selectbox(
            "Select a Tournament",
            options=tournament_names.keys(),
            format_func=lambda x: tournament_names[x],
        )

        # Fetch Selected Tournament Data (dictionary)
        selected_tournament = next(
            (t for t in filtered_tournaments if t["metadata"]["tournament_id"] == selected_tournament_id), {}
        )

        # Breakdown Selected Tournament Data into functional elements
        results_df = pd.DataFrame(selected_tournament.get("results", []))
        playoff_results = pd.DataFrame(selected_tournament.get("playoff_results", []))
        tournament_metadata = selected_tournament.get("metadata", {})
        team_selection = selected_tournament.get("metadata", {}).get("team_selection", {})

        if results_df.empty and playoff_results.empty:
            st.info("No results available for this tournament.", icon="ℹ️")
        else:
            # Perform Basic Analysis
            stats = calculate_basic_analysis(selected_tournament)
            username = st.session_state.user_data.get("username", "Player")

            # Display Summary KPIs Section
            st.markdown("---")
            st.markdown(
                f"""
                <div style='text-align: center;'>
                    <h3>🏆 {username}'s Performance</h3>
                    <p style="color: #808080;">Versus League Average</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Retrieve Overall Stats
            overall_stats = stats.get("overall", pd.DataFrame())

            # Incorporate Final Standings
            if "final_standings" in st.session_state:
                final_standings = st.session_state.final_standings
                # Map Player Names to Teams
                final_standings["Player"] = final_standings["Team"].map(
                    {v: k for k, v in team_selection.items()}
                )
                # Merge Rankings and Team Details
                overall_stats = overall_stats.merge(
                    final_standings[["Player", "Rank", "Team"]], on="Player", how="left"
                )
            else:
                # Assign Rankings if Final Standings are Missing
                overall_stats = overall_stats.assign(Rank=range(1, len(overall_stats) + 1))

            # Rename Columns for Clarity
            overall_stats.rename(
                columns={
                    "Goals_For": "GF",
                    "Goals_Against": "GA",
                    "xG_For": "xGF",
                    "xG_Against": "xGA",
                    "Wins": "W",
                    "Draws": "D",
                    "Losses": "L",
                },
                inplace=True,
            )

            # Define Tiebreakers and Column Mapping
            tiebreakers = selected_tournament.get("metadata", {}).get("tiebreakers", [])
            column_mapping = {"Goals For": "GF", "xG For": "xGF", "Wins": "W", "Draws": "D"}

            # Reorder Columns for Display
            display_columns = ["Rank", "Player", "Points", "Games", "W", "D", "L", "GF", "GA", "xGF", "xGA"]
            overall_stats = overall_stats[display_columns]

            # Sort Standings Based on Tiebreakers and Rankings
            overall_stats_final = sort_standings(overall_stats, tiebreakers, column_mapping)


            # User Stats and League Averages
            user_stats = overall_stats_final[overall_stats_final["Player"] == username]
            league_averages = overall_stats_final.mean(numeric_only=True)

            if not user_stats.empty:
                cols1 = st.columns(3)
                cols2 = st.columns(3)

                def display_stat(column, title, user_value, league_avg, better_higher=True):
                    diff = user_value - league_avg
                    color = "green" if (diff > 0 and better_higher) or (diff < 0 and not better_higher) else "red"
                    column.markdown(
                        f"<div style='text-align:center;'><strong>{title}</strong><br>"
                        f"<span style='font-size: 1.5em;'>{user_value}</span><br>"
                        f"<span style='color: {color};'>{'+' if diff > 0 else ''}{diff:.2f}</span></div>",
                        unsafe_allow_html=True,
                    )

                # Stats Display
                display_stat(cols1[0], "Games Played", user_stats.iloc[0]["Games"], league_averages["Games"])
                display_stat(cols1[1], "Goals Scored", user_stats.iloc[0]["GF"], league_averages["GF"])
                display_stat(cols1[2], "Goals Against", user_stats.iloc[0]["GA"], league_averages["GA"], better_higher=False)
                display_stat(cols2[0], "Win Rate", user_stats.iloc[0]["W"] / user_stats.iloc[0]["Games"],
                             league_averages["W"] / league_averages["Games"])
                display_stat(cols2[1], "Total xG For", user_stats.iloc[0]["xGF"], league_averages["xGF"])
                display_stat(cols2[2], "Total xG Against", user_stats.iloc[0]["xGA"], league_averages["xGA"], better_higher=False)

            # Playoff Rankings
            if not playoff_results.empty:
                st.markdown("---")
                st.markdown(
                    """
                    <div style='text-align: center; margin-top: 20px;'>
                        <h3>⚔️ Playoff Ranking </h3>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                winner = playoff_results.iloc[-1]["Home"]
                st.markdown(
                    f"""
                    <div style='text-align: center; margin-top: 20px;'>
                        <h4>🎉 Champion: {winner} 🎉</h4>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                playoff_rankings = calculate_playoff_ranks(playoff_results)
                st.dataframe(
                    playoff_rankings[["Rank", "Player", "Goals For", "Goals Against", "xG", "Games Played"]],
                    use_container_width=True,
                    hide_index=True,
                )

            # League Results
            if not overall_stats_final.empty:
                st.markdown("---")
                st.markdown(
                    """
                    <div style='text-align: center; margin-top: 20px;'>
                        <h3>🏅 League Results </h3>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.dataframe(overall_stats_final, use_container_width=True, hide_index=True)

# Footer Branding
st.markdown("---")
st.write("💡 Use this page to analyze past tournaments and improve your strategies.")
