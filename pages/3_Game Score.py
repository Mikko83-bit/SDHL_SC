import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="SDHL Scoring Chances Analysis", layout="wide")
st.title("🏒 SDHL Scoring Chances Analysis")


@st.cache_data
def load_data():
  excel_path = "SDHL 2026-2027 scoring chances.xlsx"
  xls = pd.ExcelFile(excel_path)

  players_df = pd.read_excel(xls, sheet_name="Players")
  team_df = pd.read_excel(xls, sheet_name="Team")

  players_df.columns = players_df.columns.astype(str).str.strip()
  team_df.columns = team_df.columns.astype(str).str.strip()

  if "Number" in players_df.columns:
    players_df["Number"] = (
        pd.to_numeric(players_df["Number"], errors="coerce")
        .fillna(-1)
        .astype(int)
        .astype(str)
    )
    players_df.loc[players_df["Number"] == "-1", "Number"] = ""

  p_num_cols = [
      c
      for c in players_df.columns
      if c not in ["Number", "Game ", "Opponent", "Date"]
  ]
  for col in p_num_cols:
    players_df[col] = pd.to_numeric(players_df[col], errors="coerce").fillna(0)

  t_num_cols = [
      c for c in team_df.columns if c not in ["Descriptor", "Game", "Opponent", "Date"]
  ]
  for col in t_num_cols:
    team_df[col] = pd.to_numeric(team_df[col], errors="coerce").fillna(0)

  return players_df, team_df


players_df, team_df = load_data()


# LUOKITTELU: ERÄT OMIKSI KATEGORIOIKSEENAN (Period 1, Period 2, Period 3, OT)
def classify_descriptor(desc):
  d = str(desc).strip()
  d_lower = d.lower()

  if d_lower in ["period 1", "period 2", "period 3", "ot"]:
    return d.title() if d_lower != "ot" else "OT"

  oz_list = [
      "oz tip",
      "oz rr pass",
      "oz shot+screen",
      "oz 1 area",
      "oz crash the net",
      "oz reb",
      "oz bl+screen",
  ]
  if d_lower in oz_list:
    return "OZ"

  rush_list = ["rush+rb", "rush br", "rush+", "rush-", "rush"]
  if d_lower in rush_list:
    return "Rush"

  pp_list = ["pp setup", "pp faceoff", "pp rush", "pp takeaway", "pp reb"]
  if d_lower in pp_list:
    return "PP"

  ta_list = ["ta dz", "ta nz", "ta oz"]
  if d_lower in ta_list:
    return "Takeaways"

  to_list = ["turnover dz", "turnover oz", "turnover nz"]
  if d_lower in to_list:
    return "Turnovers"

  other_list = ["empty net", "pk", "faceoff"]
  if d_lower in other_list:
    return "Others"

  return "Others"


team_df["Category"] = team_df["Descriptor"].apply(classify_descriptor)

game_col_p = (
    "Game "
    if "Game " in players_df.columns
    else ("Game" if "Game" in players_df.columns else None)
)

combined_df = pd.concat([
    (
        players_df[["Game ", "Opponent", "Date"]].rename(
            columns={"Game ": "Game"}
        )
        if "Game " in players_df.columns
        else pd.DataFrame(columns=["Game", "Opponent", "Date"])
    ),
    (
        team_df[["Game", "Opponent", "Date"]]
        if {"Game", "Opponent", "Date"}.issubset(team_df.columns)
        else pd.DataFrame(columns=["Game", "Opponent", "Date"])
    ),
]).drop_duplicates(subset=["Game"])

combined_df = combined_df.sort_values(by="Game")

game_options = []
game_mapping = {}

for _, row in combined_df.iterrows():
  g_num = row["Game"]
  opp = row.get("Opponent", "")
  date = row.get("Date", "")

  label = f"Game {g_num}"
  if pd.notna(opp) and str(opp).strip() != "":
    label += f" vs {opp}"
  if pd.notna(date) and str(date).strip() != "":
    label += f" ({date})"

  game_options.append(label)
  game_mapping[label] = g_num

