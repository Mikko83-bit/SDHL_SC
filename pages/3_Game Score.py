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
        df = pd.read_excel(file_path) # Lukee oletuksena ensimmäisen välilehden
        df.columns = [str(col).strip() for col in df.columns]
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce').dt.date
        return df
    except Exception as e:
        try:
            df = pd.read_excel(f"../{file_path}")
            df.columns = [str(col).strip() for col in df.columns]
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce').dt.date
            return df
        except Exception as e2:
            st.error(f"Error reading main file: {e2}")
            return None

@st.cache_data
def load_faceoffs_data(file_path):
    try:
        df_fo = pd.read_excel(file_path, sheet_name='Faceoffs')
        df_fo.columns = [str(col).strip() for col in df_fo.columns]
        return df_fo
    except Exception as e:
        try:
            df_fo = pd.read_excel(f"../{file_path}", sheet_name='Faceoffs')
            df_fo.columns = [str(col).strip() for col in df_fo.columns]
            return df_fo
        except Exception as e2:
            return None

df = load_data(EXCEL_FILE)
df_faceoffs = load_faceoffs_data(EXCEL_FILE)

if df is not None:
    def get_col(data, col_name):
        if col_name and col_name in data.columns:
            s = data[col_name].replace(['-', '—', ''], 0)
            return pd.to_numeric(s, errors='coerce').fillna(0)
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

    col_goals = next((c for c in df.columns if c.lower() in ['goals', 'goal']), None)
    col_assists = next((c for c in df.columns if c.lower() in ['assists', 'assist']), None)
    col_sog = next((c for c in df.columns if 'shots on goal' in c.lower() or c.lower() == 'sog'), None)
    col_blk = next((c for c in df.columns if 'blocked shots' in c.lower() or c.lower() == 'blocks'), None)
    col_pd = next((c for c in df.columns if 'penalties drawn' in c.lower()), None)
    
    col_pt = next((c for c in df.columns if c.lower() == 'penalties' or ('penalty' in c.lower() and 'drawn' not in c.lower() and 'time' not in c.lower())), None)
    if not col_pt:
        col_pt = next((c for c in df.columns if any(k in c.lower() for k in ['penalty time', 'pim', 'penalty minutes'])), None)

    col_fow = next((c for c in df.columns if 'faceoffs won' in c.lower() or c.lower() == 'fow'), None)
    col_fol = next((c for c in df.columns if 'faceoffs lost' in c.lower() or c.lower() == 'fol'), None)
    col_xg_on = next((c for c in df.columns if c.lower() in ['xgs with a player on', 'xg with a player on']), None)
    col_opp_xg_on = next((c for c in df.columns if 'opponent' in c.lower() and 'xg' in c.lower()), None)
    col_gf = next((c for c in df.columns if c.lower() in ['plus', 'gf']), None)
    col_ga = next((c for c in df.columns if c.lower() in ['minus', 'ga']), None)
    col_toi = next((c for c in df.columns if any(k in c.lower() for k in ['time on ice', 'toi', 'minutes', 'min'])), None)
    col_pos = next((c for c in df.columns if c.lower() == 'position'), None)

    g = get_col(df, col_goals)
    a_total = get_col(df, col_assists)
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
    df['Assists_clean'] = a_total
    df['Shots_clean'] = sog
    df['Block_clean'] = blk
    df['Penalties_Total_clean'] = pd_val - pt_val
    df['Faceoffs_Total_clean'] = fow - fol
    df['xG_Total_clean'] = xg_for - xg_against
    df['Plus_Minus_clean'] = gf - ga
    
    df['TOI_clean'] = df[col_toi].apply(parse_toi) if col_toi else 0.0
    df['Pos_clean'] = df[col_pos].astype(str).str.upper().str.strip() if col_pos else 'UNKNOWN'

    df['Game_Score'] = (
        (0.75 * g) + (0.7 * a_total) + (0.075 * sog) + 
        (0.05 * blk) + (0.15 * pd_val) - (0.15 * pt_val) + 
        (0.01 * fow) - (0.01 * fol) + (0.05 * xg_for) - 
        (0.05 * xg_against) + (0.15 * gf) - (0.15 * ga)
    )

    player_col = next((c for c in df.columns if 'player' in c.lower()), None)
    team_col = next((c for c in df.columns if c.lower() == 'team'), None)

    # --- SIDEBAR: FILTERS ---
    st.sidebar.header("🔍 Filters")
    
    if team_col:
        all_teams = sorted(df[team_col].dropna().unique())
        selected_teams = st.sidebar.multiselect("Select team(s):", all_teams, default=all_teams)
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

    @st.dialog("Player Card", width="large")
    def show_player_card(player_name):
        p_df = df_filtered[df_filtered[player_col] == player_name].copy()
        if not p_df.empty and 'Date' in p_df.columns:
            p_df['Temp_Date'] = pd.to_datetime(p_df['Date'], errors='coerce')
            p_df = p_df.dropna(subset=['Temp_Date']).sort_values(by='Temp_Date')
            p_df['Date_Str'] = p_df['Temp_Date'].dt.strftime('%Y-%m-%d')

        if p_df.empty:
            st.warning("No data found for this player.")
            return

        team_val = p_df[team_col].iloc[0] if team_col else "SDHL"
        gp = len(p_df)
        total_toi = p_df['TOI_clean'].sum()

        st.markdown(f"### 🏒 {player_name} &nbsp;|&nbsp; <span style='color:gray; font-size:16px;'>{team_val} | SDHL 26/27 | {gp} GP | {int(total_toi)} min</span>", unsafe_allow_html=True)
        st.markdown("---")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("GAME SCORE (Avg)", f"{p_df['Game_Score'].mean():.2f}")
        with col2:
            st.metric("TOTAL GOALS", int(p_df['Goals_clean'].sum()))
        with col3:
            st.metric("TOTAL ASSISTS", int(p_df['Assists_clean'].sum()))

        st.markdown("### 📈 Season Trend Charts")
        
        if 'Date_Str' in p_df.columns:
            card_order = list(p_df['Date_Str'].unique())
            fig_gs = px.line(p_df, x='Date_Str', y='Game_Score', markers=True, title="Game Score History")
            fig_gs.update_layout(xaxis_type='category', margin=dict(l=20, r=20, t=30, b=20), height=230)
            fig_gs.update_xaxes(categoryorder='array', categoryarray=card_order)
            st.plotly_chart(fig_gs, use_container_width=True)

        if col_toi and 'Date_Str' in p_df.columns:
            fig_toi = px.line(p_df, x='Date_Str', y='TOI_clean', markers=True, title="Time on Ice (Minutes per Match)")
            fig_toi.update_layout(xaxis_type='category', margin=dict(l=20, r=20, t=30, b=20), height=230)
            fig_toi.update_xaxes(categoryorder='array', categoryarray=card_order)
            st.plotly_chart(fig_toi, use_container_width=True)

    # --- NAVIGATION ---
    selected_tab = st.radio(
        "Navigation",
        [
            "🏆 Season Leaderboard", 
            "📊 Player Progression", 
            "📈 Game-by-Game Scores", 
            "🎯 Efficiency & Finishing",
            "🏒 Faceoffs by Zone",
            "📁 Raw Data"
        ],
        horizontal=True,
        label_visibility="collapsed"
    )
    st.markdown("---")

    if selected_tab == "🏆 Season Leaderboard":
        st.subheader("🏆 Player Leaderboard & Game Score Components")
        st.caption("Click any player row in the table to open their player card.")
        
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
                'Blocked Shots': pd.NamedAgg(column='Block_clean', aggfunc='sum'),
                'Penalties Total': pd.NamedAgg(column='Penalties_Total_clean', aggfunc='sum'),
                'Faceoffs Total': pd.NamedAgg(column='Faceoffs_Total_clean', aggfunc='sum'),
                'xG Total': pd.NamedAgg(column='xG_Total_clean', aggfunc='sum'),
                'Plus/Minus Total': pd.NamedAgg(column='Plus_Minus_clean', aggfunc='sum')
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

            for col in ['GS Average', 'GS Total', 'xG Total']:
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

                player_df = df_filtered[df_filtered[player_col] == selected_player].copy()
                if not player_df.empty and 'Date' in player_df.columns:
                    player_df['Temp_Date'] = pd.to_datetime(player_df['Date'], errors='coerce')
                    player_df = player_df.dropna(subset=['Temp_Date']).sort_values(by='Temp_Date')
                    player_df['Date_Str'] = player_df['Temp_Date'].dt.strftime('%Y-%m-%d')

                if not player_df.empty and 'Date_Str' in player_df.columns:
                    prog_order = list(player_df['Date_Str'].unique())
                    fig = px.line(
                        player_df, x='Date_Str', y='Game_Score', markers=True,
                        title=f"Player {selected_player} Game Score History"
                    )
                    fig.update_layout(xaxis_type='category')
                    fig.update_xaxes(categoryorder='array', categoryarray=prog_order)
                    st.plotly_chart(fig, use_container_width=True)

    elif selected_tab == "📈 Game-by-Game Scores":
        st.subheader("📊 Player Game-by-Game Game Score vs Averages")
        if player_col:
            players = sorted(df_filtered[player_col].dropna().unique())
            selected_player_bar = st.selectbox("Select player for analysis:", players, key='bar_player')
            
            player_df = df_filtered[df_filtered[player_col] == selected_player_bar].copy()
            if not player_df.empty and 'Date' in player_df.columns:
                player_df['Temp_Date'] = pd.to_datetime(player_df['Date'], errors='coerce')
                player_df = player_df.dropna(subset=['Temp_Date']).sort_values(by='Temp_Date')
                player_df['Date_Str'] = player_df['Temp_Date'].dt.strftime('%Y-%m-%d')
            
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

                x_axis_col = 'Date_Str'
                player_df['Performance'] = player_df['Game_Score'].apply(lambda x: 'Positive' if x >= 0 else 'Negative')
                category_order = list(player_df[x_axis_col].unique())

                fig_bar = px.bar(
                    player_df, x=x_axis_col, y='Game_Score',
                    color='Performance',
                    color_discrete_map={'Positive': '#00b4d8', 'Negative': '#ef476f'},
                    title=f"Player {selected_player_bar} Game-by-Game Game Score",
                    labels={x_axis_col: 'Game Date', 'Game_Score': 'Game Score'},
                    text_auto='.2f'
                )
                fig_bar.update_layout(showlegend=False)
                fig_bar.update_xaxes(categoryorder='array', categoryarray=category_order)

                fig_bar.add_hline(y=sdhl_ka, line_dash="dash", line_color="#adb5bd", annotation_text=f"SDHL Average ({sdhl_ka:.2f})", annotation_position="bottom right", annotation_font_color="#adb5bd")

                if team_col and not pd.isna(tiimi_ka):
                    fig_bar.add_hline(y=tiimi_ka, line_dash="dot", line_color="#ffb703", annotation_text=f"{tiimi_nimi} Average ({tiimi_ka:.2f})", annotation_position="top right", annotation_font_color="#ffb703")

                fig_bar.add_hline(y=player_oma_ka, line_dash="solid", line_color="#ffffff", annotation_text=f"Player Average ({player_oma_ka:.2f})", annotation_position="bottom left", annotation_font_color="#ffffff")

                fig_bar.update_layout(xaxis_type='category', yaxis_title="Game Score", xaxis_title="Game Date", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_bar, use_container_width=True)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Player Average", f"{player_oma_ka:.2f}")
                with col2:
                    st.metric("SDHL Average (filtered)", f"{sdhl_ka:.2f}")
                with col3:
                    if team_col:
                        st.metric(f"{tiimi_nimi} Average (filtered)", f"{tiimi_ka:.2f}")

    elif selected_tab == "🎯 Efficiency & Finishing":
        st.subheader("🎯 Player Finishing & Scoring Efficiency")
        st.caption("Comparison of actual goals scored relative to expected goals (xG) and shots.")

        if player_col:
            group_cols = [player_col]
            if team_col in df_filtered.columns:
                group_cols.append(team_col)
            if col_pos:
                group_cols.append('Pos_clean')

            eff_agg = df_filtered.groupby(group_cols).agg(
                Games=('Game_Score', 'count'),
                Goals=('Goals_clean', 'sum'),
                Shots=('Shots_clean', 'sum')
            ).reset_index()

            eff_rename = {player_col: 'Player'}
            if team_col in df_filtered.columns:
                eff_rename[team_col] = 'Team'
            if col_pos:
                eff_rename['Pos_clean'] = 'Position'
            eff_agg = eff_agg.rename(columns=eff_rename)

            eff_agg = eff_agg.sort_values(by="Goals", ascending=False).reset_index(drop=True)

            st.dataframe(
                eff_agg[['Player', 'Team', 'Position', 'Games', 'Goals', 'Shots']],
                use_container_width=True,
                hide_index=True
            )

    elif selected_tab == "🏒 Faceoffs by Zone":
        st.subheader("🏒 Faceoff Circle Analytics by Zone")
        st.caption("Detailed breakdown of faceoffs in Defense Zone (DZ), Neutral Zone (NZ), and Attack Zone (OZ) with overall win percentages.")

        if df_faceoffs is not None:
            fo_df = df_faceoffs.copy()
            
            # Tunnistetaan sarakkeet turvallisesti nimien perusteella
            fo_player_col = next((c for c in fo_df.columns if 'player' in c.lower()), 'Player')
            fo_team_col = next((c for c in fo_df.columns if 'team' in c.lower()), 'Team')
            
            # Etsitään DZ, NZ, OZ sarakkeet
            col_dz_tot = next((c for c in fo_df.columns if 'dz' in c.lower() and ('in' in c.lower() or 'total' in c.lower()) and 'won' not in c.lower()), None)
            col_dz_won = next((c for c in fo_df.columns if 'dz' in c.lower() and 'won' in c.lower()), None)
            
            col_nz_tot = next((c for c in fo_df.columns if 'nz' in c.lower() and ('in' in c.lower() or 'total' in c.lower()) and 'won' not in c.lower()), None)
            col_nz_won = next((c for c in fo_df.columns if 'nz' in c.lower() and 'won' in c.lower()), None)
            
            col_oz_tot = next((c for c in fo_df.columns if 'oz' in c.lower() and ('in' in c.lower() or 'total' in c.lower()) and 'won' not in c.lower()), None)
            col_oz_won = next((c for c in fo_df.columns if 'oz' in c.lower() and 'won' in c.lower()), None)

            # Puhdistetaan numerot
            dz_tot = get_col(fo_df, col_dz_tot) if col_dz_tot else pd.Series(0, index=fo_df.index)
            dz_won = get_col(fo_df, col_dz_won) if col_dz_won else pd.Series(0, index=fo_df.index)
            nz_tot = get_col(fo_df, col_nz_tot) if col_nz_tot else pd.Series(0, index=fo_df.index)
            nz_won = get_col(fo_df, col_nz_won) if col_nz_won else pd.Series(0, index=fo_df.index)
            oz_tot = get_col(fo_df, col_oz_tot) if col_oz_tot else pd.Series(0, index=fo_df.index)
            oz_won = get_col(fo_df, col_oz_won) if col_oz_won else pd.Series(0, index=fo_df.index)

            processed_fo = pd.DataFrame()
            processed_fo['Player'] = fo_df[fo_player_col] if fo_player_col in fo_df.columns else "Unknown"
            processed_fo['Team'] = fo_df[fo_team_col] if fo_team_col in fo_df.columns else "Unknown"
            
            # Aluekohtaiset
            processed_fo['DZ Tot'] = dz_tot
            processed_fo['DZ Won'] = dz_won
            processed_fo['DZ Win %'] = ((dz_won / dz_tot.replace(0, 1)) * 100).round(1)

            processed_fo['NZ Tot'] = nz_tot
            processed_fo['NZ Won'] = nz_won
            processed_fo['NZ Win %'] = ((nz_won / nz_tot.replace(0, 1)) * 100).round(1)

            processed_fo['OZ Tot'] = oz_tot
            processed_fo['OZ Won'] = oz_won
            processed_fo['OZ Win %'] = ((oz_won / oz_tot.replace(0, 1)) * 100).round(1)

            # Kokonaisuus
            total_faceoffs = dz_tot + nz_tot + oz_tot
            total_wins = dz_won + nz_won + oz_won
            processed_fo['Total Faceoffs'] = total_faceoffs
            processed_fo['Total Wins'] = total_wins
            processed_fo['Total Win %'] = ((total_wins / total_faceoffs.replace(0, 1)) * 100).round(1)

            # Suodatin minimialoituksille
            min_fo_zone = st.slider("Min. total faceoffs for zone table:", 0, 100, 10, 1)
            filtered_fo = processed_fo[processed_fo['Total Faceoffs'] >= min_fo_zone].sort_values(by='Total Win %', ascending=False).reset_index(drop=True)

            st.dataframe(
                filtered_fo[['Player', 'Team', 'Total Faceoffs', 'Total Win %', 'DZ Tot', 'DZ Win %', 'NZ Tot', 'NZ Win %', 'OZ Tot', 'OZ Win %']],
                use_container_width=True,
                hide_index=True
            )

            st.markdown("### 📊 Faceoff Win % by Zone (Top 15 Players)")
            top_zone_fo = filtered_fo.head(15)
            if not top_zone_fo.empty:
                melted = top_zone_fo.melt(
                    id_vars=['Player'], 
                    value_vars=['DZ Win %', 'NZ Win %', 'OZ Win %'],
                    var_name='Zone', value_name='Win %'
                )
                fig_zone = px.bar(
                    melted, x='Player', y='Win %', color='Zone',
                    barmode='group',
                    title="Faceoff Win Percentage by Zone (DZ, NZ, OZ)",
                    labels={'Win %': 'Win %'}
                )
                fig_zone.update_layout(xaxis_tickangle=-45, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_zone, use_container_width=True)
        else:
            st.warning("Could not find 'Faceoffs' sheet in the Excel file.")

    elif selected_tab == "📁 Raw Data":
        st.subheader("Raw Data and Calculated Game Score Values")
        st.dataframe(df_filtered, use_container_width=True)
