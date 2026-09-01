import streamlit as st
import pandas as pd

st.set_page_config(page_title="Scoring Chances Analysis", layout="wide")
st.title("🏒 Scoring Chances Team & Players Analysis")

# 1. Älykäs datan lukeminen
@st.cache_data
def load_data():
    # Tarkistetaan onko tiedoston ensimmäisellä rivillä Excel-komento "sep=;"
    with open("hockey_tag_data.csv", "r", encoding="utf-8") as f:
        first_line = f.readline().strip()
    
    # Jos Excel-rivi löytyy, hypätään sen yli (skiprows=1)
    skip = 1 if first_line.startswith("sep=") else 0
    
    # Luetaan data (sep=None ja engine='python' tunnistavat automaattisesti onko kyseessä , vai ;)
    df = pd.read_csv("hockey_tag_data.csv", skiprows=skip, sep=None, engine='python')
    
    # Muutetaan mahdolliset tyhjät solut numeerisissa sarakkeissa nolliksi
    outcome_cols = [
        "Goal for", "Chance for", "Goal for PP", "Chance for PP",
        "Goal agn", "Chance agn", "Goal agn PP", "Chance agn PP", "Turnover"
    ]
    for col in outcome_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    return df

# Ladataan data ilman try-except -lohkoa, jotta mahdolliset virheet näkyvät ruudulla
df = load_data()

# 2. Sivuvalikon suodattimet
st.sidebar.header("Filters")
games = st.sidebar.multiselect("Select Game", options=df["Game"].unique(), default=df["Game"].unique())
periods = st.sidebar.multiselect("Select Period", options=df["Period"].unique(), default=df["Period"].unique())

filtered_df = df[(df["Game"].isin(games)) & (df["Period"].isin(periods))]

# 3. Yhteenveto / Avainmittarit (KPIs)
col1, col2, col3, col4 = st.columns(4)
col1.metric("Goals For", int(filtered_df["Goal for"].sum() + filtered_df["Goal for PP"].sum()))
col2.metric("Goals Against", int(filtered_df["Goal agn"].sum() + filtered_df["Goal agn PP"].sum()))
col3.metric("Scoring Chances For", int(filtered_df["Chance for"].sum() + filtered_df["Chance for PP"].sum()))
col4.metric("Turnovers", int(filtered_df["Turnover"].sum()))

st.markdown("---")

# 4. Välilehdet
tab1, tab2, tab3 = st.tabs(["📊 Scoring Chances Team", "👤 Scoring Chances Players", "📄 Raw Data"])

with tab1:
    st.subheader("Team Statistics by Descriptor")
    desc_summary = filtered_df.groupby("Descriptor")[
        ["Goal for", "Chance for", "Goal for PP", "Chance for PP", "Goal agn", "Chance agn", "Turnover"]
    ].sum()
    st.dataframe(desc_summary, use_container_width=True)

with tab2:
    st.subheader("Player Statistics (P1)")
    p1_summary = filtered_df.groupby("Player 1")[
        ["Goal for", "Chance for", "Goal agn", "Chance agn", "Turnover"]
    ].sum()
    st.dataframe(p1_summary, use_container_width=True)

with tab3:
    st.subheader("Filtered Raw Data")
    st.dataframe(filtered_df, use_container_width=True)
