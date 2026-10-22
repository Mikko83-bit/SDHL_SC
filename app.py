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

# Pelaajien nimikartta numeroiden perusteella
player_names = {
    6: "Jenni Hiirikoski",
    8: "Hedvig Sturk",
    9: "Nella Berg",
    13: "Jenna Donohue",
    14: "Wilma Sjolund",
    15: "Emilie Kruse Johansen",
    18: "Edith Larsson Ornkloo",
    21: "Astrid Lindeberg",
    23: "Madison Chantler",
    25: "Fanny Aneborn",
    27: "Jaycee Magwood",
    39: "Inez Nygren",
    42: "Mei Miura",
    44: "Ebba Hörnqvist",
    71: "Ebba Hedqvist",
    72: "Aoi Shiga",
    81: "Franziska Stocker",
}


# LUOKITTELU & STANDARDOINTI
def classify_descriptor(desc):
    d = str(desc).strip()
    d_lower = d.lower()

    if d_lower in ["period 1", "period 1."]:
        return "Period", "Period 1"
    if d_lower in ["period 2", "period 2."]:
        return "Period", "Period 2"
    if d_lower in ["period 3", "period 3.", "3"]:
        return "Period", "Period 3"
    if d_lower in ["ot", "period ot"]:
        return "Period", "OT"

    oz_list = [
        "oz tip",
        "oz rr pass",
        "oz shot+screen",
        "oz 1 area",
        "oz 2 area",
        "oz crash the net",
        "oz reb",
        "oz bl+screen",
        "oz blueline+screen",
    ]
    if d_lower in oz_list:
        return "OZ", d

    rush_list = ["rush+rb", "rush br", "rush+", "rush-", "rush"]
    if d_lower in rush_list:
        return "Rush", d

    pp_list = ["pp setup", "pp faceoff", "pp rush", "pp takeaway", "pp reb"]
    if d_lower in pp_list:
        return "PP", d

    ta_list = ["ta dz", "ta nz", "ta oz"]
    if d_lower in ta_list:
        return "Takeaways", d.upper()

    if d_lower in ["turnover dz", "t over dz"]:
        return "Turnovers", "Turnover DZ"
    if d_lower in ["turnover nz", "t over nz"]:
        return "Turnovers", "Turnover NZ"
    if d_lower in ["turnover oz", "t over oz"]:
        return "Turnovers", "Turnover OZ"

    other_list = ["empty net", "pk", "faceoff"]
    if d_lower in other_list:
        return "Others", d.title()

    return "Uncategorized", d


res = team_df["Descriptor"].apply(classify_descriptor)
team_df["Category"] = [r[0] for r in res]
team_df["Descriptor"] = [r[1] for r in res]

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
        "Period",
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
    filtered_team[filtered_team["Category"] == "Period"]
    if not filtered_team[filtered_team["Category"] == "Period"].empty
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

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "📊 Scoring Chances Team",
        "👤 Scoring Chances Players",
        "📈 Visuals",
        "📊 Advanced Visuals",
        "📄 Raw Data",
    ]
)

with tab1:
    st.subheader("Team Statistics by Category & Descriptor")
    if not filtered_team.empty:
        base_cols = ["Category", "Descriptor"]
        desired_order = [
            "Goal For",
            "Chance For",
            "PP goal",
            "PP chance",
            "Goal Against",
            "Chance Against",
            "PP goal ag",
            "PP chance ag",
        ]
        available_selected = [
            c
            for c in desired_order
            if c in selected_team_metrics and c in filtered_team.columns
        ]
        num_cols = filtered_team.select_dtypes(include=["number"]).columns.tolist()
        num_cols = [c for c in num_cols if c != "Game"]

        team_summary = filtered_team.groupby(base_cols)[num_cols].sum().reset_index()
        cols_to_show = base_cols + available_selected
        extra_cols = [
            c for c in team_summary.columns if c not in cols_to_show and c not in base_cols
        ]
        team_summary = team_summary[base_cols + available_selected + extra_cols]

        team_config = {
            "Category": st.column_config.TextColumn("Category", width="small"),
            "Descriptor": st.column_config.TextColumn("Descriptor", width="medium"),
        }
        for col in team_summary.columns:
            if col not in team_config:
                team_config[col] = st.column_config.NumberColumn(col, width="small")

        st.dataframe(
            team_summary,
            use_container_width=False,
            column_config=team_config,
            hide_index=True,
        )
    else:
        st.info("No team data available for selected filters.")

