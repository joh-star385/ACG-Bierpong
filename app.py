import streamlit as st
import pandas as pd

# 1. Seiten-Design
st.set_page_config(page_title="Bierpong Live-App", page_icon="🍺", layout="wide")

# 2. Session State initialisieren
if 't_name' not in st.session_state: 
    st.session_state.t_name = "Bierpong Meisterschaft"
if 'players' not in st.session_state: 
    st.session_state.players = ['Spieler 1', 'Spieler 2', 'Spieler 3', 'Spieler 4', 'Spieler 5']

if 'matches' not in st.session_state:
    # 15 Spiele Logik
    games_logic = [
        [0, 1, 2, 3], [1, 2, 3, 4], [2, 3, 4, 0], [3, 4, 0, 1], [4, 0, 1, 2],
        [0, 2, 1, 3], [1, 3, 2, 4], [2, 4, 3, 0], [3, 0, 4, 1], [4, 1, 0, 2],
        [0, 3, 1, 2], [1, 4, 2, 3], [2, 0, 3, 4], [3, 1, 4, 0], [4, 2, 0, 1]
    ]
    st.session_state.matches = [
        {"id": i, "t1_p1": g[0], "t1_p2": g[1], "t2_p1": g[2], "t2_p2": g[3], "t1_score": None, "t2_score": None}
        for i, g in enumerate(games_logic)
    ]

if 'live' not in st.session_state: 
    st.session_state.live = None

# 3. Sidebar
with st.sidebar:
    st.header("⚙️ Einstellungen")
    st.session_state.t_name = st.text_input("Turnier Name", st.session_state.t_name)
    for i in range(5):
        st.session_state.players[i] = st.text_input(f"Spieler {i+1}", value=st.session_state.players[i])

st.title(f"👑 {st.session_state.t_name}")

# 4. Hilfsfunktionen
def save_step():
    st.session_state.live['history'].append({
        't1_cups': st.session_state.live['t1_cups'],
        't2_cups': st.session_state.live['t2_cups'],
        'nachwurf': st.session_state.live['nachwurf']
    })

def do_hit(team_hitting, amount):
    save_step()
    live = st.session_state.live
    if team_hitting == 1:
        live['t2_cups'] = max(0, live['t2_cups'] - amount)
    else:
        live['t1_cups'] = max(0, live['t1_cups'] - amount)
    
    # Nachwurf-Prüfung
    if live['t2_cups'] == 0 and live['starter'] == 1 and live['nachwurf'] is None:
        live['nachwurf'] = 2
    elif live['t1_cups'] == 0 and live['starter'] == 2 and live['nachwurf'] is None:
        live['nachwurf'] = 1

# 5. Tabs
tab1, tab2 = st.tabs(["🎮 Live Spiel", "📅 Spielplan"])

