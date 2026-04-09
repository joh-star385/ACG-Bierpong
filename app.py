import streamlit as st
import pandas as pd

# 1. Seiten-Design einstellen
st.set_page_config(page_title="Bierpong Meister-Turnier", page_icon="🍺", layout="wide")
st.title("👑 Bierpong Meister-Turnier")

# 2. Speicher der App initialisieren
if 'players' not in st.session_state:
    st.session_state.players = ['Spieler 1', 'Spieler 2', 'Spieler 3', 'Spieler 4', 'Spieler 5']

if 'matches' not in st.session_state:
    games_logic = [
        [0, 1, 2, 3], [1, 2, 3, 4], [2, 3, 4, 0], [3, 4, 0, 1], [4, 0, 1, 2],
        [0, 2, 1, 3], [1, 3, 2, 4], [2, 4, 3, 0], [3, 0, 4, 1], [4, 1, 0, 2],
        [0, 3, 1, 2], [1, 4, 2, 3], [2, 0, 3, 4], [3, 1, 4, 0], [4, 2, 0, 1]
    ]
    st.session_state.matches = [
        {"Spiel": i + 1, "T1_P1": g[0], "T1_P2": g[1], "T2_P1": g[2], "T2_P2": g[3], "Tore_T1": None, "Tore_T2": None}
        for i, g in enumerate(games_logic)
    ]

# 3. Sidebar für Spielernamen
with st.sidebar:
    st.header("⚙️ Einstellungen")
    st.write("Namen ändern:")
    for i in range(5):
        st.session_state.players[i] = st.text_input(f"Slot {i+1}", value=st.session_state.players[i])

tab1, tab2 = st.tabs(["📝 Spielplan & Eingabe", "🏆 Tabelle & Statistiken"])

# --- TAB 1: SPIELPLAN ---
with tab1:
    st.subheader("Spielplan")
    st.write("Trage die getroffenen Becher ein (max. 10).")
    
    col_left, col_right = st.columns([1, 1])
    
    for i, match in enumerate(st.session_state.matches):
        p1, p2 = st.session_state.players[match["T1_P1"]], st.session_state.players[match["T1_P2"]]
        p3, p4 = st.session_state.players[match["T2_P1"]], st.session_state.players[match["T2_P2"]]
        
        # Layout aufteilen (Links Spiel 1-8, Rechts 9-15)
        target_col = col_left if i < 8 else col_right
        
        with target_col:
            st.markdown(f"**Spiel {match['Spiel']}**")
            c1, c2, c3, c4, c5 = st.columns([3, 1.5, 0.5, 1.5, 3])
            with c1: st.write(f"{p1} & {p2}")
            with c2: t1_in = st.number_input("T1", min_value=0, max_value=10, key=f"t1_{i}", value=match["Tore_T1"], label_visibility="collapsed")
            with c3: st.write(":")
            with c4: t2_in = st.number_input("T2", min_value=0, max_value=10, key=f"t2_{i}", value=match["Tore_T2"], label_visibility="collapsed")
            with c5: st.write(f"{p3} & {p4}")
            st.divider()
            
            st.session_state.matches[i]["Tore_T1"] = t1_in
            st.session_state.matches[i]["Tore_T2"] = t2_in

