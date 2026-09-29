import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Page configuration
st.set_page_config(page_title="SDHL Game Score Analysis", page_icon="🏒", layout="wide")

st.title("🏒 SDHL Game Score Analysis Tool (2026–2027)")
st.write("This page calculates player game-by-game *Game Score* values using an xG-based formula directly from raw data.")

# File loading
EXCEL_FILE = "Sdhl Game score 2026-2027.xlsx"

@st.cache_data
def load_data(file_path):
    try:
        df = pd.read_excel(file_path)
        df.columns = [str(col).strip() for col in df.columns]
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
        return df
    except Exception as e:
        try:
            df = pd.read_excel(f"../{file_path}")
            df.columns = [str(col).strip() for col in df.columns]
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
            return df
        except Exception as e2:
            st.error(f"Error reading file: {e2}")
            return None

df = load_data(EXCEL_FILE)

if df is None:
    st.error(f"An error occurred while reading the file '{EXCEL_FILE}'. Please ensure the file is in the correct folder.")
else:
    # Helper function for safe column retrieval with zero-handling
    def get_col(data, col_name):
        if col_name in data.columns:
            return pd.to_numeric(data[col_name], errors='coerce').fillna(0)
        return 0

    # Helper function to convert time on ice (MM:SS or number) to decimal minutes
    def parse_toi(val):
        if pd.isna(val):
            return 0.0
        val_str = str(val).strip()
        if ':' in val_str:
            try:
                parts = val_str.split(':')
                minutes = float(parts[0])
                seconds = float(parts[1])
                return minutes + (seconds / 60.0)
            except:
                return 0.0
        else:
            try:
                return float(val_str)
            except:
                return 0.0

    # Find columns based on exact names
    col_goals = next((c for c in df.columns if c.lower() == 'goals'), None)
    col_a1 = next((c for c in df.columns if c.lower() == 'first assist'), None)
    col_a2 = next((c for c in df.columns if c.lower() == 'second assist'), None)
    col_sog = next((c for c in df.columns if c.lower() == 'shots on goal'), None)
    col_blk = next((c for c in df.columns if c.lower() == 'blocked shots'), None)
    col_pd = next((c for c in df.columns if c.lower() == 'penalties drawn'), None)
    col_pt = next((c for c in df.columns if c.lower() == 'penalty time'), None)
    col_fow = next((c for c in df.columns if c.lower() == 'faceoffs won'), None)
    col_fol = next((c for c in df.columns if c.lower() == 'faceoffs lost'), None)
    
    col_xg_on = next((c for c in df.columns if c.lower() in ['xgs with a player on', 'xg with a player on']), None)
    col_opp_xg_on = next((c for c in df.columns if 'opponent' in c.lower() and 'xg' in c.lower()), None)
    
    col_gf = next((c for c in df.columns if c.lower() == 'plus'), None)
    col_ga = next((c for c in df.columns if c.lower() == 'minus'), None)

    # Find time on ice and position columns
    col_toi = next((c for c in df.columns if any(k in c.lower() for k in ['time on ice', 'toi', 'minutes', 'min'])), None)
    col_pos = next((c for c in df.columns if c.lower() == 'position'), None)

    # Convert to clean numeric series
    g = get_col(df, col_goals)
    a1 = get_col(df, col_a1)
    a2 = get_col(df, col_a2)
    sog = get_col(df, col_sog)
    blk = get_col(df, col_blk)
    pd_val = get_col(df, col_pd)
    pt_val = get_col(df, col_pt)
    fow = get_col(df, col_fow)
    fol = get_col(df, col_fol)
    xg_for = get_col(df, col_xg_on)
    xg_against = get_col(df, col_opp_xg_on)
    gf = get_col(df, col_gf)
    ga = get_col(df, col_ga)

    # Store cleaned values in dataframe
    df['Goals_clean'] = g
    df['Assists_clean'] = a1 + a2
    df['Shots_clean'] = sog
    df['Block_clean'] = blk
    
    if col_toi:
        df['TOI_clean'] = df[col_toi].apply(parse_toi)
    else:
        df['TOI_clean'] = 0.0

    if col_pos:
        df['Pos_clean'] = df[col_pos].astype(str).str.upper().str.strip()
    else:
        df['Pos_clean'] = 'UNKNOWN'

    # Game Score formula
    df['Game_Score'] = (
        (0.75 * g) + 
        (0.7 * a1) + 
        (0.55 * a2) + 
        (0.075 * sog) + 
        (0.05 * blk) + 
        (0.15 * pd_val) - 
        (0.15 * pt_val) + 
        (0.01 * fow) - 
        (0.01 * fol) + 
        (0.05 * xg_for) - 
        (0.05 * xg_against) + 
        (0.15 * gf) - 
        (0.15 * ga)
    )

    player_col = next((c for c in df.columns if 'player' in c.lower()), None)
    team_col = next((c for c in df.columns if c.lower() == 'team'), None)
    opponent_col = next((c for c in df.columns if 'opponent' in c.lower()), None)

    # --- SIDEBAR: FILTERS ---
    st.sidebar.header("🔍 Filters")
    
    # 1. Team selection
    if team_col:
        all_teams = sorted(df[team_col].dropna().unique())
        selected_teams = st.sidebar.multiselect("Select your team:", all_teams, default=all_teams)
        if selected_teams:
            df_filtered = df[df[team_col].isin(selected_teams)]
        else:
            df_filtered = df.copy()
    else:
        df_filtered = df.copy()

    # 2. Opponent selection
    if opponent_col:
        all_opponents = sorted(df[opponent_col].dropna().unique())
        selected_opponents = st.sidebar.multiselect("Select opponent(s):", all_opponents, default=all_opponents)
        if selected_opponents:
            df_filtered = df_filtered[df_filtered[opponent_col].isin(selected_opponents)]

    # 3. Position selection (F / D)
    st.sidebar.subheader("🏒 Position")
    selected_positions = st.sidebar.multiselect("Select position:", ['F', 'D'], default=['F', 'D'])
    if col_pos and selected_positions:
        df_filtered = df_filtered[df_filtered['Pos_clean'].isin(selected_positions)]

    # 4. Time on ice filter for baseline comparison
    st.sidebar.subheader("⚖️ Average Comparison Baseline")
    min_toi_filter = 0.0
    if col_toi:
        min_toi_filter = st.sidebar.slider("Min. average time on ice (min/game):", 0.0, 30.0, 0.0, 0.5)
    else:
        st.sidebar.info("Time on ice column not found automatically.")

    # Filter baseline cohort for averages
    if player_col and col_toi:
        player_toi_means = df_filtered.groupby(player_col)['TOI_clean'].mean()
        regular_players = player_toi_means[player_toi_means >= min_toi_filter].index
        df_vertailu = df_filtered[df_filtered[player_col].isin(regular_players)]
    else:
        df_vertailu = df_filtered

    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Player Profile & Progression", 
        "🏆 Season Stats & Leaderboard", 
        "📈 Game-by-Game Scores", 
        "📁 Raw Data"
    ])

    with tab1:
        st.subheader("Player Progression Curve During the Season")
        if player_col:
            players = sorted(df_filtered[player_col].dropna().unique())
            if len(players) > 0:
                selected_player = st.selectbox("Select player to view:", players, key='tab1_player')
                player_df = df_filtered[df_filtered[player_col] == selected_player].sort_values(by='Date')

                if not player_df.empty:
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Games Played", len(player_df))
                    with col2:
                        st.metric("Average Game Score", round(player_df['Game_Score'].mean(), 2))
                    with col3:
                        st.metric("Total Goals", int(player_df['Goals_clean'].sum()))
                    with col4:
                        st.metric("Total Assists", int(player_df['Assists_clean'].sum()))

                    fig = px.line(
                        player_df, x='Date', y='Game_Score', markers=True,
                        labels={'Date': 'Game Date', 'Game_Score': 'Game Score'},
                        title=f"Player {selected_player} Game Score Game History"
                    )
                    fig.update_layout(xaxis_type='category')
                    st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("🏆 Player Leaderboard (Season Stats)")
        if player_col:
            group_cols = [player_col]
            if team_col in df_filtered.columns:
                group_cols.append(team_col)
            if col_pos:
                group_cols.append('Pos_clean')

            agg_kwargs = {
                'Games': pd.NamedAgg(column='Game_Score', aggfunc='count'),
                'GS Average': pd.NamedAgg(column='Game_Score', aggfunc='mean'),
                'GS Total': pd.NamedAgg(column='Game_Score', aggfunc='sum'),
                'Goals': pd.NamedAgg(column='Goals_clean', aggfunc='sum'),
                'Assists': pd.NamedAgg(column='Assists_clean', aggfunc='sum'),
                'Shots': pd.NamedAgg(column='Shots_clean', aggfunc='sum')
            }
            if col_toi:
                agg_kwargs['Avg. Time on Ice (min)'] = pd.NamedAgg(column='TOI_clean', aggfunc='mean')

            leaderboard = df_filtered.groupby(group_cols).agg(**agg_kwargs).reset_index()

            rename_map = {player_col: 'Player'}
            if team_col in df_filtered.columns:
                rename_map[team_col] = 'Team'
            if col_pos:
                rename_map['Pos_clean'] = 'Position'
            
            leaderboard = leaderboard.rename(columns=rename_map)

            if col_toi and min_toi_filter > 0 and 'Avg. Time on Ice (min)' in leaderboard.columns:
                leaderboard = leaderboard[leaderboard['Avg. Time on Ice (min)'] >= min_toi_filter]
                leaderboard['Avg. Time on Ice (min)'] = leaderboard['Avg. Time on Ice (min)'].round(2)

            if 'GS Average' in leaderboard.columns:
                leaderboard['GS Average'] = leaderboard['GS Average'].round(2)
            if 'GS Total' in leaderboard.columns:
                leaderboard['GS Total'] = leaderboard['GS Total'].round(2)

            st.dataframe(leaderboard.sort_values(by="GS Average", ascending=False), use_container_width=True, hide_index=True)

    with tab3:
        st.subheader("📊 Player Game-by-Game Game Score vs Averages")
        
        if player_col:
            players = sorted(df_filtered[player_col].dropna().unique())
            selected_player_bar = st.selectbox("Select player for analysis:", players, key='bar_player')
            
            player_df = df_filtered[df_filtered[player_col] == selected_player_bar].sort_values(by='Date')
            
            if not player_df.empty:
                player_oma_ka = player_df['Game_Score'].mean()
                sdhl_ka = df_vertailu['Game_Score'].mean()
                
                if team_col:
                    pelaajan_tiimi = player_df[team_col].iloc[0]
                    tiimi_df = df_vertailu[df_vertailu[team_col] == pelaajan_tiimi]
                    tiimi_ka = tiimi_df['Game_Score'].mean() if not tiimi_df.empty else 0
                    tiimi_nimi = pelaajan_tiimi
                else:
                    tiimi_ka = None
                    tiimi_nimi = "Team"

                fig_bar = px.bar(
                    player_df, 
                    x='Date', 
                    y='Game_Score',
                    title=f"Player {selected_player_bar} Game-by-Game Game Score",
                    labels={'Date': 'Game Date', 'Game_Score': 'Game Score'},
                    text_auto='.2f'
                )
                fig_bar.update_traces(marker_color='#00b4d8')

                fig_bar.add_hline(
                    y=sdhl_ka, 
                    line_dash="dash", 
                    line_color="#adb5bd", 
                    annotation_text=f"SDHL Average ({sdhl_ka:.2f})", 
                    annotation_position="bottom right",
                    annotation_font_color="#adb5bd"
                )

                if team_col and not pd.isna(tiimi_ka):
                    fig_bar.add_hline(
                        y=tiimi_ka, 
                        line_dash="dot", 
                        line_color="#ffb703", 
                        annotation_text=f"{tiimi_nimi} Average ({tiimi_ka:.2f})", 
                        annotation_position="top right",
                        annotation_font_color="#ffb703"
                    )

                fig_bar.add_hline(
                    y=player_oma_ka, 
                    line_dash="solid", 
                    line_color="#2ec4b6", 
                    annotation_text=f"Player Average ({player_oma_ka:.2f})", 
                    annotation_position="bottom left",
                    annotation_font_color="#2ec4b6"
                )

                fig_bar.update_layout(
                    xaxis_type='category',
                    yaxis_title="Game Score",
                    xaxis_title="Game Date",
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)'
                )

                st.plotly_chart(fig_bar, use_container_width=True)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Player Average", f"{player_oma_ka:.2f}")
                with col2:
                    st.metric("SDHL Average (filtered)", f"{sdhl_ka:.2f}")
                with col3:
                    if team_col:
                        st.metric(f"{tiimi_nimi} Average (filtered)", f"{tiimi_ka:.2f}")

    with tab4:
        st.subheader("Raw Data and Calculated Game Score Values")
        st.dataframe(df_filtered, use_container_width=True)
