import streamlit as st
import pandas as pd

st.set_page_config(page_title="LHF Advanced Stats", layout="wide")
st.title("⭐ LHF Dam - Advanced Player Statistics")

@st.cache_data
def load_advanced_data():
    adv_path = "LHF Dam season 2026-2027.xlsx"
    xls_adv = pd.ExcelFile(adv_path)
    df = pd.read_excel(xls_adv, sheet_name=xls_adv.sheet_names[0])
    df.columns = df.columns.astype(str).str.strip()
    return df

df = load_advanced_data()

st.subheader("All Player Metrics (Corsi, Fenwick, xG, Faceoffs, etc.)")
if not df.empty:
    shirt_col = next((c for c in df.columns if 'shirt' in c.lower() or 'number' in c.lower()), None)
    player_name_col = next((c for c in df.columns if 'player' in c.lower() and 'shirt' not in c.lower()), None)
    
    # Suodatin pelaajalle sivupalkkiin
    if player_name_col:
        all_players = sorted(df[player_name_col].dropna().unique().tolist())
        selected_players = st.sidebar.multiselect("Select Player", options=all_players, default=all_players)
        if selected_players:
            df = df[df[player_name_col].isin(selected_players)]
            
    group_cols = [c for c in [shirt_col, player_name_col] if c]
    
    # Otetaan numeeriset sarakkeet, mutta suljetaan ryhmittelysarakkeet pois laskennasta
    num_cols = [c for c in df.select_dtypes(include=['number']).columns.tolist() if c not in group_cols]
    
    if group_cols and num_cols:
        summary_df = df.groupby(group_cols)[num_cols].sum().reset_index()
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No data found in LHF Advanced Stats file.")
