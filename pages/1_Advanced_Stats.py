import streamlit as st
import pandas as pd

st.set_page_config(page_title="LHF Advanced Stats", layout="wide")
st.title("⭐ LHF SDHL - Advanced Player Statistics & Impact Score")

@st.cache_data
def load_advanced_data():
    adv_path = "LHF Dam season 2026-2027.xlsx"
    xls_adv = pd.ExcelFile(adv_path)
    df = pd.read_excel(xls_adv, sheet_name=xls_adv.sheet_names[0])
    df.columns = df.columns.astype(str).str.strip()
    return df

df = load_advanced_data()

st.subheader("Player Metrics & 5v5 Impact Score")
if not df.empty:
    shirt_col = next((c for c in df.columns if 'shirt' in c.lower() or 'number' in c.lower()), None)
    player_name_col = next((c for c in df.columns if 'player' in c.lower() and 'shirt' not in c.lower()), None)
    
    # Pelaajasuodatin sivupalkkiin
    if player_name_col:
        all_players = sorted(df[player_name_col].dropna().unique().tolist())
        selected_players = st.sidebar.multiselect("Select Player", options=all_players, default=all_players)
        if selected_players:
            df = df[df[player_name_col].isin(selected_players)]
            
    group_cols = [c for c in [shirt_col, player_name_col] if c]
    num_cols = [c for c in df.select_dtypes(include=['number']).columns.tolist() if c not in group_cols]
    
    if group_cols and num_cols:
        summary_df = df.groupby(group_cols)[num_cols].sum().reset_index()
        
        # Luodaan 5v5 Impact Score hyödyntämällä olemassa olevia edistyneitä sarakkeita (jos ne löytyvät datasta)
        net_xg_col = next((c for c in summary_df.columns if 'net xg' in c.lower() or ('xg' in c.lower() and 'opp' in c.lower())), None)
        corsi_pct_col = next((c for c in summary_df.columns if 'corsi for, %' in c.lower()), None)
        battles_col = next((c for c in summary_df.columns if 'puck battles won' in c.lower()), None)
        
        # Lasketaan painotettu vaikutusluku
        impact_score = 0
        if net_xg_col:
            impact_score += summary_df[net_xg_col] * 10
        if corsi_pct_col:
            # Normataan Corsi-% suhteessa 50% keskiarvoon
            impact_score += (summary_df[corsi_pct_col] - 50) * 0.2
        if battles_col:
            impact_score += summary_df[battles_col] * 0.1
            
        summary_df['5v5 Impact Score'] = round(impact_score, 2)
        
        # Nostetaan uusi Impact Score taulukon alkupäähän heti nimen perään
        cols = list(summary_df.columns)
        if '5v5 Impact Score' in cols:
            cols.remove('5v5 Impact Score')
            insert_pos = 2 if len(cols) >= 2 else len(cols)
            cols.insert(insert_pos, '5v5 Impact Score')
            summary_df = summary_df[cols]
            
        # Järjestetään oletuksena parhaan Impact Scorena mukaan
        summary_df = summary_df.sort_values(by='5v5 Impact Score', ascending=False).reset_index(drop=True)
        
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No data found in LHF Advanced Stats file.")
