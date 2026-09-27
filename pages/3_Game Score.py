import streamlit as st
import pandas as pd
import plotly.express as px

# Sivun asetukset
st.set_page_config(page_title="SDHL Game Score -analyysi", page_icon="🏒", layout="wide")

st.title("🏒 SDHL Game Score -analyysityökalu (2026–2027)")
st.write("Tämä sivu laskee ja visualisoi pelaajien pelikohtaiset *Game Score* -pisteet InStat-tilastojen pohjalta.")

# Tiedoston lataus
EXCEL_FILE = "Sdhl Game score 2026-2027.xlsx"

@st.cache_data
def load_data(file_path):
    try:
        df = pd.read_excel(file_path)
        
        # Siivotaan sarakkeiden nimet
        df.columns = df.columns.str.strip()
        
        # Korjataan Date-sarake pelkiksi päivämääriksi
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
            
        return df
    except Exception as e:
        return None

df = load_data(EXCEL_FILE)

if df is None:
    st.error(f"Tiedostoa '{EXCEL_FILE}' ei löytynyt tai sen lukemisessa tapahtui virhe. Varmista, että tiedosto on oikeassa kansiossa.")
else:
    # Apufunktio sarakkeiden turvalliseen hakuun
    def get_col(data, col_name, default=0):
        if col_name in data.columns:
            return pd.to_numeric(data[col_name], errors='coerce').fillna(0)
        return 0

    # Tunnistetaan sarakkeet
    goals_col = next((c for c in df.columns if 'goal' in c.lower() and 'shot' not in c.lower() and 'x' not in c.lower()), None)
    assists_col = next((c for c in df.columns if 'assist' in c.lower() and 'first' not in c.lower()), None)
    shots_col = next((c for c in df.columns if 'shots on goal' in c.lower() or c.lower() == 'shots'), None)
    net_xg_col = next((c for c in df.columns if 'net xg' in c.lower()), None)
    fw_col = next((c for c in df.columns if 'faceoffs won' in c.lower()), None)
    fl_col = next((c for c in df.columns if 'faceoffs lost' in c.lower()), None)

    # Lasketaan puhtaat arvot
    df['Goals_clean'] = get_col(df, goals_col) if goals_col else 0
    df['Assists_clean'] = get_col(df, assists_col) if assists_col else 0
    df['Shots_clean'] = get_col(df, shots_col) if shots_col else 0
    df['NetXG_clean'] = get_col(df, net_xg_col) if net_xg_col else 0
    df['FW_clean'] = get_col(df, fw_col) if fw_col else 0
    df['FL_clean'] = get_col(df, fl_col) if fl_col else 0

    # Game Score -laskenta
    df['Game_Score'] = (
        (df['Goals_clean'] * 1.0) +
        (df['Assists_clean'] * 0.7) +
        (df['Shots_clean'] * 0.1) +
        (df['NetXG_clean'] * 0.5) +
        ((df['FW_clean'] - df['FL_clean']) * 0.05)
    )

    player_col = next((c for c in df.columns if 'player' in c.lower()), df.columns[6] if len(df.columns) > 6 else df.columns[0])
    opponent_col = next((c for c in df.columns if 'opponent' in c.lower()), None)

    # --- SIVUPALKKI: SUODATTIMET ---
    st.sidebar.header("🔍 Suodattimet")
    
    # Vastustaja / Joukkue -suodatin
    if opponent_col:
        kaikki_vastustajat = sorted(df[opponent_col].dropna().unique())
        valitut_vastustajat = st.sidebar.multiselect("Valitse vastustaja(t):", kaikki_vastustajat, default=kaikki_vastustajat)
        
        # Suodatetaan data valittujen vastustajien mukaan
        if valitut_vastustajat:
            df = df[df[opponent_col].isin(valitut_vastustajat)]

    # Välilehdet sovellukseen
    tab1, tab2, tab3 = st.tabs(["📊 Pelaajaprofiili & Kehitys", "🏆 Ottelun Leaderboard", "📁 Raakadata"])

    with tab1:
        st.subheader("Pelaajan kehityskäyrä kauden aikana")
        
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
        st.subheader("Ottelukohtainen Leaderboard")
        
        date_col = 'Date' if 'Date' in df.columns else None
        
        if date_col and opponent_col:
            df['Ottelu_info'] = df[date_col].astype(str) + " vs " + df[opponent_col].astype(str)
            valittu_peli = st.selectbox("Valitse ottelu:", sorted(df['Ottelu_info'].unique()))
            
            peli_df = df[df['Ottelu_info'] == valittu_peli].sort_values(by='Game_Score', ascending=False)
            
            st.dataframe(peli_df[[player_col, 'Game_Score', 'Goals_clean', 'Assists_clean', 'Shots_clean', 'NetXG_clean']], use_container_width=True)
        else:
            st.warning("Päivämäärä- tai vastustajatietoja ei löytynyt taulukosta.")

    with tab3:
        st.subheader("Raakadata ja lasketut Game Score -pisteet")
        st.dataframe(df, use_container_width=True)
        
