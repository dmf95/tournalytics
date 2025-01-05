import streamlit as st

def render_home():
    """Render the Home page with mobile-first enhancements."""
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 20px; padding: 10px;">
            <h1 style="font-size: 2.2em; margin-bottom: 10px;">🎮 Welcome to Tournalytics</h1>
            <p style="font-size: 1.1em; color: #555; max-width: 600px; margin: 0 auto;">
                The Tournament app.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Feature Overview Section
    st.markdown(
        """
        <div style="margin: 20px 0; padding: 10px;">
            <h2 style="text-align: center; font-size: 1.8em; margin-bottom: 20px;">Features</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Stacked layout for mobile-friendliness
    with st.container():
        st.markdown(
            """
            <div style="margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 8px;">
                <h3>🏆 <strong>Start a Tournament</strong></h3>
                <p style="font-size: 1em; color: #555;">
                    Set up, manage, and monitor tournaments with ease.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div style="margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 8px;">
                <h3>👤 <strong>Manage Players</strong></h3>
                <p style="font-size: 1em; color: #555;">
                    Manage player rosters and teams efficiently.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div style="margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 8px;">
                <h3>📊 <strong>View Stats</strong></h3>
                <p style="font-size: 1em; color: #555;">
                    Dive into performance insights and analyze past tournaments.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Footer Section
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; margin-top: 20px; font-size: 0.9em; color: #777;">
            Built with ❤️ by Tournalytics | v1.0.0
        </div>
        """,
        unsafe_allow_html=True,
    )

# Define pages
home_page = st.Page(render_home, title="Home", icon="🎮", default=True)
tournaments_page = st.Page("tournaments.py", title="Tournaments", icon="🏆")
players_page = st.Page("players.py", title="Players", icon="🏃")
stats_page = st.Page("stats.py", title="Stats", icon="📊")

# Set the default page to Home
if "page" not in st.session_state:
    st.session_state.page = "Home"  # Default page

# Navigation (Streamlit automatically handles the page transitions)
pg = st.navigation(
    {
        "Main": [home_page],
        "Features": [tournaments_page, players_page, stats_page],
    }
)

# This part ensures the page switch works based on `st.session_state.page`
# Do NOT manually call `run()` here! Navigation is handled automatically by `st.navigation`
pg.run()
