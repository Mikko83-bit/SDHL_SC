import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Sivun asetukset
st.set_page_config(page_title="SDHL Game Score -analyysi", page_icon="🏒", layout="wide")

st.title("🏒 SDHL Game Score -analyysityökalu (2026–2027)")
st.write("Tämä sivu laskee pelaajien pelikohtaiset *Game Score* -pisteet xG-pohjaisella kaavalla suoraan raakadatasta.")

# Tiedoston lataus (huomioi tarvittaessa polku, jos tiedosto on pääkansiossa '../')
EXCEL_FILE = "Sdhl Game score 2026-2027.xlsx"

@st.cache_data
def load_data(file_path):
    try:
        df = pd.read_excel(file_path)
        df.columns = [str(col).strip() for col in df.columns]
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
        return df
    except Exception as e:
        # Kokeillaan tarvittaessa hakea kansiota ylempää, jos sivu on pages-kansiossa
        try:
            df = pd.read_excel(f"../{file_path}")
            df.columns = [str(col).strip() for col in df.columns]
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
            return df
        except Exception as e2:
            st.error(f"Virhe tiedoston luvussa: {e2}")
            return None

df = load_data(EXCEL_FILE)

if df is None:
    st.error(f"Tiedoston '{EXCEL_FILE}' lukemisessa tapahtui virhe. Varmista, että tiedosto on oikeassa kansiossa.")
