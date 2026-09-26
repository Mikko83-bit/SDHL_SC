import pandas as pd
import streamlit as st

st.set_page_config(page_title="Kauden Yhteenveto", page_icon="📊", layout="wide")

st.header("📊 Luleå HF – Koko Kauden Yhteenveto (SDHL)")
st.markdown(
    "Tämä sivu laskee yhteen kaikkien pelattujen otteluiden tilastot ja pelaajien"
    " kokonaissaldot."
)

# Tiedoston lataus (automaattinen tai manuaalinen)
excel_path = "LHF Dam season 2026–2027.xlsx"
df = None

try:
  df = pd.read_excel(excel_path)
except Exception:
  pass

uploaded_file = st.file_uploader(
    "Lataa tai päivitä kauden Excel-tiedosto:", type=["xlsx", "csv"]
)
if uploaded_file is not None:
  if uploaded_file.name.endswith(".csv"):
    df = pd.read_csv(uploaded_file)
  else:
    df = pd.read_excel(uploaded_file)

if df is not None:
  # Tarkistetaan sarakkeiden nimet (puhdistetaan mahdolliset tyhjät välit)
  df.columns = df.columns.str.strip()

  # Varmistetaan että tarvittavat sarakkeet löytyvät
  pelaaja_col = (
      "Player" if "Player" in df.columns else ("Pelaaja" if "Pelaaja" in df else None)
  )

  if pelaaja_col:
    st.success(f"Data ladattu onnistuneesti! Rivejä yhteensä: {len(df)}")

    # Muutetaan numeromuotoisiksi sarakkeet, joissa voi olla lukuja (korvataan puuttuvat nollilla)
    numeric_cols = ["Goals", "Assists", "Points", "Shots on goal", "xG (Expected goals)"]
    for col in numeric_cols:
      if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Ryhmitellään pelaajittain koko kauden yhteenvetoa varten
    agg_dict = {}
    if "Goals" in df.columns:
      agg_dict["Goals"] = "sum"
    if "Assists" in df.columns:
      agg_dict["Assists"] = "sum"
    if "Points" in df.columns:
      agg_dict["Points"] = "sum"
    if "Shots on goal" in df.columns:
      agg_dict["Shots on goal"] = "sum"
    if "xG (Expected goals)" in df.columns:
      agg_dict["xG (Expected goals)"] = "sum"
    if "Game" in df.columns:
      agg_dict["Game"] = "count"  # Pelatut ottelut

    if agg_dict:
      summary_df = df.groupby(pelaaja_col).agg(agg_dict).reset_index()
      if "Game" in summary_df.columns:
        summary_df = summary_df.rename(columns={"Game": "Games Played"})

      # Järjestetään pisteiden mukaan
      sort_col = "Points" if "Points" in summary_df.columns else summary_df.columns[1]
      summary_df = summary_df.sort_values(by=sort_col, ascending=False)

      st.subheader("🏆 Pelaajien kokonaistilastot kaudelta")
      st.dataframe(summary_df, use_container_width=True)

      # Visualisointi
      st.subheader("📈 Pisteet / Maalit per pelaaja")
      chart_col = "Points" if "Points" in summary_df.columns else "Goals"
      st.bar_chart(summary_df.set_index(pelaaja_col)[chart_col])

    with st.expander("🔍 Näytä koko raakadata"):
      st.dataframe(df)

  else:
    st.error(
        "Taulukosta ei löytynyt pelaajan nimitunnistetta ('Player' tai"
        " 'Pelaaja'). Tarkista tiedoston sarakkeet."
    )
else:
  st.info("Lataa tiedosto yllä olevasta laatikosta aloittaaksesi.")
    
