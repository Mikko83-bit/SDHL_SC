with tab3:
    st.subheader("Team Performance: For vs Against by Category")
    
    import plotly.express as px
    
    def get_category(desc):
        d = str(desc).lower()
        if "ozp" in d:
            return "OZP"
        elif "rush" in d:
            return "Rush"
        elif "takeaway" in d:
            return "Takeaway"
        else:
            return "Other"
            
    team_df = filtered_df.copy()
    team_df["Category"] = team_df["Descriptor"].apply(get_category)
    
    team_summary = team_df.groupby("Category")[
        ["Goal for", "Chance for", "Goal agn", "Chance agn"]
    ].sum().reset_index()
    
    team_summary["For"] = team_summary["Goal for"] + team_summary["Chance for"]
    team_summary["Against"] = team_summary["Goal agn"] + team_summary["Chance agn"]
    
    # Muokataan data Plotlylle sopivaan muotoon (long format)
    plot_data = pd.melt(
        team_summary, 
        id_vars=["Category"], 
        value_vars=["For", "Against"],
        var_name="Type", 
        value_name="Count"
    )
    
    # Piirretään vierekkäiset pylväät Plotlyllä
    fig = px.bar(
        plot_data, 
        x="Category", 
        y="Count", 
        color="Type", 
        barmode="group",
        color_discrete_map={"For": "#1f77b4", "Against": "#d62728"} # Sininen ja punainen
    )
    fig.update_layout(xaxis_title="Category", yaxis_title="Total (Goals + Chances)")
    
    st.plotly_chart(fig, use_container_width=True)
