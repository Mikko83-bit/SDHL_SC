import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="LHF Advanced Stats & Impact Score", layout="wide")
st.title("⭐ LHF Dam - Advanced Player Statistics & Impact Analysis")

adv_path = "LHF Dam season 2026-2027.xlsx"
sc_path = "SDHL 2026-2027 scoring chances.xlsx"

@st.cache_data
def load_all_data(adv_mtime, sc_mtime):
    xls_adv = pd.ExcelFile(adv_path)
    df_adv = pd.read_excel(xls_adv, sheet_name=xls_adv.sheet_names[0])
    df_adv.columns = df_adv.columns.astype(str).str.strip()
    
    xls_sc = pd.ExcelFile(sc_path)
    df_sc = pd.read_excel(xls_sc, sheet_name="Players")
    df_sc.columns = df_sc.columns.astype(str).str.strip()
    
    return df_adv, df_sc

mtime_adv = os.path.getmtime(adv_path) if os.path.exists(adv_path) else 0
mtime_sc = os.path.getmtime(sc_path) if os.path.exists(sc_path) else 0

df, players_sc_df = load_all_data(mtime_adv, mtime_sc)

if not df.empty:
    shirt_col = next((c for c in df.columns if 'shirt' in c.lower() or 'number' in c.lower()), None)
    player_name_col = next((c for c in df.columns if 'player' in c.lower() and 'shirt' not in c.lower()), None)
    game_col = next((c for c in df.columns if 'game' in c.lower()), None)
    toi_col = next((c for c in df.columns if 'time on ice' in c.lower() or 'toi' in c.lower()), None)
    
    # Apufunktio jääajan (mm:ss tai sekunnit) muuttamiseksi desinuuteiksi
    def toi_to_minutes(val):
        if pd.isna(val):
            return 0.0
        if isinstance(val, (int, float)):
            return float(val) # Jos se on jo minuutteina
        val_str = str(val).strip()
        if ':' in val_str:
            parts = val_str.split(':')
            try:
                return float(parts[0]) + float(parts[1]) / 60.0
            except ValueError:
                return 0.0
        try:
            return float(val_str)
        except ValueError:
            return 0.0

    if toi_col:
        df['TOI_Minutes'] = df[toi_col].apply(toi_to_minutes)
    else:
        df['TOI_Minutes'] = 0.0

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
    exclude_cols = group_cols + ([game_col, toi_col] if game_col and toi_col else ([game_col] if game_col else []))
    num_cols = [c for c in df.select_dtypes(include=['number']).columns.tolist() if c not in exclude_cols]
    
    if group_cols and num_cols:
        # Summataan tilastot ja peliaika yhteen pelaajakohtaisesti
        summary_df = df.groupby(group_cols)[num_cols].sum().reset_index()
        
        if game_col:
            games_played = df.groupby(group_cols)[game_col].nunique().reset_index(name='Games Played')
            summary_df = pd.merge(summary_df, games_played, on=group_cols)
            
        if sc_totals is not None and shirt_col in summary_df.columns:
            summary_df['Clean_Number'] = pd.to_numeric(summary_df[shirt_col], errors='coerce').fillna(-1).astype(int).astype(str)
            summary_df = pd.merge(summary_df, sc_totals[['Clean_Number', 'Scoring Chances Total']], on='Clean_Number', how='left')
            summary_df = summary_df.drop(columns=['Clean_Number'])
            summary_df['Scoring Chances Total'] = summary_df['Scoring Chances Total'].fillna(0)
        
        net_xg_col = next((c for c in summary_df.columns if 'net xg' in c.lower() or 'xg' in c.lower()), None)
        corsi_col = next((c for c in summary_df.columns if 'corsi' in c.lower()), None)
        battles_col = next((c for c in summary_df.columns if 'battle' in c.lower() or 'puck' in c.lower()), None)
        
        def clean_and_convert(series):
            if series is None:
                return None
            if series.dtype == object:
                series = series.astype(str).str.replace(',', '.', regex=False)
            return pd.to_numeric(series, errors='coerce').fillna(0)

        if net_xg_col:
            summary_df[net_xg_col] = clean_and_convert(summary_df[net_xg_col])
        if corsi_col:
            summary_df[corsi_col] = clean_and_convert(summary_df[corsi_col])
        if battles_col:
            summary_df[battles_col] = clean_and_convert(summary_df[battles_col])

        # --- JÄÄAIKAAN SUHTEUTTAMINEN (Per 60 minuuttia) ---
        toi_sum_col = 'TOI_Minutes' if 'TOI_Minutes' in summary_df.columns else None
        
        if toi_sum_col and summary_df[toi_sum_col].sum() > 0:
            # Muutetaan arvot suhteessa peliaikaan (per 60 min) jotta vertailu on reilua
            factor = 60.0 / summary_df[toi_sum_col].replace(0, 1) # vältetään nollalla jako
            
            # Luodaan vertailua varten Per 60 -sarakkeet Z-score laskentaa varten
            metric_net_xg = summary_df[net_xg_col] * factor if net_xg_col else pd.Series(0, index=summary_df.index)
            metric_sc = summary_df['Scoring Chances Total'] * factor if 'Scoring Chances Total' in summary_df.columns else pd.Series(0, index=summary_df.index)
            metric_corsi = summary_df[corsi_col] * factor if corsi_col else pd.Series(0, index=summary_df.index)
            metric_battles = summary_df[battles_col] * factor if battles_col else pd.Series(0, index=summary_df.index)
        else:
            metric_net_xg = summary_df[net_xg_col] if net_xg_col else pd.Series(0, index=summary_df.index)
            metric_sc = summary_df['Scoring Chances Total'] if 'Scoring Chances Total' in summary_df.columns else pd.Series(0, index=summary_df.index)
            metric_corsi = summary_df[corsi_col] if corsi_col else pd.Series(0, index=summary_df.index)
            metric_battles = summary_df[battles_col] if battles_col else pd.Series(0, index=summary_df.index)

        def get_z_score(series):
            if series is None or series.std() == 0 or pd.isna(series.std()):
                return pd.Series(0, index=series.index)
            return (series - series.mean()) / series.std()

        z_xg = get_z_score(metric_net_xg)
        z_sc = get_z_score(metric_sc)
        z_corsi = get_z_score(metric_corsi)
        z_battles = get_z_score(metric_battles)
        
        summary_df['Comp_NetxG'] = z_xg * 1.5
        summary_df['Comp_SC'] = z_sc * 1.2
        summary_df['Comp_Corsi'] = z_corsi * 1.0
        summary_df['Comp_Battles'] = z_battles * 0.8
        
        summary_df['5v5 Impact Score'] = round(
            summary_df['Comp_NetxG'] + summary_df['Comp_SC'] + summary_df['Comp_Corsi'] + summary_df['Comp_Battles'], 2
        )
        
        # Siivotaan apusarake pois lopullisesta näytöstä
        if 'TOI_Minutes' in summary_df.columns:
            summary_df = summary_df.drop(columns=['TOI_Minutes'])

        summary_df = summary_df.sort_values(by='5v5 Impact Score', ascending=False).reset_index(drop=True)

        tab_table, tab_breakdown = st.tabs(["📊 Advanced Player Stats", "⭐ 5v5 Impact Score Breakdown"])

        with tab_table:
            st.subheader("Advanced Player Statistics (Per 60 min normalized impact)")
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
            st.subheader("What makes up the 5v5 Impact Score? (Z-score standardized Per 60)")
            st.markdown("""
            Statistics are adjusted to **Per 60 minutes** and standardized (Z-score) so that players with different ice times can be compared fairly:
            * **Net xG / 60 (Weight 1.5)**
            * **Scoring Chances / 60 (Weight 1.2)**
            * **CORSI Net / 60 (Weight 1.0)**
            * **Puck Battles / 60 (Weight 0.8)**
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
                'Comp_Battles': 'Battles (Z-score)'
            })
            
            st.dataframe(breakdown_display, use_container_width=True, hide_index=True)

    else:
        st.info("No suitable columns found for calculations.")
else:
    st.info("No data available.")