# --- TAB 2: ENGINE & STATISTIKEN ---
with tab2:
    players = st.session_state.players
    matches = st.session_state.matches
    
    # 1. Basis-Statistiken berechnen
    player_stats = []
    for i, p in enumerate(players):
        sp = s = n = diff = 0
        streak_val = 0
        for m in matches:
            t1_g, t2_g = m['Tore_T1'], m['Tore_T2']
            if t1_g is not None and t2_g is not None:
                if i in [m['T1_P1'], m['T1_P2']]:
                    sp += 1
                    if t1_g > t2_g:
                        s += 1; diff += (t1_g - t2_g)
                        streak_val = streak_val + 1 if streak_val > 0 else 1
                    else:
                        n += 1; diff += (t1_g - t2_g)
                        streak_val = streak_val - 1 if streak_val < 0 else -1
                elif i in [m['T2_P1'], m['T2_P2']]:
                    sp += 1
                    if t2_g > t1_g:
                        s += 1; diff += (t2_g - t1_g)
                        streak_val = streak_val + 1 if streak_val > 0 else 1
                    else:
                        n += 1; diff += (t2_g - t1_g)
                        streak_val = streak_val - 1 if streak_val < 0 else -1

        rest = 12 - sp
        score = s * 10000 + diff
        s_pct = f"{int((s/sp)*100)}%" if sp > 0 else "0%"
        
        streak_text = "-"
        streak_emoji = ""
        if streak_val > 0:
            streak_text = f"{streak_val}S"
            if streak_val >= 3: streak_emoji = "🔥"
        elif streak_val < 0:
            streak_text = f"{abs(streak_val)}N"
            if streak_val <= -3: streak_emoji = "💀"

        player_stats.append({
            'id': i, 'NAME': p, 'SP': sp, 'S': s, 'N': n, 'DIFF': diff,
            'S%': s_pct, 'SERIE': streak_text, ' ': streak_emoji,
            'Rest': rest, 'Score': score
        })

    # 2. Elbo-Fix (Status Berechnung)
    total_played = sum(1 for m in matches if m['Tore_T1'] is not None and m['Tore_T2'] is not None)
    is_finished = total_played == 15
    max_current_score = max(ps['Score'] for ps in player_stats) if player_stats else 0

    for ps in player_stats:
        max_potential_score = ps['Score'] + ps['Rest'] * 10010
        min_opp_scores = []
        for opp in player_stats:
            if ps['id'] == opp['id']: continue
            
            open_together = 0
            for m in matches:
                if m['Tore_T1'] is None:
                    team1, team2 = [m['T1_P1'], m['T1_P2']], [m['T2_P1'], m['T2_P2']]
                    if (ps['id'] in team1 and opp['id'] in team1) or (ps['id'] in team2 and opp['id'] in team2):
                        open_together += 1

            guaranteed_opp_score = opp['Score'] + (open_together * 10020) - (opp['Rest'] * 10)
            min_opp_scores.append(guaranteed_opp_score)

        highest_opp_score = max(min_opp_scores) if min_opp_scores else 0

        if is_finished:
            ps['STATUS'] = "👑 MEISTER" if ps['Score'] == max_current_score else "Eliminated"
        else:
            ps['STATUS'] = "Titel drin" if max_potential_score >= highest_opp_score else "Eliminated"

    # Meister vorzeitig küren
    titel_count = sum(1 for ps in player_stats if ps['STATUS'] == "Titel drin")
    if not is_finished and titel_count == 1:
        for ps in player_stats:
            if ps['STATUS'] == "Titel drin": ps['STATUS'] = "👑 MEISTER"

    # 3. Haupttabelle anzeigen
    df_main = pd.DataFrame(player_stats)
    df_main = df_main.sort_values(by=['Score'], ascending=False).reset_index(drop=True)
    df_main.index += 1
    
    def get_medal(rank):
        if rank == 1: return "1 🏆"
        elif rank == 2: return "2 🥈"
        elif rank == 3: return "3 🥉"
        return str(rank)
    
    df_main.insert(0, 'RANG', df_main.index.map(get_medal))
    df_display = df_main[['RANG', 'NAME', 'SP', 'S', 'N', 'DIFF', 'S%', 'SERIE', ' ', 'STATUS']]

    # Styling wie in Excel
    def style_df(val):
        if val == 'Eliminated': return 'color: #9C0006; font-weight: bold'
        if val == 'Titel drin': return 'color: #008000; font-weight: bold'
        if val == '👑 MEISTER': return 'background-color: #FFD966; color: black; font-weight: bold'
        if isinstance(val, int) and val > 0: return 'color: #008000; font-weight: bold'
        if isinstance(val, int) and val < 0: return 'color: #FF0000; font-weight: bold'
        if isinstance(val, str) and 'S' in val and val != "STATUS": return 'color: #008000; font-weight: bold'
        if isinstance(val, str) and 'N' in val and val != "NAME" and val != "STATUS": return 'color: #FF0000; font-weight: bold'
        return ''

    st.subheader("Die Meister-Tabelle")
    st.dataframe(df_display.style.map(style_df), use_container_width=True, hide_index=True)

    st.divider()

    # 4. Untere Tabellen
    col_stat1, col_stat2 = st.columns(2)

    with col_stat1:
        st.subheader("Höchste Siege (Top 3)")
        match_diffs = []
        for m in matches:
            if m['Tore_T1'] is not None:
                diff = abs(m['Tore_T1'] - m['Tore_T2'])
                text = f"Spiel {m['Spiel']}: {players[m['T1_P1']]}/{players[m['T1_P2']]} vs {players[m['T2_P1']]}/{players[m['T2_P2']]} ({m['Tore_T1']}:{m['Tore_T2']})"
                match_diffs.append({'Spiel': text, 'Diff': diff})
        
        if match_diffs:
            df_top_matches = pd.DataFrame(match_diffs).sort_values(by='Diff', ascending=False).head(3)
            st.dataframe(df_top_matches[['Spiel']], hide_index=True, use_container_width=True)
        else:
            st.write("Noch keine Spiele absolviert.")

        st.subheader("Bestes Duo (Top 3)")
        pairs = [(0,1), (0,2), (0,3), (0,4), (1,2), (1,3), (1,4), (2,3), (2,4), (3,4)]
        duo_stats = []
        for p1, p2 in pairs:
            sp = s = diff = 0
            for m in matches:
                t1, t2 = m['Tore_T1'], m['Tore_T2']
                if t1 is not None:
                    team1, team2 = [m['T1_P1'], m['T1_P2']], [m['T2_P1'], m['T2_P2']]
                    if p1 in team1 and p2 in team1:
                        sp += 1
                        if t1 > t2: s += 1
                        diff += (t1 - t2)
                    elif p1 in team2 and p2 in team2:
                        sp += 1
                        if t2 > t1: s += 1
                        diff += (t2 - t1)
            duo_stats.append({'Paar': f"{players[p1]} & {players[p2]}", 'SP': sp, 'S': s, 'DIFF': diff})
        
        df_duos = pd.DataFrame(duo_stats).sort_values(by=['S', 'DIFF'], ascending=[False, False]).head(3).reset_index(drop=True)
        df_duos.index += 1
        df_duos.insert(0, 'RANG', df_duos.index)
        st.dataframe(df_duos, hide_index=True, use_container_width=True)

    with col_stat2:
        st.subheader("Offene Partner-Spiele")
        matrix = []
        for r in range(5):
            row = { "Spieler": players[r] }
            for c in range(5):
                if r == c:
                    row[players[c]] = "-"
                else:
                    open_games = 0
                    for m in matches:
                        if m['Tore_T1'] is None:
                            inv = [m['T1_P1'], m['T1_P2'], m['T2_P1'], m['T2_P2']]
                            if r in inv and c in inv: open_games += 1
                    row[players[c]] = str(open_games)
            matrix.append(row)
        
        df_matrix = pd.DataFrame(matrix)
        st.dataframe(df_matrix, hide_index=True, use_container_width=True)
