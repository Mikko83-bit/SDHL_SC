import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Scoring Chances Analysis", layout="wide")
st.title("🏒 Scoring Chances Team & Players Analysis")

@st.cache_data
def load_data():
    with open("hockey_tag_data.csv", "r", encoding="utf-8") as f:
        first_line = f.readline().strip()
    skip = 1 if first_line.startswith("sep=") else 0
    df = pd.read_csv("hockey_tag_data.csv", skiprows=skip, sep=None, engine='python')
    
    all_possible_cols = [
        "Goal for", "Chance for", "Goal for PP", "Chance for PP",
        "Goal agn", "Chance agn", "Goal agn PP", "Chance agn PP", "Turnover"
    ]
    for col in all_possible_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    return df

df = load_data()

# Sivuvalikon suodattimet
st.sidebar.header("Filters")
games = st.sidebar.multiselect("Select Game", options=df["Game"].unique(), default=df["Game"].unique())
periods = st.sidebar.multiselect("Select Period", options=df["Period"].unique(), default=df["Period"].unique())

filtered_df = df[(df["Game"].isin(games)) & (df["Period"].isin(periods))]

# KPI-mittarit
total_gf = int(filtered_df["Goal for"].sum() + filtered_df["Goal for PP"].sum() if "Goal for PP" in filtered_df else filtered_df["Goal for"].sum())
total_ga = int(filtered_df["Goal agn"].sum())
total_cf = int(filtered_df["Chance for"].sum())
total_ca = int(filtered_df["Chance agn"].sum())
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
    numeric_cols = filtered_df.select_dtypes(include=['number']).columns.tolist()
    numeric_cols = [c for c in numeric_cols if c not in ["Game", "Period"]]
    desc_summary = filtered_df.groupby("Descriptor")[numeric_cols].sum()
    st.dataframe(desc_summary, use_container_width=True)

with tab2:
    st.subheader("Player Statistics by Role (For / Involved)")
    
    all_players = pd.unique(filtered_df[['Player 1', 'Player 2', 'Player 3']].values.ravel())
    players_list = [p for p in all_players if pd.notna(p) and str(p).strip() != '' and str(p).strip() != 'nan']
    
    player_rows = []
    for p in players_list:
        p_str = str(p).strip()
        
        # 1. Kun pelaaja on Player 1 (Pääasiallinen tekijä)
        df_p1 = filtered_df[filtered_df['Player 1'].astype(str).str.strip() == p_str]
        
        # 2. Kun pelaaja on Player 2 tai 3 (Mukana / INV)
        df_inv = filtered_df[
            (filtered_df['Player 2'].astype(str).str.strip() == p_str) | 
            (filtered_df['Player 3'].astype(str).str.strip() == p_str)
        ]
        
        # 3. Kun pelaaja on millä tahansa paikalla (käytetään puolustus-/agn-tilastoissa, jos halutaan kentällä olo)
        df_any = filtered_df[
            (filtered_df['Player 1'].astype(str).str.strip() == p_str) | 
            (filtered_df['Player 2'].astype(str).str.strip() == p_str) | 
            (filtered_df['Player 3'].astype(str).str.strip() == p_str)
        ]
        
        row_data = {
            'Player': p_str,
            'Goal for': int(df_p1['Goal for'].sum()) if 'Goal for' in df_p1 else 0,
            'Goal for INV': int(df_inv['Goal for'].sum()) if 'Goal for' in df_inv else 0,
            'Chance for': int(df_p1['Chance for'].sum()) if 'Chance for' in df_p1 else 0,
            'Chance for INV': int(df_inv['Chance for'].sum()) if 'Chance for' in df_inv else 0,
            'Goal for PP': int(df_p1['Goal for PP'].sum()) if 'Goal for PP' in df_p1 else 0,
            'Goal for PP inv': int(df_inv['Goal for PP'].sum()) if 'Goal for PP' in df_inv else 0,
            'Chance for PP': int(df_p1['Chance for PP'].sum()) if 'Chance for PP' in df_p1 else 0,
            'Chance for inv PP': int(df_inv['Chance for PP'].sum()) if 'Chance for PP' in df_inv else 0,
            'Goal agn': int(df_any['Goal agn'].sum()) if 'Goal agn' in df_any else 0,
            'Chance agn': int(df_any['Chance agn'].sum()) if 'Chance agn' in df_any else 0,
            'Goal agn PP': int(df_any['Goal agn PP'].sum()) if 'Goal agn PP' in df_any else 0,
            'Chance agn PP': int(df_any['Chance agn PP'].sum()) if 'Chance agn PP' in df_any else 0,
        }
        player_rows.append(row_data)
        
    player_df = pd.DataFrame(player_rows)
    if not player_df.empty:
        player_df = player_df.set_index('Player').sort_values(by='Goal for', ascending=False)
        st.dataframe(player_df, use_container_width=True)
    else:
        st.info("No player data available.")

with tab3:
    st.subheader("Team Performance: For vs Against by Category")
    
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
    
    if "Goal for" in team_df.columns and "Chance for" in team_df.columns:
        team_df["For"] = team_df["Goal for"] + team_df["Chance for"]
        team_df["Against"] = team_df["Goal agn"] + team_df["Chance agn"]
        
        team_summary = team_df.groupby("Category")[["For", "Against"]].sum().reset_index()
        
        plot_data = pd.melt(
            team_summary, 
            id_vars=["Category"], 
            value_vars=["For", "Against"],
            var_name="Type", 
            value_name="Count"
        )
        
        fig = px.bar(
            plot_data, 
            x="Category", 
            y="Count", 
            color="Type", 
            barmode="group",
            color_discrete_map={"For": "#1f77b4", "Against": "#d62728"}
        )
        fig.update_layout(xaxis_title="Category", yaxis_title="Total (Goals + Chances)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Tarvittavia sarakkeita ei löydy kaavion piirtämiseen.")

with tab4:
    st.subheader("Filtered Raw Data")
    st.dataframe(filtered_df, use_container_width=True)
