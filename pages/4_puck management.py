import streamlit as st
import pandas as pd
import plotly.express as px

# Sivun asetukset
st.set_page_config(page_title="Puck Management & Transitions", page_icon="🏒", layout="wide")

st.title("🏒 Puck Management & Transitions - Visuaalinen Analytiikka")
st.caption("Puhtaat kiekonhallinta-, riistot-, menetys- ja siirtymätilastot graafeina ja taulukoina.")

EXCEL_FILE = "Sdhl Game score 2026-2027.xlsx"

@st.cache_data
def load_puck_data(file_path):
    try:
        df = pd.read_excel(file_path, sheet_name='Puck management')
        df.columns = [str(col).strip() for col in df.columns]
        return df
    except Exception as e:
        try:
            df = pd.read_excel(f"../{file_path}", sheet_name='Puck management')
            df.columns = [str(col).strip() for col in df.columns]
            return df
        except Exception as e2:
            st.error(f"Virhe ladattaessa Puck management -välilehteä: {e2}")
            return None

df_puck = load_puck_data(EXCEL_FILE)

if df_puck is not None:
    def get_col(data, col_name):
        if col_name and col_name in data.columns:
            s = data[col_name].replace(['-', '—', ''], 0)
            return pd.to_numeric(s, errors='coerce').fillna(0)
        return pd.Series(0, index=data.index)

    # Tunnistetaan sarakkeet
    player_col = next((c for c in df_puck.columns if 'player' in c.lower()), 'Player')
    team_col = next((c for c in df_puck.columns if 'team' in c.lower()), 'Team')
    pos_col = next((c for c in df_puck.columns if 'position' in c.lower()), 'Position')

    df_puck['Player_clean'] = df_puck[player_col] if player_col in df_puck.columns else 'Unknown'
    df_puck['Team_clean'] = df_puck[team_col] if team_col in df_puck.columns else 'Unknown'
    df_puck['Pos_clean'] = df_puck[pos_col].astype(str).str.upper().str.strip() if pos_col in df_puck.columns else 'F'

    # --- SIVUPALKIN SUODATTIMET ---
    st.sidebar.header("🔍 Suodattimet")
    
    if team_col in df_puck.columns:
        all_teams = sorted(df_puck['Team_clean'].dropna().unique())
        selected_teams = st.sidebar.multiselect("Valitse joukkue(et):", all_teams, default=all_teams)
        df_filtered = df_puck[df_puck['Team_clean'].isin(selected_teams)].copy()
    else:
        df_filtered = df_puck.copy()

    selected_positions = st.sidebar.multiselect("Valitse pelipaikka:", ['F', 'D'], default=['F', 'D'])
    if pos_col in df_puck.columns:
        df_filtered = df_filtered[df_filtered['Pos_clean'].isin(selected_positions)]

    # --- VÄLILEHDET ---
    tab_team, tab_player = st.tabs(["🛡️ Joukkueiden Graafit & Yhteenveto", "👥 Pelaajien Tilastot"])

    with tab_team:
        st.subheader("🛡️ Joukkuekohtainen visuaalinen vertailu")
        st.caption("Vertaa joukkueiden pelityylejä, kiekonriistoja, menetyksiä ja sisäänvientejä.")

        if team_col in df_filtered.columns:
            exclude_words = ['shirt', 'shift', 'ice', 'time', 'gp']
            stat_cols = [c for c in df_filtered.columns if c not in [player_col, team_col, pos_col, 'Player_clean', 'Team_clean', 'Pos_clean'] 
                         and not any(w in c.lower() for w in exclude_words)]

            for col in stat_cols:
                df_filtered[col] = get_col(df_filtered, col)

            # Ryhmitellään joukkueittain
            team_agg = df_filtered.groupby('Team_clean')[stat_cols].sum().reset_index()
            team_agg = team_agg.rename(columns={'Team_clean': 'Team'})

            # Lasketaan nettorvo riistot - menetykset
            if 'Takeaways' in team_agg.columns and 'Puck losses' in team_agg.columns:
                team_agg['Net Takeaways'] = team_agg['Takeaways'] - team_agg['Puck losses']

            # --- GRAAFIT JOUKKUEILLE ---
            col_g1, col_g2 = st.columns(2)

            with col_g1:
                if 'Takeaways' in team_agg.columns and 'Puck losses' in team_agg.columns:
                    st.markdown("### 📊 Joukkueet: Riistot vs Menetykset")
                    fig_tka = px.bar(
                        team_agg.sort_values(by='Takeaways', ascending=True),
                        y='Team', x=['Takeaways', 'Puck losses'],
                        barmode='group',
                        orientation='h',
                        title="Riistot ja menetykset joukkueittain",
                        labels={'value': 'Määrä', 'variable': 'Metriikka', 'Team': 'Joukkue'}
                    )
                    fig_tka.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_tka, use_container_width=True)

            with col_g2:
                if 'Net Takeaways' in team_agg.columns:
                    st.markdown("### ⚖️ Joukkueet: Netto-riistot (Riistot - Menetykset)")
                    fig_net = px.bar(
                        team_agg.sort_values(by='Net Takeaways', ascending=True),
                        y='Team', x='Net Takeaways',
                        orientation='h',
                        title="Kiekonhallinnan netto (Positiivinen = enemmän riistoja kuin menetyksiä)",
                        color='Net Takeaways', color_continuous_scale='Teal'
                    )
                    fig_net.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', showlegend=False)
                    st.plotly_chart(fig_net, use_container_width=True)

            # Sisäänvientien tyylit joukkueittain (stacked bar)
            ent_pass_col = next((c for c in team_agg.columns if 'entries via pass' in c.lower()), None)
            ent_dump_col = next((c for c in team_agg.columns if 'entries via dump in' in c.lower()), None)
            ent_stick_col = next((c for c in team_agg.columns if 'entries via stickhandling' in c.lower()), None)

            if ent_pass_col and ent_dump_col and ent_stick_col:
                st.markdown("### 🏒 Joukkueiden hyökkäysalueelle tuonnin tyylit")
                fig_entries = px.bar(
                    team_agg.sort_values(by='Entries', ascending=True) if 'Entries' in team_agg.columns else team_agg,
                    y='Team', x=[ent_pass_col, ent_dump_col, ent_stick_col],
                    barmode='stack',
                    orientation='h',
                    title="Sisäänvientien jakauma (Syöttö, Roikkukiekko, Kuljetus)",
                    labels={'value': 'Määrä', 'variable': 'Sisäänvientityyli', 'Team': 'Joukkue'}
                )
                fig_entries.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_entries, use_container_width=True)

            st.markdown("---")
            st.subheader("📋 Joukkueiden raakatilastot taulukkona")
            st.dataframe(team_agg, use_container_width=True, hide_index=True)
        else:
            st.warning("Joukesaraketta ei löytynyt.")

    with tab_player:
        st.subheader("👥 Pelaajakohtaiset graafit")
        
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.markdown("### 📊 Top 10: Riistot pelaajittain")
            if 'Takeaways' in df_filtered.columns:
                df_filtered['Takeaways_num'] = get_col(df_filtered, 'Takeaways')
                top_tka = df_filtered.sort_values(by='Takeaways_num', ascending=True).tail(10)
                fig_ptka = px.bar(top_tka, y='Player_clean', x='Takeaways_num', color='Team_clean', orientation='h', title="Eniten riistoja keränneet pelaajat")
                fig_ptka.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_ptka, use_container_width=True)

        with col_p2:
            st.markdown("### 🎯 Top 10: Laukauksen jälkeiset haut")
            ret_col = next((c for c in df_filtered.columns if 'retrievals after shots' in c.lower()), None)
            if ret_col:
                df_filtered['Ret_num'] = get_col(df_filtered, ret_col)
                top_ret = df_filtered.sort_values(by='Ret_num', ascending=True).tail(10)
                fig_pret = px.bar(top_ret, y='Player_clean', x='Ret_num', color='Team_clean', orientation='h', title="Eniten laukauksen jälkeisiä irtokiekon hakuja")
                fig_pret.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_pret, use_container_width=True)

        st.markdown("---")
        st.subheader("📋 Pelaajataulukko")
        display_cols = [c for c in df_filtered.columns if c not in ['Player_clean', 'Team_clean', 'Pos_clean'] and not any(w in c.lower() for w in ['time on ice', 'all shifts', 'shirt number'])]
        st.dataframe(df_filtered[['Player_clean', 'Team_clean', 'Pos_clean'] + [c for c in display_cols if c not in [player_col, team_col, pos_col]]], use_container_width=True, hide_index=True)

else:
    st.warning("Puck management -välilehden lataaminen epäonnistui.")
