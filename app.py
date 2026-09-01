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
total_gf = int(filtered_df["Goal for"].sum() + filtered_df["Goal for PP"].sum())
total_ga = int(filtered_df["Goal agn"].sum() + filtered_df["Goal agn PP"].sum())
total_cf = int(filtered_df["Chance for"].sum() + filtered_df["Chance for PP"].sum())
total_ca = int(filtered_df["Chance agn"].sum() + filtered_df["Chance agn PP"].sum())
total_net = (total_gf + total_cf) - (total_ga + total_ca)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Goals For", total_gf)
col2.metric("Goals Against", total_ga)
col3.metric("Scoring Chances For", total_cf)
col4.metric("Chances Against", total_ca)
col5.metric("Total (Net)", total_net)

st.markdown("---")

# 4. Välilehdet
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Scoring Chances Team", 
    "👤 Scoring Chances Players", 
    "📈 Visuals", 
    "📄 Raw Data"
])

with tab1:
    st.subheader("Team Statistics by Category (OZP / Rush / Takeaway)")
    
    def get_category(desc):
        d = str(desc).lower()
        if "ozp" in d:
            return "OZP"
        elif "rush" in d:
            return "Rush"
        elif "takeaway" in d:
            return "Takeaway"
        else:
            return "Other"
            
    team_df = filtered_df.copy()
    team_df["Category"] = team_df["Descriptor"].apply(get_category)
    
    team_summary = team_df.groupby("Category")[
        ["Goal for", "Chance for", "Goal for PP", "Chance for PP", 
         "Goal agn", "Chance agn", "Goal agn PP", "Chance agn PP"]
    ].sum()
    
    team_summary["Total (Net)"] = (team_summary["Goal for"] + team_summary["Chance for"]) - (team_summary["Goal agn"] + team_summary["Chance agn"])
    st.dataframe(team_summary, use_container_width=True)

with tab2:
    st.subheader("Player Statistics by Outcome Columns")
    
    outcome_cols = [
        "Goal for", "Chance for", "Goal for PP", "Chance for PP", 
        "Goal agn", "Chance agn", "Goal agn PP", "Chance agn PP", "Turnover"
    ]
    
    all_players = pd.unique(filtered_df[['Player 1', 'Player 2', 'Player 3']].values.ravel())
    players_list = [p for p in all_players if pd.notna(p) and str(p).strip() != '']
    
    player_rows = []
    for p in players_list:
        row_data = {'Player': p}
        p_mask = (filtered_df['Player 1'] == p) | (filtered_df['Player 2'] == p) | (filtered_df['Player 3'] == p)
        p_df = filtered_df[p_mask]
        
        for col in outcome_cols:
            row_data[col] = int(p_df[col].sum())
            
        row_data['Total (5v5 Net)'] = (row_data['Goal for'] + row_data['Chance for']) - (row_data['Goal agn'] + row_data['Chance agn'])
        player_rows.append(row_data)
        
    player_df = pd.DataFrame(player_rows)
    if not player_df.empty:
        player_df = player_df.set_index('Player').sort_values(by='Total (5v5 Net)', ascending=False)
        st.dataframe(player_df, use_container_width=True)
    else:
        st.info("No player data available.")

with tab3:
    st.subheader("Visualizations & Performance Charts")
    if not player_df.empty:
        st.markdown("### Player Net Performance (5v5 Net)")
        st.bar_chart(player_df[['Total (5v5 Net)']])
    else:
        st.info("No data available for charts.")

with tab4:
    st.subheader("Filtered Raw Data")
    st.dataframe(filtered_df, use_container_width=True)
