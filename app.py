import streamlit as st
import pandas as pd
import copy

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
        {
            "id": i, "t1_p1": g[0], "t1_p2": g[1], "t2_p1": g[2], "t2_p2": g[3], 
            "t1_score": None, "t2_score": None, "stats": None, "last_scorer": None, 
            "winner_turns": 0, "action_log": [], "live_backup": None
        }
        for i, g in enumerate(games_logic)
    ]

if 'live' not in st.session_state: 
    st.session_state.live = None

if 'confirm_abort' not in st.session_state:
    st.session_state.confirm_abort = False

# 3. Sidebar
with st.sidebar:
    st.header("⚙️ Einstellungen")
    st.session_state.t_name = st.text_input("Turnier Name", st.session_state.t_name)
    st.write("---")
    for i in range(5):
        st.session_state.players[i] = st.text_input(f"Spieler {i+1}", value=st.session_state.players[i])

st.title(f"👑 {st.session_state.t_name}")

# 4. Hilfsfunktionen für das Live-Spiel
def save_step():
    st.session_state.live['history'].append(copy.deepcopy({
        't1_cups': st.session_state.live['t1_cups'],
        't2_cups': st.session_state.live['t2_cups'],
        'nachwurf': st.session_state.live['nachwurf'],
        'possession': st.session_state.live['possession'],
        'balls_back': st.session_state.live['balls_back'],
        'pending_bomb': st.session_state.live.get('pending_bomb', False),
        'last_scorer': st.session_state.live.get('last_scorer', None),
        'stats': st.session_state.live['stats'],
        'action_log': st.session_state.live['action_log']
    }))

def change_possession(new_poss):
    live = st.session_state.live
    live['possession'] = new_poss
    if new_poss == 1: live['stats']['turns_t1'] += 1
    else: live['stats']['turns_t2'] += 1

def add_stat(p_idx, hits, throws):
    st.session_state.live['stats'][f'p{p_idx}_h'] += hits
    st.session_state.live['stats'][f'p{p_idx}_t'] += throws

def log_action(text):
    st.session_state.live['action_log'].append(text)

def do_hit(team_hitting, amount, hits=[], misses=[], bombe_thrower=None, is_balls_back=False):
    save_step()
    live = st.session_state.live
    names = st.session_state.players
    m = st.session_state.matches[live['match_id']]
    
    live['balls_back'] = is_balls_back
    
    # Team Namen für Log
    if team_hitting == 1: t_name = f"{names[m['t1_p1']]} & {names[m['t1_p2']]}"
    else: t_name = f"{names[m['t2_p1']]} & {names[m['t2_p2']]}"
    
    turn = live['stats'][f'turns_t{team_hitting}']
    
    # Action Log Text generieren
    if amount == 1:
        log_action(f"[{t_name} | Zug {turn}] 🎯 Einzeltreffer von {names[hits[0]]}")
    elif amount == 2:
        log_action(f"[{t_name} | Zug {turn}] ✌️ Doppeltreffer von {names[hits[0]]} & {names[hits[1]]} (Balls Back)")
    elif amount == 3:
        log_action(f"[{t_name} | Zug {turn}] 💣 Dreifachtreffer! Zweiter Ball von {names[bombe_thrower]} (Balls Back)")

    # Letzten Torschützen merken
    if bombe_thrower is not None: live['last_scorer'] = bombe_thrower
    elif hits: live['last_scorer'] = hits[0]
        
    # Becher abziehen
    if team_hitting == 1: live['t2_cups'] = max(0, live['t2_cups'] - amount)
    else: live['t1_cups'] = max(0, live['t1_cups'] - amount)
    
    # Statistiken aktualisieren
    for p in hits:
        live['stats'][f'p{p}_h'] += 1
        live['stats'][f'p{p}_t'] += 1
    for p in misses:
        live['stats'][f'p{p}_t'] += 1
    if bombe_thrower is not None:
        live['stats'][f'p{bombe_thrower}_b'] += 1
        
    # Ballbesitz
    if not is_balls_back:
        change_possession(2 if team_hitting == 1 else 1)
        
    # Nachwurf prüfen
    if live['t2_cups'] == 0 and live['starter'] == 1 and live['nachwurf'] is None:
        live['nachwurf'] = 2; change_possession(2)
        log_action(f"🚨 NACHWURF für {names[m['t2_p1']]} & {names[m['t2_p2']]}!")
    elif live['t1_cups'] == 0 and live['starter'] == 2 and live['nachwurf'] is None:
        live['nachwurf'] = 1; change_possession(1)
        log_action(f"🚨 NACHWURF für {names[m['t1_p1']]} & {names[m['t1_p2']]}!")

