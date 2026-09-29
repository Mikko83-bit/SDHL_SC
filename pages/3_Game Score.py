import streamlit as st
import pandas as pd
import plotly.express as px

# Sivun asetukset
st.set_page_config(page_title="SDHL Game Score -analyysi", page_icon="🏒", layout="wide")

st.title("🏒 SDHL Game Score -analyysityökalu (2026–2027)")
st.write("Tämä sivu lukee Master-taulukkoa, laskee ja visualisoi pelaajien pelikohtaiset *Game Score* -pisteet sekä kausitilastot InStat-tilastojen pohjalta.")

# Tiedoston lataus
EXCEL_FILE = "Sdhl Game score 2026-2027.xlsx"

@st.cache_data
def load_data(file_path):
    try:
        # Luetaan suoraan tiedosto (oletustiedosto / ensimmäinen välilehti)
        df = pd.read_excel(file_path)
        
        # Muutetaan sarakkeiden nimet turvallisesti merkkijonoiksi ja siivotaan välilyönnit
        df.columns = [str(col).strip() for col in df.columns]
        
        # Korjataan Date-sarake pelkiksi päivämääriksi
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
            
        return df
    except Exception as e:
        st.error(f"Virhe tiedoston luvussa: {e}")
        return None

df = load_data(EXCEL_FILE)

if df is None:
    st.error(f"Tiedoston '{EXCEL_FILE}' lukemisessa tapahtui virhe. Varmista, että tiedosto on oikeassa kansiossa.")
else:
    # Apufunktio sarakkeiden turvalliseen hakuun
    def get_col(data, col_name):
        if col_name in data.columns:
            return pd.to_numeric(data[col_name], errors='coerce').fillna(0)
        return 0

    # Tunnistetaan sarakkeet InStat-datasta tarkasti
    goals_col = next((c for c in df.columns if 'goal' in c.lower() and 'shot' not in c.lower() and 'x' not in c.lower()), None)
    
    # Syötöt: Tarkistetaan 'Assists' tai lasketaan First + Second assist yhteen
    assists_col = next((c for c in df.columns if c.lower() == 'assists'), None)
    
    # Laukaukset: Haetaan nimenomaan maalia kohti menneet laukaukset ('Shots on goal')
    shots_col = next((c for c in df.columns if 'shots on goal' in c.lower()), None)
    if not shots_col: # Varasuunnitelma, jos ei löydy tarkalla nimellä
        shots_col = next((c for c in df.columns if 'shot' in c.lower() and 'goal' in c.lower() and 'x' not in c.lower()), None)

    net_xg_col = next((c for c in df.columns if 'net xg' in c.lower()), None)
    fw_col = next((c for c in df.columns if 'faceoffs won' in c.lower()), None)
    fl_col = next((c for c in df.columns if 'faceoffs lost' in c.lower()), None)

    # Lasketaan puhtaat arvot nollakäsittelyllä
    df['Goals_clean'] = get_col(df, goals_col)
    
    if assists_col:
        df['Assists_clean'] = get_col(df, assists_col)
    else:
        first_ast = next((c for c in df.columns if 'first assist' in c.lower()), None)
        second_ast = next((c for c in df.columns if 'second assist' in c.lower()), None)
        val_first = pd.to_numeric(df[first_ast], errors='coerce').fillna(0) if first_ast else 0
        val_second = pd.to_numeric(df[second_ast], errors='coerce').fillna(0) if second_ast else 0
        df['Assists_clean'] = val_first + val_second

    df['Shots_clean'] = get_col(df, shots_col)
    df['NetXG_clean'] = get_col(df, net_xg_col)
    df['FW_clean'] = get_col(df, fw_col)
    df['FL_clean'] = get_col(df, fl_col)

    # Game Score -laskenta
    df['Game_Score'] = (
        (df['Goals_clean'] * 1.0) +
        (df['Assists_clean'] * 0.7) +
        (df['Shots_clean'] * 0.1) +
        (df['NetXG_clean'] * 0.5) +
        ((df['FW_clean'] - df['FL_clean']) * 0.05)
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

    # Välilehdet sovelluksessa
    tab1, tab2, tab3 = st.tabs(["📊 Pelaajaprofiili & Kehitys", "🏆 Kausitilastot & Leaderboard", "📁 Raakadata"])

    with tab1:
        st.subheader("Pelaajan kehityskäyrä kauden aikana")
        
        if player_col:
            pelaajat = sorted(df[player_col].dropna().unique())
            if len(pelaajat) > 0:
                valittu_pelaaja = st.selectbox("Valitse tarkasteltava pelaaja:", pelaajat)
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
                        pelaaja_df, 
                        x='Date', 
                        y='Game_Score', 
                        markers=True,
                        labels={'Date': 'Ottelupäivä', 'Game_Score': 'Game Score'},
                        title=f"Pelaajan {valittu_pelaaja} Game Score otteluhistoria"
                    )
                    fig.update_layout(xaxis_type='category')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Valitulla pelaajalla ei ole tilastomerkintöjä valituilla suodattimilla.")
            else:
                st.warning("Ei löytynyt pelaajia annetuilla suodattimilla.")
        else:
            st.error("Pelaajasaraketta ('Player') ei löytynyt taulukosta.")

    with tab2:
        st.subheader("🏆 Pelaajien Leaderboard (Kausitilastot)")
        st.write("Tässä näkyvät pelaajien yhteenlasketut ja keskimääräiset tilastot valittujen suodattimien (joukkue/vastustaja) ajalta.")

        if player_col:
            agg_dict = {
                'Game_Score': ['count', 'mean', 'sum'],
                'Goals_clean': 'sum',
                'Assists_clean': 'sum',
                'Shots_clean': 'sum',
                'NetXG_clean': 'sum'
            }
            
            if team_col in df.columns:
                leaderboard = df.groupby([player_col, team_col]).agg(agg_dict).reset_index()
                leaderboard.columns = ['Pelaaja', 'Joukkue', 'Pelit', 'GS Keskiarvo', 'GS Yhteensä', 'Maalit', 'Syötöt', 'Laukaukset', 'Net xG']
            else:
                leaderboard = df.groupby([player_col]).agg(agg_dict).reset_index()
                leaderboard.columns = ['Pelaaja', 'Pelit', 'GS Keskiarvo', 'GS Yhteensä', 'Maalit', 'Syötöt', 'Laukaukset', 'Net xG']

            jarjestys_peruste = st.radio(
                "Järjestä taulukko:",
                ["Game Score (Keskiarvo)", "Game Score (Yhteensä)", "Maalit (Yhteensä)"],
                horizontal=True
            )

            sort_col_map = {
                "Game Score (Keskiarvo)": "GS Keskiarvo",
                "Game Score (Yhteensä)": "GS Yhteensä",
                "Maalit (Yhteensä)": "Maalit"
            }
            
            leaderboard = leaderboard.sort_values(by=sort_col_map[jarjestys_peruste], ascending=False)

            leaderboard['GS Keskiarvo'] = leaderboard['GS Keskiarvo'].round(2)
            leaderboard['GS Yhteensä'] = leaderboard['GS Yhteensä'].round(2)
            leaderboard['Net xG'] = leaderboard['Net xG'].round(2)

            st.dataframe(leaderboard, use_container_width=True, hide_index=True)
        else:
            st.error("Pelaajasaraketta ei löytynyt.")

    with tab3:
        st.subheader("Raakadata ja lasketut Game Score -pisteet")
        st.dataframe(df, use_container_width=True)