with tab2:
    st.subheader("Player Statistics with Total Score")
    if not filtered_players.empty:
        p_num_cols = [
            c
            for c in filtered_players.select_dtypes(include=["number"]).columns.tolist()
            if c not in ["Game", "Game "]
        ]
        player_summary = (
            filtered_players.groupby("Number")[p_num_cols].sum().reset_index()
        )

        gf = (
            player_summary["Goal For"]
            if "Goal For" in player_summary.columns
            else 0
        )
        gfi = (
            player_summary["Goal For inv"]
            if "Goal For inv" in player_summary.columns
            else 0
        )
        cf = (
            player_summary["Chance For"]
            if "Chance For" in player_summary.columns
            else 0
        )
        cfi = (
            player_summary["Chance For inv"]
            if "Chance For inv" in player_summary.columns
            else 0
        )
        ga = (
            player_summary["Goal Against"]
            if "Goal Against" in player_summary.columns
            else 0
        )
        ca = (
            player_summary["Chance Against"]
            if "Chance Against" in player_summary.columns
            else 0
        )

        player_summary["Total"] = (gf + gfi + cf + cfi) - (ga + ca)

        player_summary["Num_Int"] = pd.to_numeric(
            player_summary["Number"], errors="coerce"
        )
        player_summary["Name"] = player_summary["Num_Int"].map(player_names)

        # Suodatetaan pois pelaajat joilla ei ole nimeä sanakirjassa
        player_summary = player_summary.dropna(subset=["Name"])

        player_summary = player_summary.sort_values(
            by="Total", ascending=False
        ).reset_index(drop=True)

        if not player_summary.empty:
            col_top, col_bot = st.columns(2)

            # 🟢 TOP 5 PARHAAT
            with col_top:
                st.markdown("### 🟢 Top 5 Players (Best Net Impact)")
                top_players = player_summary.head(5).copy()
                top_players["Player_Label"] = (
                    "#" + top_players["Number"].astype(str) + " " + top_players["Name"]
                )

                fig_top = px.bar(
                    top_players,
                    x="Total",
                    y="Player_Label",
                    orientation="h",
                    text="Total",
                    color="Total",
                    color_continuous_scale="Greens",
                    title="Top 5 Impact",
                )
                fig_top.update_layout(
                    yaxis=dict(type="category", autorange="reversed"),
                    xaxis_title="Total Score Net Balance",
                    yaxis_title="Player",
                    showlegend=False,
                    height=300,
                )
                fig_top.update_traces(textposition="outside")
                st.plotly_chart(fig_top, use_container_width=True)

            # 🔴 BOTTOM 5 HEIKOIMMAT
            with col_bot:
                st.markdown("### 🔴 Bottom 5 Players (Lowest Net Impact)")
                bot_players = (
                    player_summary.tail(5)
                    .copy()
                    .sort_values(by="Total", ascending=True)
                )
                bot_players["Player_Label"] = (
                    "#" + bot_players["Number"].astype(str) + " " + bot_players["Name"]
                )

                fig_bot = px.bar(
                    bot_players,
                    x="Total",
                    y="Player_Label",
                    orientation="h",
                    text="Total",
                    color="Total",
                    color_continuous_scale="Reds_r",
                    title="Bottom 5 Impact",
                )
                fig_bot.update_layout(
                    yaxis=dict(type="category", autorange="reversed"),
                    xaxis_title="Total Score Net Balance",
                    yaxis_title="Player",
                    showlegend=False,
                    height=300,
                )
                fig_bot.update_traces(textposition="outside")
                st.plotly_chart(fig_bot, use_container_width=True)

            st.markdown("---")
            st.markdown("### Player Statistics Table")

            cols = ["Number", "Name"] + [
                c
                for c in player_summary.columns
                if c
                not in [
                    "Number",
                    "Name",
                    "Num_Int",
                    "Total",
                ]
            ] + ["Total"]
            player_summary_table = player_summary[cols]

            column_config = {
                col: st.column_config.NumberColumn(col, width="small")
                for col in player_summary_table.columns
            }
            column_config["Number"] = st.column_config.TextColumn("Number", width="small")
            column_config["Name"] = st.column_config.TextColumn("Name", width="medium")

            st.dataframe(
                player_summary_table,
                use_container_width=False,
                column_config=column_config,
                hide_index=True,
            )
        else:
            st.info("No named players found for the selected filters.")
    else:
        st.info("No player data available for selected filters.")

