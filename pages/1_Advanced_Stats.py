import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="LHF Dam - Player Statistics Summary", layout="wide")
st.title("📊 LHF Dam - Player Statistics Summary")

adv_path = "LHF Dam season 2026-2027.xlsx"
sc_path = "SDHL 2026-2027 scoring chances.xlsx"

@st.cache_data
def load_all_data(adv_mtime, sc_mtime):
    if os.path.exists(adv_path):
        xls_adv = pd.ExcelFile(adv_path)
        df_adv = pd.read_excel(xls_adv, sheet_name=xls_adv.sheet_names[0])
        df_adv.columns = df_adv.columns.astype(str).str.strip()
    else:
        df_adv = pd.DataFrame()
    
    if os.path.exists(sc_path):
        xls_sc = pd.ExcelFile(sc_path)
        df_sc = pd.read_excel(xls_sc, sheet_name="Players")
        df_sc.columns = df_sc.columns.astype(str).str.strip()
    else:
        df_sc = pd.DataFrame()
        
    return df_adv, df_sc

mtime_adv = os.path.getmtime(adv_path) if os.path.exists(adv_path) else 0
mtime_sc = os.path.getmtime(sc_path) if os.path.exists(sc_path) else 0

df, players_sc_df = load_all_data(mtime_adv, mtime_sc)