def do_miss(team):
    save_step()
    live = st.session_state.live
    live['balls_back'] = False
    m = st.session_state.matches[live['match_id']]
    names = st.session_state.players
    
    if team == 1: t_name = f"{names[m['t1_p1']]} & {names[m['t1_p2']]}"
    else: t_name = f"{names[m['t2_p1']]} & {names[m['t2_p2']]}"
    
    turn = live['stats'][f'turns_t{team}']
    log_action(f"[{t_name} | Zug {turn}] 🚫 Kein Treffer (Wechsel)")
    
    if team == 1:
        add_stat(m['t1_p1'], 0, 1); add_stat(m['t1_p2'], 0, 1)
        change_possession(2)
    else:
        add_stat(m['t2_p1'], 0, 1); add_stat(m['t2_p2'], 0, 1)
        change_possession(1)

def do_penalty(team):
    save_step()
    live = st.session_state.live
    names = st.session_state.players
    m = st.session_state.matches[live['match_id']]
    
    if team == 1: t_name = f"{names[m['t1_p1']]} & {names[m['t1_p2']]}"
    else: t_name = f"{names[m['t2_p1']]} & {names[m['t2_p2']]}"
    
    turn = live['stats'][f'turns_t{team}']
    log_action(f"[{t_name} | Zug {turn}] ⚠️ Fehler (-1 eigener Becher)")
    
    if team == 1: live['t1_cups'] = max(0, live['t1_cups'] - 1)
    else: live['t2_cups'] = max(0, live['t2_cups'] - 1)

def get_pct(hits, throws):
    if throws == 0: return 0
    return int((hits / throws) * 100)

# 5. Tabs Layout
tab1, tab2, tab3 = st.tabs(["🎮 Live Spiel", "🏆 Tabelle & Spielplan", "📊 Statistiken"])

