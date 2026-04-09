import streamlit as st
import pandas as pd
import copy

# 1. Seiten-Design
st.set_page_config(page_title="Bierpong App", page_icon="🍺", layout="wide")

# 2. Session State (Speicher) initialisieren
if 't_name' not in st.session_state: 
    st.session_state.t_name = "Unser Bierpong Turnier"
if 'players' not in st.session_state: 
    st.session_state.players = ['Spieler 1', 'Spieler 2', 'Spieler 3', 'Spieler 4', 'Spieler 5']

if 'matches' not in st.session_state:
    games_logic = [
        [0, 1, 2, 3], [1, 2, 3, 4], [2, 3, 4, 0], [3, 4, 0, 1], [4, 0, 1, 2],
        [0, 2, 1, 3], [1, 3, 2, 4], [2, 4, 3, 0], [3, 0, 4, 1], [4, 1, 0, 2],
        [0, 3, 1, 2], [1, 4, 2, 3], [2, 0, 3, 4], [3, 1, 4, 0], [4, 2, 0, 1]
    ]
    st.session_state.matches = [
        {"id": i, "t1_p1": g[0], "t1_p2": g[1], "t2_p1": g[2], "t2_p2": g[3], "t1_score": None, "t2_score": None}
        for i, g in enumerate(games_logic)
    ]

# Speicher für das aktuell laufende Live-Spiel
if 'live' not in st.session_state: 
    st.session_state.live = None

# 3. Sidebar (Einstellungen)
with st.sidebar:
    st.header("⚙️ Turnier Einstellungen")
    st.session_state.t_name = st.text_input("Turnier Name", st.session_state.t_name)
    st.write("---")
    st.write("Spieler eintragen:")
    for i in range(5):
        st.session_state.players[i] = st.text_input(f"Slot {i+1}", value=st.session_state.players[i])

st.title(f"👑 {st.session_state.t_name}")

# 4. Tabs
tab1, tab2 = st.tabs(["🎮 Live Spiel", "📅 Spielplan"])

# --- HILFSFUNKTIONEN FÜR DAS LIVE SPIEL ---
def save_history():
    st.session_state.live['history'].append({
        't1_cups': st.session_state.live['t1_cups'],
        't2_cups': st.session_state.live['t2_cups'],
        'nachwurf': st.session_state.live['nachwurf']
    })

def undo():
    if len(st.session_state.live['history']) > 0:
        last_state = st.session_state.live['history'].pop()
        st.session_state.live['t1_cups'] = last_state['t1_cups']
        st.session_state.live['t2_cups'] = last_state['t2_cups']
        st.session_state.live['nachwurf'] = last_state['nachwurf']

def hit(team, amount):
    save_history()
    if team == 1:
        st.session_state.live['t2_cups'] = max(0, st.session_state.live['t2_cups'] - amount)
    else:
        st.session_state.live['t1_cups'] = max(0, st.session_state.live['t1_cups'] - amount)
    
    # Nachwurf Logik prüfen
    live = st.session_state.live
    if live['t2_cups'] == 0 and live['starter'] == 1 and live['nachwurf'] is None:
        live['nachwurf'] = 2
    elif live['t1_cups'] == 0 and live['starter'] == 2 and live['nachwurf'] is None:
        live['nachwurf'] = 1

