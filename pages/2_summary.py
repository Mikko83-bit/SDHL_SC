import pandas as pd
import streamlit as st

st.set_page_config(page_title="Kauden Yhteenveto", page_icon="📊", layout="wide")

st.header("📊 Luleå HF – Koko Kauden Yhteenveto (SDHL)")
st.markdown("Tämä sivu kokoaa yhteen kaikkien pelattujen otteluiden tilastot.")

# Ladataan kausitiedosto
excel_path = "LHF Dam season 2026–2027.xlsx"

try:
  # Luetaan Excel (varmista että sheets vastaa tiedostosi rakennetta)
  df = pd.read_excel(excel_path)

  st.subheader("📋 Koko kauden raakadata")
  st.dataframe(df)

  # Esimerkki yhteenvedosta: Jos taulukossa on pelaajat ja maalit/pisteet
  if "Pelaaja" in df.columns and "Maalit" in df.columns:
    st.subheader("⭐ Pelaajien kokonaistehot kaudelta")
    summary_df = (
        df.groupby("Pelaaja")[["Maalit", "Laukaukset"]]
        .sum()
        .reset_index()
        .sort_values(by="Maalit", ascending=False)
    )
    st.dataframe(summary_df)

    st.bar_chart(summary_df.set_index("Pelaaja")["Maalit"])

except Exception as e:
  st.warning(
      f"Tiedostoa '{excel_path}' ei voitu ladata automaattisesti. Virhe: {e}"
  )
  uploaded_file = st.file_uploader(
      "Lataa kauden Excel-tiedosto manuaalisesti", type=["xlsx", "csv"]
  )
  if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    st.dataframe(df)