# --- TAB 1: LIVE SPIEL ---
with tab1:
    if st.session_state.live is None:
        st.subheader("Spiel auswählen")
        match_opts = {}
        next_open_found = False
        for m in st.session_state.matches:
            p1, p2 = st.session_state.players[m['t1_p1']], st.session_state.players[m['t1_p2']]
            p3, p4 = st.session_state.players[m['t2_p1']], st.session_state.players[m['t2_p2']]
            txt = f"Spiel {m['id']+1}: {p1} & {p2} vs {p3} & {p4}"
            
            if m['t1_score'] is not None:
                match_opts[m['id']] = f"🟢 BEENDET - {txt} ({m['t1_score']}:{m['t2_score']})"
            else:
                if not next_open_found:
                    match_opts[m['id']] = f"👉 NÄCHSTES - {txt}"
                    next_open_found = True
                else:
                    match_opts[m['id']] = f"⚪ OFFEN - {txt}"
                    
        sel_id = st.selectbox("Wähle ein Spiel aus der Liste:", options=list(match_opts.keys()), format_func=lambda x: match_opts[x])
        sel_m = st.session_state.matches[sel_id]
        
        if sel_m['t1_score'] is not None:
            st.info(f"Dieses Spiel ist bereits beendet (Ergebnis: {sel_m['t1_score']}:{sel_m['t2_score']} Rest-Becher).")
            
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("✏️ Spiel neu bearbeiten (Altes Ergebnis überschreiben)", use_container_width=True):
                    st.session_state.live = copy.deepcopy(sel_m['live_backup'])
                    sel_m['t1_score'] = None
                    sel_m['t2_score'] = None
                    st.rerun()
        else:
            if st.button("▶️ Spiel starten", type="primary", use_container_width=True):
                st.session_state.live = {
                    'match_id': sel_id, 'starter': None, 'possession': None,
                    't1_cups': 10, 't2_cups': 10, 'nachwurf': None, 
                    'balls_back': False, 'pending_bomb': False, 'bomb_team': None,
                    'last_scorer': None, 'action_log': [], 'history': [],
                    'stats': {
                        'turns_t1': 0, 'turns_t2': 0,
                        f"p{sel_m['t1_p1']}_h": 0, f"p{sel_m['t1_p1']}_t": 0, f"p{sel_m['t1_p1']}_b": 0,
                        f"p{sel_m['t1_p2']}_h": 0, f"p{sel_m['t1_p2']}_t": 0, f"p{sel_m['t1_p2']}_b": 0,
                        f"p{sel_m['t2_p1']}_h": 0, f"p{sel_m['t2_p1']}_t": 0, f"p{sel_m['t2_p1']}_b": 0,
                        f"p{sel_m['t2_p2']}_h": 0, f"p{sel_m['t2_p2']}_t": 0, f"p{sel_m['t2_p2']}_b": 0,
                    }
                }
                st.rerun()

    else:
        live = st.session_state.live
        m = st.session_state.matches[live['match_id']]
        names = st.session_state.players
        i_p1, i_p2, i_p3, i_p4 = m['t1_p1'], m['t1_p2'], m['t2_p1'], m['t2_p2']
        p1, p2, p3, p4 = names[i_p1], names[i_p2], names[i_p3], names[i_p4]

        if live['starter'] is None:
            st.info("🪨✂️📄 Wer fängt an? (Gewinner Schere-Stein-Papier)")
            cA, cB = st.columns(2)
            if cA.button(f"{p1} & {p2} beginnen", use_container_width=True): 
                live['starter'] = 1; live['possession'] = 1; live['stats']['turns_t1'] = 1
                log_action(f"🏁 Team 1 ({p1} & {p2}) fängt an.")
                st.rerun()
            if cB.button(f"{p3} & {p4} beginnen", use_container_width=True): 
                live['starter'] = 2; live['possession'] = 2; live['stats']['turns_t2'] = 1
                log_action(f"🏁 Team 2 ({p3} & {p4}) fängt an.")
                st.rerun()
            st.button("❌ Spiel abbrechen", on_click=lambda: st.session_state.update(live=None))
        
        else:
            # --- KOMPAKTES LIVE UI ---
            if live['nachwurf']: st.error(f"🚨 NACHWURF FÜR TEAM {live['nachwurf']}!")
            elif live['balls_back']: st.success("🔥 BALLS BACK! Nochmal werfen.")

            disp1, disp_vs, disp2 = st.columns([5, 1, 5])
            
            with disp1:
                st.markdown(f"<div style='text-align: center; line-height: 1.1; margin-bottom: 10px;'><span style='font-size: 55px; font-weight: bold; color: {'#9C0006' if live['t1_cups']==0 else 'inherit'};'>{live['t1_cups']}</span><span style='font-size: 16px;'> Becher</span></div>", unsafe_allow_html=True)
                st_txt = "🏁 Starter" if live['starter'] == 1 else "🛡️ Hat Nachwurf" if live['starter'] == 2 else ""
                st.markdown(f"<p style='text-align:center; color:gray; font-size:14px; margin:0;'>{st_txt} | Zug-Nr: {live['stats']['turns_t1']}</p>", unsafe_allow_html=True)
                
                s1_h, s1_t = live['stats'][f'p{i_p1}_h'], live['stats'][f'p{i_p1}_t']
                s2_h, s2_t = live['stats'][f'p{i_p2}_h'], live['stats'][f'p{i_p2}_t']
                st.markdown(f"<h4 style='text-align: center; margin-bottom:5px;'>{p1} & {p2}</h4>", unsafe_allow_html=True)
                st.markdown(f"<p style='text-align:center; font-size:14px; margin:0;'>{p1}: {s1_h} Treffer ({get_pct(s1_h, s1_t)}%) | {p2}: {s2_h} Treffer ({get_pct(s2_h, s2_t)}%)</p>", unsafe_allow_html=True)
                if live['possession'] == 1 and not live.get('pending_bomb', False): st.info("🟢 BALLBESITZ")

            with disp_vs:
                st.markdown("<h3 style='text-align: center; margin-top: 25px; color: gray;'>VS</h3>", unsafe_allow_html=True)
                
            with disp2:
                st.markdown(f"<div style='text-align: center; line-height: 1.1; margin-bottom: 10px;'><span style='font-size: 55px; font-weight: bold; color: {'#9C0006' if live['t2_cups']==0 else 'inherit'};'>{live['t2_cups']}</span><span style='font-size: 16px;'> Becher</span></div>", unsafe_allow_html=True)
                st_txt2 = "🏁 Starter" if live['starter'] == 2 else "🛡️ Hat Nachwurf" if live['starter'] == 1 else ""
                st.markdown(f"<p style='text-align:center; color:gray; font-size:14px; margin:0;'>{st_txt2} | Zug-Nr: {live['stats']['turns_t2']}</p>", unsafe_allow_html=True)
                
                s3_h, s3_t = live['stats'][f'p{i_p3}_h'], live['stats'][f'p{i_p3}_t']
                s4_h, s4_t = live['stats'][f'p{i_p4}_h'], live['stats'][f'p{i_p4}_t']
                st.markdown(f"<h4 style='text-align: center; margin-bottom:5px;'>{p3} & {p4}</h4>", unsafe_allow_html=True)
                st.markdown(f"<p style='text-align:center; font-size:14px; margin:0;'>{p3}: {s3_h} Treffer ({get_pct(s3_h, s3_t)}%) | {p4}: {s4_h} Treffer ({get_pct(s4_h, s4_t)}%)</p>", unsafe_allow_html=True)
                if live['possession'] == 2 and not live.get('pending_bomb', False): st.info("🟢 BALLBESITZ")

            st.write("---")

            # --- STEUERUNG ---
            if live.get('pending_bomb', False):
                st.warning("💣 DREIFACHTREFFER! Welcher Spieler hat den ZWEITEN Ball versenkt?")
                bp1, bp2 = st.columns(2)
                if live['bomb_team'] == 1:
                    if bp1.button(f"{p1} hat nachgeworfen", use_container_width=True): do_hit(1, 3, hits=[i_p1, i_p2], bombe_thrower=i_p1, is_balls_back=True); live['pending_bomb'] = False; st.rerun()
                    if bp2.button(f"{p2} hat nachgeworfen", use_container_width=True): do_hit(1, 3, hits=[i_p1, i_p2], bombe_thrower=i_p2, is_balls_back=True); live['pending_bomb'] = False; st.rerun()
                else:
                    if bp1.button(f"{p3} hat nachgeworfen", use_container_width=True): do_hit(2, 3, hits=[i_p3, i_p4], bombe_thrower=i_p3, is_balls_back=True); live['pending_bomb'] = False; st.rerun()
                    if bp2.button(f"{p4} hat nachgeworfen", use_container_width=True): do_hit(2, 3, hits=[i_p3, i_p4], bombe_thrower=i_p4, is_balls_back=True); live['pending_bomb'] = False; st.rerun()
            else:
                colL, colR = st.columns(2)
                # TEAM 1 STEUERUNG
                with colL:
                    if live['possession'] == 1:
                        st.button("🚫 Kein Treffer (Wechsel)", use_container_width=True, on_click=lambda: do_miss(1))
                        c_h1, c_h2 = st.columns(2)
                        if c_h1.button(f"🎯 Treffer {p1}", use_container_width=True, disabled=live['t2_cups']==0): do_hit(1, 1, hits=[i_p1], misses=[i_p2]); st.rerun()
                        if c_h2.button(f"🎯 Treffer {p2}", use_container_width=True, disabled=live['t2_cups']==0): do_hit(1, 1, hits=[i_p2], misses=[i_p1]); st.rerun()
                        c_s1, c_s2 = st.columns(2)
                        if c_s1.button("✌️ Doppel (-2)", use_container_width=True, disabled=live['t2_cups']==0): do_hit(1, 2, hits=[i_p1, i_p2], is_balls_back=True); st.rerun()
                        if c_s2.button("💣 Dreifach (-3)", use_container_width=True, disabled=live['t2_cups']==0): 
                            save_step(); live['pending_bomb'] = True; live['bomb_team'] = 1; st.rerun()
                    st.write("")
                    if st.button("⚠️ Fehler Team 1 (-1 Becher)", use_container_width=True): do_penalty(1); st.rerun()

                # TEAM 2 STEUERUNG
                with colR:
                    if live['possession'] == 2:
                        st.button("🚫 Kein Treffer (Wechsel)", use_container_width=True, on_click=lambda: do_miss(2))
                        c_h3, c_h4 = st.columns(2)
                        if c_h3.button(f"🎯 Treffer {p3}", use_container_width=True, disabled=live['t1_cups']==0): do_hit(2, 1, hits=[i_p3], misses=[i_p4]); st.rerun()
                        if c_h4.button(f"🎯 Treffer {p4}", use_container_width=True, disabled=live['t1_cups']==0): do_hit(2, 1, hits=[i_p4], misses=[i_p3]); st.rerun()
                        c_s3, c_s4 = st.columns(2)
                        if c_s3.button("✌️ Doppel (-2)", use_container_width=True, disabled=live['t1_cups']==0): do_hit(2, 2, hits=[i_p3, i_p4], is_balls_back=True); st.rerun()
                        if c_s4.button("💣 Dreifach (-3)", use_container_width=True, disabled=live['t1_cups']==0): 
                            save_step(); live['pending_bomb'] = True; live['bomb_team'] = 2; st.rerun()
                    st.write("")
                    if st.button("⚠️ Fehler Team 2 (-1 Becher)", use_container_width=True): do_penalty(2); st.rerun()

            st.write("---")
            # --- KONTROLL-LEISTE ---
            ctrl1, ctrl2, ctrl3 = st.columns(3)
            with ctrl1:
                if st.button("↩️ Undo", use_container_width=True, disabled=not live['history']):
                    last = live['history'].pop()
                    live['t1_cups'], live['t2_cups'] = last['t1_cups'], last['t2_cups']
                    live['nachwurf'], live['possession'] = last['nachwurf'], last['possession']
                    live['balls_back'], live['pending_bomb'] = last['balls_back'], last['pending_bomb']
                    live['last_scorer'], live['stats'] = last['last_scorer'], last['stats']
                    live['action_log'] = last['action_log']
                    st.rerun()
                    
            with ctrl2:
                if st.session_state.confirm_abort:
                    st.warning("Wirklich abbrechen? Fortschritt geht verloren.")
                    cy, cn = st.columns(2)
                    if cy.button("✔️ Ja", use_container_width=True): 
                        st.session_state.live = None; st.session_state.confirm_abort = False; st.rerun()
                    if cn.button("❌ Nein", use_container_width=True): 
                        st.session_state.confirm_abort = False; st.rerun()
                else:
                    if st.button("❌ Spiel Abbrechen", use_container_width=True): 
                        st.session_state.confirm_abort = True; st.rerun()
                        
            with ctrl3:
                can_save = (live['t1_cups'] == 0 or live['t2_cups'] == 0) and not (live['t1_cups'] == 0 and live['t2_cups'] == 0)
                if st.button("💾 Speichern (Rest-Becher)", use_container_width=True, type="primary", disabled=not can_save):
                    m['t1_score'] = live['t1_cups']
                    m['t2_score'] = live['t2_cups']
                    m['stats'] = copy.deepcopy(live['stats'])
                    m['last_scorer'] = live.get('last_scorer', None)
                    m['action_log'] = copy.deepcopy(live['action_log'])
                    
                    if live['t1_cups'] == 0: m['winner_turns'] = live['stats']['turns_t2'] 
                    else: m['winner_turns'] = live['stats']['turns_t1']
                    
                    st.session_state.live = None
                    st.rerun()
                elif live['t1_cups'] == 0 and live['t2_cups'] == 0:
                    st.success("Unentschieden! 🔄 Verlängerung starten?")
                    if st.button("Verlängerung einleiten", use_container_width=True):
                        log_action("🔄 Verlängerung gestartet!")
                        live['t1_cups'], live['t2_cups'], live['nachwurf'] = 3, 3, None 
                        st.rerun()

