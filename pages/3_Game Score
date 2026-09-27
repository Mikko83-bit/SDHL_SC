import streamlit as st
import pandas as pd
import numpy as np

# Page configuration
st.set_page_config(
    page_title="SDHL Game Score Dashboard",
    page_icon="🏒",
    layout="wide"
)

st.title("🏒 SDHL Game Score -analyysityökalu (2026–2027)")
st.markdown("Tämä sivu laskee ja visualisoi pelaajien pelikohtaiset *Game Score* -pisteet InStat-tilastojen pohjalta.")

# File loading function
@st.cache_data
def load_data(file_path):
    try:
        # Load excel file
        df = pd.read_excel(file_path)
        return df
    except Exception as e:
        return None

# Path to the excel file
file_name = "Sdhl Game score 2026-2027.xlsx"

# Try loading data
df = load_data(file_name)

if df is None:
    st.error(f"Tiedostoa '{file_name}' ei löytynyt kansiosta. Varmista, että tiedosto on tallennettu samaan hakemistoon sovelluksen kanssa.")
    
    # Upload fallback widget
    uploaded_file = st.file_uploader("Tai lataa Excel-tiedosto manuaalisesti:", type=["xlsx"])
    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
    else:
        st.stop()

# Data preprocessing and Game Score calculation
# Ensure column names match and handle missing data using N-like logic
def calculate_game_score(row):
    try:
        goals = float(row.get('Goals', 0)) if pd.notna(row.get('Goals')) and row.get('Goals') != '-' else 0.0
        assists = float(row.get('Assists', 0)) if pd.notna(row.get('Assists')) and row.get('Assists') != '-' else 0.0
        shots = float(row.get('Shots on goal', 0)) if pd.notna(row.get('Shots on goal')) and row.get('Shots on goal') != '-' else 0.0
        net_xg = float(row.get('Net xG (xG player on - opp. team\'s xG)', 0)) if pd.notna(row.get('Net xG (xG player on - opp. team\'s xG)')) and row.get('Net xG (xG player on - opp. team\'s xG)') != '-' else 0.0
        fo_won = float(row.get('Faceoffs won', 0)) if pd.notna(row.get('Faceoffs won')) and row.get('Faceoffs won') != '-' else 0.0
        fo_lost = float(row.get('Faceoffs lost', 0)) if pd.notna(row.get('Faceoffs lost')) and row.get('Faceoffs lost') != '-' else 0.0
        
        # Game score formula: Goals*1.0 + Assists*0.7 + Shots*0.1 + Net xG*0.5 + (Faceoffs won - lost)*0.05
        score = (goals * 1.0) + (assists * 0.7) + (shots * 0.1) + (net_xg * 0.5) + ((fo_won - fo_lost) * 0.05)
        return round(score, 2)
    except:
        return 0.0

# Calculate Game Score for all rows if not already present
if 'Game Score' not in df.columns:
    df['Game Score'] = df.apply(calculate_game_score, axis=1)

# Sidebar filters
st.sidebar.header("Suodattimet")

# Filter by Player if column exists
if 'Player' in df.columns:
    all_players = sorted(df['Player'].dropna().unique())
    selected_players = st.sidebar.multiselect("Valitse pelaajat:", all_players, default=[])
else:
    selected_players = []

# Filter by Opponent if column exists
if 'Opponent' in df.columns:
    all_opponents = sorted(df['Opponent'].dropna().unique())
    selected_opponents = st.sidebar.multiselect("Vastustaja:", all_opponents, default=[])
else:
    selected_opponents = []

# Apply filters
filtered_df = df.copy()
if selected_players and 'Player' in filtered_df.columns:
    filtered_df = filtered_df[filtered_df['Player'].isin(selected_players)]
if selected_opponents and 'Opponent' in filtered_df.columns:
    filtered_df = filtered_df[filtered_df['Opponent'].isin(selected_opponents)]

# Main layout tabs
tab1, tab2, tab3 = st.tabs(["📊 Pelaajaprofiili & Kehitys", "🏆 Ottelun Leaderboard", "📁 Raakadata"])

with tab1:
    st.subheader("Pelaajan kehityskäyrä kauden aikana")
    if 'Player' in df.columns:
        player_list = sorted(df['Player'].dropna().unique())
        chosen_player = st.selectbox("Valitse tarkasteltava pelaaja:", player_list)
        
        player_df = df[df['Player'] == chosen_player]
        
        if not player_df.empty:
            # Display metrics
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Pelatut ottelut", len(player_df))
            col2.metric("Keskiarvo Game Score", round(player_df['Game Score'].mean(), 2))
            col3.metric("Kokonaismaalit", int(player_df['Goals'].replace('-', 0).sum()) if 'Goals' in player_df.columns else 0)
            col4.metric("Kokonaisyötöt", int(player_df['Assists'].replace('-', 0).sum()) if 'Assists' in player_df.columns else 0)
            
            # Line chart over time / games
            if 'Date' in player_df.columns or 'Game ID' in player_df.columns:
                x_axis = 'Date' if 'Date' in player_df.columns else 'Game ID'
                chart_data = player_df.sort_values(by=x_axis)
                st.line_chart(chart_data.set_index(x_axis)['Game Score'])
            else:
                st.line_chart(player_df['Game Score'])
        else:
            st.info("Ei dataa valitulle pelaajalle.")
    else:
        st.warning("Pelaajasaraketta ('Player') ei löytynyt tiedostosta.")

with tab2:
    st.subheader("Ottelukohtainen Top-lista (Game Score)")
    if 'Game ID' in df.columns or 'Date' in df.columns:
        game_col = 'Game ID' if 'Game ID' in df.columns else 'Date'
        game_list = sorted(df[game_col].dropna().unique())
        chosen_game = st.selectbox("Valitse ottelu:", game_list)
        
        game_df = df[df[game_col] == chosen_game]
        
        if not game_df.empty:
            # Sort by Game Score descending
            leaderboard = game_df.sort_values(by='Game Score', ascending=False)
            
            # Select key display columns if available
            display_cols = [c for c in ['Player', 'Position', 'Goals', 'Assists', 'Shots on goal', 'Net xG (xG player on - opp. team\'s xG)', 'Game Score'] if c in leaderboard.columns]
            
            st.dataframe(leaderboard[display_cols], use_container_width=True)
    else:
        st.info("Ottelutunnistetta ('Game ID' tai 'Date') ei löytynyt tiedostosta.")

with tab3:
    st.subheader("Suodatettu raakadata")
    st.dataframe(filtered_df, use_container_width=True)