if not game_options:
  all_games = (
      sorted(
          list(
              set(
                  players_df[game_col_p].dropna().unique().tolist()
                  + team_df["Game"].dropna().unique().tolist()
              )
          )
      )
      if game_col_p
      else []
  )
  game_options = [f"Game {g}" for g in all_games]
  game_mapping = {f"Game {g}": g for g in all_games}

all_players = sorted([p for p in players_df["Number"].unique() if p != ""])
all_categories = sorted(team_df["Category"].dropna().unique().tolist())

st.sidebar.header("Filters")
selected_labels = st.sidebar.multiselect(
    "Select Game", options=game_options, default=game_options
)
selected_games = [
    game_mapping[label] for label in selected_labels if label in game_mapping
]

default_cats = [
    c
    for c in [
        "OZ",
        "Takeaways",
        "Turnovers",
        "Rush",
        "PP",
        "Others",
        "Period 1",
        "Period 2",
        "Period 3",
        "OT",
    ]
    if c in all_categories
]
selected_categories = st.sidebar.multiselect(
    "Select Category", options=all_categories, default=default_cats
)
selected_players = st.sidebar.multiselect(
    "Select Player Number", options=all_players, default=all_players
)

all_metric_options = [
    "Goal For",
    "Goal For inv",
    "Chance For",
    "Chance For inv",
    "PP goal",
    "PP goal inv",
    "PP chance",
    "PP chance inv",
    "Goal Against",
    "Chance Against",
    "PP goal ag",
    "PP chance ag",
]
valid_metric_defaults = [m for m in all_metric_options if m in team_df.columns]
selected_team_metrics = st.sidebar.multiselect(
    "Select Team Metrics to Compare",
    options=valid_metric_defaults,
    default=valid_metric_defaults,
)

filtered_players = players_df.copy()
if game_col_p and selected_games:
  filtered_players = filtered_players[
      filtered_players[game_col_p].isin(selected_games)
  ]
if "Number" in filtered_players.columns and selected_players:
  filtered_players = filtered_players[
      filtered_players["Number"].isin(selected_players)
  ]

filtered_team = team_df.copy()
if "Game" in filtered_team.columns and selected_games:
  filtered_team = filtered_team[filtered_team["Game"].isin(selected_games)]
if "Category" in filtered_team.columns and selected_categories:
  filtered_team = filtered_team[
      filtered_team["Category"].isin(selected_categories)
  ]

kpi_source = (
    filtered_team[filtered_team["Category"].isin(["Period 1", "Period 2", "Period 3", "OT"])]
    if not filtered_team[filtered_team["Category"].isin(["Period 1", "Period 2", "Period 3", "OT"])].empty
    else filtered_team
)

total_gf = (
    int(kpi_source["Goal For"].sum() + kpi_source["PP goal"].sum())
    if "Goal For" in kpi_source.columns
    else 0
)
total_ga = (
    int(kpi_source["Goal Against"].sum() + kpi_source["PP goal ag"].sum())
    if "Goal Against" in kpi_source.columns
    else 0
)
goals_net = total_gf - total_ga

total_cf = (
    int(kpi_source["Chance For"].sum() + kpi_source["PP chance"].sum())
    if "Chance For" in kpi_source.columns
    else 0
)
total_ca = (
    int(kpi_source["Chance Against"].sum() + kpi_source["PP chance ag"].sum())
    if "Chance Against" in kpi_source.columns
    else 0
)
chances_net = total_cf - total_ca

total_net = goals_net + chances_net

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Goals For / Against", f"{total_gf} / {total_ga}", f"{goals_net:+d}")
col2.metric("Chances For / Against", f"{total_cf} / {total_ca}", f"{chances_net:+d}")
col3.metric("Goals Total (GF)", total_gf)
col4.metric("Chances Total (CF)", total_cf)
col5.metric("Total (Net)", total_net)

st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 Scoring Chances Team", "👤 Scoring Chances Players", "📈 Visuals", "📄 Raw Data"]
)

with tab1:
  st.subheader("Team Statistics by Category & Descriptor")
  if not filtered_team.empty
