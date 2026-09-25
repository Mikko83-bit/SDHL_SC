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
    game_col = next((c for c in df.columns if c.strip().lower() == 'game'), None)
    toi_col = next((c for c in df.columns if 'time on ice' in c.lower() or 'toi' in c.lower()), None)
    
    def toi_to_seconds(val):
        if pd.isna(val):
            return 0
        if isinstance(val, (int, float)):
            return float(val) * 60
        val_str = str(val).strip()
        if ':' in val_str:
            parts = val_str.split(':')
            try:
                return float(parts[0]) * 60 + float(parts[1])
            except ValueError:
                return 0.0
        try:
            return float(val_str) * 60
        except ValueError:
            return 0.0

    if toi_col:
        df['TOI_Seconds'] = df[toi_col].apply(toi_to_seconds)
    else:
        df['TOI_Seconds'] = 0.0

    # Scoring Chances yhteenveto
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
    
    # Poistetaan Fenwick-sarakkeet
    df = df.drop(columns=[c for c in df.columns if 'fenwick' in c.lower()], errors='ignore')
    
    exclude_cols = group_cols + ([game_col, toi_col] if game_col and toi_col else ([game_col] if game_col else []))
    num_cols = [c for c in df.select_dtypes(include=['number']).columns.tolist() if c not in exclude_cols]
    
    if group_cols and num_cols:
        summary_df = df.groupby(group_cols)[num_cols].sum().reset_index()
        
        # Lasketaan pelatut pelit
        if game_col:
            games_played_df = df.groupby(group_cols)[game_col].nunique().reset_index(name='Games Played')
            summary_df = pd.merge(summary_df, games_played_df, on=group_cols, how='left')
        else:
            summary_df['Games Played'] = 1
            
        # Peliajan keskiarvo
        if toi_col and 'TOI_Seconds' in df.columns:
            toi_summary = df.groupby(group_cols)['TOI_Seconds'].sum().reset_index(name='Total_TOI_Sec')
            summary_df = pd.merge(summary_df, toi_summary, on=group_cols, how='left')
            games_for_toi = summary_df['Games Played'] if 'Games Played' in summary_df.columns else 1
            avg_sec = summary_df['Total_TOI_Sec'] / games_for_toi.replace(0, 1)
            summary_df['Average TOI'] = avg_sec.apply(lambda s: f"{int(s // 60)}:{int(s % 60):02d}")
            summary_df = summary_df.drop(columns=['Total_TOI_Sec', 'TOI_Seconds'], errors='ignore')

        # Scoring Chances liitos
        if sc_totals is not None and shirt_col in summary_df.columns:
            summary_df['Clean_Number'] = pd.to_numeric(summary_df[shirt_col], errors='coerce').fillna(-1).astype(int).astype(str)
            summary_df = pd.merge(summary_df, sc_totals[['Clean_Number', 'Scoring Chances Total']], on='Clean_Number', how='left')
            summary_df = summary_df.drop(columns=['Clean_Number'])
            summary_df['Scoring Chances Total'] = summary_df['Scoring Chances Total'].fillna(0)
        else:
            summary_df['Scoring Chances Total'] = 0
        
        # Siivotaan numeromuodot
        for col in summary_df.columns:
            if summary_df[col].dtype == object and col not in group_cols and col != 'Average TOI':
                summary_df[col] = summary_df[col].astype(str).str.replace(',', '.', regex=False)
                summary_df[col] = pd.to_numeric(summary_df[col], errors='coerce').fillna(0)

        # Siivotaan ylimääräiset Corsi-sarakkeet pois
        corsi_main = next((c for c in summary_df.columns if c.strip().upper() == 'CORSI'), None)
        cols_to_drop = [c for c in summary_df.columns if 'corsi' in c.lower() and c != corsi_main]
        if cols_to_drop:
            summary_df = summary_df.drop(columns=cols_to_drop)

        # Haetaan Net xG tarkalla nimellä ja nimetään uudeksi sarakkeeksi
        target_net_xg = "Net xG (xG player on - opp. team's xG)"
        if target_net_xg in summary_df.columns:
            summary_df['Net xG Total'] = summary_df[target_net_xg]
        else:
            # Varakuvaus, jos nimi poikkeaa vähän
            net_xg_source = next((c for c in summary_df.columns if 'net xg' in c.lower()), None)
            if net_xg_source:
                summary_df['Net xG Total'] = summary_df[net_xg_source]

        sort_col = 'Points' if 'Points' in summary_df.columns else (shirt_col if shirt_col else group_cols[0])
        if sort_col in summary_df.columns:
            summary_df = summary_df.sort_values(by=sort_col, ascending=False).reset_index(drop=True)

        # Määritellään tasan ne sarakkeet, jotka halutaan näyttää (ja varmistetaan etteivät ne katoa)
        desired_columns = []
        for c in group_cols:
            desired_columns.append(c)
        
        for c in ['Games Played', 'Average TOI', 'Goals', 'Points', 'Net xG Total', 'CORSI', 'Scoring Chances Total']:
            if c in summary_df.columns and c not in desired_columns:
                desired_columns.append(c)

        final_summary_df = summary_df[desired_columns]

        st.subheader("Pelaajien tilastoyhteenveto")
        st.dataframe(final_summary_df, use_container_width=True, hide_index=True)

    else:
        st.info("Ei löytynyt sopivia sarakkeita laskentaan.")
else:
    st.info("Ei dataa saatavilla.")
