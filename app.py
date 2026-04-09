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

# 4. Hilfsfunktionen Live-Spiel
def save_step():
    # Speichert den aktuellen Stand für die Undo-Funktion
    live = st.session_state.live
    live['history'].append({
        't1_cups': live['t1_cups'], 't2_cups': live['t2_cups'],
        'nachwurf': live['nachwurf'], 'possession': live['possession'],
        'balls_back': live['balls_back'], 'pending_bomb': live.get('pending_bomb', False)
    })

def do_hit(team_hitting, amount, player_hit=None, is_balls_back=False):
    save_step()
    live = st.session_state.live
    live['balls_back'] = is_balls_back
    
    if team_hitting == 1:
        live['t2_cups'] = max(0, live['t2_cups'] - amount)
        if not is_balls_back: live['possession'] = 2
    else:
        live['t1_cups'] = max(0, live['t1_cups'] - amount)
        if not is_balls_back: live['possession'] = 1
    
    # Nachwurf-Prüfung
    if live['t2_cups'] == 0 and live['starter'] == 1 and live['nachwurf'] is None:
        live['nachwurf'] = 2
        live['possession'] = 2
    elif live['t1_cups'] == 0 and live['starter'] == 2 and live['nachwurf'] is None:
        live['nachwurf'] = 1
        live['possession'] = 1

def do_miss():
    save_step()
    live = st.session_state.live
    live['balls_back'] = False
    live['possession'] = 2 if live['possession'] == 1 else 1

def do_penalty(team):
    save_step()
    live = st.session_state.live
    if team == 1: live['t1_cups'] = max(0, live['t1_cups'] - 1)
    else: live['t2_cups'] = max(0, live['t2_cups'] - 1)

# 5. Tabs
tab1, tab2 = st.tabs(["🎮 Live Spiel", "🏆 Tabelle & Spielplan"])

