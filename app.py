with tab2:
    st.subheader("Player Statistics by Role (P1 = Scorer/Receiver, P2/P3 = Creators)")
    
    # Kerätään kaikki uniikit pelaajat kaikista kolmesta sarakkeesta
    all_players = pd.unique(filtered_df[['Player 1', 'Player 2', 'Player 3']].values.ravel())
    players_list = [p for p in all_players if pd.notna(p) and str(p).strip() != '']
    
    player_rows = []
    for p in players_list:
        # P1 roolit (Maalintekijä, Paikan saaja, Menettäjä, Päävirhe)
        goals_scored = filtered_df[(filtered_df['Player 1'] == p) & (filtered_df['Goal for'] == 1)].shape[0]
        chances_rcv = filtered_df[(filtered_df['Player 1'] == p) & (filtered_df['Chance for'] == 1)].shape[0]
        turnovers = filtered_df[(filtered_df['Player 1'] == p) & (filtered_df['Turnover'] == 1)].shape[0]
        goals_agn_p1 = filtered_df[(filtered_df['Player 1'] == p) & (filtered_df['Goal agn'] == 1)].shape[0]
        
        # P2 & P3 roolit (Luojat / Syöttäjät / Apuvirheet)
        goals_created = filtered_df[((filtered_df['Player 2'] == p) | (filtered_df['Player 3'] == p)) & (filtered_df['Goal for'] == 1)].shape[0]
        chances_created = filtered_df[((filtered_df['Player 2'] == p) | (filtered_df['Player 3'] == p)) & (filtered_df['Chance for'] == 1)].shape[0]
        
        player_rows.append({
            'Player': p,
            'Goals (P1)': goals_scored,
            'Assists (P2/P3)': goals_created,
            'Points': goals_scored + goals_created,
            'Chances For (P1)': chances_rcv,
            'Chances Created (P2/P3)': chances_created,
            'Turnovers (P1)': turnovers,
            'Goal Agst Error (P1)': goals_agn_p1
        })
        
    player_df = pd.DataFrame(player_rows)
    if not player_df.empty:
        player_df = player_df.set_index('Player').sort_values(by='Points', ascending=False)
        st.dataframe(player_df, use_container_width=True)
    else:
        st.info("No player data available.")
