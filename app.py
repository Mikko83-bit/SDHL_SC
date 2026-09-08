import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="SDHL Scoring Chances Analysis", layout="wide")
st.title("🏒 SDHL Scoring Chances Analysis")

@st.cache_data
def load_data():
    excel_path = "SDHL 2026-2027 scoring chances.xlsx"
    xls = pd.ExcelFile(excel_path)
    
    players_df = pd.read_excel(xls, sheet_name="Players")
    team_df = pd.read_excel(xls, sheet_name="Team")
    
    players_df.columns = players_df.columns.astype(str).str.strip()
    team_df.columns = team_df.columns.astype(str).str.strip()
    
    if 'Number' in players_df.columns:
        players_df['Number'] = pd.to_numeric(players_df['Number'], errors='coerce').fillna(-1).astype(int).astype(str)
        players_df.loc[players_df['Number'] == '-1', 'Number'] = ''
        
    p_num_cols = [c for c in players_df.columns if c not in ['Number', 'Game']]
    for col in p_num_cols:
        players_df[col] = pd.to_numeric(players_df[col], errors='coerce').fillna(0)
        
    t_num_cols = [c for c in team_df.columns if c not in ['Descriptor', 'Game']]
    for col in t_num_cols:
        team_df[col] = pd.to_numeric(team_df[col], errors='coerce').fillna(0)
        
    return players_df, team_df

players_df, team_df = load_data()

all_games = sorted(list(set(players_df['Game'].dropna().unique().tolist() + team_df['Game'].dropna().unique().tolist()))) if 'Game' in players_df.columns else []
all_players = sorted([p for p in players_df['Number'].unique() if p != ''])
all_descriptors = sorted(team_df['Descriptor'].dropna().unique().tolist()) if 'Descriptor' in team_df.columns else []

# Sivuvalikon suodattimet
st.sidebar.header("Filters")
selected_games = st.sidebar.multiselect("Select Game", options=all_games, default=all_games)
selected_players = st.sidebar.multiselect("Select Player Number", options=all_players, default=all_players)
selected_descriptors = st.sidebar.multiselect("Select Descriptor", options=all_descriptors, default=all_descriptors)

# Suodatetaan data
filtered_players = players_df.copy()
if 'Game' in filtered_players.columns and selected_games:
    filtered_players = filtered_players[filtered_players['Game'].isin(selected_games)]
if 'Number' in filtered_players.columns and selected_players:
    filtered_players = filtered_players[filtered_players['Number'].isin(selected_players)]

filtered_team = team_df.copy()
if 'Game' in filtered_team.columns and selected_games:
    filtered_team = filtered_team[filtered_team['Game'].isin(selected_games)]
if 'Descriptor' in filtered_team.columns and selected_descriptors:
    filtered_team = filtered_team[filtered_team['Descriptor'].isin(selected_descriptors)]

# KPI-mittarit Team-datasta
total_gf = int(filtered_team['Goal For'].sum() + filtered_team['PP goal'].sum()) if 'Goal For' in filtered_team.columns else 0
total_ga = int(filtered_team['Goal Against'].sum() + filtered_team['PP goal ag'].sum()) if 'Goal Against' in filtered_team.columns else 0
total_cf = int(filtered_team['Chance For'].sum() + filtered_team['PP chance'].sum()) if 'Chance For' in filtered_team.columns else 0
total_ca = int(filtered_team['Chance Against'].sum() + filtered_team['PP chance ag'].sum()) if 'Chance Against' in filtered_team.columns else 0
total_net = (total_gf + total_cf) - (total_ga + total_ca)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Goals For", total_gf)
col2.metric("Goals Against", total_ga)
col3.metric("Scoring Chances For", total_cf)
col4.metric("Chances Against", total_ca)
col5.metric("Total (Net)", total_net)

st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Scoring Chances Team", 
    "👤 Scoring Chances Players", 
    "📈 Visuals", 
    "📄 Raw Data"
])

with tab1:
    st.subheader("Team Statistics by Descriptor")
    if not filtered_team.empty:
        num_cols = filtered_team.select_dtypes(include=['number']).columns.tolist()
        num_cols = [c for c in num_cols if c != "Game"]
        team_summary = filtered_team.groupby("Descriptor")[num_cols].sum()
        st.dataframe(team_summary, use_container_width=True)
    else:
        st.info("No team data available for selected filters.")

with tab2:
    st.subheader("Player Statistics")
    if not filtered_players.empty:
        p_num_cols = [c for c in filtered_players.select_dtypes(include=['number']).columns.tolist() if c != "Game"]
        player_summary = filtered_players.groupby("Number")[p_num_cols].sum().reset_index()
        
        sort_col = "Goal For" if "Goal For" in player_summary.columns else player_summary.columns[1]
        player_summary = player_summary.set_index('Number').sort_values(by=sort_col, ascending=False)
        
        st.dataframe(player_summary, use_container_width=True)
    else:
        st.info("No player data available for selected filters.")

with tab3:
    st.subheader("Team Performance Overview")
    if not filtered_team.empty:
        chart_data = filtered_team.groupby("Descriptor")[["Goal For", "Chance For", "Goal Against", "Chance Against"]].sum().reset_index()
        chart_data["For Total"] = chart_data["Goal For"] + chart_data["Chance For"]
        chart_data["Against Total"] = chart_data["Goal Against"] + chart_data["Chance Against"]
        
        plot_df = pd.melt(
            chart_data, 
            id_vars=["Descriptor"], 
            value_vars=["For Total", "Against Total"],
            var_name="Type", 
            value_name="Count"
        )
        
        fig = px.bar(
            plot_df, 
            x="Descriptor", 
            y="Count", 
            color="Type", 
            barmode="group",
            color_discrete_map={"For Total": "#1f77b4", "Against Total": "#d62728"}
        )
        fig.update_layout(xaxis_title="Descriptor", yaxis_title="Total Count")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Ei dataa kaavion piirtämiseen.")

with tab4:
    st.subheader("Raw Data Sheets")
    st.markdown("### Players Sheet")
    st.dataframe(filtered_players, use_container_width=True)
    st.markdown("### Team Sheet")
    st.dataframe(filtered_team, use_container_width=True)
    