# --- TAB 1: LIVE SPIEL ---
with tab1:
    if st.session_state.live is None:
        st.subheader("Neues Spiel starten")
        # Finde das nächste offene Spiel
        open_matches = [m for m in st.session_state.matches if m['t1_score'] is None]
        
        if not open_matches:
            st.success("🎉 Alle Spiele sind absolviert! Das Turnier ist beendet.")
        else:
            match_opts = {}
            for m in open_matches:
                p1, p2 = st.session_state.players[m['t1_p1']], st.session_state.players[m['t1_p2']]
                p3, p4 = st.session_state.players[m['t2_p1']], st.session_state.players[m['t2_p2']]
                match_opts[m['id']] = f"Spiel {m['id']+1}: {p1} & {p2}  VS  {p3} & {p4}"
            
            selected_match_id = st.selectbox("Wähle ein Spiel:", options=list(match_opts.keys()), format_func=lambda x: match_opts[x])
            
            if st.button("▶️ Spiel vorbereiten", use_container_width=True):
                st.session_state.live = {
                    'match_id': selected_match_id,
                    'starter': None,
                    't1_cups': 10,
                    't2_cups': 10,
                    'nachwurf': None,
                    'history': []
                }
                st.rerun()

    else:
        # Ein Spiel ist aktiv
        live = st.session_state.live
        m = st.session_state.matches[live['match_id']]
        p1, p2 = st.session_state.players[m['t1_p1']], st.session_state.players[m['t1_p2']]
        p3, p4 = st.session_state.players[m['t2_p1']], st.session_state.players[m['t2_p2']]

        st.subheader(f"🔴 LIVE: Spiel {m['id']+1}")

        # Schritt 1: Wer fängt an?
        if live['starter'] is None:
            st.write("### 🪨✂️📄 Schere-Stein-Papier!")
            st.write("Welches Team hat gewonnen und fängt an?")
            colA, colB = st.columns(2)
            if colA.button(f"Team 1 fängt an\n({p1} & {p2})", use_container_width=True):
                st.session_state.live['starter'] = 1
                st.rerun()
            if colB.button(f"Team 2 fängt an\n({p3} & {p4})", use_container_width=True):
                st.session_state.live['starter'] = 2
                st.rerun()
            
            st.write("---")
            if st.button("❌ Spiel abbrechen"):
                st.session_state.live = None
                st.rerun()

        # Schritt 2: Das eigentliche Spiel
        else:
            # Nachwurf Anzeige
            if live['nachwurf'] == 1:
                st.error(f"🚨 NACHWURF FÜR TEAM 1 ({p1} & {p2})!")
            elif live['nachwurf'] == 2:
                st.error(f"🚨 NACHWURF FÜR TEAM 2 ({p3} & {p4})!")

            # Punkteanzeige
            c1, c2, c3 = st.columns([2, 1, 2])
            with c1:
                st.markdown(f"<h1 style='text-align: center; color: {'#9C0006' if live['t1_cups']==0 else 'white'};'>{live['t1_cups']} Becher</h1>", unsafe_allow_html=True)
                st.markdown(f"<h3 style='text-align: center;'>{p1} & {p2}</h3>", unsafe_allow_html=True)
            with c2:
                st.markdown("<h1 style='text-align: center;'>:</h1>", unsafe_allow_html=True)
            with c3:
                st.markdown(f"<h1 style='text-align: center; color: {'#9C0006' if live['t2_cups']==0 else 'white'};'>{live['t2_cups']} Becher</h1>", unsafe_allow_html=True)
                st.markdown(f"<h3 style='text-align: center;'>{p3} & {p4}</h3>", unsafe_allow_html=True)

            st.write("---")

            # Verlängerungs-Check (beide auf 0)
            if live['t1_cups'] == 0 and live['t2_cups'] == 0:
                st.success("🔥 VERLÄNGERUNG! Beide Teams haben alle Becher getroffen.")
                if st.button("🔄 Letzte 2 Würfe zurücksetzen (Verlängerung starten)", use_container_width=True):
                    undo()
                    undo()
                    st.session_state.live['nachwurf'] = None
                    st.rerun()
            else:
                # Steuerung (Buttons)
                col_t1, col_t2 = st.columns(2)
                
                # TEAM 1 STEUERUNG
                with col_t1:
                    st.write("**Einzeltreffer:**")
                    r1c1, r1c2 = st.columns(2)
                    if r1c1.button(f"🎯 {p1} trifft", use_container_width=True, disabled=live['t2_cups']==0): hit(1, 1); st.rerun()
                    if r1c2.button(f"🎯 {p2} trifft", use_container_width=True, disabled=live['t2_cups']==0): hit(1, 1); st.rerun()
                    
                    st.write("**Sonderregeln:**")
                    if st.button("✌️ Doppeltreffer (-2 Becher)", key="d1", use_container_width=True, disabled=live['t2_cups']==0): hit(1, 2); st.rerun()
                    if st.button("💣 Dreifachtreffer / Bombe (-3 Becher)", key="b1", use_container_width=True, disabled=live['t2_cups']==0): hit(1, 3); st.rerun()

                # TEAM 2 STEUERUNG
                with col_t2:
                    st.write("**Einzeltreffer:**")
                    r2c1, r2c2 = st.columns(2)
                    if r2c1.button(f"🎯 {p3} trifft", use_container_width=True, disabled=live['t1_cups']==0): hit(2, 1); st.rerun()
                    if r2c2.button(f"🎯 {p4} trifft", use_container_width=True, disabled=live['t1_cups']==0): hit(2, 1); st.rerun()
                    
                    st.write("**Sonderregeln:**")
                    if st.button("✌️ Doppeltreffer (-2 Becher)", key="d2", use_container_width=True, disabled=live['t1_cups']==0): hit(2, 2); st.rerun()
                    if st.button("💣 Dreifachtreffer / Bombe (-3 Becher)", key="b2", use_container_width=True, disabled=live['t1_cups']==0): hit(2, 3); st.rerun()

            st.write("---")
            # Kontroll-Leiste unten
            ctrl1, ctrl2, ctrl3 = st.columns(3)
            with ctrl1:
                if st.button("↩️ Undo (Wurf zurücknehmen)", use_container_width=True, disabled=len(live['history'])==0):
                    undo()
                    st.rerun()
            with ctrl2:
                if st.button("❌ Spiel abbrechen", use_container_width=True):
                    st.session_state.live = None
                    st.rerun()
            with ctrl3:
                # Spiel speichern ist nur möglich, wenn jemand auf 0 ist und es KEINE Verlängerung gibt
                can_save = (live['t1_cups'] == 0 or live['t2_cups'] == 0) and not (live['t1_cups'] == 0 and live['t2_cups'] == 0)
                if st.button("💾 Ergebnis Speichern", use_container_width=True, type="primary", disabled=not can_save):
                    # In die Match-Tabelle schreiben (10 - restliche Becher des Gegners)
                    st.session_state.matches[live['match_id']]['t1_score'] = 10 - live['t2_cups']
                    st.session_state.matches[live['match_id']]['t2_score'] = 10 - live['t1_cups']
                    st.session_state.live = None
                    st.rerun()


