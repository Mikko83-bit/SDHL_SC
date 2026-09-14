import streamlit as st
import pandas as pd

st.set_page_config(page_title="LHF Dam - Scoring Chances Analysis", layout="wide")
st.title("⭐ LHF Dam - Scoring Chances Analysis")

@st.cache_data
def load_data():
    sc_path = "SDHL 2026-2027 scoring chances.xlsx"
    xls_sc = pd.ExcelFile(sc_path)
    df_sc = pd.read_excel(xls_sc, sheet_name="Players")
    df_sc.columns = df_sc.columns.astype(str).str.strip()
    return df_sc

df = load_data()

if not df.empty:
    # --- 0. SUODATIN: Team (Joukkue) ---
    team_col = next((c for c in df.columns if 'team' in c.lower()), None)
    if team_col:
        teams = sorted(df[team_col].dropna().astype(str).unique().tolist())
        selected_teams = st.sidebar.multiselect("Select Team", options=teams, default=teams)
        if selected_teams:
            df = df[df[team_col].astype(str).isin(selected_teams)]

    # --- 1. SUODATIN: Category (esim. OZ, NZ, DZ) ---
    cat_col = next((c for c in df.columns if c.strip().lower() in ['category', 'cat']), None)
    if cat_col:
        categories = sorted(df[cat_col].dropna().astype(str).unique().tolist())
        selected_cats = st.sidebar.multiselect("Select Category", options=categories, default=categories)
        if selected_cats:
            df = df[df[cat_col].astype(str).isin(selected_cats)]

    # --- 2. SUODATIN: Tapahtumat / Sarakkeet Scoring Chances Totalia varten ---
    event_columns = [
        'Goal For', 'Goal For inv', 'Chance For', 'Chance For inv', 
        'PP goal', 'PP goal inv', 'PP chance', 'PP chance inv', 
        'Goal Against', 'Chance Against', 'PP goal ag', 'PP chance ag'
    ]
    available_events = [c for c in event_columns if c in df.columns]
    
    selected_events = st.sidebar.multiselect(
        "Select Metrics for Scoring Chances Total", 
        options=available_events, 
        default=available_events
    )

    st.sidebar.markdown("---")

    # Etsitään numerus- ja pelaajasarakkeet
    num_col = next((c for c in df.columns if 'number' in c.lower() or c.strip() == 'Number'), None)
    player_col = next((c for c in df.columns if 'player' in c.lower() or 'name' in c.lower()), None)
    game_col = next((c for c in df.columns if 'game' in c.lower()), None)

    if player_col:
        all_players = sorted(df[player_col].dropna().unique().tolist())
        selected_players = st.sidebar.multiselect("Select Player", options=all_players, default=all_players)
        if selected_players:
            df = df[df[player_col].isin(selected_players)]

    group_cols = [c for c in [num_col, player_col] if c]
    
    if group_cols and available_events:
        # Summataan kaikki numeriset sarakkeet ryhmittäin
        p_num_cols = [c for c in df.select_dtypes(include=['number']).columns.tolist() if c not in group_cols and c != game_col]
        summary_df = df.groupby(group_cols)[p_num_cols].sum().reset_index()
        
        if game_col:
            games_played = df.groupby(group_cols)[game_col].nunique().reset_index(name='Games Played')
            summary_df = pd.merge(summary_df, games_played, on=group_cols)
        
        # Lasketaan Scoring Chances Total valituista sarakkeista (Plussat miinus Miinukset)
        if selected_events:
            positive_options = [e for e in selected_events if 'against' not in e.lower() and 'ag' not in e.lower()]
            negative_options = [e for e in selected_events if 'against' in e.lower() or 'ag' in e.lower()]
            
            pos_sum = sum(summary_df[e] for e in positive_options if e in summary_df.columns) if positive_options else 0
            neg_sum = sum(summary_df[e] for e in negative_options if e in summary_df.columns) if negative_options else 0
            
            summary_df['Scoring Chances Total'] = pos_sum - neg_sum
        else:
            summary_df['Scoring Chances Total'] = 0

        # Siirretään Scoring Chances Total etualalle jos mahdollista
        cols = list(summary_df.columns)
        if 'Scoring Chances Total' in cols:
            cols.remove('Scoring Chances Total')
            insert_idx = 2 if len(cols) >= 2 else len(cols)
            cols.insert(insert_idx, 'Scoring Chances Total')
            summary_df = summary_df[cols]

        st.subheader("Scoring Chances Summary by Player")
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
    else:
        st.info("Ei löydetty sopivia ryhmittelysarakkeita tai tapahtumia.")
else:
    st.info("Ei dataa ladattavissa.")
