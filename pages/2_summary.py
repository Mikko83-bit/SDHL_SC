import pandas as pd
import streamlit as st

st.set_page_config(page_title="Kauden Yhteenveto & Indeksi", page_icon="🏒", layout="wide")

st.header("🏒 Luleå HF – Koko Kauden Yhteenveto & Oma Indeksi")
st.markdown("Tämä sivu laskee yhteen kauden tilastot ja rakentaa mukautetun suoritusindeksin.")

# Tiedoston lataus
excel_path = "LHF Dam season 2026–2027.xlsx"
df = None

try:
    df = pd.read_excel(excel_path)
except Exception:
    pass

uploaded_file = st.file_uploader("Lataa tai päivitä kauden Excel-tiedosto:", type=["xlsx", "csv"])
if uploaded_file is not None:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

if df is not None:
    df.columns = df.columns.str.strip()
    pelaaja_col = "Player" if "Player" in df.columns else ("Pelaaja" if "Pelaaja" in df else None)

    if pelaaja_col:
        # Puhdistetaan numeromuodot
        numeric_cols = ["Goals", "Assists", "Points", "Shots on goal", "xG (Expected goals)", "Blocked shots", "Hits"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        # --- OMA INDEKSI - SIVUPALKKI ---
        st.sidebar.header("⚙️ Oma Indeksi -painotukset")
        st.sidebar.markdown("Säädä muuttujien painoarvoja:")
        
        w_maalit = st.sidebar.slider("Maalit (Goals)", 1.0, 10.0, 5.0)
        w_syotot = st.sidebar.slider("Syötöt (Assists)", 0.5, 5.0, 3.0)
        w_xg = st.sidebar.slider("Odottamat (xG)", 0.0, 10.0, 3.0)
        w_blokit = st.sidebar.slider("Blokatut laukaukset", 0.0, 5.0, 1.5)
        w_taklaukset = st.sidebar.slider("Taklaukset (Hits)", 0.0, 3.0, 1.0)
        perustaso = st.sidebar.slider("Indeksin perustaso (Baseline)", 50, 150, 100)

        # Lasketaan oma indeksi jokaiselle riville (ottelukohtaisesti)
        df["Oma_Indeksi"] = (
            perustaso
            + (df.get("Goals", 0) * w_maalit)
            + (df.get("Assists", 0) * w_syotot)
            + (df.get("xG (Expected goals)", 0) * w_xg)
            + (df.get("Blocked shots", 0) * w_blokit)
            + (df.get("Hits", 0) * w_taklaukset)
        )

        # Ryhmitellään kauden yhteenvedoksi (as_index=False estää törmäykset)
        agg_dict = {
            "Goals": "sum",
            "Assists": "sum",
            "Points": "sum",
            "Shots on goal": "sum",
            "xG (Expected goals)": "sum",
            "Oma_Indeksi": "mean" # Keskiarvo-indeksi per peli
        }
        
        # Suodatetaan vain sarakkeet jotka löytyvät datasta
        agg_dict = {k: v for k, v in agg_dict.items() if k in df.columns}

        summary_df = df.groupby(pelaaja_col, as_index=False).agg(agg_dict)
        
        # Lasketaan pelatut ottelut erikseen ja lisätään taulukkoon
        games_played = df.groupby(pelaaja_col).size().reset_index(name="Games Played")
        summary_df = pd.merge(summary_df, games_played, on=pelaaja_col)

        summary_df = summary_df.rename(columns={
            pelaaja_col: "Player", 
            "Goals": "Tot Goals", 
            "Points": "Tot Points", 
            "Oma_Indeksi": "Avg Custom Index"
        })
        
        if "Player" in summary_df.columns:
            summary_df = summary_df.sort_values(by="Avg Custom Index", ascending=False)

            st.subheader("⭐ Pelaajien Ranking – Oma Suoritusindeksi")
            st.markdown("Tämä taulukko näyttää pelaajien keskimääräisen indeksin ottelua kohden säädettyjen painotusten mukaan.")
            st.dataframe(summary_df, use_container_width=True)

            # Graafi
            st.subheader("📈 Pelaajien vertailu omalla indeksillä")
            st.bar_chart(summary_df.set_index("Player")["Avg Custom Index"])

        with st.expander("🔍 Näytä koko raakadata"):
            st.dataframe(df)

    else:
        st.error("Taulukosta ei löytynyt pelaajan nimitunnistetta ('Player' tai 'Pelaaja').")
else:
    st.info("Lataa tiedosto yllä olevasta laatikosta aloittaaksesi.")
