import streamlit as st
import pandas as pd
import plotly.express as px

# Page configuration
st.set_page_config(page_title="SDHL Game Score Analysis", page_icon="🏒", layout="wide")

st.title("🏒 SDHL Game Score Analysis Tool (2026–2027) - 5v5 Net Rating Model")

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

if df is not None:
    # Helper functions
    def get_col(data, col_name):
        if col_name in data.columns:
            return pd.to_numeric(data[col_name], errors='coerce').fillna(0)
        return 0

    def parse_toi(val):
        if pd.isna(val):
            return 0.0
        val_str = str(val).strip()
        if ':' in val_str:
            try:
                parts = val_str.split(':')
                return float(parts[0]) + (float(parts[1]) / 60.0)
            except:
                return 0.0
        else:
            try:
                return float(val_str)
            except:
                return 0.0

    # Column mappings (tukee joustavasti erilaisia sarakkeiden nimiä Excelissä)
    col_goals = next((c for c in df.columns if c.lower() == 'goals'), None)
    col_a1 = next((c for c in df.columns if c.lower() in ['first assist', 'assist 1', 'a1']), None)
    col_a2 = next((c for c in df.columns if c.lower() in ['second assist', 'assist 2', 'a2']), None)
    col_sog = next((c for c in df.columns if c.lower() in ['shots on goal', 'sog', 'shots']), None)
    col_blk = next((c for c in df.columns if c.lower() in ['blocked shots', 'blocks']), None)
    col_pd = next((c for c in df.columns if c.lower() == 'penalties drawn'), None)
    col_pt = next((c for c in df.columns if c.lower() in ['penalty time', 'pim']), None)
    col_fow = next((c for c in df.columns if c.lower() == 'faceoffs won'), None)
    col_fol = next((c for c in df.columns if c.lower() == 'faceoffs lost'), None)
    
    col_xg_on = next((c for c in df.columns if c.lower() in ['xgs with a player on', 'xg with a player on', 'ixg', 'xg for']), None)
    col_opp_xg_on = next((c for c in df.columns if 'opponent' in c.lower() and 'xg' in c.lower() or 'xg against' in c.lower()), None)
    
    col_gf = next((c for c in df.columns if c.lower() in ['plus', 'goals for', 'gf']), None)
    col_ga = next((c for c in df.columns if c.lower() in ['minus', 'goals against', 'ga']), None)
    col_toi = next((c for c in df.columns if any(k in c.lower() for k in ['time on ice', 'toi', 'minutes', 'min'])), None)
    col_pos = next((c for c in df.columns if c.lower() == 'position'), None)

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

    df['Goals_clean'] = g
    df['Assists_clean'] = a1 + a2
    df['Shots_clean'] = sog
    df['Block_clean'] = blk
    df['TOI_clean'] = df[col_toi].apply(parse_toi) if col_toi else 0.0
    df['Pos_clean'] = df[col_pos].astype(str).str.upper().str.strip() if col_pos else 'F'

    # --- 5v5 NET RATING / GAME SCORE -MALLI (Offensiv / Defensiv erittely) ---
    # Erotellaan painotukset hyökkääjille (F) ja puolustajille (D) jakamasi mallin hengessä
    is_def = df['Pos_clean'] == 'D'

    # Offensiiviset komponentit (Mål, Assists, Shots/xG, On-ice Mål för)
    off_indiv = (0.75 * g) + (0.7 * a1) + (0.55 * a2) + (0.075 * sog) + (0.05 * xg_for)
    # Puolustajille annetaan hieman isompi painoarvo laukauksissa/on-ice hyökkäyksessä
    off_onice = df.apply(lambda row: (0.425 * gf[row.name] + 0.05 * fow[row.name]) if row['Pos_clean'] == 'D' else (0.625 * gf[row.name] + 0.01 * fow[row.name]), axis=1)
    df['Offensive_Score'] = off_indiv + off_onice

    # Defensiiviset komponentit (Utvisningar miinuksena, On-ice Mål bakåt / xG against)
    def_penalties = (0.15 * pd_val) - (0.15 * pt_val) - (0.01 * fol)
    def_onice = df.apply(lambda row: (-0.575 * ga[row.name] - 0.05 * xg_against[row.name]) if row['Pos_clean'] == 'D' else (-0.4375 * ga[row.name] - 0.05 * xg_against[row.name]), axis=1)
    df['Defensive_Score'] = def_penalties + def_onice

    # Kokonais Game Score
    df['Game_Score'] = df['Offensive_Score'] + df['Defensive_Score']

    player_col = next((c for c in df.columns if 'player' in c.lower()), None)
    team_col = next((c for c in df.columns if c.lower() == 'team'), None)
    opponent_col = next((c for c in df.columns if 'opponent' in c.lower()), None)

    # --- SIDEBAR: FILTERS ---
    st.sidebar.header("🔍 Filters")
    
    if team_col:
        all_teams = sorted(df[team_col].dropna().unique())
        selected_teams = st.sidebar.multiselect("Select your team:", all_teams, default=all_teams)
        df_filtered = df[df[team_col].isin(selected_teams)] if selected_teams else df.copy()
    else:
        df_filtered = df.copy()

    st.sidebar.subheader("🏒 Position")
    selected_positions = st.sidebar.multiselect("Select position:", ['F', 'D'], default=['F', 'D'])
    if col_pos and selected_positions:
        df_filtered = df_filtered[df_filtered['Pos_clean'].isin(selected_positions)]

    min_toi_filter = st.sidebar.slider("Min. average time on ice (min/game):", 0.0, 30.0, 0.0, 0.5) if col_toi else 0.0

    if player_col and col_toi:
        player_toi_means = df_filtered.groupby(player_col)['TOI_clean'].mean()
        regular_players = player_toi_means[player_toi_means >= min_toi_filter].index
        df_vertailu = df_filtered[df_filtered[player_col].isin(regular_players)]
    else:
        df_vertailu = df_filtered

    # --- PLAYER CARD DIALOG ---
    @st.dialog("Player Card", width="large")
    def show_player_card(player_name):
        p_df = df_filtered[df_filtered[player_col] == player_name].sort_values(by='Date')
        if p_df.empty:
            st.warning("No data found for this player.")
            return

        team_val = p_df[team_col].iloc[0] if team_col else "SDHL"
        gp = len(p_df)
        total_toi = p_df['TOI_clean'].sum()

        st.markdown(f"### 🏒 {player_name} &nbsp;|&nbsp; <span style='color:gray; font-size:16px;'>{team_val} | 5v5 Model | {gp} GP | {int(total_toi)} min</span>", unsafe_allow_html=True)
        st.markdown("---")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("GAME SCORE (Avg)", f"{p_df['Game_Score'].mean():.2f}")
        with col2:
            st.metric("OFFENSIVE (Avg)", f"{p_df['Offensive_Score'].mean():.2f}")
        with col3:
            st.metric("DEFENSIVE (Avg)", f"{p_df['Defensive_Score'].mean():.2f}")
        with col4:
            st.metric("TOTAL GOALS", int(p_df['Goals_clean'].sum()))

        st.markdown("### 📈 Season Trend Charts")
        
        fig_gs = px.line(p_df, x='Date', y='Game_Score', markers=True, title="Game Score Game History (5v5)")
        fig_gs.update_layout(xaxis_type='category', margin=dict(l=20, r=20, t=30, b=20), height=230)
        st.plotly_chart(fig_gs, use_container_width=True)

        if col_toi:
            fig_toi = px.line(p_df, x='Date', y='TOI_clean', markers=True, title="Time on Ice (Minutes per Match)")
            fig_toi.update_layout(xaxis_type='category', margin=dict(l=20, r=20, t=30, b=20), height=230)
            st.plotly_chart(fig_toi, use_container_width=True)

    # --- NAVIGATION ---
    selected_tab = st.radio(
        "Navigation",
        [
            "🏆 Season Leaderboard", 
            "📊 Player Progression", 
            "📈 Game-by-Game Scores", 
            "📁 Raw Data"
        ],
        horizontal=True,
        label_visibility="collapsed"
    )
    st.markdown("---")

    if selected_tab == "🏆 Season Leaderboard":
        st.subheader("🏆 Player Leaderboard (5v5 Model)")
        st.caption("Klikkaa mitä tahansa pelaajariviä taulukosta avataksesi pelaajakortin.")
        
        if player_col:
            group_cols = [player_col]
            if team_col in df_filtered.columns:
                group_cols.append(team_col)
            if col_pos:
                group_cols.append('Pos_clean')

            agg_kwargs = {
                'Games': pd.NamedAgg(column='Game_Score', aggfunc='count'),
                'GS Average': pd.NamedAgg(column='Game_Score', aggfunc='mean'),
                'Offensive Avg': pd.NamedAgg(column='Offensive_Score', aggfunc='mean'),
                'Defensive Avg': pd.NamedAgg(column='Defensive_Score', aggfunc='mean'),
                'Goals': pd.NamedAgg(column='Goals_clean', aggfunc='sum'),
                'Assists': pd.NamedAgg(column='Assists_clean', aggfunc='sum'),
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

            for col_to_round in ['GS Average', 'Offensive Avg', 'Defensive Avg']:
                if col_to_round in leaderboard.columns:
                    leaderboard[col_to_round] = leaderboard[col_to_round].round(2)

            leaderboard = leaderboard.sort_values(by="GS Average", ascending=False).reset_index(drop=True)

            event = st.dataframe(
                leaderboard, 
                use_container_width=True, 
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                key="leaderboard_interactive_table"
            )

            if event and event.selection and event.selection.rows:
                clicked_index = event.selection.rows[0]
                clicked_player = leaderboard.iloc[clicked_index]['Player']
                show_player_card(clicked_player)

    elif selected_tab == "📊 Player Progression":
        st.subheader("Player Progression Curve During the Season")
        if player_col:
            players = sorted(df_filtered[player_col].dropna().unique())
            if len(players) > 0:
                selected_player = st.selectbox("Select player to view:", players, key='tab2_player')
                
                if st.button("Open Player Card 🃏", key='btn_card_tab2'):
                    show_player_card(selected_player)

                player_df = df_filtered[df_filtered[player_col] == selected_player].sort_values(by='Date')

                if not player_df.empty:
                    fig = px.line(
                        player_df, x='Date', y='Game_Score', markers=True,
                        title=f"Player {selected_player} Game Score History (5v5)"
                    )
                    fig.update_layout(xaxis_type='category')
                    st.plotly_chart(fig, use_container_width=True)

    elif selected_tab == "📈 Game-by-Game Scores":
        st.subheader("📊 Player Game-by-Game Game Score vs Averages (5v5)")
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
                    player_df, x='Date', y='Game_Score',
                    title=f"Player {selected_player_bar} Game-by-Game Game Score (5v5)",
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
                    yaxis_title="Game Score (5v5)",
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

    elif selected_tab == "📁 Raw Data":
        st.subheader("Raw Data and Calculated 5v5 Game Score Values")
        st.dataframe(df_filtered, use_container_width=True)
