import streamlit as st
import pandas as pd

st.set_page_config(page_title="LHF Advanced Stats & Impact Score", layout="wide")
st.title("⭐ LHF Dam - Advanced Player Statistics & Impact Analysis")

@st.cache_data
def load_all_data():
    adv_path = "LHF Dam season 2026-2027.xlsx"
    xls_adv = pd.ExcelFile(adv_path)
    df_adv = pd.read_excel(xls_adv, sheet_name=xls_adv.sheet_names[0])
    df_adv.columns = df_adv.columns.astype(str).str.strip()
    
    sc_path = "SDHL 2026-2027 scoring chances.xlsx"
    xls_sc = pd.ExcelFile(sc_path)
    df_sc = pd.read_excel(xls_sc, sheet_name="Players")
    df_sc.columns = df_sc.columns.astype(str).str.strip()
    
    return df_adv, df_sc

df, players_sc_df = load_all_data()

if not df.empty:
    shirt_col = next((c for c in df.columns if 'shirt' in c.lower() or 'number' in c.lower()), None)
    player_name_col = next((c for c in df.columns if 'player' in c.lower() and 'shirt' not in c.lower()), None)
    game_col = next((c for c in df.columns if 'game' in c.lower()), None)
    
    sc_totals = None
    if not players_sc_df.empty and 'Number' in players_sc_df.columns:
        p_num_cols = [c for c in players_sc_df.select_dtypes(include=['number']).columns.tolist() if c not in ["Number", "Game", "Game "]]
        sc_summary = players_sc_df.groupby("Number")[p_num_cols].sum().reset_index()
        
        gf = sc_summary['Goal For'] if 'Goal For' in sc_summary.columns else 0
        gfi = sc_summary['Goal For inv'] if 'Goal For inv' in sc_summary.columns else 0
        cf = sc_summary['Chance For'] if 'Chance For' in sc_summary.columns else 0
        cfi = sc_summary['Chance For inv'] if 'Chance For inv' in sc_summary.columns else 0
        ga = sc_summary['Goal Against'] if 'Goal Against' in sc_summary.columns else 0
        ca = sc_summary['Chance Against'] if 'Chance Against' in sc_summary.columns else 0
        
        sc_summary['Scoring Chances Total'] = (gf + gfi + cf + cfi) - (ga + ca)
        sc_totals = sc_summary[['Number', 'Scoring Chances Total']].copy()
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
        
        # Oikeat sarakkeet suoraan kuvasta
        net_xg_col = next((c for c in summary_df.columns if 'net xg' in c.lower()), None)
        corsi_pct_col = next((c for c in summary_df.columns if 'corsi for, %' in c.lower()), None)
        battles_col = next((c for c in summary_df.columns if 'puck battles won' in c.lower()), None)
        
        # Varmistetaan että Corsi % on varmasti numeerinen
        if corsi_pct_col:
            summary_df[corsi_pct_col] = pd.to_numeric(summary_df[corsi_pct_col], errors='coerce')
        
        def get_z_score(series):
            if series is None or series.std() == 0 or pd.isna(series.std()):
                return pd.Series(0, index=series.index)
            return (series - series.mean()) / series.std()

        z_xg = get_z_score(summary_df[net_xg_col]) if net_xg_col else pd.Series(0, index=summary_df.index)
        z_sc = get_z_score(summary_df['Scoring Chances Total']) if 'Scoring Chances Total' in summary_df.columns else pd.Series(0, index=summary_df.index)
        z_corsi = get_z_score(summary_df[corsi_pct_col]) if corsi_pct_col else pd.Series(0, index=summary_df.index)
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
            st.subheader("Laaja tilastotaulukko")
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
            st.subheader("Mistä pelaajien 5v5 Impact Score koostuu? (Z-score standardoitu)")
            st.markdown("""
            Tilastot on standardoitu (Z-score), jotta eri osa-alueet ovat vertailukelpoisia keskenään:
            * **Net xG (Paino 1.5)**
            * **Scoring Chances Total (Paino 1.2)**
            * **CORSI for, % (Paino 1.0)**
            * **Voitetut puck battles won (Paino 0.8)**
            """)
            
            st.markdown("---")
            st.subheader("Pelaajakohtainen komponenttitaulukko")
            
            breakdown_table_cols = [shirt_col, player_name_col, '5v5 Impact Score', 'Comp_NetxG', 'Comp_SC', 'Comp_Corsi', 'Comp_Battles']
            breakdown_table_cols = [c for c in breakdown_table_cols if c and c in summary_df.columns]
            
            breakdown_display = summary_df[breakdown_table_cols].copy()
            breakdown_display = breakdown_display.rename(columns={
                'Comp_NetxG': 'Net xG (Z-pisteet)',
                'Comp_SC': 'Scoring Chances (Z-pisteet)',
                'Comp_Corsi': 'Corsi % (Z-pisteet)',
                'Comp_Battles': 'Kamppailut (Z-pisteet)'
            })
            
            st.dataframe(breakdown_display, use_container_width=True, hide_index=True)

    else:
        st.info("Ei löydetty sopivia sarakkeita laskentaan.")
else:
    st.info("Ei dataa ladattavissa.")
