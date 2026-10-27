import streamlit as st
import pandas as pd
import plotly.express as px

# Sivun asetukset
st.set_page_config(page_title="Puck Management & Transitions", page_icon="🏒", layout="wide")

st.title("🏒 Puck Management, Transitions & Control")
st.caption("Syväanalytiikka: Riistot, menetykset, sisäänviennit, ulostulot, laukauksen jälkeiset haut ja kiekonhallinta.")

# Sama Excel-tiedosto
EXCEL_FILE = "Sdhl Game score 2026-2027.xlsx"

@st.cache_data
def load_puck_data(file_path):
    try:
        df = pd.read_excel(file_path, sheet_name='Puck management')
        df.columns = [str(col).strip() for col in df.columns]
        return df
    except Exception as e:
        try:
            df = pd.read_excel(f"../{file_path}", sheet_name='Puck management')
            df.columns = [str(col).strip() for col in df.columns]
            return df
        except Exception as e2:
            st.error(f"Virhe ladattaessa Puck management -välilehteä: {e2}")
            return None

df_puck = load_puck_data(EXCEL_FILE)

if df_puck is not None:
    def get_col(data, col_name):
        if col_name and col_name in data.columns:
            s = data[col_name].replace(['-', '—', ''], 0)
            return pd.to_numeric(s, errors='coerce').fillna(0)
        return pd.Series(0, index=data.index)

    # Tunnistetaan sarakkeet turvallisesti
    player_col = next((c for c in df_puck.columns if 'player' in c.lower()), 'Player')
    team_col = next((c for c in df_puck.columns if 'team' in c.lower()), 'Team')
    pos_col = next((c for c in df_puck.columns if 'position' in c.lower()), 'Position')

    # Siivotaan perustiedot
    df_puck['Player_clean'] = df_puck[player_col]
    df_puck['Team_clean'] = df_puck[team_col] if team_col in df_puck.columns else 'Unknown'
    df_puck['Pos_clean'] = df_puck[pos_col].astype(str).str.upper().str.strip() if pos_col in df_puck.columns else 'F'

    # --- SIVUPALKIN SUODATTIMET ---
    st.sidebar.header("🔍 Puck Management Filters")
    
    if team_col in df_puck.columns:
        all_teams = sorted(df_puck['Team_clean'].dropna().unique())
        selected_teams = st.sidebar.multiselect("Valitse joukkue(et):", all_teams, default=all_teams)
        df_filtered = df_puck[df_puck['Team_clean'].isin(selected_teams)].copy()
    else:
        df_filtered = df_puck.copy()

    selected_positions = st.sidebar.multiselect("Valitse pelipaikka:", ['F', 'D'], default=['F', 'D'])
    if pos_col in df_puck.columns:
        df_filtered = df_filtered[df_filtered['Pos_clean'].isin(selected_positions)]

    min_gp = st.sidebar.slider("Min. ottelumäärä (Games played):", 1, 15, 1, 1)
    gp_col = next((c for c in df_puck.columns if 'games' in c.lower() or c.lower() == 'gp'), None)
    if gp_col:
        df_filtered['GP_num'] = get_col(df_filtered, gp_col)
        df_filtered = df_filtered[df_filtered['GP_num'] >= min_gp]

    # --- SIVUN ALAVÄLILEHDET ---
    sub_tab1, sub_tab2 = st.tabs(["👥 Pelaajataulukko & Kaaviot", "🛡️ Joukkuekohtainen Yhteenveto"])

    with sub_tab1:
        st.subheader("📋 Pelaajien syväanalytiikan kokonaistaulukko")
        st.dataframe(df_filtered, use_container_width=True, hide_index=True)

        st.markdown("---")

        col_l, col_r = st.columns(2)

        with col_l:
            st.markdown("### 📊 Top 10: Riistot vs. Menetykset")
            takeaway_col = next((c for c in df_puck.columns if c.lower() == 'takeaways'), None)
            loss_col = next((c for c in df_puck.columns if c.lower() == 'puck losses'), None)

            if takeaway_col and loss_col:
                df_filtered['Takeaways_num'] = get_col(df_filtered, takeaway_col)
                df_filtered['Losses_num'] = get_col(df_filtered, loss_col)
                
                top_tka = df_filtered.sort_values(by='Takeaways_num', ascending=False).head(10)
                
                fig_tka = px.bar(
                    top_tka, x='Player_clean', y=['Takeaways_num', 'Losses_num'],
                    barmode='group',
                    title="Riistot ja menetykset (Top 10 riistäjät)",
                    labels={'value': 'Määrä', 'variable': 'Metriikka', 'Player_clean': 'Pelaaja'}
                )
                fig_tka.update_layout(xaxis_tickangle=-45, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_tka, use_container_width=True)

        with col_r:
            st.markdown("### 🎯 Top 10: Laukauksen jälkeiset haut (Puck retrievals after shots)")
            retrieval_col = next((c for c in df_puck.columns if 'retrievals after shots' in c.lower()), None)

            if retrieval_col:
                df_filtered['Retrievals_num'] = get_col(df_filtered, retrieval_col)
                top_ret = df_filtered.sort_values(by='Retrievals_num', ascending=False).head(10)

                fig_ret = px.bar(
                    top_ret, x='Player_clean', y='Retrievals_num',
                    title="Eniten laukauksen jälkeisiä irtokiekon hakuja",
                    labels={'Retrievals_num': 'Määrä', 'Player_clean': 'Pelaaja'},
                    color='Retrievals_num', color_continuous_scale='Blues'
                )
                fig_ret.update_layout(xaxis_tickangle=-45, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', showlegend=False)
                st.plotly_chart(fig_ret, use_container_width=True)
            else:
                st.info("Saraketta 'Puck retrievals after shots' ei löytynyt automaattisesti.")

    with sub_tab2:
        st.subheader("🛡️ Joukkuekohtainen yhteenveto")
        st.caption("Joukkueiden yhteenlasketut syväanalytiikan tilastot valittujen suodattimien mukaan.")

        if team_col in df_filtered.columns:
            numeric_cols = [c for c in df_filtered.columns if c not in [player_col, team_col, pos_col, 'Player_clean', 'Team_clean', 'Pos_clean']]
            
            for col in numeric_cols:
                df_filtered[col] = get_col(df_filtered, col)

            team_summary = df_filtered.groupby('Team_clean')[numeric_cols].sum().reset_index()
            team_summary = team_summary.rename(columns={'Team_clean': 'Team'})

            st.dataframe(team_summary, use_container_width=True, hide_index=True)
        else:
            st.warning("Joukesaraketta ei löytynyt.")
else:
    st.warning("Puck management -välilehden lataaminen epäonnistui Excel-tiedostosta.")
