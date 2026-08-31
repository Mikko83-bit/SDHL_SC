import streamlit as st
import pandas as pd
import glob

st.title("Jääkiekon Pelitapa- ja Pelaaja-analyysi")

# 1. Lue kaikki CSV-tiedostot kerralla
@st.cache_data
def load_data():
    files = glob.glob("data/*.csv")
    df_list = [pd.read_csv(f, sep=";") for f in files]
    return pd.concat(df_list, ignore_index=True)

df = load_data()

# 2. Sivuvalikon suodattimet
st.sidebar.header("Suodattimet")
selected_game = st.sidebar.multiselect("Valitse Peli", df["Game"].unique(), default=df["Game"].unique())
filtered_df = df[df["Game"].isin(selected_game)]

# 3. Joukkueen kokonaistilasto (Descriptor-jakauma)
st.subheader("Joukkueen pelitapatilastot")
desc_stats = filtered_df.groupby("Descriptor")[["Goal for", "Chance for", "Goal agn", "Chance agn", "Turnover"]].sum()
st.dataframe(desc_stats)

# 4. Pelaajakohtainen tarkastelu (Maalintekijät P1)
st.subheader("Maalintekijät (P1)")
goals_df = filtered_df[filtered_df["Goal for"] == 1]
st.bar_chart(goals_df["Player 1"].value_counts())