with tab1:
    if st.session_state.live is None:
        st.subheader("Neues Spiel starten")
        open_matches = [m for m in st.session_state.matches if m['t1_score'] is None]
        
        if not open_matches:
            st.success("Alle Spiele beendet!")
        else:
            match_opts = {m['id']: f"Spiel {m['id']+1}: {st.session_state.players[m['t1_p1']]} & {st.session_state.players[m['t1_p2']]} vs {st.session_state.players[m['t2_p1']]} & {st.session_state.players[m['t2_p2']]}" for m in open_matches}
            sel_id = st.selectbox("Wähle das Spiel:", options=list(match_opts.keys()), format_func=lambda x: match_opts[x])
            
            if st.button("▶️ Spiel starten", use_container_width=True):
                st.session_state.live = {
                    'match_id': sel_id, 'starter': None, 't1_cups': 10, 't2_cups': 10, 'nachwurf': None, 'history': []
                }
                st.rerun()
    else:
        live = st.session_state.live
        m = st.session_state.matches[live['match_id']]
        names = st.session_state.players
        p1, p2, p3, p4 = names[m['t1_p1']], names[m['t1_p2']], names[m['t2_p1']], names[m['t2_p2']]

        if live['starter'] is None:
            st.info("Wer fängt an? (Gewinner Schere-Stein-Papier)")
            cA, cB = st.columns(2)
            if cA.button(f"{p1} & {p2}", use_container_width=True): live['starter'] = 1; st.rerun()
            if cB.button(f"{p3} & {p4}", use_container_width=True): live['starter'] = 2; st.rerun()
        else:
            # LIVE ANZEIGE
            if live['nachwurf']:
                st.warning(f"🚨 NACHWURF FÜR TEAM {live['nachwurf']}!")

            # Hier ist die neue, sichtbare Becher-Anzeige
            st.write("---")
            disp1, disp_vs, disp2 = st.columns([2, 1, 2])
            
            with disp1:
                st.markdown(f"<div style='text-align: center;'><span style='font-size: 80px; font-weight: bold;'>{live['t1_cups']}</span><br><span style='font-size: 20px;'>Becher übrig</span></div>", unsafe_allow_html=True)
                st.markdown(f"<h3 style='text-align: center;'>{p1} & {p2}</h3>", unsafe_allow_html=True)
            
            with disp_vs:
                st.markdown("<h1 style='text-align: center; margin-top: 30px;'>VS</h1>", unsafe_allow_html=True)
                
            with disp2:
                st.markdown(f"<div style='text-align: center;'><span style='font-size: 80px; font-weight: bold;'>{live['t2_cups']}</span><br><span style='font-size: 20px;'>Becher übrig</span></div>", unsafe_allow_html=True)
                st.markdown(f"<h3 style='text-align: center;'>{p3} & {p4}</h3>", unsafe_allow_html=True)

            st.write("---")

            # Treffer-Buttons
            colL, colR = st.columns(2)
            with colL:
                st.write(f"**Team 1 trifft:**")
                b1, b2 = st.columns(2)
                if b1.button(f"🎯 {p1}", use_container_width=True): do_hit(1, 1); st.rerun()
                if b2.button(f"🎯 {p2}", use_container_width=True): do_hit(1, 1); st.rerun()
                if st.button("✌️ Doppeltreffer (-2)", key="dt1", use_container_width=True): do_hit(1, 2); st.rerun()
                if st.button("💣 Bombe (-3)", key="bb1", use_container_width=True): do_hit(1, 3); st.rerun()

            with colR:
                st.write(f"**Team 2 trifft:**")
                b3, b4 = st.columns(2)
                if b3.button(f"🎯 {p3}", use_container_width=True): do_hit(2, 1); st.rerun()
                if b4.button(f"🎯 {p4}", use_container_width=True): do_hit(2, 1); st.rerun()
                if st.button("✌️ Doppeltreffer (-2)", key="dt2", use_container_width=True): do_hit(2, 2); st.rerun()
                if st.button("💣 Bombe (-3)", key="bb2", use_container_width=True): do_hit(2, 3); st.rerun()

            # Ende & Undo
            st.write("---")
            u_col, a_col, s_col = st.columns(3)
            with u_col:
                if st.button("↩️ Undo", use_container_width=True, disabled=not live['history']):
                    last = live['history'].pop()
                    live['t1_cups'], live['t2_cups'], live['nachwurf'] = last['t1_cups'], last['t2_cups'], last['nachwurf']
                    st.rerun()
            with a_col:
                if st.button("❌ Abbruch", use_container_width=True): st.session_state.live = None; st.rerun()
            with s_col:
                if (live['t1_cups'] == 0 or live['t2_cups'] == 0) and not (live['t1_cups'] == 0 and live['t2_cups'] == 0):
                    if st.button("💾 Speichern", use_container_width=True, type="primary"):
                        st.session_state.matches[live['match_id']]['t1_score'] = 10 - live['t2_cups']
                        st.session_state.matches[live['match_id']]['t2_score'] = 10 - live['t1_cups']
                        st.session_state.live = None
                        st.rerun()
                elif live['t1_cups'] == 0 and live['t2_cups'] == 0:
                    st.success("Unentschieden -> Verlängerung!")
                    if st.button("🔄 Verlängerung starten", use_container_width=True):
                        # Reset auf z.B. 2 Becher oder letzte Züge undo
                        live['t1_cups'], live['t2_cups'], live['nachwurf'] = 1, 1, None # Beispiel für schnelles Ende
                        st.rerun()

with tab2:
    st.subheader("Spielplan Übersicht")
    for m in st.session_state.matches:
        txt = f"Spiel {m['id']+1}: {st.session_state.players[m['t1_p1']]} & {st.session_state.players[m['t1_p2']]} vs {st.session_state.players[m['t2_p1']]} & {st.session_state.players[m['t2_p2']]}"
        if m['t1_score'] is not None:
            st.success(f"{txt} | Ergebnis: {m['t1_score']}:{m['t2_score']}")
        elif st.session_state.live and st.session_state.live['match_id'] == m['id']:
            st.warning(f"{txt} | 🔴 LÄUFT GERADE")
        else:
            st.write(txt)
