import streamlit as st
import pandas as pd

st.set_page_config(page_title="LHF Dam - Advanced Player Statistics & Impact Analysis", layout="wide")
st.title("⭐ LHF Dam - Advanced Player Statistics & Impact Analysis")

@st.cache_data
def load_all_data():
    adv_path = "LHF Dam season 2026-2027.xlsx"
    xls_adv = pd.ExcelFile(adv_path)
    df_adv = pd.read_excel(xls_adv, sheet_name=xls_adv.sheet_names[0])
    df_adv.columns = df_adv.columns.astype(str).str.strip()
    
    sc_path = "SDHL 2026-2027 scoring chances.xlsx"
    xls_sc = pd.ExcelFile(xls_sc_path := sc_path) # pylint: disable=undefined-variable
    xls_sc = pd.ExcelFile(sc_path)
    df_sc = pd.read_excel(xls_sc, sheet_name="Players")
    df_sc.columns = df_sc.columns.astype(str).str.strip()
    
    return df_adv, df_sc

df, players_sc_df = load_all_data()

if not df.empty:
    filtered_sc_df = players_sc_df.copy()
    
    # --- 1. SUODATIN: Category (esim. OZ, NZ, DZ) ---
    cat_col = next((c for c in filtered_sc_df.columns if c.strip().lower() in ['category', 'cat']), None)
    if cat_col:
        categories = sorted(filtered_sc_df[cat_col].dropna().astype(str).unique().tolist())
        selected_cats = st.sidebar.multiselect("Select Category", options=categories, default=categories)
        if selected_cats:
            filtered_sc_df = filtered_sc_df[filtered_sc_df[cat_col].astype(str).isin(selected_cats)]

    # --- 2. SUODATIN: Tapahtumatyyppi / Sarakkeet (Goal For, Chance For, PP goal, Goal Against yms.) ---
    # Etsitään sarakkeet jotka vastaavat näitä tapahtumia taulukosta
    event_columns = [
        'Goal For', 'Goal For inv', 'Chance For', 'Chance For inv', 
        'PP goal', 'PP goal inv', 'PP chance', 'PP chance inv', 
        'Goal Against', 'Chance Against', 'PP goal ag', 'PP chance ag'
    ]
    available_events = [c for c in event_columns if c in filtered_sc_df.columns]
    
    if available_events:
        selected_events = st.sidebar.multiselect(
            "Select Event Type", 
            options=available_events, 
            default=available_events
        )
    else:
        selected_events = []

    st.sidebar.markdown("---")

    shirt_col = next((c for c in df.columns if 'shirt' in c.lower() or 'number' in c.lower()), None)
    player_name_col = next((c for c in df.columns if 'player' in c.lower() and 'shirt' not in c.lower()), None)
    game_col = next((c for c in df.columns if 'game' in c.lower()), None)
    
    sc_totals = None
    sc_num_col = next((c for c in filtered_sc_df.columns if 'number' in c.lower() or c.strip() == 'Number'), None)
    
    if not filtered_sc_df.empty and sc_num_col:
        p_num_cols = [c for c in filtered_sc_df.select_dtypes(include=['number']).columns.tolist() if c not in [sc_num_col, "Game", "Game "]]
        sc_summary = filtered_sc_df.groupby(sc_num_col)[p_num_cols].sum().reset_index()
        
        # Jos käyttäjä on rajannut tapahtumia toisella suodattimella, huomioidaan ne laskennassa
        if selected_events:
            positive_opts = [e for e in selected_events if 'against' not in e.lower() and 'ag' not in e.lower()]
            negative_opts = [e for e in selected_events if 'against' in e.lower() or 'ag' in e.lower()]
            
            pos_sum = sum(sc_summary[e] for e in positive_opts if e in sc_summary.columns) if positive_opts else 0
            neg_sum = sum(sc_summary[e] for e in negative_opts if e in sc_summary.columns) if negative_opts else 0
            sc_summary['Scoring Chances Total'] = pos_sum - neg_sum
        else:
            sc_summary['Scoring Chances Total'] = 0
            
        sc_totals = sc_summary[[sc_num_col, 'Scoring Chances Total']].copy()
        sc_totals.columns = ['Number', 'Scoring Chances Total']
        sc_totals['Clean_Number'] = pd.to_numeric(sc_totals['Number'], errors='coerce').fillna(-1).astype(int).astype(str)

    if player_name_col:
        all_players = sorted(df[player_name_col].dropna().unique().tolist())
        selected_players = st.sidebar.multiselect("Select Player", options=all_players, default=all_players)
        if selected_players:
            df = df[df[player_name_col].isin(selected_players)]
            
    group_cols = [c for c in [shirt_col, player_name_col] if c]
    exclude_cols = group_cols + ([game_col] if game_col else [])
    num_cols = [c for c in df.select_dtypes(include=['number']).columns.tolist() if c not in exclude_cols]
    
    if group_cols and num_cols:
        summary_df = df.groupby(group_cols)[num_cols].sum().reset_index()
        
        if game_col:
            games_played = df.groupby(group_cols)[game_col].nunique().reset_index(name='Games Played')
            summary_df = pd.merge(summary_df, games_played, on=group_cols)
            
        if sc_totals is not None and shirt_col in summary_df.columns:
            summary_df['Clean_Number'] = pd.to_numeric(summary_df[shirt_col], errors='coerce').fillna(-1).astype(int).astype(str)
            summary_df = pd.merge(summary_df, sc_totals[['Clean_Number', 'Scoring Chances Total']], on='Clean_Number', how='left')
            summary_df = summary_df.drop(columns=['Clean_Number'])
            summary_df['Scoring Chances Total'] = summary_df['Scoring Chances Total'].fillna(0)
        
        net_xg_col = next((c for c in summary_df.columns if 'net xg' in c.lower()), None)
        corsi_col = next((c for c in summary_df.columns if c.strip().upper() == 'CORSI'), None)
        battles_col = next((c for c in summary_df.columns if 'puck battles won' in c.lower()), None)
        
        if corsi_col:
            summary_df[corsi_col] = pd.to_numeric(summary_df[corsi_col], errors='coerce')
        
        def get_z_score(series):
            if series is None or series.std() == 0 or pd.isna(series.std()):
                return pd.Series(0, index=series.index)
            return (series - series.mean()) / series.std()

        z_xg = get_z_score(summary_df[net_xg_col]) if net_xg_col else pd.Series(0, index=summary_df.index)
        z_sc = get_z_score(summary_df['Scoring Chances Total']) if 'Scoring Chances Total' in summary_df.columns else pd.Series(0, index=summary_df.index)
        z_corsi = get_z_score(summary_df[corsi_col]) if corsi_col else pd.Series(0, index=summary_df.index)
        z_battles = get_z_score(summary_df[battles_col]) if battles_col else pd.Series(0, index=summary_df.index)
        
        summary_df['Comp_NetxG'] = z_xg * 1.5
        summary_df['Comp_SC'] = z_sc * 1.2
        summary_df['Comp_Corsi'] = z_corsi * 1.0
        summary_df['Comp_Battles'] = z_battles * 0.8
        
        summary_df['5v5 Impact Score'] = round(
            summary_df['Comp_NetxG'] + summary_df['Comp_SC'] + summary_df['Comp_Corsi'] + summary_df['Comp_Battles'], 2
        )
        
        summary_df = summary_df.sort_values(by='5v5 Impact Score', ascending=False).reset_index(drop=True)

        tab_table, tab_breakdown = st.tabs(["📊 Advanced Player Stats", "⭐ 5v5 Impact Score Breakdown"])

        with tab_table:
            st.subheader("Advanced Player Statistics")
            display_df = summary_df.drop(columns=[c for c in summary_df.columns if c.startswith('Comp_')])
            
            cols = list(display_df.columns)
            for col_to_move in ['5v5 Impact Score', 'Scoring Chances Total', 'Games Played']:
                if col_to_move in cols:
                    cols.remove(col_to_move)
            insert_idx = 2 if len(cols) >= 2 else len(cols)
            for col_to_move in reversed(['5v5 Impact Score', 'Scoring Chances Total', 'Games Played']):
                if col_to_move in display_df.columns:
                    cols.insert(insert_idx, col_to_move)
            
            st.dataframe(display_df[cols], use_container_width=True, hide_index=True)

        with tab_breakdown:
            st.subheader("What makes up the 5v5 Impact Score? (Z-score standardized)")
            st.markdown("""
            Statistics are standardized (Z-score) to make different metrics directly comparable:
            * **Net xG (Weight 1.5)**
            * **Scoring Chances Total (Weight 1.2)**
            * **CORSI Net (Weight 1.0)**
            * **Puck Battles Won (Weight 0.8)**
            """)
            
            st.markdown("---")
            st.subheader("Player Component Breakdown")
            
            breakdown_table_cols = [shirt_col, player_name_col, '5v5 Impact Score', 'Comp_NetxG', 'Comp_SC', 'Comp_Corsi', 'Comp_Battles']
            breakdown_table_cols = [c for c in breakdown_table_cols if c and c in summary_df.columns]
            
            breakdown_display = summary_df[breakdown_table_cols].copy()
            breakdown_display = breakdown_display.rename(columns={
                'Comp_NetxG': 'Net xG (Z-score)',
                'Comp_SC': 'Scoring Chances (Z-score)',
                'Comp_Corsi': 'CORSI (Z-score)',
                'Comp_Battles': 'Battles Won (Z-score)'
            })
            
            st.dataframe(breakdown_display, use_container_width=True, hide_index=True)

    else:
        st.info("No suitable columns found for calculations.")
else:
    st.info("No data available.")
