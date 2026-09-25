import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="LHF Dam - Player Statistics Summary", layout="wide")
st.title("📊 LHF Dam - Player Statistics Summary")

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
    
    # Haetaan Scoring Chances tiedostosta yhteenveto pelaajille
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
        # Summataan tilastot yhteen pelaajakohtaisesti
        summary_df = df.groupby(group_cols)[num_cols].sum().reset_index()
        
        # Lasketaan pelatut pelit erikseen (unikaalit pelit per pelaaja)
        if game_col:
            games_played = df.groupby(group_cols)[game_col].nunique().reset_index(name='Games Played')
            summary_df = pd.merge(summary_df, games_played, on=group_cols)
            
        # Liitetään Scoring Chances Total mukaan
        if sc_totals is not None and shirt_col in summary_df.columns:
            summary_df['Clean_Number'] = pd.to_numeric(summary_df[shirt_col], errors='coerce').fillna(-1).astype(int).astype(str)
            summary_df = pd.merge(summary_df, sc_totals[['Clean_Number', 'Scoring Chances Total']], on='Clean_Number', how='left')
            summary_df = summary_df.drop(columns=['Clean_Number'])
            summary_df['Scoring Chances Total'] = summary_df['Scoring Chances Total'].fillna(0)
        
        # Siivotaan ja muutetaan tekstinä olevat arvot varmuuden vuoksi numeroiksi
        for col in summary_df.columns:
            if summary_df[col].dtype == object and col not in group_cols:
                summary_df[col] = summary_df[col].astype(str).str.replace(',', '.', regex=False)
                summary_df[col] = pd.to_numeric(summary_df[col], errors='coerce').fillna(0)

        # Järjestetään haluttujen sarakkeiden mukaan (esim. pisteiden mukaan laskevasti, jos löytyy)
        sort_col = 'Points' if 'Points' in summary_df.columns else (shirt_col if shirt_col else group_cols[0])
        summary_df = summary_df.sort_values(by=sort_col, ascending=False).reset_index(drop=True)

        # Määritellään sarakkeiden haluttu järjestys (Games Played, Goals, Points, jne. ensin)
        cols = list(summary_df.columns)
        priority_cols = ['Games Played', 'Goals', 'Points', '+/-', 'Faceoffs', 'Shots on goal', 'Net xG (xg on ice - opp. team\'s xG)', 'CORSI', 'Scoring Chances Total']
        
        reordered_cols = []
        for c in group_cols:
            if c in cols:
                reordered_cols.append(c)
        for c in priority_cols:
            if c in cols and c not in reordered_cols:
                reordered_cols.append(c)
        for c in cols:
            if c not in reordered_cols:
                reordered_cols.append(c)

        st.subheader("Pelaajien tilastoyhteenveto")
        st.dataframe(summary_df[reordered_cols], use_container_width=True, hide_index=True)

    else:
        st.info("Ei löydyttä sopivia sarakkeita laskentaan.")
else:
    st.info("Ei dataa saatavilla.")
