import streamlit as st
import pandas as pd
import plotly.express as px

# Page configuration
st.set_page_config(page_title="Puck Management & Transitions", page_icon="🏒", layout="wide")

st.title("🏒 Puck Management, Transitions & xG Analytics")
st.caption("Clean puck management, turnovers, zone entries, transition statistics, and team xG performance.")

EXCEL_FILE = "Sdhl Game score 2026-2027.xlsx"

@st.cache_data
def load_excel_sheet(file_path, sheet_name):
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        df.columns = [str(col).strip() for col in df.columns]
        return df
    except Exception as e:
        try:
            df = pd.read_excel(f"../{file_path}", sheet_name=sheet_name)
            df.columns = [str(col).strip() for col in df.columns]
            return df
        except Exception as e2:
            return None

df_puck = load_excel_sheet(EXCEL_FILE, 'Puck management')

# Try loading raw game logs (usually default or first sheet) for xG calculations
@st.cache_data
def load_game_logs(file_path):
    try:
        xls = pd.ExcelFile(file_path)
        first_sheet = xls.sheet_names[0]
        df = pd.read_excel(file_path, sheet_name=first_sheet)
        df.columns = [str(col).strip() for col in df.columns]
        return df
    except Exception:
        try:
            xls = pd.ExcelFile(f"../{file_path}")
            first_sheet = xls.sheet_names[0]
            df = pd.read_excel(f"../{file_path}", sheet_name=first_sheet)
            df.columns = [str(col).strip() for col in df.columns]
            return df
        except Exception:
            return None

df_games = load_game_logs(EXCEL_FILE)

