import streamlit as st
import pandas as pd
import plotly.express as px

# Sivun asetukset
st.set_page_config(page_title="SDHL Game Score -analyysi", page_icon="🏒", layout="wide")

st.title("🏒 SDHL Game Score -analyysityökalu (2026–2027)")
st.write("Tämä sivu lukee automaattisesti kaikki joukkueiden välilehdet[cite: 4], laskee ja visualisoi pelaajien pelikohtaiset *Game Score* -pisteet InStat-tilastojen pohjalta[cite: 1, 2].")

# Tiedoston lataus
EXCEL_FILE = "Sdhl Game score 2026-2027.xlsx"

@st.cache_data
def load_data(file_path):
    try:
        # Luetaan KAIKKI välilehdet sanakirjana (sheet_name=None), jotta saadaan kaikkien joukkueiden data mukaan
        excel_data = pd.read_excel(file_path, sheet_name=None)
        
        df_list = []
        for sheet_name, sheet_df in excel_data.items():
            # Siivotaan sarakkeiden nimet
            sheet_df.columns = sheet_df.columns.str.strip()
            # Tallennetaan halutessaan tiedoksi myös alkuperäinen välilehti/joukkue
            sheet_df['Team_Sheet'] = sheet_name
            df_list.append(sheet_df)
            
        # Yhdistetään kaikkien välilehtien rivit yhdeksi DataFrameksi
        df = pd.concat(df_list, ignore_index=True)
        
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

    # Tunnistetaan sarakkeet InStat-datasta
    goals_col = next((c for c in df.columns if 'goal' in c.lower() and 'shot' not in c.lower() and 'x' not in c.lower()), None)
    assists_col = next((c for c in df.columns if 'assist' in c.lower() and 'first' not in c.lower()), None)
    shots_col = next((c for c in df.columns if 'shots on goal' in c.lower() or c.lower() == 'shots'), None)
    net_xg_col = next((c for c in df.columns if 'net xg' in c.lower()), None)
    fw_col = next((c for c in df.columns if 'faceoffs won' in c.lower()), None)
    fl_col = next((c for c in df.columns if 'faceoffs lost' in c.lower()), None)

    # Lasketaan puhtaat arvot nollakäsittelyllä
    df['Goals_clean'] = get_col(df, goals_col)
    df['Assists_clean'] = get_col(df, assists_clean if 'assists_clean' in locals() else assists_col)
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

    player_col = next((c for c in df.columns if 'player' in c.lower()), df.columns[5] if len(df.columns) > 5 else df.columns[0])
    opponent_col = next((c for c in df.columns if 'opponent' in c.lower()), None)

    # --- SIVUPALKKI: SUODATTIMET ---
    st.sidebar.header("🔍 Suodattimet")
    
    # Valitse joukkue (Excelin välilehden mukaan)
    if 'Team_Sheet' in df.columns:
        kaikki_tiimit = sorted(df['Team_Sheet'].dropna().unique())
        valitut_tiimit = st.sidebar.multiselect("Valitse joukkue (Välilehti):", kaikki_tiimit, default=kaikki_tiimit)
        if valitut_tiimit:
            df = df[df['Team_Sheet'].isin(valitut_tiimit)]

    # Vastustaja-suodatin
    if opponent_col:
        kaikki_vastustajat = sorted(df[opponent_col].dropna().unique())
        valitut_vastustajat = st.sidebar.multiselect("Valitse vastustaja(t):", kaikki_vastustajat, default=kaikki_vastustajat)
        if valitut_vastustajat:
            df = df[df[opponent_col].isin(valitut_vastustajat)]

    # Välilehdet sovelluksessa[cite: 3]
    tab1, tab2, tab3 = st.tabs(["📊 Pelaajaprofiili & Kehitys[cite: 3]", "🏆 Ottelun Leaderboard[cite: 3]", "📁 Raakadata[cite: 3]"])

    with tab1:
        st.subheader("Pelaajan kehityskäyrä kauden aikana[cite: 3]")
        
        pelaajat = sorted(df[player_col].dropna().unique())
        if len(pelaajat) > 0:
            valittu_pelaaja = st.selectbox("Valitse tarkasteltava pelaaja:", pelaajat)

            # Suodatetaan pelaajan data
            pelaaja_df = df[df[player_col] == valittu_pelaaja].sort_values(by='Date')

            if not pelaaja_df.empty:
                # Yläreunan metriikkakortit
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Pelatut ottelut", len(pelaaja_df))
                with col2:
                    st.metric("Keskiarvo Game Score", round(pelaaja_df['Game_Score'].mean(), 2))
                with col3:
                    st.metric("Kokonaismaalit", int(pelaaja_df['Goals_clean'].sum()))
                with col4:
                    st.metric("Kokonaisyvätöt", int(pelaaja_df['Assists_clean'].sum()))

                # Viivakaavio
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

    with tab2:
        st.subheader("Ottelukohtainen Leaderboard[cite: 3]")
        
        date_col = 'Date' if 'Date' in df.columns else None
        
        if date_col and opponent_col:
            df['Ottelu_info'] = df[date_col].astype(str) + " vs " + df[opponent_col].astype(str)
            valittu_peli = st.selectbox("Valitse ottelu:", sorted(df['Ottelu_info'].unique()))
            
            peli_df = df[df['Ottelu_info'] == valittu_peli].sort_values(by='Game_Score', ascending=False)
            
            st.dataframe(peli_df[[player_col, 'Game_Score', 'Goals_clean', 'Assists_clean', 'Shots_clean', 'NetXG_clean', 'Team_Sheet']], use_container_width=True)
        else:
            st.warning("Päivämäärä- tai vastustajatietoja ei löytynyt taulukosta.")

    with tab3:
        st.subheader("Raakadata ja lasketut Game Score -pisteet[cite: 3]")
        st.dataframe(df, use_container_width=True)