with tab3:
    st.subheader("Category & Period Performance Overview")
    chart_source = filtered_team.copy()
    if not chart_source.empty and selected_team_metrics:
        for_metrics = [
            m
            for m in selected_team_metrics
            if "against" not in m.lower() and "ag" not in m.lower()
        ]
        ag_metrics = [
            m
            for m in selected_team_metrics
            if "against" in m.lower() or "ag" in m.lower()
        ]

        chart_source["Visual_Group"] = chart_source.apply(
            lambda r: r["Descriptor"] if r["Category"] == "Period" else r["Category"],
            axis=1,
        )

        chart_data = (
            chart_source.groupby("Visual_Group")[selected_team_metrics]
            .sum()
            .reset_index()
        )
        chart_data["For Total"] = (
            chart_data[for_metrics].sum(axis=1) if for_metrics else 0
        )
        chart_data["Against Total"] = (
            chart_data[ag_metrics].sum(axis=1) if ag_metrics else 0
        )

        plot_df = pd.melt(
            chart_data,
            id_vars=["Visual_Group"],
            value_vars=["For Total", "Against Total"],
            var_name="Type",
            value_name="Count",
        )

        fig = px.bar(
            plot_df,
            x="Visual_Group",
            y="Count",
            color="Type",
            barmode="group",
            color_discrete_map={"For Total": "#1f77b4", "Against Total": "#d62728"},
        )

        fig.update_traces(texttemplate="%{y}", textposition="outside")
        fig.update_layout(
            xaxis_title="Category / Period",
            yaxis_title="Total Count",
            uniformtext_minsize=8,
            uniformtext_mode="hide",
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Valitse vähintään yksi metriikka sivupalkista kaavion näyttämiseksi.")

with tab4:
    st.subheader("Advanced Performance Analytics")
    if not filtered_team.empty:
        col_vis1, col_vis2 = st.columns(2)

        with col_vis1:
            st.markdown("### Net Scoring Chances by Category")
            net_df = (
                filtered_team.groupby("Category")
                .apply(
                    lambda g: (g["Goal For"].sum() + g["Chance For"].sum())
                    - (g["Goal Against"].sum() + g["Chance Against"].sum())
                )
                .reset_index(name="Net Difference")
            )

            fig_net = px.bar(
                net_df,
                x="Category",
                y="Net Difference",
                color="Net Difference",
                color_continuous_scale=["#d62728", "#e0e0e0", "#2ca02c"],
                title="Net Difference (For - Against)",
            )
            fig_net.update_traces(texttemplate="%{y}", textposition="outside")
            st.plotly_chart(fig_net, use_container_width=True)

        with col_vis2:
            st.markdown("### Chance Creation Share by Category")
            for_df = (
                filtered_team[filtered_team["Category"] != "Period"]
                .groupby("Category")[["Chance For", "Goal For"]]
                .sum()
                .sum(axis=1)
                .reset_index(name="Total For")
            )
            fig_pie = px.pie(
                for_df,
                names="Category",
                values="Total For",
                hole=0.4,
                title="Where Do Scoring Chances Come From?",
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        st.markdown("---")
        st.markdown("### Game-by-Game Scoring Chances Trend")
        trend_df = (
            filtered_team[filtered_team["Category"] == "Period"]
            .groupby("Game")[["Goal For", "Chance For", "Goal Against", "Chance Against"]]
            .sum()
            .reset_index()
        )
        trend_df["Total For"] = trend_df["Goal For"] + trend_df["Chance For"]
        trend_df["Total Against"] = trend_df["Goal Against"] + trend_df["Chance Against"]

        fig_trend = px.line(
            trend_df,
            x="Game",
            y=["Total For", "Total Against"],
            markers=True,
            color_discrete_map={"Total For": "#1f77b4", "Total Against": "#d62728"},
            labels={"value": "Total Count", "variable": "Type"},
            title="Performance Across Selected Games",
        )
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("No data available for advanced analytics.")

with tab5:
    st.subheader("Raw Data Sheets")
    st.markdown("### Players Sheet")
    st.dataframe(filtered_players, use_container_width=True)
    st.markdown("### Team Sheet")
    st.dataframe(filtered_team, use_container_width=True)
