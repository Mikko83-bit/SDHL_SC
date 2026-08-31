import streamlit as st
import pandas as pd

st.set_page_config(page_title="Scoring Chances Analysis", layout="wide")

st.title("🏒 Scoring Chances Team & Players Analysis")

# 1. Luetaan CSV-tiedosto
@st.cache_data
def load_data():
    # Luetaan CSV puolipiste-erottimella
    df = pd.read_csv("hockey_tag_data.csv", sep=";")
    
    # Muutetaan mahdolliset tyhjät solut numeerisissa sarakkeissa nolliksi
    outcome_cols = [
        "Goal for", "Chance for", "Goal for PP", "Chance for PP",
        "Goal agn", "Chance agn", "Goal agn PP", "Chance agn PP", "Turnover"
    ]
    for col in outcome_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    return df

try:
    df = load_data()

    # 2. Sivuvalikon suodattimet (Interaktiivisuus)
    st.sidebar.header("Filters")
    
    games = st.sidebar.multiselect("Select Game", options=df["Game"].unique(), default=df["Game"].unique())
    periods = st.sidebar.multiselect("Select Period", options=df["Period"].unique(), default=df["Period"].unique())

    # Suodatetaan data valintojen mukaan
    filtered_df = df[(df["Game"].isin(games)) & (df["Period"].isin(periods))]

    # 3. Yhteenveto / Avainmittarit (KPIs)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Goals For", int(filtered_df["Goal for"].sum() + filtered_df["Goal for PP"].sum()))
    col2.metric("Goals Against", int(filtered_df["Goal agn"].sum() + filtered_df["Goal agn PP"].sum()))
    col3.metric("Scoring Chances For", int(filtered_df["Chance for"].sum() + filtered_df["Chance for PP"].sum()))
    col4.metric("Turnovers", int(filtered_df["Turnover"].sum()))

    st.markdown("---")

    # 4. Välilehdet uusin nimin
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

except Exception as e:
    st.error("Could not load 'hockey_tag_data.csv'.")
    st.info("Make sure 'hockey_tag_data.csv' is uploaded to the root directory of your GitHub repository.")
