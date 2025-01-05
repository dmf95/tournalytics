#-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-
#-- dependencies
#-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-

# main libraries
import streamlit as st
import pandas as pd
import numpy as np
# custom libraries
from utils.tournament_utils import determine_winner

#-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-
#-- tournament.py: finals tab (4th)
#-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-

def render():

    if "playoff_results" not in st.session_state or st.session_state.playoff_results.empty:
        st.warning("Playoffs have not been generated yet.")
        st.stop()
        st.write("poo")

    else:
        playoff_results = st.session_state.playoff_results.copy()
        st.write("blah")

        # Check semi-final completion
        semi_final_matches = playoff_results[playoff_results["Match"].str.startswith("SF")]
        if semi_final_matches["Home Goals"].isna().any() or semi_final_matches["Away Goals"].isna().any():
            st.warning("Finals are locked until all semi-final matches are completed.")
            st.stop()

        # Determine winners for SF1 and SF2
        sf1_matches = playoff_results[playoff_results["Match"].str.startswith("SF1")]
        sf2_matches = playoff_results[playoff_results["Match"].str.startswith("SF2")]

        sf1_win = determine_winner(sf1_matches) if not sf1_matches.dropna(subset=["Home Goals", "Away Goals"]).empty else None
        sf2_win = determine_winner(sf2_matches) if not sf2_matches.dropna(subset=["Home Goals", "Away Goals"]).empty else None


        # Update final matches with semi-final winners
        if sf1_win and sf2_win:
            final_matches = playoff_results["Match"].str.startswith("Final")
            playoff_results.loc[final_matches, ["Home", "Away"]] = (
                playoff_results.loc[final_matches, ["Home", "Away"]]
                .replace({"Winner SF1": sf1_win, "Winner SF2": sf2_win})
            )
            
            # Write back updated playoff results to session state
            st.session_state.playoff_results = playoff_results.copy()

        # Display Finals
        final_matches = playoff_results[playoff_results["Match"].str.contains("Final", na=False)]
        if final_matches.empty:
            st.info("No finals matches available.")
        else:
            # Check if all finals games are complete
            if not final_matches["Home Goals"].isna().any() and not final_matches["Away Goals"].isna().any():
                # Determine the overall winner
                overall_winner = determine_winner(final_matches)
                winner_team = st.session_state.teams[overall_winner]

                # Display winner message and GIF under the header
                st.markdown(f"### 🏆 Congratulations to **{winner_team}**! 🏆")
                st.image("assets/_champion.gif", caption=f"{winner_team} is the champion!")

            # Add team names and status to playoff results
            final_matches["Home Team"] = final_matches["Home"].map(st.session_state.teams)
            final_matches["Away Team"] = final_matches["Away"].map(st.session_state.teams)
            final_matches["Status"] = final_matches["Game #"].apply(
                lambda game_id: "✅" if not pd.isna(
                    final_matches.loc[final_matches["Game #"] == game_id, "Home Goals"]
                ).all() else ""
            )

            # Display playoff results with consistent attributes
            st.subheader("Finals")
            final_bracket = final_matches[["Game #", "Match", "Home Team", "Away Team", "Console", "Status"]]
            st.dataframe(
                final_bracket[final_bracket["Match"].str.contains("Final", na=False)],
                use_container_width=True,
            )

            # Allow updating results for finals games
            st.subheader("Update Finals Match Results")
            selected_final_game = st.selectbox("Select Finals Game to Update", final_matches["Game #"])

            if selected_final_game:
                match_row = final_matches[final_matches["Game #"] == selected_final_game].iloc[0]
                home_team = match_row["Home"]
                away_team = match_row["Away"]

                st.write(f"**Home Team**: {home_team}")
                st.write(f"**Away Team**: {away_team}")

                home_goals = st.number_input(f"Goals for {home_team}", min_value=0, step=1, key=f"home_goals_final_{selected_final_game}")
                away_goals = st.number_input(f"Goals for {away_team}", min_value=0, step=1, key=f"away_goals_final_{selected_final_game}")
                home_xg = st.number_input(f"xG for {home_team}", min_value=0.0, step=0.1, key=f"home_xg_final_{selected_final_game}")
                away_xg = st.number_input(f"xG for {away_team}", min_value=0.0, step=0.1, key=f"away_xg_final_{selected_final_game}")

                if st.button("Update Finals Match Results"):
                    st.session_state.playoff_results.loc[
                        st.session_state.playoff_results["Game #"] == selected_final_game,
                        ["Home Goals", "Away Goals", "Home xG", "Away xG"]
                    ] = [home_goals, away_goals, home_xg, away_xg]

                    st.success(f"Results updated for Finals Game {selected_final_game}")