if not df.empty:
    shirt_col = next((c for c in df.columns if 'shirt' in c.lower() or 'number' in c.lower()), None)
    player_name_col = next((c for c in df.columns if 'player' in c.lower() and 'shirt' not in c.lower()), None)
    game_col = next((c for c in df.columns if c.strip().lower() == 'game'), None)
    toi_col = next((c for c in df.columns if 'time on ice' in c.lower() or 'toi' in c.lower()), None)
    
    # Pakotetaan perussarakkeet ja aloitussarakkeet numeroiksi
    for col_name in df.columns:
        if any(term in col_name.lower() for term in ['goals', 'points', 'net xg', 'faceoff', 'draw', 'won']):
            df[col_name] = df[col_name].astype(str).str.replace(',', '.', regex=False)
            df[col_name] = pd.to_numeric(df[col_name], errors='coerce').fillna(0)

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

    # Scoring Chances Total laskenta tiedostosta
    sc_totals = None
    if not players_sc_df.empty and 'Number' in players_sc_df.columns:
        for col in players_sc_df.columns:
            if col not in ["Number", "Game", "Opponent", "Date"]:
                players_sc_df[col] = pd.to_numeric(players_sc_df[col].astype(str).str.replace(',', '.', regex=False), errors='coerce').fillna(0)

        for_cols = [c for c in players_sc_df.columns if ('for' in c.lower() or 'goal' in c.lower()) and 'agains' not in c.lower() and c not in ["Number", "Game", "Opponent", "Date"]]
        against_cols = [c for c in players_sc_df.columns if 'agains' in c.lower() and c not in ["Number", "Game", "Opponent", "Date"]]

        sc_summary = players_sc_df.groupby("Number").agg({c: 'sum' for c in for_cols + against_cols}).reset_index()

        total_chances_for = sc_summary[for_cols].sum(axis=1) if for_cols else 0
        total_chances_against = sc_summary[against_cols].sum(axis=1) if against_cols else 0
        
        sc_summary['Scoring Chances Total'] = total_chances_for - total_chances_against

        sc_totals = sc_summary[['Number', 'Scoring Chances Total']].copy()
        sc_totals['Clean_Number'] = pd.to_numeric(sc_totals['Number'], errors='coerce').fillna(-1).astype(int).astype(str)

    if player_name_col:
        all_players = sorted(df[player_name_col].dropna().unique().tolist())
        selected_players = st.sidebar.multiselect("Select Player", options=all_players, default=all_players)
        if selected_players:
            df = df[df[player_name_col].isin(selected_players)]
            
    group_cols = [c for c in [shirt_col, player_name_col] if c]
    
    df = df.drop(columns=[c for c in df.columns if 'fenwick' in c.lower()], errors='ignore')
    
    exclude_cols = group_cols + ([game_col, toi_col] if game_col and toi_col else ([game_col] if game_col else []))
    num_cols = [c for c in df.select_dtypes(include=['number']).columns.tolist() if c not in exclude_cols]
    
    if group_cols and num_cols:
        summary_df = df.groupby(group_cols)[num_cols].sum().reset_index()
        
        if game_col:
            games_played_df = df.groupby(group_cols)[game_col].nunique().reset_index(name='Games Played')
            summary_df = pd.merge(summary_df, games_played_df, on=group_cols, how='left')
        else:
            summary_df['Games Played'] = 1
            
        if toi_col and 'TOI_Seconds' in df.columns:
            toi_summary = df.groupby(group_cols)['TOI_Seconds'].sum().reset_index(name='Total_TOI_Sec')
            summary_df = pd.merge(summary_df, toi_summary, on=group_cols, how='left')
            games_for_toi = summary_df['Games Played'] if 'Games Played' in summary_df.columns else 1
            avg_sec = summary_df['Total_TOI_Sec'] / games_for_toi.replace(0, 1)
            summary_df['Average TOI'] = avg_sec.apply(lambda s: f"{int(s // 60)}:{int(s % 60):02d}")
            summary_df = summary_df.drop(columns=['Total_TOI_Sec', 'TOI_Seconds'], errors='ignore')

        # Aloitusten (Faceoffs) haku ja laskenta englanninkielisillä nimillä
        fo_total_col = next((c for c in df.columns if c.strip().lower() == 'faceoffs'), None)
        fo_won_col = next((c for c in df.columns if 'faceoffs won' in c.lower() and '%' not in c.lower()), None)

        if fo_total_col and fo_won_col:
            fo_summary = df.groupby(group_cols)[[fo_total_col, fo_won_col]].sum().reset_index()
            summary_df['Faceoffs'] = fo_summary[fo_total_col]
            summary_df['Faceoffs won %'] = (fo_summary[fo_won_col] / fo_summary[fo_total_col].replace(0, 1) * 100).round(1)
        else:
            possible_fo = [c for c in df.columns if 'faceoff' in c.lower() and 'won' not in c.lower() and '%' not in c.lower()]
            if possible_fo:
                summary_df['Faceoffs'] = df.groupby(group_cols)[possible_fo[0]].sum().values
            else:
                summary_df['Faceoffs'] = 0
            summary_df['Faceoffs won %'] = 0.0

        # Liitetään Scoring Chances Total pelaajan numeron perusteella
        if sc_totals is not None and shirt_col in summary_df.columns:
            summary_df['Clean_Number'] = pd.to_numeric(summary_df[shirt_col], errors='coerce').fillna(-1).astype(int).astype(str)
            summary_df = pd.merge(summary_df, sc_totals[['Clean_Number', 'Scoring Chances Total']], on='Clean_Number', how='left')
            summary_df = summary_df.drop(columns=['Clean_Number'])
            summary_df['Scoring Chances Total'] = summary_df['Scoring Chances Total'].fillna(0)
        else:
            summary_df['Scoring Chances Total'] = 0

        corsi_main = next((c for c in summary_df.columns if c.strip().upper() == 'CORSI'), None)
        cols_to_drop = [c for c in summary_df.columns if 'corsi' in c.lower() and c != corsi_main]
        if cols_to_drop:
            summary_df = summary_df.drop(columns=cols_to_drop)

        target_net_xg = "Net xG (xG player on - opp. team's xG)"
        if target_net_xg in summary_df.columns:
            summary_df['Net xG Total'] = summary_df[target_net_xg]

        sort_col = 'Points' if 'Points' in summary_df.columns else (shirt_col if shirt_col else group_cols[0])
        if sort_col in summary_df.columns:
            summary_df = summary_df.sort_values(by=sort_col, ascending=False).reset_index(drop=True)

        desired_columns = []
        for c in group_cols:
            desired_columns.append(c)
        
        for c in ['Games Played', 'Average TOI', 'Goals', 'Points', 'Net xG Total', 'CORSI', 'Scoring Chances Total', 'Faceoffs', 'Faceoffs won %']:
            if c in summary_df.columns and c not in desired_columns:
                desired_columns.append(c)

        final_summary_df = summary_df[desired_columns]

        st.subheader("Pelaajien tilastoyhteenveto")
        
        column_config = {
            shirt_col: st.column_config.NumberColumn("Shirt number", width="small"),
            player_name_col: st.column_config.TextColumn("Player", width="medium"),
            "Games Played": st.column_config.NumberColumn("Games Played", width="small"),
            "Average TOI": st.column_config.TextColumn("Average TOI", width="small"),
            "Goals": st.column_config.NumberColumn("Goals", width="small"),
            "Points": st.column_config.NumberColumn("Points", width="small"),
            "Net xG Total": st.column_config.NumberColumn("Net xG Total", width="small", format="%.2f"),
            "CORSI": st.column_config.NumberColumn("CORSI", width="small"),
            "Scoring Chances Total": st.column_config.NumberColumn("Scoring Chances Total", width="small"),
            "Faceoffs": st.column_config.NumberColumn("Faceoffs", width="small"),
            "Faceoffs won %": st.column_config.NumberColumn("Faceoffs won %", width="small", format="%.1f%%")
        }

        st.dataframe(
            final_summary_df, 
            use_container_width=False, 
            hide_index=True,
            column_config={k: v for k, v in column_config.items() if k in final_summary_df.columns}
        )

    else:
        st.info("Ei löytynyt sopivia sarakkeita laskentaan.")
else:
    st.info("Ei dataa saatavilla.")