# --- TAB 2: SPIELPLAN ÜBERSICHT ---
with tab2:
    st.subheader("📅 Alle Spiele im Überblick")
    
    # Finde das aktuelle / nächste Spiel für die farbliche Hervorhebung
    next_game_id = None
    for m in st.session_state.matches:
        if m['t1_score'] is None:
            next_game_id = m['id']
            break

    for m in st.session_state.matches:
        p1, p2 = st.session_state.players[m['t1_p1']], st.session_state.players[m['t1_p2']]
        p3, p4 = st.session_state.players[m['t2_p1']], st.session_state.players[m['t2_p2']]
        
        # Farbliche Hervorhebung
        if m['id'] == next_game_id and st.session_state.live is None:
            st.info(f"**👉 NÄCHSTES SPIEL: Spiel {m['id']+1} | {p1} & {p2} VS {p3} & {p4}**")
        elif st.session_state.live is not None and st.session_state.live['match_id'] == m['id']:
            st.warning(f"**🔴 LÄUFT GERADE: Spiel {m['id']+1} | {p1} & {p2} VS {p3} & {p4}**")
        else:
            if m['t1_score'] is not None:
                st.success(f"✔️ Spiel {m['id']+1}: {p1} & {p2} **({m['t1_score']} : {m['t2_score']})** {p3} & {p4}")
            else:
                st.write(f"⚪ Spiel {m['id']+1}: {p1} & {p2}  vs  {p3} & {p4}")