# --- TAB 2: TABELLE & SPIELPLAN ---
with tab2:
    st.subheader("Die Meister-Tabelle")
    players = st.session_state.players
    matches = st.session_state.matches
    
    player_stats = []
    for i, p in enumerate(players):
        sp = s = n = diff = streak_val = 0
        for m in matches:
            t1, t2 = m['t1_score'], m['t2_score']
            if t1 is not None and t2 is not None:
                if i in [m['t1_p1'], m['t1_p2']]:
                    sp += 1
                    if t1 > t2: s += 1; diff += (t1 - t2); streak_val = streak_val + 1 if streak_val > 0 else 1
                    else: n += 1; diff += (t1 - t2); streak_val = streak_val - 1 if streak_val < 0 else -1
                elif i in [m['t2_p1'], m['t2_p2']]:
                    sp += 1
                    if t2 > t1: s += 1; diff += (t2 - t1); streak_val = streak_val + 1 if streak_val > 0 else 1
                    else: n += 1; diff += (t2 - t1); streak_val = streak_val - 1 if streak_val < 0 else -1

        score = s * 10000 + diff
        s_pct = f"{int((s/sp)*100)}%" if sp > 0 else "0%"
        st_txt = f"{streak_val}S" if streak_val > 0 else f"{abs(streak_val)}N" if streak_val < 0 else "-"
        st_emj = "🔥" if streak_val >= 3 else "💀" if streak_val <= -3 else ""
        
        player_stats.append({
            'id': i, 'NAME': p, 'SP': sp, 'S': s, 'N': n, 'DIFF': diff,
            'S%': s_pct, 'SERIE': st_txt, ' ': st_emj, 'Rest': 12 - sp, 'Score': score
        })

    is_finished = sum(1 for m in matches if m['t1_score'] is not None) == 15
    max_score = max(ps['Score'] for ps in player_stats) if player_stats else 0

    for ps in player_stats:
        max_pot = ps['Score'] + ps['Rest'] * 10010
        min_opp_scores = []
        for opp in player_stats:
            if ps['id'] == opp['id']: continue
            open_t = sum(1 for m in matches if m['t1_score'] is None and ((ps['id'] in [m['t1_p1'], m['t1_p2']] and opp['id'] in [m['t1_p1'], m['t1_p2']]) or (ps['id'] in [m['t2_p1'], m['t2_p2']] and opp['id'] in [m['t2_p1'], m['t2_p2']])))
            min_opp_scores.append(opp['Score'] + (open_t * 10020) - (opp['Rest'] * 10))

        if is_finished: ps['STATUS'] = "👑 MEISTER" if ps['Score'] == max_score else "Eliminated"
        else: ps['STATUS'] = "Titel drin" if max_pot >= (max(min_opp_scores) if min_opp_scores else 0) else "Eliminated"

    if not is_finished and sum(1 for ps in player_stats if ps['STATUS'] == "Titel drin") == 1:
        for ps in player_stats:
            if ps['STATUS'] == "Titel drin": ps['STATUS'] = "👑 MEISTER"

    df = pd.DataFrame(player_stats).sort_values(by=['Score'], ascending=False).reset_index(drop=True)
    df.index += 1
    df.insert(0, 'RANG', df.index.map(lambda x: ["1 🏆", "2 🥈", "3 🥉", "4", "5"][x-1] if x<=5 else str(x)))
    
    def style_df(val):
        if val == 'Eliminated': return 'color: #9C0006; font-weight: bold'
        if val == 'Titel drin': return 'color: #008000; font-weight: bold'
        if val == '👑 MEISTER': return 'background-color: #FFD966; color: black; font-weight: bold'
        if isinstance(val, int) and val > 0: return 'color: #008000; font-weight: bold'
        if isinstance(val, int) and val < 0: return 'color: #FF0000; font-weight: bold'
        if isinstance(val, str) and 'S' in val and val != "STATUS": return 'color: #008000; font-weight: bold'
        if isinstance(val, str) and 'N' in val and val != "NAME" and val != "STATUS": return 'color: #FF0000; font-weight: bold'
        return ''

    st.dataframe(df[['RANG', 'NAME', 'SP', 'S', 'N', 'DIFF', 'S%', 'SERIE', ' ', 'STATUS']].style.map(style_df), hide_index=True, use_container_width=True)

    st.divider()
    st.subheader("📅 Spielplan & Spielberichte")
    
    for m in matches:
        p1, p2 = players[m['t1_p1']], players[m['t1_p2']]
        p3, p4 = players[m['t2_p1']], players[m['t2_p2']]
        txt = f"Spiel {m['id']+1}: {p1} & {p2} VS {p3} & {p4}"
        
        if m['t1_score'] is not None:
            st.success(f"✔️ {txt} **({m['t1_score']} : {m['t2_score']})**")
            with st.expander("📄 Spielbericht anzeigen"):
                if m.get('action_log'):
                    for entry in m['action_log']: st.write(entry)
                else:
                    st.write("Kein Log vorhanden.")
        elif st.session_state.live and st.session_state.live['match_id'] == m['id']:
            st.warning(f"🔴 LÄUFT GERADE: {txt}")
        else:
            st.write(f"⚪ {txt}")