with tab1:
    if st.session_state.live is None:
        st.subheader("Neues Spiel starten")
        open_matches = [m for m in st.session_state.matches if m['t1_score'] is None]
        
        if not open_matches:
            st.success("🎉 Alle Spiele beendet!")
        else:
            match_opts = {m['id']: f"Spiel {m['id']+1}: {st.session_state.players[m['t1_p1']]} & {st.session_state.players[m['t1_p2']]} vs {st.session_state.players[m['t2_p1']]} & {st.session_state.players[m['t2_p2']]}" for m in open_matches}
            sel_id = st.selectbox("Wähle das Spiel:", options=list(match_opts.keys()), format_func=lambda x: match_opts[x])
            
            if st.button("▶️ Spiel starten", use_container_width=True):
                st.session_state.live = {
                    'match_id': sel_id, 'starter': None, 'possession': None,
                    't1_cups': 10, 't2_cups': 10, 'nachwurf': None, 
                    'balls_back': False, 'pending_bomb': False, 'bomb_team': None,
                    'history': []
                }
                st.rerun()
    else:
        live = st.session_state.live
        m = st.session_state.matches[live['match_id']]
        names = st.session_state.players
        p1, p2, p3, p4 = names[m['t1_p1']], names[m['t1_p2']], names[m['t2_p1']], names[m['t2_p2']]

        if live['starter'] is None:
            st.info("🪨✂️📄 Wer fängt an? (Gewinner Schere-Stein-Papier)")
            cA, cB = st.columns(2)
            if cA.button(f"{p1} & {p2}", use_container_width=True): 
                live['starter'] = 1; live['possession'] = 1; st.rerun()
            if cB.button(f"{p3} & {p4}", use_container_width=True): 
                live['starter'] = 2; live['possession'] = 2; st.rerun()
            st.button("❌ Spiel abbrechen", on_click=lambda: st.session_state.update(live=None))
        
        else:
            # --- LIVE ANZEIGE ---
            if live['nachwurf']:
                st.error(f"🚨 NACHWURF FÜR TEAM {live['nachwurf']}!")
            elif live['balls_back']:
                st.success("🔥 BALLS BACK! Team darf nochmal werfen.")

            st.write("---")
            disp1, disp_vs, disp2 = st.columns([2, 1, 2])
            
            with disp1:
                st.markdown(f"<div style='text-align: center;'><span style='font-size: 80px; font-weight: bold; color: {'#9C0006' if live['t1_cups']==0 else 'white'};'>{live['t1_cups']}</span><br><span style='font-size: 20px;'>Becher</span></div>", unsafe_allow_html=True)
                st.markdown(f"<h3 style='text-align: center;'>{p1} & {p2}</h3>", unsafe_allow_html=True)
                if live['possession'] == 1 and not live['pending_bomb']: st.info("🟢 BALLBESITZ")
            
            with disp_vs:
                st.markdown("<h1 style='text-align: center; margin-top: 30px;'>VS</h1>", unsafe_allow_html=True)
                
            with disp2:
                st.markdown(f"<div style='text-align: center;'><span style='font-size: 80px; font-weight: bold; color: {'#9C0006' if live['t2_cups']==0 else 'white'};'>{live['t2_cups']}</span><br><span style='font-size: 20px;'>Becher</span></div>", unsafe_allow_html=True)
                st.markdown(f"<h3 style='text-align: center;'>{p3} & {p4}</h3>", unsafe_allow_html=True)
                if live['possession'] == 2 and not live['pending_bomb']: st.info("🟢 BALLBESITZ")

            st.write("---")

            # --- STEUERUNG ---
            # Wenn eine Bombe geworfen wurde, frage wer den 2. Ball versenkt hat
            if live.get('pending_bomb', False):
                st.warning("💣 Dreifachtreffer! Welcher Spieler hat den ZWEITEN Ball in den selben Becher geworfen?")
                bp1, bp2 = st.columns(2)
                team = live['bomb_team']
                player_A = p1 if team == 1 else p3
                player_B = p2 if team == 1 else p4
                
                if bp1.button(f"{player_A}", use_container_width=True):
                    do_hit(team, 3, is_balls_back=True)
                    live['pending_bomb'] = False
                    st.rerun()
                if bp2.button(f"{player_B}", use_container_width=True):
                    do_hit(team, 3, is_balls_back=True)
                    live['pending_bomb'] = False
                    st.rerun()
            
            else:
                # Normale Steuerung (Nur sichtbar für das Team, das dran ist)
                if live['possession'] == 1:
                    st.button("🚫 Kein Treffer", use_container_width=True, on_click=do_miss)
                    c_h1, c_h2 = st.columns(2)
                    if c_h1.button(f"🎯 Einzeltreffer ({p1})", use_container_width=True, disabled=live['t2_cups']==0): do_hit(1, 1); st.rerun()
                    if c_h2.button(f"🎯 Einzeltreffer ({p2})", use_container_width=True, disabled=live['t2_cups']==0): do_hit(1, 1); st.rerun()
                    
                    c_s1, c_s2 = st.columns(2)
                    if c_s1.button("✌️ Doppeltreffer (-2)", use_container_width=True, disabled=live['t2_cups']==0): do_hit(1, 2, is_balls_back=True); st.rerun()
                    if c_s2.button("💣 Dreifachtreffer (-3)", use_container_width=True, disabled=live['t2_cups']==0): 
                        save_step()
                        live['pending_bomb'] = True; live['bomb_team'] = 1; st.rerun()
                    
                    if st.button(f"⚠️ Fehler Team 1 (-1 eigener Becher)", use_container_width=True): do_penalty(1); st.rerun()

                elif live['possession'] == 2:
                    st.button("🚫 Kein Treffer", use_container_width=True, on_click=do_miss)
                    c_h3, c_h4 = st.columns(2)
                    if c_h3.button(f"🎯 Einzeltreffer ({p3})", use_container_width=True, disabled=live['t1_cups']==0): do_hit(2, 1); st.rerun()
                    if c_h4.button(f"🎯 Einzeltreffer ({p4})", use_container_width=True, disabled=live['t1_cups']==0): do_hit(2, 1); st.rerun()
                    
                    c_s3, c_s4 = st.columns(2)
                    if c_s3.button("✌️ Doppeltreffer (-2)", use_container_width=True, disabled=live['t1_cups']==0): do_hit(2, 2, is_balls_back=True); st.rerun()
                    if c_s4.button("💣 Dreifachtreffer (-3)", use_container_width=True, disabled=live['t1_cups']==0): 
                        save_step()
                        live['pending_bomb'] = True; live['bomb_team'] = 2; st.rerun()
                        
                    if st.button(f"⚠️ Fehler Team 2 (-1 eigener Becher)", use_container_width=True): do_penalty(2); st.rerun()

            st.write("---")
            # --- KONTROLL-LEISTE ---
            ctrl1, ctrl2, ctrl3 = st.columns(3)
            with ctrl1:
                if st.button("↩️ Undo", use_container_width=True, disabled=not live['history']):
                    last = live['history'].pop()
                    live['t1_cups'], live['t2_cups'] = last['t1_cups'], last['t2_cups']
                    live['nachwurf'], live['possession'] = last['nachwurf'], last['possession']
                    live['balls_back'], live['pending_bomb'] = last['balls_back'], last['pending_bomb']
                    st.rerun()
            with ctrl2:
                if st.button("❌ Abbruch", use_container_width=True): st.session_state.live = None; st.rerun()
            with ctrl3:
                can_save = (live['t1_cups'] == 0 or live['t2_cups'] == 0) and not (live['t1_cups'] == 0 and live['t2_cups'] == 0)
                if st.button("💾 Speichern (Rest-Becher)", use_container_width=True, type="primary", disabled=not can_save):
                    # WICHTIG: Speichere die VERBLEIBENDEN Becher (0:4 Logik)
                    st.session_state.matches[live['match_id']]['t1_score'] = live['t1_cups']
                    st.session_state.matches[live['match_id']]['t2_score'] = live['t2_cups']
                    st.session_state.live = None
                    st.rerun()
                elif live['t1_cups'] == 0 and live['t2_cups'] == 0:
                    st.success("Verlängerung!")
                    if st.button("🔄 Verlängerung starten", use_container_width=True):
                        # Minimaler Reset für Overtime (z.B. 3 Becher)
                        live['t1_cups'], live['t2_cups'], live['nachwurf'] = 3, 3, None 
                        st.rerun()

with tab2:
    st.subheader("📅 Spielplan Übersicht")
    
    next_game_id = next((m['id'] for m in st.session_state.matches if m['t1_score'] is None), None)

    for m in st.session_state.matches:
        p1, p2 = st.session_state.players[m['t1_p1']], st.session_state.players[m['t1_p2']]
        p3, p4 = st.session_state.players[m['t2_p1']], st.session_state.players[m['t2_p2']]
        
        txt = f"Spiel {m['id']+1}: {p1} & {p2}  VS  {p3} & {p4}"
        
        if m['id'] == next_game_id and st.session_state.live is None:
            st.info(f"**👉 NÄCHSTES SPIEL: {txt}**")
        elif st.session_state.live and st.session_state.live['match_id'] == m['id']:
            st.warning(f"**🔴 LÄUFT GERADE: {txt}**")
        else:
            if m['t1_score'] is not None:
                st.success(f"✔️ {txt} **(Ergebnis: {m['t1_score']} : {m['t2_score']} Rest-Becher)**")
            else:
                st.write(f"⚪ {txt}")
