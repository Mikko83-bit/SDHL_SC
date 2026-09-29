import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Sivun asetukset
st.set_page_config(page_title="SDHL Game Score -analyysi", page_icon="🏒", layout="wide")

st.title("🏒 SDHL Game Score -analyysityökalu (2026–2027)")
st.write("Tämä sivu laskee pelaajien pelikohtaiset *Game Score* -pisteet xG-pohjaisella kaavalla suoraan raakadatasta.")

# Tiedoston lataus
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

    # Apufunktio peliajan (MM:SS tai pelkkä luku) muuntamiseksi desimaaliminuuteiksi
    def parse_toi(val):
        if pd.isna(val):
            return 0.0
        val_str = str(val).strip()
        if ':' in val_str:
            try:
                parts = val_str.split(':')
                minutes = float(parts[0])
                seconds = float(parts[1])
                return minutes + (seconds / 60.0)
            except:
                return 0.0
        else:
            try:
                return float(val_str)
            except:
                return 0.0

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
    
    col_xg_on = next((c for c in df.columns if c.lower() in ['xgs with a player on', 'xg with a player on']), None)
    col_opp_xg_on = next((c for c in df.columns if 'opponent' in c.lower() and 'xg' in c.lower()), None)
    
    col_gf = next((c for c in df.columns if c.lower() == 'plus'), None)
    col_ga = next((c for c in df.columns if c.lower() == 'minus'), None)

    # Etsitään peliaika- ja pelipaikkasarake
    col_toi = next((c for c in df.columns if any(k in c.lower() for k in ['time on ice', 'toi', 'minutes', 'min'])), None)
    col_pos = next((c for c in df.columns if c.lower() == 'position'), None)

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
    
    if col_toi:
        df['TOI_clean'] = df[col_toi].apply(parse_toi)
    else:
        df['TOI_clean'] = 0.0

    if col_pos:
        df['Pos_clean'] = df[col_pos].astype(str).str.upper().str.strip()
    else:
        df['Pos_clean'] = 'UNKNOWN'

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
    
    # 1. Joukkueen valinta
    if team_col:
        kaikki_tiimit = sorted(df[team_col].dropna().unique())
        valitut_tiimit = st.sidebar.multiselect("Valitse oma joukkue:", kaikki_tiimit, default=kaikki_tiimit)
        if valitut_tiimit:
            df_filtered = df[df[team_col].isin(valitut_tiimit)]
        else:
            df_filtered = df.copy()
    else:
        df_filtered = df.copy()

    # 2. Vastustajan valinta
    if opponent_col:
        kaikki_vastustajat = sorted(df[opponent_col].dropna().unique())
        valitut_vastustajat = st.sidebar.multiselect("Valitse vastustaja(t):", kaikki_vastustajat, default=kaikki_vastustajat)
        if valitut_vastustajat:
            df_filtered = df_filtered[df_filtered[opponent_col].isin(valitut_vastustajat)]

    # 3. Pelipaikan valinta (F / D)
    st.sidebar.subheader("🏒 Pelipaikka")
    valitut_pelipaikat = st.sidebar.multiselect("Valitse pelipaikka:", ['F', 'D'], default=['F', 'D'])
    if col_pos and valitut_pelipaikat:
        df_filtered = df_filtered[df_filtered['Pos_clean'].isin(valitut_pelipaikat)]

    # 4. Peliaikasuodatin vertailupohjalle
    st.sidebar.subheader("⚖️ Keskiarvojen vertailupohja")
    min_toi_filter = 0.0
    if col_toi:
        min_toi_filter = st.sidebar.slider("Min. keskimääräinen peliaika (min/ottelu):", 0.0, 30.0, 0.0, 0.5)
    else:
        st.sidebar.info("Peliaikasaraketta (Time on ice) ei löytynyt automaattisesti.")

    # Rajataan verrokkijoukko keskiarvoja varten
    if player_col and col_toi:
        pelaaja_toi_keskiarvot = df_filtered.groupby(player_col)['TOI_clean'].mean()
        vakituiset_pelaajat = pelaaja_toi_keskiarvot[pelaaja_toi_keskiarvot >= min_toi_filter].index
        df_vertailu = df_filtered[df_filtered[player_col].isin(vakituiset_pelaajat)]
    else:
        df_vertailu = df_filtered

    # Luodaan välilehdet kerralla
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Pelaajaprofiili & Kehitys", 
        "🏆 Kausitilastot & Leaderboard", 
        "📈 Ottelukohtaiset pisteet", 
        "📁 Raakadata"
    ])

    with tab1:
        st.subheader("Pelaajan kehityskäyrä kauden aikana")
        if player_col:
            pelaajat = sorted(df_filtered[player_col].dropna().unique())
            if len(pelaajat) > 0:
                valittu_pelaaja = st.selectbox("Valitse tarkasteltava pelaaja:", pelaajat, key='tab1_player')
                pelaaja_df = df_filtered[df_filtered[player_col] == valittu_pelaaja].sort_values(by='Date')

                if not pelaaja_df.empty:
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Pelatut ottelut", len(pelaaja_df))
                    with col2:
                        st.metric("Keskiarvo Game Score", round(pelaaja_df['Game_Score'].mean(), 2))
                    with col3:
                        st.metric("Kokonaismaalit", int(pelaaja_df['Goals_clean'].sum()))
                    with col4:
                        st.metric("Kokonaisyötöt", int(pelaaja_df['Assists_clean'].sum()))

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
            if col_toi:
                agg_dict['TOI_clean'] = 'mean'
            if col_pos:
                agg_dict['Pos_clean'] = 'first'

            group_cols = [player_col]
            if team_col in df_filtered.columns:
                group_cols.append(team_col)
            if col_pos:
                group_cols.append('Pos_clean')

            leaderboard = df_filtered.groupby(group_cols).agg(agg_dict).reset_index()
            
            # Rakennetaan sarakkeet dynaamisesti sen mukaan mitä ryhmittelysarakkeitä ja aggregaatteja tuli mukaan
            cols = ['Pelaaja']
            if team_col in df_filtered.columns:
                cols.append('Joukkue')
            if col_pos:
                cols.append('Pelipaikka')
            
            cols.extend(['Pelit', 'GS Keskiarvo', 'GS Yhteensä', 'Maalit', 'Syötöt', 'Laukaukset'])
            if col_toi:
                cols.append('Keskim. Peliaika (min)')

            # Varmistetaan että sarakkeiden määrä varmasti täsmää
            if len(leaderboard.columns) == len(cols):
                leaderboard.columns = cols

            # Suodatetaan peliajan mukaan jos sarake löytyy
            if col_toi and min_toi_filter > 0 and 'Keskim. Peliaika (min)' in leaderboard.columns:
                leaderboard = leaderboard[leaderboard['Keskim. Peliaika (min)'] >= min_toi_filter]
                leaderboard['Keskim. Peliaika (min)'] = leaderboard['Keskim. Peliaika (min)'].round(2)

            if 'GS Keskiarvo' in leaderboard.columns:
                leaderboard['GS Keskiarvo'] = leaderboard['GS Keskiarvo'].round(2)
            if 'GS Yhteensä' in leaderboard.columns:
                leaderboard['GS Yhteensä'] = leaderboard['GS Yhteensä'].round(2)

            st.dataframe(leaderboard.sort_values(by="GS Keskiarvo", ascending=False), use_container_width=True, hide_index=True)

    with tab3:
        st.subheader("📊 Pelaajan ottelukohtainen Game Score vs Keskiarvot")
        
        if player_col:
            pelaajat = sorted(df_filtered[player_col].dropna().unique())
            valittu_pelaaja_pylvas = st.selectbox("Valitse pelaaja tarkasteluun:", pelaajat, key='bar_player')
            
            pelaaja_df = df_filtered[df_filtered[player_col] == valittu_pelaaja_pylvas].sort_values(by='Date')
            
            if not pelaaja_df.empty:
                pelaajan_oma_ka = pelaaja_df['Game_Score'].mean()
                
                # Lasketaan keskiarvot rajatusta verrokkijoukosta
                sdhl_ka = df_vertailu['Game_Score'].mean()
                
                if team_col:
                    pelaajan_tiimi = pelaaja_df[team_col].iloc[0]
                    tiimi_df = df_vertailu[df_vertailu[team_col] == pelaajan_tiimi]
                    tiimi_ka = tiimi_df['Game_Score'].mean() if not tiimi_df.empty else 0
                    tiimi_nimi = pelaajan_tiimi
                else:
                    tiimi_ka = None
                    tiimi_nimi = "Joukkue"

                fig_bar = px.bar(
                    pelaaja_df, 
                    x='Date', 
                    y='Game_Score',
                    title=f"Pelaajan {valittu_pelaaja_pylvas} ottelukohtainen Game Score",
                    labels={'Date': 'Ottelupäivä', 'Game_Score': 'Game Score'},
                    text_auto='.2f'
                )
                fig_bar.update_traces(marker_color='#00b4d8')

                # 1. SDHL-keskiarvo poikkiviivana (Harmaa)
                fig_bar.add_hline(
                    y=sdhl_ka, 
                    line_dash="dash", 
                    line_color="#adb5bd", 
                    annotation_text=f"SDHL Keskiarvo ({sdhl_ka:.2f})", 
                    annotation_position="bottom right",
                    annotation_font_color="#adb5bd"
                )

                # 2. Oman joukkueen keskiarvo poikkiviivana (Oranssi)
                if team_col and not pd.isna(tiimi_ka):
                    fig_bar.add_hline(
                        y=tiimi_ka, 
                        line_dash="dot", 
                        line_color="#ffb703", 
                        annotation_text=f"{tiimi_nimi} Keskiarvo ({tiimi_ka:.2f})", 
                        annotation_position="top right",
                        annotation_font_color="#ffb703"
                    )

                # 3. Pelaajan oma keskiarvo poikkiviivana (Turkoosi)
                fig_bar.add_hline(
                    y=pelaajan_oma_ka, 
                    line_dash="solid", 
                    line_color="#2ec4b6", 
                    annotation_text=f"Pelaajan keskiarvo ({pelaajan_oma_ka:.2f})", 
                    annotation_position="bottom left",
                    annotation_font_color="#2ec4b6"
                )

                fig_bar.update_layout(
                    xaxis_type='category',
                    yaxis_title="Game Score",
                    xaxis_title="Ottelupäivä",
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)'
                )

                st.plotly_chart(fig_bar, use_container_width=True)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Pelaajan keskiarvo", f"{pelaajan_oma_ka:.2f}")
                with col2:
                    st.metric("SDHL keskiarvo (rajattu)", f"{sdhl_ka:.2f}")
                with col3:
                    if team_col:
                        st.metric(f"{tiimi_nimi} keskiarvo (rajattu)", f"{tiimi_ka:.2f}")

    with tab4:
        st.subheader("Raakadata ja lasketut Game Score -pisteet")
        st.dataframe(df_filtered, use_container_width=True)