else:
    # Apufunktio sarakkeiden turvalliseen hakuun (nollakäsittelyllä)
    def get_col(data, col_name):
        if col_name in data.columns:
            return pd.to_numeric(data[col_name], errors='coerce').fillna(0)
        return 0

    # Etsitään sarakkeet tarkkojen nimien perusteella
    col_goals = next((c for c in df.columns if c.lower() == 'goals'), None)
    col_a1 = next((c for c in df.columns if c.lower() == 'first assist'), None)
    col_a2 = next((c for c in df.columns if c.lower() == 'second assist'), None)
    col_sog = next((c for c in df.columns if c.lower() == 'shots on goal'), None)
    col_blk = next((c for c in df.columns if c.lower() == 'blocked shots'), None)
    col_pd = next((c for c in df.columns if c.lower() == 'penalties drawn'), None)
    col_pt = next((c for c in df.columns if c.lower() == 'penalty time'), None)
    col_fow = next((c for c in df.columns if c.lower() == 'faceoffs won'), None)
    col_fol = next((c for c in df.columns if c.lower() == 'faceoffs lost'), None)
    
    col_xg_on = next((c for c in df.columns if c.lower() == 'xgs with a player on' or c.lower() == 'xg with a player on'), None)
    col_opp_xg_on = next((c for c in df.columns if 'opponent' in c.lower() and 'xg' in c.lower()), None)
    
    col_gf = next((c for c in df.columns if c.lower() == 'plus'), None)
    col_ga = next((c for c in df.columns if c.lower() == 'minus'), None)

    # Muutetaan puhtaiksi numeerisiksi sarjoiksi
    g = get_col(df, col_goals)
    a1 = get_col(df, col_a1)
    a2 = get_col(df, col_a2)
    sog = get_col(df, col_sog)
    blk = get_col(df, col_blk)
    pd_val = get_col(df, col_pd)
    pt_val = get_col(df, col_pt)
    fow = get_col(df, col_fow)
    fol = get_col(df, col_fol)
    xg_for = get_col(df, col_xg_on)
    xg_against = get_col(df, col_opp_xg_on)
    gf = get_col(df, col_gf)
    ga = get_col(df, col_ga)

    # Tallennetaan siivotut arvot taulukkoon
    df['Goals_clean'] = g
    df['Assists_clean'] = a1 + a2
    df['Shots_clean'] = sog
    df['Block_clean'] = blk

    # Game Score -kaava
    df['Game_Score'] = (
        (0.75 * g) + 
        (0.7 * a1) + 
        (0.55 * a2) + 
        (0.075 * sog) + 
        (0.05 * blk) + 
        (0.15 * pd_val) - 
        (0.15 * pt_val) + 
        (0.01 * fow) - 
        (0.01 * fol) + 
        (0.05 * xg_for) - 
        (0.05 * xg_against) + 
        (0.15 * gf) - 
        (0.15 * ga)
    )

    player_col = next((c for c in df.columns if 'player' in c.lower()), None)
    team_col = next((c for c in df.columns if c.lower() == 'team'), None)
    opponent_col = next((c for c in df.columns if 'opponent' in c.lower()), None)

    # --- SIVUPALKKI: SUODATTIMET ---
    st.sidebar.header("🔍 Suodattimet")
    
    if team_col:
        kaikki_tiimit = sorted(df[team_col].dropna().unique())
        valitut_tiimit = st.sidebar.multiselect("Valitse oma joukkue:", kaikki_tiimit, default=kaikki_tiimit)
        if valitut_tiimit:
            df = df[df[team_col].isin(valitut_tiimit)]

    if opponent_col:
        kaikki_vastustajat = sorted(df[opponent_col].dropna().unique())
        valitut_vastustajat = st.sidebar.multiselect("Valitse vastustaja(t):", kaikki_vastustajat, default=kaikki_vastustajat)
        if valitut_vastustajat:
            df = df[df[opponent_col].isin(valitut_vastustajat)]

    # Luodaan välilehdet turvallisesti kerralla
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Pelaajaprofiili & Kehitys", 
        "🏆 Kausitilastot & Leaderboard", 
        "🕸️ Pelaajavertailu (Tutka)", 
        "📁 Raakadata"
    ])

    with tab1:
        st.subheader("Pelaajan kehityskäyrä kauden aikana")
        if player_col:
            pelaajat = sorted(df[player_col].dropna().unique())
            if len(pelaajat) > 0:
                valittu_pelaaja = st.selectbox("Valitse tarkasteltava pelaaja:", pelaajat, key='tab1_player')
                pelaaja_df = df[df[player_col] == valittu_pelaaja].sort_values(by='Date')

                if not pelaaja_df.empty:
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Pelatut ottelut", len(pelaaja_df))
                    with col2:
                        st.metric("Keskiarvo Game Score", round(pelaaja_df['Game_Score'].mean(), 2))
                    with col3:
                        st.metric("Kokonaismaalit", int(pelaaja_df['Goals_clean'].sum()))
                    with col4:
                        st.metric("Kokonaisyvätöt", int(pelaaja_df['Assists_clean'].sum()))

                    fig = px.line(
                        pelaaja_df, x='Date', y='Game_Score', markers=True,
                        labels={'Date': 'Ottelupäivä', 'Game_Score': 'Game Score'},
                        title=f"Pelaajan {valittu_pelaaja} Game Score otteluhistoria"
                    )
                    fig.update_layout(xaxis_type='category')
                    st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("🏆 Pelaajien Leaderboard (Kausitilastot)")
        if player_col:
            agg_dict = {
                'Game_Score': ['count', 'mean', 'sum'],
                'Goals_clean': 'sum',
                'Assists_clean': 'sum',
                'Shots_clean': 'sum'
            }
            if team_col in df.columns:
                leaderboard = df.groupby([player_col, team_col]).agg(agg_dict).reset_index()
                leaderboard.columns = ['Pelaaja', 'Joukkue', 'Pelit', 'GS Keskiarvo', 'GS Yhteensä', 'Maalit', 'Syötöt', 'Laukaukset']
            else:
                leaderboard = df.groupby([player_col]).agg(agg_dict).reset_index()
                leaderboard.columns = ['Pelaaja', 'Pelit', 'GS Keskiarvo', 'GS Yhteensä', 'Maalit', 'Syötöt', 'Laukaukset']

            leaderboard['GS Keskiarvo'] = leaderboard['GS Keskiarvo'].round(2)
            leaderboard['GS Yhteensä'] = leaderboard['GS Yhteensä'].round(2)

            st.dataframe(leaderboard.sort_values(by="GS Keskiarvo", ascending=False), use_container_width=True, hide_index=True)

    with tab3:
        st.subheader("🕸️ Pelaajan Game Score -komponentit vs Joukkue & SDHL")
        
        if player_col:
            pelaajat = sorted(df[player_col].dropna().unique())
            valittu_pelaaja_tutka = st.selectbox("Valitse pelaaja tutkavertailuun:", pelaajat, key='radar_player')
            
            def laske_komponentit(subset):
                g_sub = get_col(subset, col_goals)
                a1_sub = get_col(subset, col_a1)
                a2_sub = get_col(subset, col_a2)
                sog_sub = get_col(subset, col_sog)
                blk_sub = get_col(subset, col_blk)
                
                return [
                    subset['Game_Score'].mean(),
                    (0.75 * g_sub + 0.7 * a1_sub + 0.55 * a2_sub).mean(),
                    (0.075 * sog_sub).mean(),
                    (0.05 * blk_sub).mean(),
                    (0.05 * get_col(subset, col_xg_on)).mean()
                ]

            labels_list = ['Game Score (Keskiarvo)', 'Tehopisteet (GS)', 'Laukaukset (GS)', 'Blokit (GS)', 'xG-vaikutus (GS)']

            pelaaja_all = df[df[player_col] == valittu_pelaaja_tutka]
            pelaaja_means = laske_komponentit(pelaaja_all)

            if team_col and not pelaaja_all.empty:
                pelaajan_tiimi = pelaaja_all[team_col].iloc[0]
                tiimi_all = df[df[team_col] == pelaajan_tiimi]
                tiimi_means = laske_komponentit(tiimi_all)
                tiimi_label = f"Joukkueen ({pelaajan_tiimi}) keskiarvo"
            else:
                tiimi_means = [0] * len(labels_list)
                tiimi_label = "Joukkueen keskiarvo"

            sdhl_means = laske_komponentit(df)

            fig_radar = go.Figure()

            fig_radar.add_trace(go.Scatterpolar(
                r=pelaaja_means + [pelaaja_means[0]],
                theta=labels_list + [labels_list[0]],
                fill='toself',
                name=valittu_pelaaja_tutka,
                line_color='cyan'
            ))

            if team_col:
                fig_radar.add_trace(go.Scatterpolar(
                    r=tiimi_means + [tiimi_means[0]],
                    theta=labels_list + [labels_list[0]],
                    fill='toself',
                    name=tiimi_label,
                    line_color='orange'
                ))

            fig_radar.add_trace(go.Scatterpolar(
                r=sdhl_means + [sdhl_means[0]],
                theta=labels_list + [labels_list[0]],
                fill='toself',
                name='SDHL Keskiarvo',
                line_color='gray',
                opacity=0.5
            ))

            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True)),
                title=f"Game Score -profiili: {valittu_pelaaja_tutka} vs Joukkue & SDHL",
                showlegend=True
            )

            st.plotly_chart(fig_radar, use_container_width=True)

    with tab4:
        st.subheader("Raakadata ja lasketut Game Score -pisteet")
        st.dataframe(df, use_container_width=True)
