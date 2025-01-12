import plotly.figure_factory as ff

def create_bracket_visualization(bracket):
    data = [
        [game["Round"], game["Home"], game["Away"], game["Match"]]
        for game in bracket
    ]
    return pd.DataFrame(data, columns=["Round", "Home", "Away", "Match"])

def plot_bracket(bracket_df):
    fig = ff.create_table(bracket_df)
    return fig
