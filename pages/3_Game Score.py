import streamlit as st
import pandas as pd
import plotly.express as px

# Page configuration
st.set_page_config(page_title="SDHL Game Score Analysis", page_icon="🏒", layout="wide")

st.title("🏒 SDHL Game Score Analysis Tool (2026–2027) - 5v5 Model (Per 60)")

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

    # Column mappings
    col_goals = next((c for c in df.columns if c.lower() == 'goals'), None)
    col_a1 = next((c for c in df.columns if c.lower() in ['first assist', 'assist 1', 'a1']), None)
    col_a2 = next((c for c in df.columns if c.lower() in ['second assist', 'assist 2', 'a2']), None)
    col_sog = next((c for c in df.columns if c.lower() in ['shots on goal', 'sog', 'shots']), None)
    col_ixg = next((c for c in df.columns if c.lower() in ['ixg', 'individual xg']), None)
    col_pt = next((c for c in df.columns if c.lower() in ['penalty time', 'pim', 'utvisningsminuter']), None)
    
    col_gf = next((c for c in df.columns if c.lower() in ['plus', 'goals for', 'gf']), None)
    col_ga = next((c for c in df.columns if c.lower() in ['minus', 'goals against', 'ga']), None)
    col_cf = next((c for c in df.columns if c.lower() in ['corsi for', 'cf']), None)
    col_ca = next((c for c in df.columns if c.lower() in ['corsi against', 'ca']), None)
    
    col_toi = next((c for c in df.columns if any(k in c.lower() for k in ['time on ice', 'toi', 'minutes', 'min'])), None)
    col_pos = next((c for c in df.columns if c.lower() == 'position'), None)

    g = get_col(df, col_goals)
    a1 = get_col(df, col_a1)
    a2 = get_col(df, col_a2)
    sog = get_col(df, col_sog)
    ixg = get_col(df, col_ixg) if col_ixg else get_col(df, col_sog) * 0.1
    pt_val = get_col(df, col_pt)
    gf = get_col(df, col_gf)
    ga = get_col(df, col_ga)
    cf = get_col(df, col_cf) if col_cf else get_col(df, col_sog)
    ca = get_col(df, col_ca) if col_ca else 0

    df['Goals_clean'] = g
    df['Assists_clean'] = a1 + a2
    df['Shots_clean'] = sog
    df['TOI_clean'] = df[col_toi].apply(parse_toi) if col_toi else 0.0
    df['Pos_clean'] = df[col_pos].astype(str).str.upper().str.strip() if col_pos else 'F'
    df['iXG_clean'] = ixg
    df['PT_clean'] = pt_val
    df['GF_clean'] = gf
    df['GA_clean'] = ga
    df['CF_clean'] = cf
    df['CA_clean'] = ca

    player_col = next((c for c in df.columns if 'player' in c.lower()), None)
    team_col = next((c for c in df.columns if c.lower() == 'team'), None)

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

    min_toi_filter = st.sidebar.slider("Min. total or average time on ice:", 0.0, 30.0, 0.0, 0.5) if col_toi else 0.0

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

        # Lasketaan pelaajakohtainen Per 60 korttiin
        if total_toi > 0:
            scale_factor = 60.0 / total_toi
            p_g = p_df['Goals_clean'].sum() * scale_factor
            p_a1 = p_df.get('A1_clean', p_df['Assists_clean'] * 0.6).sum() * scale_factor # Arvio / tarkistus
            p_ixg = p_df['iXG_clean'].sum() * scale_factor
            p_gf = p_df['GF_clean'].sum() * scale_factor
            p_cf = p_df['CF_clean'].sum() * scale_factor
            p_pt = p_df['PT_clean'].sum() * scale_factor
            p_ga = p_df['GA_clean'].sum() * scale_factor
            p_ca = p_df['CA_clean'].sum() * scale_factor
            pos = p_df['Pos_clean'].iloc[0]
            
            is_d_p = (pos == 'D')
            off_card = (0.75 * p_g) + (0.7 * (p_df['Assists_clean'].sum()*0.6*scale_factor)) + (0.55 * (p_df['Assists_clean'].sum()*0.4*scale_factor)) + (0.5 * p_ixg) + \
                       ((0.425 if is_d_p else 0.625) * p_gf) + ((1.7 if is_d_p else 0.625) * p_cf)
            def_card = - (0.15 * p_pt) - ((0.575 if is_d_p else 0.4375) * p_ga) - ((2.3 if is_d_p else 1.75) * p_ca)
            gs_card = off_card + def_card
        else:
            gs_card, off_card, def_card = 0, 0, 0

        st.markdown(f"### 🏒 {player_name} &nbsp;|&nbsp; <span style='color:gray; font-size:16px;'>{team_val} | 5v5 Per 60 Model | {gp} GP | {int(total_toi)} total min</span>", unsafe_allow_html=True)
        st.markdown("---")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("GAME SCORE (Per 60)", f"{gs_card:.2f}")
        with col2:
            st.metric("OFFENSIVE (Per 60)", f"{off_card:.2f}")
        with col3:
            st.metric("DEFENSIVE (Per 60)", f"{def_card:.2f}")
        with col4:
            st.metric("TOTAL GOALS", int(p_df['Goals_clean'].sum()))

        st.markdown("### 📈 Season Trend Charts")
        
        # Peli-kohtainen kehitys ottelukohtaisilla arvoilla
        p_df['Off_Match'] = (0.75 * p_df['Goals_clean']) + (0.7 * a1.loc[p_df.index]) + (0.55 * a2.loc[p_df.index]) + (0.5 * p_df['iXG_clean']) + \
                            p_df.apply(lambda r: (0.425 if r['Pos_clean']=='D' else 0.625)*r['GF_clean'] + (1.7 if r['Pos_clean']=='D' else 0.625)*r['CF_clean'], axis=1)
        p_df['Def_Match'] = - (0.15 * p_df['PT_clean']) - p_df.apply(lambda r: (0.575 if r['Pos_clean']=='D' else 0.4375)*r['GA_clean'] + (2.3 if r['Pos_clean']=='D' else 1.75)*r['CA_clean'], axis=1)
        p_df['GS_Match'] = p_df['Off_Match'] + p_df['Def_Match']

        fig_gs = px.line(p_df, x='Date', y='GS_Match', markers=True, title="Game Score per Match")
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
        st.subheader("🏆 Player Leaderboard (5v5 Per 60 Model)")
        st.caption("Tilastot on suhteutettu 60 minuutin peliaikaan (Per 60). Klikkaa mitä tahansa pelaajariviä avataksesi pelaajakortin.")
        
        if player_col:
            group_cols = [player_col]
            if team_col in df_filtered.columns:
                group_cols.append(team_col)
            if col_pos:
                group_cols.append('Pos_clean')

            # Aggregoidaan summat per pelaaja kauden aikana
            agg_dict = {
                'TOI_clean': 'sum',
                'Goals_clean': 'sum',
                'Assists_clean': 'sum',
                'iXG_clean': 'sum',
                'PT_clean': 'sum',
                'GF_clean': 'sum',
                'GA_clean': 'sum',
                'CF_clean': 'sum',
                'CA_clean': 'sum',
                'Game_Score': 'count' # Pelatut ottelut
            }
            
            agg_df = df_filtered.groupby(group_cols).agg(agg_dict).reset_index()
            agg_df = agg_df.rename(columns={'Game_Score': 'Games'})

            # Muutetaan Per 60 -muotoon koko kauden kokonaissummien ja peliajan perusteella
            def calculate_per_60(row):
                toi = row['TOI_clean']
                if toi <= 0:
                    return pd.Series([0.0, 0.0, 0.0])
                
                factor = 60.0 / toi
                is_d = row['Pos_clean'] == 'D'
                
                g_val = row['Goals_clean'] * factor
                # Oletetaan a1/a2 suhde samaksi kuin annetuissa syötöissä
                a_tot = row['Assists_clean'] * factor
                a1_val = a_tot * 0.6
                a2_val = a_tot * 0.4
                ixg_val = row['iXG_clean'] * factor
                gf_val = row['GF_clean'] * factor
                cf_val = row['CF_clean'] * factor
                
                pt_val = row['PT_clean'] * factor
                ga_val = row['GA_clean'] * factor
                ca_val = row['CA_clean'] * factor
                
                # Offensiv Per 60
                off = (0.75 * g_val) + (0.7 * a1_val) + (0.55 * a2_val) + (0.5 * ixg_val) + \
                      ((0.425 if is_d else 0.625) * gf_val) + ((1.7 if is_d else 0.625) * cf_val)
                
                # Defensiv Per 60
                def_s = - (0.15 * pt_val) - ((0.575 if is_d else 0.4375) * ga_val) - ((2.3 if is_d else 1.75) * ca_val)
                
                gs = off + def_s
                return pd.Series([gs, off, def_s])

            agg_df[['GS Per 60', 'Offensive Per 60', 'Defensive Per 60']] = agg_df.apply(calculate_per_60, axis=1)

            # Viimeistellään taulukko
            leaderboard = agg_df.copy()
            leaderboard['Avg. Time on Ice (min)'] = leaderboard['TOI_clean'] / leaderboard['Games']
            leaderboard['Goals'] = leaderboard['Goals_clean']
            leaderboard['Assists'] = leaderboard['Assists_clean']

            rename_map = {player_col: 'Player'}
            if team_col in df_filtered.columns:
                rename_map[team_col] = 'Team'
            if col_pos:
                rename_map['Pos_clean'] = 'Position'
            
            leaderboard = leaderboard.rename(columns=rename_map)

            cols_to_keep = ['Player', 'Team', 'Position', 'Games', 'GS Per 60', 'Offensive Per 60', 'Defensive Per 60', 'Goals', 'Assists', 'Avg. Time on Ice (min)']
            leaderboard = leaderboard[[c for c in cols_to_keep if c in leaderboard.columns]]

            if col_toi and min_toi_filter > 0:
                leaderboard = leaderboard[leaderboard['Avg. Time on Ice (min)'] >= min_toi_filter]

            for col_to_round in ['GS Per 60', 'Offensive Per 60', 'Defensive Per 60', 'Avg. Time on Ice (min)']:
                if col_to_round in leaderboard.columns:
                    leaderboard[col_to_round] = leaderboard[col_to_round].round(2)

            leaderboard = leaderboard.sort_values(by="GS Per 60", ascending=False).reset_index(drop=True)

            event = st.dataframe(
                leaderboard, 
                use_container_width=True, 
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                key="leaderboard_per60_table"
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
                    player_df['Off_Match'] = (0.75 * player_df['Goals_clean']) + (0.7 * a1.loc[player_df.index]) + (0.55 * a2.loc[player_df.index]) + (0.5 * player_df['iXG_clean']) + \
                                            player_df.apply(lambda r: (0.425 if r['Pos_clean']=='D' else 0.625)*r['GF_clean'] + (1.7 if r['Pos_clean']=='D' else 0.625)*r['CF_clean'], axis=1)
                    player_df['Def_Match'] = - (0.15 * player_df['PT_clean']) - player_df.apply(lambda r: (0.575 if r['Pos_clean']=='D' else 0.4375)*r['GA_clean'] + (2.3 if r['Pos_clean']=='D' else 1.75)*r['CA_clean'], axis=1)
                    player_df['GS_Match'] = player_df['Off_Match'] + player_df['Def_Match']

                    fig = px.line(
                        player_df, x='Date', y='GS_Match', markers=True,
                        title=f"Player {selected_player} Game Score History (Per Match)"
                    )
                    fig.update_layout(xaxis_type='category')
                    st.plotly_chart(fig, use_container_width=True)

    elif selected_tab == "📈 Game-by-Game Scores":
        st.subheader("📊 Player Game-by-Game Game Score")
        if player_col:
            players = sorted(df_filtered[player_col].dropna().unique())
            selected_player_bar = st.selectbox("Select player for analysis:", players, key='bar_player')
            
            player_df = df_filtered[df_filtered[player_col] == selected_player_bar].sort_values(by='Date')
            
            if not player_df.empty:
                player_df['Off_Match'] = (0.75 * player_df['Goals_clean']) + (0.7 * a1.loc[player_df.index]) + (0.55 * a2.loc[player_df.index]) + (0.5 * player_df['iXG_clean']) + \
                                        player_df.apply(lambda r: (0.425 if r['Pos_clean']=='D' else 0.625)*r['GF_clean'] + (1.7 if r['Pos_clean']=='D' else 0.625)*r['CF_clean'], axis=1)
                player_df['Def_Match'] = - (0.15 * player_df['PT_clean']) - player_df.apply(lambda r: (0.575 if r['Pos_clean']=='D' else 0.4375)*r['GA_clean'] + (2.3 if r['Pos_clean']=='D' else 1.75)*r['CA_clean'], axis=1)
                player_df['GS_Match'] = player_df['Off_Match'] + player_df['Def_Match']

                player_oma_ka = player_df['GS_Match'].mean()
                
                fig_bar = px.bar(
                    player_df, x='Date', y='GS_Match',
                    title=f"Player {selected_player_bar} Game Score per Game",
                    labels={'Date': 'Game Date', 'GS_Match': 'Game Score'},
                    text_auto='.2f'
                )
                fig_bar.update_traces(marker_color='#00b4d8')
                fig_bar.update_layout(
                    xaxis_type='category',
                    yaxis_title="Game Score",
                    xaxis_title="Game Date",
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)'
                )

                st.plotly_chart(fig_bar, use_container_width=True)
                st.metric("Player Average per Game", f"{player_oma_ka:.2f}")

    elif selected_tab == "📁 Raw Data":
        st.subheader("Raw Data")
        st.dataframe(df_filtered, use_container_width=True)
