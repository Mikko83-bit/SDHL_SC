import streamlit as st
import pandas as pd

st.set_page_config(page_title="Scoring Chances Analysis", layout="wide")
st.title("🏒 Scoring Chances Team & Players Analysis")

# 1. Älykäs datan lukeminen (huomioi Excelin sep=-rivin)
@st.cache_data
def load_data():
    with open("hockey_tag_data.csv", "r", encoding="utf-8") as f:
        first_line = f.readline().strip()
    skip = 1 if first_line.startswith("sep=") else 0
    df = pd.read_csv("hockey_tag_data.csv", skiprows=skip, sep=None, engine='python')
    
    outcome_cols = [
        "Goal for", "Chance for", "Goal for PP", "Chance for PP",
        "Goal agn", "Chance agn", "Goal agn PP", "Chance agn PP", "Turnover"
    ]
    for col in outcome_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    return df

df = load_data()

# 2. Sivuvalikon suodattimet
st.sidebar.header("Filters")
games = st.sidebar.multiselect("Select Game", options=df["Game"].unique(), default=df["Game"].unique())
periods = st.sidebar.multiselect("Select Period", options=df["Period"].unique(), default=df["Period"].unique())

filtered_df = df[(df["Game"].isin(games)) & (df["Period"].isin(periods))]

# 3. Yhteenveto / Avainmittarit (KPIs)
col1, col2, col3, col4 = st.columns(4)
col1.metric("Goals For", int(filtered_df["Goal for"].sum() + filtered_df["Goal for PP"].sum()))
col2.metric("Goals Against", int(filtered_df["Goal agn"].sum() + filtered_df["Goal agn PP"].sum()))
col3.metric("Scoring Chances For", int(filtered_df["Chance for"].sum() + filtered_df["Chance for PP"].sum()))
col4.metric("Turnovers", int(filtered_df["Turnover"].sum()))

st.markdown("---")

# 4. Välilehdet (Määritellään ENNEN tab-lohkoja)
tab1, tab2, tab3 = st.tabs(["📊 Scoring Chances Team", "👤 Scoring Chances Players", "📄 Raw Data"])

with tab1:
    st.subheader("Team Statistics by Descriptor")
    desc_summary = filtered_df.groupby("Descriptor")[
        ["Goal for", "Chance for", "Goal for PP", "Chance for PP", 
         "Goal agn", "Chance agn", "Goal agn PP", "Chance agn PP", "Turnover"]
    ].sum()
    st.dataframe(desc_summary, use_container_width=True)

with tab2:
    st.subheader("Player Statistics by Role (P1 = Scorer/Receiver, P2/P3 = Creators)")
    
    all_players = pd.unique(filtered_df[['Player 1', 'Player 2', 'Player 3']].values.ravel())
    players_list = [p for p in all_players if pd.notna(p) and str(p).strip() != '']
    
    player_rows = []
    for p in players_list:
        goals_scored = filtered_df[(filtered_df['Player 1'] == p) & (filtered_df['Goal for'] == 1)].shape[0]
        chances_rcv = filtered_df[(filtered_df['Player 1'] == p) & (filtered_df['Chance for'] == 1)].shape[0]
        turnovers = filtered_df[(filtered_df['Player 1'] == p) & (filtered_df['Turnover'] == 1)].shape[0]
        goals_agn_p1 = filtered_df[(filtered_df['Player 1'] == p) & (filtered_df['Goal agn'] == 1)].shape[0]
        
        goals_created = filtered_df[((filtered_df['Player 2'] == p) | (filtered_df['Player 3'] == p)) & (filtered_df['Goal for'] == 1)].shape[0]
        chances_created = filtered_df[((filtered_df['Player 2'] == p) | (filtered_df['Player 3'] == p)) & (filtered_df['Chance for'] == 1)].shape[0]
        
        player_rows.append({
            'Player': p,
            'Goals (P1)': goals_scored,
            'Assists (P2/P3)': goals_created,
            'Points': goals_scored + goals_created,
            'Chances For (P1)': chances_rcv,
            'Chances Created (P2/P3)': chances_created,
            'Turnovers (P1)': turnovers,
            'Goal Agst Error (P1)': goals_agn_p1
        })
        
    player_df = pd.DataFrame(player_rows)
    if not player_df.empty:
        player_df = player_df.set_index('Player').sort_values(by='Points', ascending=False)
        st.dataframe(player_df, use_container_width=True)
    else:
        st.info("No player data available.")

with tab3:
    st.subheader("Filtered Raw Data")
    st.dataframe(filtered_df, use_container_width=True)
