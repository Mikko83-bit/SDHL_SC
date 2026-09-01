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
    
    # Poistetaan sarakkeiden nimistä ylimääräiset välilyönnit
    df.columns = df.columns.astype(str).str.strip()
    
    # Siivotaan pelaajasarakkeet: poistetaan desimaalit jos niitä syntyy, ja muutetaan merkkijonoiksi
    for player_col in ['Player 1', 'Player 2', 'Player 3']:
        if player_col in df.columns:
            df[player_col] = pd.to_numeric(df[player_col], errors='coerce')
            df[player_col] = df[player_col].fillna(-1).astype(int).astype(str)
            df.loc[df[player_col] == '-1', player_col] = ''
            
    # Täytetään numeeriset sarakkeet nollilla
    numeric_cols = [
        "Goal for", "Chance for", "Goal for PP", "Chance for PP",
        "Goal agn", "Chance agn", "Goal agn PP", "Chance agn PP", "Turnover"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    return df

df = load_data()

# Sivuvalikon suodattimet
st.sidebar.header("Filters")
games = st.sidebar.multiselect("Select Game", options=df["Game"].unique(), default=df["Game"].unique()) if "Game" in df.columns else []
periods = st.sidebar.multiselect("Select Period", options=df["Period"].unique(), default=df["Period"].unique()) if "Period" in df.columns else []

filtered_df = df.copy()
if "Game" in df.columns and games:
    filtered_df = filtered_df[filtered_df["Game"].isin(games)]
if "Period" in df.columns and periods:
    filtered_df = filtered_df[filtered_df["Period"].isin(periods)]

# KPI-mittarit
total_gf = int(filtered_df["Goal for"].sum() if "Goal for" in filtered_df else 0)
total_ga = int(filtered_df["Goal agn"].sum() if "Goal agn" in filtered_df else 0)
total_cf = int(filtered_df["Chance for"].sum() if "Chance for" in filtered_df else 0)
total_ca = int(filtered_df["Chance agn"].sum() if "Chance agn" in filtered_df else 0)
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
    if "Descriptor" in filtered_df.columns:
        num_cols = filtered_df.select_dtypes(include=['number']).columns.tolist()
        num_cols = [c for c in num_cols if c not in ["Game", "Period"]]
        desc_summary = filtered_df.groupby("Descriptor")[num_cols].sum()
        st.dataframe(desc_summary, use_container_width=True)
    else:
        st.warning("Descriptor-saraketta ei löydy datasta.")

with tab2:
    st.subheader("Player Statistics by Role (For / Involved)")
    
    if all(col in filtered_df.columns for col in ['Player 1', 'Player 2', 'Player 3']):
        all_players = pd.unique(filtered_df[['Player 1', 'Player 2', 'Player 3']].values.ravel())
        players_list = [p for p in all_players if pd.notna(p) and str(p).strip() != '' and str(p).strip() != 'nan']
        
        player_rows = []
        for p in players_list:
            p_str = str(p).strip()
            
            # Roolit: Player 1 = pääasiallinen tekijä, Player 2 & 3 = mukana (INV)
            df_p1 = filtered_df[filtered_df['Player 1'] == p_str]
            df_inv = filtered_df[
                (filtered_df['Player 2'] == p_str) | 
                (filtered_df['Player 3'] == p_str)
            ]
            df_agn = filtered_df[
                (filtered_df['Player 1'] == p_str) | 
                (filtered_df['Player 2'] == p_str) | 
                (filtered_df['Player 3'] == p_str)
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
                'Goal agn': int(df_agn['Goal agn'].sum()) if 'Goal agn' in df_agn else 0,
                'Chance agn': int(df_agn['Chance agn'].sum()) if 'Chance agn' in df_agn else 0,
                'Goal agn PP': int(df_agn['Goal agn PP'].sum()) if 'Goal agn PP' in df_agn else 0,
                'Chance agn PP': int(df_agn['Chance agn PP'].sum()) if 'Chance agn PP' in df_agn else 0,
            }
            player_rows.append(row_data)
            
        player_df = pd.DataFrame(player_rows)
        if not player_df.empty:
            sort_col = "Goal for" if "Goal for" in player_df.columns else player_df.columns[1]
            player_df = player_df.set_index('Player').sort_values(by=sort_col, ascending=False)
            st.dataframe(player_df, use_container_width=True)
        else:
            st.info("No player data available.")
    else:
        st.warning("Player 1, Player 2 tai Player 3 -sarakkeita ei löydy datasta.")

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
            
    if "Descriptor" in filtered_df.columns and "Goal for" in filtered_df.columns:
        team_df = filtered_df.copy()
        team_df["Category"] = team_df["Descriptor"].apply(get_category)
        
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
