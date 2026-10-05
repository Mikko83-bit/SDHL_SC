import streamlit as st
import pandas as pd
import plotly.express as px

# Page configuration
st.set_page_config(page_title="SDHL Game Score Analysis", page_icon="🏒", layout="wide")

st.title("🏒 SDHL Game Score Analysis Tool (2026–2027)")

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
        return pd.Series(0, index=data.index)

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

    # Column mappings
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
    df['A1_clean'] = a1
    df['A2_clean'] = a2
    df['Assists_clean'] = a1 + a2
    df['Shots_clean'] = sog
    df['Block_clean'] = blk
    df['PD_clean'] = pd_val
    df['PT_clean'] = pt_val
    df['FOW_clean'] = fow
    df['FOL_clean'] = fol
    df['XG_For_clean'] = xg_for
    df['XG_Against_clean'] = xg_against
    df['GF_clean'] = gf
    df['GA_clean'] = ga
    
    df['TOI_clean'] = df[col_toi].apply(parse_toi) if col_toi else 0.0
    df['Pos_clean'] = df[col_pos].astype(str).str.upper().str.strip() if col_pos else 'UNKNOWN'

    df['Game_Score'] = (
        (0.75 * g) + (0.7 * a1) + (0.55 * a2) + (0.075 * sog) + 
        (0.05 * blk) + (0.15 * pd_val) - (0.15 * pt_val) + 
        (0.01 * fow) - (0.01 * fol) + (0.05 * xg_for) - 
        (0.05 * xg_against) + (0.15 * gf) - (0.15 * ga)
    )

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

        st.markdown(f"### 🏒 {player_name} &nbsp;|&nbsp; <span style='color:gray; font-size:16px;'>{team_val} | SDHL 26/27 | {gp} GP | {int(total_toi)} min</span>", unsafe_allow_html=True)
        st.markdown("---")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("GAME SCORE (Avg)", f"{p_df['Game_Score'].mean():.2f}")
        with col2:
            st.metric("TOTAL GOALS", int(p_df['Goals_clean'].sum()))
        with col3:
            st.metric("TOTAL ASSISTS", int(p_df['Assists_clean'].sum()))
        with col4:
            st.metric("TOTAL SHOTS", int(p_df['Shots_clean'].sum()))

        # Lisätietorivit kortille
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Blocked Shots", int(p_df['Block_clean'].sum()))
        with c2:
            st.metric("Penalties Drawn", int(p_df['PD_clean'].sum()))
        with c3:
            st.metric("Penalty Time (min)", int(p_df['PT_clean'].sum()))
        with c4:
            st.metric("Faceoffs Won/Lost", f"{int(p_df['FOW_clean'].sum())} / {int(p_df['FOL_clean'].sum())}")

        st.markdown("### 📈 Season Trend Charts")
        
        fig_gs = px.line(p_df, x='Date', y='Game_Score', markers=True, title="Game Score Game History")
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
        st.subheader("🏆 Player Leaderboard")
        st.caption("Taulukko näyttää kaikki Game Score -kaavaan vaikuttavat tilastot. Klikkaa mitä tahansa riviä avataksesi pelaajakortin.")
        
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
                'Shots': pd.NamedAgg(column='Shots_clean', aggfunc='sum'),
                'Blocks': pd.NamedAgg(column='Block_clean', aggfunc='sum'),
                'Pen. Drawn': pd.NamedAgg(column='PD_clean', aggfunc='sum'),
                'Pen. Time': pd.NamedAgg(column='PT_clean', aggfunc='sum'),
                'FO Won': pd.NamedAgg(column='FOW_clean', aggfunc='sum'),
                'FO Lost': pd.NamedAgg(column='FOL_clean', aggfunc='sum'),
                'Plus': pd.NamedAgg(column='GF_clean', aggfunc='sum'),
                'Minus': pd.NamedAgg(column='GA_clean', aggfunc='sum'),
                'xG For': pd.NamedAgg(column='XG_For_clean', aggfunc='sum'),
                'xG Against': pd.NamedAgg(column='XG_Against_clean', aggfunc='sum')
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

            # Pyöristetään desimaalit fiksusti
            for col in ['GS Average', 'GS Total', 'xG For', 'xG Against']:
                if col in leaderboard.columns:
                    leaderboard[col] = leaderboard[col].round(2)

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
                        title=f"Player {selected_player} Game Score Game History"
                    )
                    fig.update_layout(xaxis_type='category')
                    st.plotly_chart(fig, use_container_width=True)

    elif selected_tab == "📈 Game-by-Game Scores":
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
                    player_df, x='Date', y='Game_Score',
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

    elif selected_tab == "📁 Raw Data":
        st.subheader("Raw Data and Calculated Game Score Values")
        st.dataframe(df_filtered, use_container_width=True)
