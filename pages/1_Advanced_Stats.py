import streamlit as st
import pandas as pd
import plotly.express as px

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
    
    # 1. Scoring Chances Total laskenta pelinumeron mukaan (korjattu tuplalisäysvirhe)
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

    # Sivupalkin suodattimet
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
        
        # Tunnistetaan sarakkeet kaavaa varten
        net_xg_col = next((c for c in summary_df.columns if 'net xg' in c.lower() or ('xg' in c.lower() and 'opp' in c.lower())), None)
        corsi_pct_col = next((c for c in summary_df.columns if 'corsi for, %' in c.lower()), None)
        battles_col = next((c for c in summary_df.columns if 'puck battles won' in c.lower()), None)
        
        # Lasketaan komponentit erikseen erittelyä varten
        summary_df['Comp_NetxG'] = summary_df[net_xg_col] * 8 if net_xg_col else 0
        summary_df['Comp_Corsi'] = (summary_df[corsi_pct_col] - 50) * 0.15 if corsi_pct_col else 0
        summary_df['Comp_Battles'] = summary_df[battles_col] * 0.05 if battles_col else 0
        summary_df['Comp_SC'] = summary_df['Scoring Chances Total'] * 0.5 if 'Scoring Chances Total' in summary_df.columns else 0
        
        summary_df['5v5 Impact Score'] = round(
            summary_df['Comp_NetxG'] + summary_df['Comp_Corsi'] + summary_df['Comp_Battles'] + summary_df['Comp_SC'], 2
        )
        
        summary_df = summary_df.sort_values(by='5v5 Impact Score', ascending=False).reset_index(drop=True)

        # Luodaan välilehdet sivulle
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
            st.subheader("Mistä pelaajien 5v5 Impact Score koostuu?")
            st.markdown("""
            Kaava painottaa seuraavia osa-alueita:
            * **Net xG × 8** (Odotettujen maalien erotus jäällä)
            * **Scoring Chances Total × 0.5** (Maalipaikkojen nettotulos)
            * **(Corsi% - 50) × 0.15** (Kiekonhallinnan suhde)
            * **Voitetut kaksinkamppailut × 0.05** (Fyysinen panos)
            """)

            breakdown_player = st.selectbox("Valitse pelaaja tarkastellaksesi kaavan avausta:", options=summary_df[player_name_col].tolist())
            
            p_data = summary_df[summary_df[player_name_col] == breakdown_player].iloc[0]
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Yhteensä 5v5 Impact Score", p_data['5v5 Impact Score'])
                st.markdown(f"**Pelinumero:** {p_data[shirt_col] if shirt_col else '-'}")
                st.markdown(f"**Pelatut pelit:** {p_data.get('Games Played', '-')}")
            
            with col_b:
                breakdown_chart_data = pd.DataFrame({
                    "Komponentti": ["Net xG (x8)", "Scoring Chances (x0.5)", "Corsi % osuus", "Kaksinkamppailut"],
                    "Pisteet": [p_data['Comp_NetxG'], p_data['Comp_SC'], p_data['Comp_Corsi'], p_data['Comp_Battles']]
                })
                fig = px.bar(breakdown_chart_data, x="Komponentti", y="Pisteet", title=f"Pistekertymän osuudet: {breakdown_player}", color="Pisteet", color_continuous_scale="RdBu")
                st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("Ei löydetty sopivia sarakkeita laskentaan.")
else:
    st.info("Ei dataa ladattavissa.")