if df_puck is not None:
    def get_col(data, col_name):
        if col_name and col_name in data.columns:
            s = data[col_name].replace(['-', '—', ''], 0)
            return pd.to_numeric(s, errors='coerce').fillna(0)
        return pd.Series(0, index=data.index)

    # Identify columns safely
    player_col = next((c for c in df_puck.columns if 'player' in c.lower()), 'Player')
    team_col = next((c for c in df_puck.columns if 'team' in c.lower()), 'Team')
    pos_col = next((c for c in df_puck.columns if 'position' in c.lower()), 'Position')

    df_puck['Player_clean'] = df_puck[player_col] if player_col in df_puck.columns else 'Unknown'
    df_puck['Team_clean'] = df_puck[team_col] if team_col in df_puck.columns else 'Unknown'
    df_puck['Pos_clean'] = df_puck[pos_col].astype(str).str.upper().str.strip() if pos_col in df_puck.columns else 'F'

    # --- SIDEBAR FILTERS ---
    st.sidebar.header("🔍 Filters")
    
    if team_col in df_puck.columns:
        all_teams = sorted(df_puck['Team_clean'].dropna().unique())
        selected_teams = st.sidebar.multiselect("Select Team(s):", all_teams, default=all_teams)
        df_filtered = df_puck[df_puck['Team_clean'].isin(selected_teams)].copy()
    else:
        df_filtered = df_puck.copy()

    selected_positions = st.sidebar.multiselect("Select Position:", ['F', 'D'], default=['F', 'D'])
    if pos_col in df_puck.columns:
        df_filtered = df_filtered[df_filtered['Pos_clean'].isin(selected_positions)]

    # --- MAIN TABS ---
    tab_team, tab_player, tab_xg = st.tabs([
        "🛡️ Team Analytics", 
        "👥 Player Statistics", 
        "📊 Expected Goals (xG) Analytics"
    ])

    # ---------------------------------------------------------
    # TAB 1: TEAM ANALYTICS
    # ---------------------------------------------------------
    with tab_team:
        st.subheader("🛡️ Team-Level Visual Comparisons")
        st.caption("Compare team playing styles, turnovers, net control, and total zone entries.")

        if team_col in df_filtered.columns:
            exclude_words = ['shirt', 'shift', 'ice', 'time', 'gp']
            stat_cols = [c for c in df_filtered.columns if c not in [player_col, team_col, pos_col, 'Player_clean', 'Team_clean', 'Pos_clean'] 
                         and not any(w in c.lower() for w in exclude_words)]

            for col in stat_cols:
                df_filtered[col] = get_col(df_filtered, col)

            # Aggregate sums by team
            team_agg = df_filtered.groupby('Team_clean')[stat_cols].sum().reset_index()
            team_agg = team_agg.rename(columns={'Team_clean': 'Team'})

            # Calculate Net Takeaways
            if 'Takeaways' in team_agg.columns and 'Puck losses' in team_agg.columns:
                team_agg['Net Takeaways'] = team_agg['Takeaways'] - team_agg['Puck losses']

            # --- CHARTS ---
            col_g1, col_g2 = st.columns(2)

            with col_g1:
                if 'Takeaways' in team_agg.columns and 'Puck losses' in team_agg.columns:
                    st.markdown("### 📊 Takeaways vs Puck Losses")
                    fig_tka = px.bar(
                        team_agg.sort_values(by='Takeaways', ascending=True),
                        y='Team', x=['Takeaways', 'Puck losses'],
                        barmode='group',
                        orientation='h',
                        title="Takeaways and Puck Losses by Team",
                        labels={'value': 'Count', 'variable': 'Metric', 'Team': 'Team'}
                    )
                    fig_tka.update_traces(texttemplate='%{x}', textposition='inside')
                    fig_tka.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_tka, use_container_width=True)

            with col_g2:
                if 'Net Takeaways' in team_agg.columns:
                    st.markdown("### ⚖️ Net Takeaways (Takeaways - Losses)")
                    fig_net = px.bar(
                        team_agg.sort_values(by='Net Takeaways', ascending=True),
                        y='Team', x='Net Takeaways',
                        orientation='h',
                        title="Puck Management Net (Positive = More takeaways than losses)",
                        color='Net Takeaways', color_continuous_scale='Teal'
                    )
                    fig_net.update_traces(texttemplate='%{x}', textposition='inside')
                    fig_net.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', showlegend=False)
                    st.plotly_chart(fig_net, use_container_width=True)

            # --- TOTAL ENTRIES & ENTRY STYLES ---
            entries_col = next((c for c in team_agg.columns if c.lower() == 'entries'), None)
            ent_pass_col = next((c for c in team_agg.columns if 'entries via pass' in c.lower()), None)
            ent_dump_col = next((c for c in team_agg.columns if 'entries via dump in' in c.lower()), None)
            ent_stick_col = next((c for c in team_agg.columns if 'entries via stickhandling' in c.lower()), None)

            col_e1, col_e2 = st.columns(2)

            with col_e1:
                if entries_col:
                    st.markdown("### 📥 Total Zone Entries")
                    fig_entries_tot = px.bar(
                        team_agg.sort_values(by=entries_col, ascending=True),
                        y='Team', x=entries_col,
                        orientation='h',
                        title="Total Zone Entries by Team",
                        labels={entries_col: 'Total Entries', 'Team': 'Team'},
                        color=entries_col, color_continuous_scale='Blues'
                    )
                    fig_entries_tot.update_traces(texttemplate='%{x}', textposition='inside')
                    fig_entries_tot.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', showlegend=False)
                    st.plotly_chart(fig_entries_tot, use_container_width=True)

            with col_e2:
                if ent_pass_col and ent_dump_col and ent_stick_col:
                    st.markdown("### 🏒 Zone Entry Styles Breakdown")
                    fig_entries_stack = px.bar(
                        team_agg.sort_values(by=entries_col if entries_col else team_agg.columns[1], ascending=True),
                        y='Team', x=[ent_pass_col, ent_dump_col, ent_stick_col],
                        barmode='stack',
                        orientation='h',
                        title="Entry Styles (Pass, Dump-in, Stickhandling)",
                        labels={'value': 'Count', 'variable': 'Entry Type', 'Team': 'Team'}
                    )
                    fig_entries_stack.update_traces(texttemplate='%{x}', textposition='inside')
                    fig_entries_stack.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_entries_stack, use_container_width=True)

            st.markdown("---")
            st.subheader("📋 Team Summary Table")
            st.dataframe(team_agg, use_container_width=True, hide_index=True)
        else:
            st.warning("Team column not found.")

    # ---------------------------------------------------------
    # TAB 2: PLAYER STATISTICS
    # ---------------------------------------------------------
    with tab_player:
        st.subheader("👥 Player Statistics & Rankings")
        
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.markdown("### 📊 Top 10 Takeaways by Player")
            if 'Takeaways' in df_filtered.columns:
                df_filtered['Takeaways_num'] = get_col(df_filtered, 'Takeaways')
                top_tka = df_filtered.sort_values(by='Takeaways_num', ascending=True).tail(10)
                fig_ptka = px.bar(top_tka, y='Player_clean', x='Takeaways_num', color='Team_clean', orientation='h', title="Top Takeaways")
                fig_ptka.update_traces(texttemplate='%{x}', textposition='inside')
                fig_ptka.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_ptka, use_container_width=True)

        with col_p2:
            st.markdown("### 🎯 Top 10 Puck Retrievals After Shots")
            ret_col = next((c for c in df_filtered.columns if 'retrievals after shots' in c.lower()), None)
            if ret_col:
                df_filtered['Ret_num'] = get_col(df_filtered, ret_col)
                top_ret = df_filtered.sort_values(by='Ret_num', ascending=True).tail(10)
                fig_pret = px.bar(top_ret, y='Player_clean', x='Ret_num', color='Team_clean', orientation='h', title="Top Retrievals After Shots")
                fig_pret.update_traces(texttemplate='%{x}', textposition='inside')
                fig_pret.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_pret, use_container_width=True)

        st.markdown("---")
        st.subheader("📋 Player Data Table")
        display_cols = [c for c in df_filtered.columns if c not in ['Player_clean', 'Team_clean', 'Pos_clean'] and not any(w in c.lower() for w in ['time on ice', 'all shifts', 'shirt number'])]
        st.dataframe(df_filtered[['Player_clean', 'Team_clean', 'Pos_clean'] + [c for c in display_cols if c not in [player_col, team_col, pos_col]]], use_container_width=True, hide_index=True)

    # ---------------------------------------------------------
    # TAB 3: EXPECTED GOALS (xG) ANALYTICS
    # ---------------------------------------------------------
    with tab_xg:
        st.subheader("📊 Team Expected Goals (xG) & Finishing Analysis")
        st.caption("Calculated team-level total Expected Goals (xG), actual goals scored, and finishing efficiency.")

        if df_games is not None:
            g_team_col = next((c for c in df_games.columns if 'team' in c.lower()), None)
            g_xg_col = next((c for c in df_games.columns if 'expected goals' in c.lower() or c.lower() == 'xg'), None)
            g_goals_col = next((c for c in df_games.columns if c.lower() == 'goals'), None)
            g_shots_col = next((c for c in df_games.columns if 'shots on goal' in c.lower()), None)

            if g_team_col and g_xg_col:
                # Ensure clean numbers
                df_games['xG_num'] = pd.to_numeric(df_games[g_xg_col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
                df_games['Goals_num'] = pd.to_numeric(df_games[g_goals_col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0) if g_goals_col else 0
                df_games['Shots_num'] = pd.to_numeric(df_games[g_shots_col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0) if g_shots_col else 0

                # Filter teams matching sidebar
                df_g_filtered = df_games[df_games[g_team_col].isin(selected_teams)].copy() if g_team_col in df_games.columns else df_games.copy()

                # Group by team
                team_xg_summary = df_g_filtered.groupby(g_team_col).agg({
                    'xG_num': 'sum',
                    'Goals_num': 'sum',
                    'Shots_num': 'sum'
                }).reset_index()

                team_xg_summary = team_xg_summary.rename(columns={
                    g_team_col: 'Team',
                    'xG_num': 'Total xG',
                    'Goals_num': 'Total Goals',
                    'Shots_num': 'Shots on Goal'
                })

                # Calculate finishing efficiency
                team_xg_summary['Finishing vs xG'] = team_xg_summary['Total Goals'] - team_xg_summary['Total xG']
                team_xg_summary = team_xg_summary.sort_values(by='Total xG', ascending=True)

                col_xg1, col_xg2 = st.columns(2)

                with col_xg1:
                    st.markdown("### 🎯 Total Expected Goals (xG) by Team")
                    fig_xg = px.bar(
                        team_xg_summary,
                        y='Team', x='Total xG',
                        orientation='h',
                        title="Cumulative Expected Goals (xG)",
                        color='Total xG',
                        color_continuous_scale='Teal'
                    )
                    fig_xg.update_traces(texttemplate='%{x:.2f}', textposition='inside')
                    fig_xg.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', showlegend=False)
                    st.plotly_chart(fig_xg, use_container_width=True)

                with col_xg2:
                    st.markdown("### ⚡ Finishing Efficiency (Goals - xG)")
                    fig_finish = px.bar(
                        team_xg_summary.sort_values(by='Finishing vs xG', ascending=True),
                        y='Team', x='Finishing vs xG',
                        orientation='h',
                        title="Finishing Differential (Positive = Outperforming xG)",
                        color='Finishing vs xG',
                        color_continuous_scale='RdYlGn'
                    )
                    fig_finish.update_traces(texttemplate='%{x:.2f}', textposition='inside')
                    fig_finish.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', showlegend=False)
                    st.plotly_chart(fig_finish, use_container_width=True)

                st.markdown("---")
                st.subheader("📋 Team xG Summary Table")
                st.dataframe(team_xg_summary.sort_values(by='Total xG', ascending=False), use_container_width=True, hide_index=True)

            else:
                st.warning("Required xG or Team columns were not found in the game log sheet.")
        else:
            st.info("Game log sheet could not be loaded for xG aggregation.")

else:
    st.warning("Failed to load Puck management data from Excel.")
