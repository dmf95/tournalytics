import streamlit as st
import pandas as pd
from firebase_admin import firestore
from utils.analytics_utils import calculate_basic_analysis, calculate_playoff_ranks


# Mobile-First Design: Optimized Page Header
st.markdown(
    """
    <div style='text-align: center; margin-bottom: 20px;'>
        <h2>📈 Tournament Stats</h2>
        <p style='font-size: 14px; color: #808080;'>Analyze your performance and gain insights from past tournaments.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Fetch Leagues and Enable League Selection
league_ids = st.session_state.user_data.get("league_ids", [])
league_mapping = st.session_state.league_mapping

if not league_ids or not league_mapping:
    st.error("No leagues are associated with your account.", icon="❌")
else:
    # League Selection Dropdown
    selected_league_id = st.selectbox(
        "Select a League to View Stats",
        options=league_ids,
        format_func=lambda x: league_mapping.get(x, "Unknown League"),
    )

    # Fetch tournaments from Firebase
    @st.cache_data(ttl=600)  # Cache the data for 10 minutes
    def fetch_tournaments():
        db = firestore.client()
        tournaments_ref = db.collection("tournaments")
        docs = tournaments_ref.stream()
        return [doc.to_dict() for doc in docs]

    tournaments = fetch_tournaments()
    filtered_tournaments = [
        t for t in tournaments if t.get("metadata", {}).get("league_id") == selected_league_id
    ]

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

        # Fetch Selected Tournament Data
        selected_tournament = next(
            (t for t in filtered_tournaments if t["metadata"]["tournament_id"] == selected_tournament_id), {}
        )
        results_df = pd.DataFrame(selected_tournament.get("results", []))
        playoff_results = pd.DataFrame(selected_tournament.get("playoff_results", []))
        team_selection = selected_tournament.get("metadata", {}).get("team_selection", {})

        if results_df.empty and playoff_results.empty:
            st.info("No results available for this tournament.", icon="ℹ️")
        else:
            # Perform Basic Analysis
            stats = calculate_basic_analysis(results_df)

            # Fetch the username from session state
            username = st.session_state.user_data.get("username", "Player")

            # Display Summary KPIs with improved title and personalized message
            st.markdown("---")
            st.markdown(
                f"""
                <div style='text-align: center;'>
                    <h3>🏆 {username}'s Performance</h3>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Calculate League Averages
            overall_stats = stats.get("overall")

            # Add Rank from final standings if available
            if "final_standings" in st.session_state:
                final_standings = st.session_state.final_standings
                # Map team names to usernames using team_selection
                final_standings["Player"] = final_standings["Team"].map(
                    {v: k for k, v in team_selection.items()}
                )
                if "Player" in final_standings.columns:
                    # Select only the 'Player', 'Rank', and 'Team' columns for merging
                    final_standings_filtered = final_standings[["Player", "Rank", "Team"]]
                    # Merge with overall_stats
                    overall_stats = overall_stats.merge(final_standings_filtered, on="Player", how="left")
                    # Display the result
                    #st.write(overall_stats)


                else:
                    st.warning("Final standings are missing the 'Player' column after mapping.", icon="⚠️")
            else:
                overall_stats = overall_stats.assign(Rank=range(1, len(overall_stats) + 1))

            # Ensure correct column order
            overall_stats = overall_stats[[
                "Rank", "Player",  "Points", "Games", "Wins", "Draws", "Losses", "Goals_For", "Goals_Against", "xG_For", "xG_Against"
            ]]
            # Rename columns for brevity
            overall_stats.rename(
                columns={
                    "Goals_For": "GF",
                    "Goals_Against": "GA",
                    "xG_For": "xGF",
                    "xG_Against": "xGA",
                    "Wins": "W",
                    "Draws": "D",
                    "Losses": "L"
                },
                inplace=True
            )

            # Ensure correct column order
            overall_stats = overall_stats[[
                "Player", "Rank", "Points", "Games", "W", "D", "L", "GF", "GA", "xGF", "xGA"
            ]]

            # Sort by Rank in ascending order
            overall_stats = overall_stats.sort_values(by="Rank", ascending=True)


            # Display Updated KPIs
            user_stats = overall_stats[overall_stats["Player"] == username]
            league_averages = overall_stats.mean(numeric_only=True)

            if not user_stats.empty:
                cols1 = st.columns(3)
                cols2 = st.columns(3)
                
                user_games = user_stats.iloc[0]["Games"]
                user_goals = user_stats.iloc[0]["GF"]
                user_goals_against = user_stats.iloc[0]["GA"]
                user_xg_for = user_stats.iloc[0]["xGF"]
                user_xg_against = user_stats.iloc[0]["xGA"]
                user_win_rate = user_stats.iloc[0]["W"] / user_games if user_games else 0

                cols1[0].metric(
                    "Games Played",
                    f"{user_games}",
                    f"{'+' if user_games > league_averages['Games'] else ''}{user_games - league_averages['Games']:.1f}",
                )
                cols1[1].metric(
                    "Goals Scored",
                    f"{user_goals}",
                    f"{'+' if user_goals > league_averages['GF'] else ''}{user_goals - league_averages['GF']:.1f}",
                )
                cols1[2].metric(
                    "Goals Against",
                    f"{user_goals_against}",
                    f"{'+' if user_goals_against < league_averages['GA'] else ''}{user_goals_against - league_averages['GA']:.1f}",
                )

                cols2[0].metric(
                    "Win Rate",
                    f"{user_win_rate:.1%}",
                    f"{'+' if user_win_rate > league_averages['W'] / league_averages['Games'] else ''}{(user_win_rate - league_averages['W'] / league_averages['Games']):.1%}",
                )
                cols2[1].metric(
                    "Total xG For",
                    f"{user_xg_for:.2f}",
                    f"{'+' if user_xg_for > league_averages['xGF'] else ''}{user_xg_for - league_averages['xGF']:.2f}",
                )
                cols2[2].metric(
                    "Total xG Against",
                    f"{user_xg_against:.2f}",
                    f"{'+' if user_xg_against < league_averages['xGA'] else ''}{user_xg_against - league_averages['xGA']:.2f}",
                )

            # Playoff Rankings
            if not playoff_results.empty:
                st.markdown("---")
                st.markdown(
                    f"""
                    <div style='text-align: center; margin-top: 20px;'>
                        <h3>⚔️ Playoff Ranking </h3>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                winner = playoff_results.iloc[-1]["Home"]  # Assuming the last match decides the winner
                st.markdown(
                    f"""
                    <div style='text-align: center; margin-top: 20px;'>
                        <h4>🎉 Champion: {winner} 🎉</h4>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Prepare rankings based on round and goals
                playoff_rankings = calculate_playoff_ranks(playoff_results)

                st.dataframe(
                    playoff_rankings[["Rank", "Player", "Goals For", "Goals Against", "xG", "Games Played"]],
                    use_container_width=True,
                    hide_index=True,
                )

            # League Results
            if not overall_stats.empty:
                st.markdown("---")
                st.markdown(
                    f"""
                    <div style='text-align: center; margin-top: 20px;'>
                        <h3>🏅 League Results </h3>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.dataframe(
                    overall_stats,
                    use_container_width=True,
                    hide_index=True,
             )  


# Footer Branding
st.markdown("---")
st.write("💡 Use this page to analyze past tournaments and improve your strategies.")
