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
    def get_col(data, col_name):
        if col_name and col_name in data.columns:
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
                # Jos peliaika on esim. minuutteina desimaalina tai kokonaislukuna
                return float(val_str)
            except:
                return 0.0

    # Poimitaan tarkat sarakkeet suoraan Excelin otsikoista
    col_goals = 'Goals' if 'Goals' in df.columns else None
    col_a1 = 'First assist' if 'First assist' in df.columns else None
    col_a2 = 'Second assist' if 'Second assist' in df.columns else None
    col_ixg = 'xG (Expected goals)' if 'xG (Expected goals)' in df.columns else None
    col_pt = 'Penalty time' if 'Penalty time' in df.columns else None
    
    col_gf = 'Plus' if 'Plus' in df.columns else None
    col_ga = 'Minus' if 'Minus' in df.columns else None
    col_cf = 'CORSI+' if 'CORSI+' in df.columns else None
    col_ca = 'CORSI-' if 'CORSI-' in df.columns else None
    
    col_toi = 'Time on ice' if 'Time on ice' in df.columns else None
    col_pos = 'Position' if 'Position' in df.columns else None
    player_col = 'Player' if 'Player' in df.columns else None
    team_col = 'Team' if 'Team' in df.columns else None

    df['Goals_clean'] = get_col(df, col_goals)
    df['A1_clean'] = get_col(df, col_a1)
    df['A2_clean'] = get_col(df, col_a2)
    df['Assists_clean'] = df['A1_clean'] + df['A2_clean']
    
    df['TOI_clean'] = df[col_toi].apply(parse_toi) if col_toi else 0.0
    df['Pos_clean'] = df[col_pos].astype(str).str.upper().str.strip() if col_pos else 'F'
    df['iXG_clean'] = get_col(df, col_ixg) if col_ixg else 0.0
    df['PT_clean'] = get_col(df, col_pt)
    df['GF_clean'] = get_col(df, col_gf)
    df['GA_clean'] = get_col(df, col_ga)
    df['CF_clean'] = get_col(df, col_cf)
    df['CA_clean'] = get_col(df, col_ca)
    df['Game_Count'] = 1  # Ottelulaskuri

    # --- SIDEBAR: FILTERS ---
    st.sidebar.header("🔍 Filters")
    
    if team_col and team_col in df.columns:
        all_teams = sorted(df[team_col].dropna().unique())
        selected_teams = st.sidebar.multiselect("Select your team:", all_teams, default=all_teams)
        df_filtered = df[df[team_col].isin(selected_teams)] if selected_teams else df.copy()
    else:
        df_filtered = df.copy()

    st.sidebar.subheader("🏒 Position")
    selected_positions = st.sidebar.multiselect("Select position:", ['F', 'D'], default=['F', 'D'])
    if col_pos and selected_positions:
        df_filtered = df_filtered[df_filtered['Pos_clean'].isin(selected_positions)]

    min_toi_filter = st.sidebar.slider("Min. average time on ice (min):", 0.0, 30.0, 0.0, 0.5)

    # --- PLAYER CARD DIALOG ---
    @st.dialog("Player Card", width="large")
    def show_player_card(player_name):
        p_df = df_filtered[df_filtered[player_col] == player_name].sort_values(by='Date') if 'Date' in df_filtered.columns else df_filtered[df_filtered[player_col] == player_name]
        if p_df.empty:
            st.warning("No data found for this player.")
            return

        team_val = p_df[team_col].iloc[0] if team_col else "SDHL"
        gp = len(p_df)
        total_toi = p_df['TOI_clean'].sum()

        if total_toi > 0:
            scale_factor = 60.0 / total_toi
            p_g = p_df['Goals_clean'].sum() * scale_factor
            p_a1 = p_df['A1_clean'].sum() * scale_factor
            p_a2 = p_df['A2_clean'].sum() * scale_factor
            p_ixg = p_df['iXG_clean'].sum() * scale_factor
            p_gf = p_df['GF_clean'].sum() * scale_factor
            p_cf = p_df['CF_clean'].sum() * scale_factor
            p_pt = p_df['PT_clean'].sum() * scale_factor
            p_ga = p_df['GA_clean'].sum() * scale_factor
            p_ca = p_df['CA_clean'].sum() * scale_factor
            pos = p_df['Pos_clean'].iloc[0]
            
            is_d_p = (pos == 'D')
            off_card = (0.75 * p_g) + (0.7 * p_a1) + (0.55 * p_a2) + (0.5 * p_ixg) + \
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

    # --- NAVIGATION ---
    selected_tab = st.radio(
        "Navigation",
        ["🏆 Season Leaderboard", "📊 Player Progression", "📈 Game-by-Game Scores", "📁 Raw Data"],
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

            agg_dict = {
                'TOI_clean': 'sum',
                'Goals_clean': 'sum',
                'A1_clean': 'sum',
                'A2_clean': 'sum',
                'Assists_clean': 'sum',
                'iXG_clean': 'sum',
                'PT_clean': 'sum',
                'GF_clean': 'sum',
                'GA_clean': 'sum',
                'CF_clean': 'sum',
                'CA_clean': 'sum',
                'Game_Count': 'sum'
            }
            
            agg_df = df_filtered.groupby(group_cols).agg(agg_dict).reset_index()
            agg_df = agg_df.rename(columns={'Game_Count': 'Games'})

            def calculate_per_60(row):
                toi = row['TOI_clean']
                if toi <= 0:
                    return pd.Series([0.0, 0.0, 0.0])
                
                factor = 60.0 / toi
                is_d = row['Pos_clean'] == 'D'
                
                g_val = row['Goals_clean'] * factor
                a1_val = row['A1_clean'] * factor
                a2_val = row['A2_clean'] * factor
                ixg_val = row['iXG_clean'] * factor
                gf_val = row['GF_clean'] * factor
                cf_val = row['CF_clean'] * factor
                
                pt_val = row['PT_clean'] * factor
                ga_val = row['GA_clean'] * factor
                ca_val = row['CA_clean'] * factor
                
                off = (0.75 * g_val) + (0.7 * a1_val) + (0.55 * a2_val) + (0.5 * ixg_val) + \
                      ((0.425 if is_d else 0.625) * gf_val) + ((1.7 if is_d else 0.625) * cf_val)
                
                def_s = - (0.15 * pt_val) - ((0.575 if is_d else 0.4375) * ga_val) - ((2.3 if is_d else 1.75) * ca_val)
                
                gs = off + def_s
                return pd.Series([gs, off, def_s])

            agg_df[['GS Per 60', 'Offensive Per 60', 'Defensive Per 60']] = agg_df.apply(calculate_per_60, axis=1)

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

    elif selected_tab == "📁 Raw Data":
        st.subheader("Raw Data")
        st.dataframe(df_filtered, use_container_width=True)