# --- TAB 3: STATISTIKEN ---
with tab3:
    st.subheader("📊 Einzel-Statistiken")
    
    ind_stats = []
    for i, p in enumerate(st.session_state.players):
        hits = throws = bombs = gw = 0
        for m in st.session_state.matches:
            if m['t1_score'] is not None and m['stats'] is not None:
                hits += m['stats'].get(f'p{i}_h', 0)
                throws += m['stats'].get(f'p{i}_t', 0)
                bombs += m['stats'].get(f'p{i}_b', 0)
                if m.get('last_scorer') == i:
                    gw += 1
        
        quote = (hits / throws * 100) if throws > 0 else 0.0
        ind_stats.append({
            'NAME': p, 'TREFFER': hits, 'WÜRFE': throws, 
            'QUOTE_VAL': quote, 'QUOTE': f"{quote:.2f} %", 
            'SIEGTREFFER': gw, 'DREIFACHTREFFER': bombs
        })
    
    col_i1, col_i2, col_i3 = st.columns(3)
    
    with col_i1:
        st.write("**🎯 Trefferquoten**")
        df_quote = pd.DataFrame(ind_stats).sort_values(by=['QUOTE_VAL', 'TREFFER'], ascending=[False, False]).reset_index(drop=True)
        df_quote.index += 1
        df_quote.insert(0, 'RANG', df_quote.index)
        st.dataframe(df_quote[['RANG', 'NAME', 'TREFFER', 'WÜRFE', 'QUOTE']], hide_index=True, use_container_width=True)

    with col_i2:
        st.write("**🔪 Vollstrecker (Game Winners)**")
        df_gw = pd.DataFrame(ind_stats).sort_values(by='SIEGTREFFER', ascending=False).reset_index(drop=True)
        df_gw.index += 1
        df_gw.insert(0, 'RANG', df_gw.index)
        st.dataframe(df_gw[['RANG', 'NAME', 'SIEGTREFFER']], hide_index=True, use_container_width=True)

    with col_i3:
        st.write("**💣 Die Bomber**")
        df_bomb = pd.DataFrame(ind_stats).sort_values(by='DREIFACHTREFFER', ascending=False).reset_index(drop=True)
        df_bomb.index += 1
        df_bomb.insert(0, 'RANG', df_bomb.index)
        st.dataframe(df_bomb[['RANG', 'NAME', 'DREIFACHTREFFER']], hide_index=True, use_container_width=True)

    st.divider()
    
    # SPIEL-STATISTIKEN
    match_data = []
    for m in st.session_state.matches:
        if m['t1_score'] is not None:
            diff = abs(m['t1_score'] - m['t2_score'])
            turns = m.get('winner_turns', 0)
            txt = f"Spiel {m['id']+1}: {players[m['t1_p1']]} & {players[m['t1_p2']]} vs {players[m['t2_p1']]} & {players[m['t2_p2']]}"
            res = f"{m['t1_score']} : {m['t2_score']}"
            match_data.append({'SPIEL': txt, 'ERGEBNIS': res, 'DIFF': diff, 'ZÜGE (SIEGER)': turns})

    col_m1, col_m2 = st.columns(2)
    
    with col_m1:
        st.write("**🏆 Höchster Sieg (Top 3)**")
        if match_data:
            df_hs = pd.DataFrame(match_data).sort_values(by=['DIFF', 'ZÜGE (SIEGER)'], ascending=[False, True]).head(3).reset_index(drop=True)
            df_hs.index += 1
            df_hs.insert(0, 'RANG', df_hs.index)
            st.dataframe(df_hs[['RANG', 'SPIEL', 'ERGEBNIS', 'DIFF', 'ZÜGE (SIEGER)']], hide_index=True, use_container_width=True)
        else:
            st.write("Noch keine Spiele absolviert.")

    with col_m2:
        st.write("**⚡ Blitzkrieg (Schnellste Siege - Top 3)**")
        if match_data:
            df_bk = pd.DataFrame(match_data).sort_values(by='ZÜGE (SIEGER)', ascending=True).head(3).reset_index(drop=True)
            df_bk.index += 1
            df_bk.insert(0, 'RANG', df_bk.index)
            st.dataframe(df_bk[['RANG', 'SPIEL', 'ZÜGE (SIEGER)', 'ERGEBNIS']], hide_index=True, use_container_width=True)
        else:
            st.write("Noch keine Spiele absolviert.")
