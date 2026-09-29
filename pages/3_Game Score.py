with tab3:
        st.subheader("🕸️ Pelaajan Game Score -komponentit vs Joukkue & SDHL")
        
        if player_col:
            pelaajat = sorted(df[player_col].dropna().unique())
            valittu_pelaaja_tutka = st.selectbox("Valitse pelaaja tutkavertailuun:", pelaajat, key='radar_player')
            
            # Määritellään Game Score -komponentit, joilla on sama mittaluokka / rooli pisteytyksessä
            # Lasketaan komponentit suoraan kaavan osatekijöistä
            def laske_komponentit(subset):
                g = get_col(subset, col_goals)
                a1 = get_col(subset, col_a1)
                a2 = get_col(subset, col_a2)
                sog = get_col(subset, col_sog)
                blk = get_col(subset, col_blk)
                
                return [
                    subset['Game_Score'].mean(),
                    (0.75 * g + 0.7 * a1 + 0.55 * a2).mean(), # Tehopisteiden painotettu vaikutus
                    (0.075 * sog).mean(),                     # Laukaukset
                    (0.05 * blk).mean(),                      # Blokit
                    (0.05 * get_col(subset, col_xg_on)).mean() # xG-vaikutus
                ]

            labels_list = ['Game Score (Keskiarvo)', 'Tehopisteet (GS)', 'Laukaukset (GS)', 'Blokit (GS)', 'xG-vaikutus (GS)']

            # 1. Valittu pelaaja
            pelaaja_all = df[df[player_col] == valittu_pelaaja_tutka]
            pelaaja_means = laske_komponentit(pelaaja_all)

            # 2. Joukkue
            if team_col and not pelaaja_all.empty:
                pelaajan_tiimi = pelaaja_all[team_col].iloc[0]
                tiimi_all = df[df[team_col] == pelaajan_tiimi]
                tiimi_means = laske_komponentit(tiimi_all)
                tiimi_label = f"Joukkueen ({pelaajan_tiimi}) keskiarvo"
            else:
                tiimi_means = [0] * len(labels_list)
                tiimi_label = "Joukkueen keskiarvo"

            # 3. SDHL Keskiarvo
            sdhl_means = laske_komponentit(df)

            # Piirretään Plotly-tutkakaavio
            fig_radar = go.Figure()

            fig_radar.add_trace(go.Scatterpolar(
                r=pelaaja_means + [pelaaja_means[0]],
                theta=labels_list + [labels_list[0]],
                fill='toself',
                name=valittu_pelaaja_tutka,
                line_color='cyan'
            ))

            if team_col:
                fig_radar.add_trace(go.Scatterpolar(
                    r=tiimi_means + [tiimi_means[0]],
                    theta=labels_list + [labels_list[0]],
                    fill='toself',
                    name=tiimi_label,
                    line_color='orange'
                ))

            fig_radar.add_trace(go.Scatterpolar(
                r=sdhl_means + [sdhl_means[0]],
                theta=labels_list + [labels_list[0]],
                fill='toself',
                name='SDHL Keskiarvo',
                line_color='gray',
                opacity=0.5
            ))

            fig_radar.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True)
                ),
                title=f"Game Score -profiili: {valittu_pelaaja_tutka} vs Joukkue & SDHL",
                showlegend=True
            )

            st.plotly_chart(fig_radar, use_container_width=True)
