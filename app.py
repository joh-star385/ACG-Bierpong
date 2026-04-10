import streamlit as st
import pandas as pd
import copy
import json
import time
from datetime import date
import io

# Optionales Auto-Refresh für Zuschauer
try:
    from streamlit_autorefresh import st_autorefresh
    has_autorefresh = True
except ImportError:
    has_autorefresh = False

# --- FIREBASE SETUP ---
import firebase_admin
from firebase_admin import credentials, firestore

# 1. Seiten-Design
st.set_page_config(page_title="Bierpong Live-App", page_icon="🍺", layout="wide")

# Firebase initialisieren
@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        key_dict = json.loads(st.secrets["FIREBASE_KEY"], strict=False)
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()

try:
    db = init_firebase()
    db_connected = True
except Exception as e:
    st.error(f"Datenbank-Verbindungsfehler. Fehler: {e}")
    db_connected = False

# --- HILFSFUNKTIONEN FÜR TURNIERE & CLOUD ---
def get_pct(hits, throws):
    return int((hits / throws) * 100) if throws > 0 else 0

def get_tournament_list():
    if db_connected:
        try:
            docs = db.collection('bierpong_turniere').stream()
            return {doc.id: doc.to_dict().get("t_name", "Unbekanntes Turnier") for doc in docs}
        except Exception:
            pass
    return {}

def load_tournament(doc_id):
    if db_connected:
        doc = db.collection('bierpong_turniere').document(doc_id).get()
        if doc.exists:
            data = doc.to_dict()
            st.session_state.current_tournament_id = doc_id
            st.session_state.t_name = data.get("t_name", "Bierpong Meisterschaft")
            st.session_state.t_date = data.get("t_date", str(date.today()))
            st.session_state.players = data.get("players", ['Spieler 1', 'Spieler 2', 'Spieler 3', 'Spieler 4', 'Spieler 5'])
            st.session_state.matches = data.get("matches", generate_fresh_matches())
            st.session_state.live = data.get("live", None)

def sync_to_cloud():
    if db_connected and st.session_state.current_tournament_id:
        doc_ref = db.collection('bierpong_turniere').document(st.session_state.current_tournament_id)
        data = {
            "t_name": st.session_state.t_name,
            "t_date": str(st.session_state.t_date),
            "players": st.session_state.players,
            "matches": st.session_state.matches,
            "live": st.session_state.live
        }
        doc_ref.set(data)

def generate_fresh_matches():
    games_logic = [
        [0, 1, 2, 3], [1, 2, 3, 4], [2, 3, 4, 0], [3, 4, 0, 1], [4, 0, 1, 2],
        [0, 2, 1, 3], [1, 3, 2, 4], [2, 4, 3, 0], [3, 0, 4, 1], [4, 1, 0, 2],
        [0, 3, 1, 2], [1, 4, 2, 3], [2, 0, 3, 4], [3, 1, 4, 0], [4, 2, 0, 1]
    ]
    return [
        {
            "id": i, "t1_p1": g[0], "t1_p2": g[1], "t2_p1": g[2], "t2_p2": g[3], 
            "t1_score": None, "t2_score": None, "stats": None, "last_scorer": None, 
            "winner_turns": 0, "action_log": [], "live_backup": None,
            "bombs_events": [], "clutch_nachwurf_events": []
        }
        for i, g in enumerate(games_logic)
    ]

# 2. Session State initialisieren
if 'current_tournament_id' not in st.session_state: st.session_state.current_tournament_id = None
if 't_name' not in st.session_state: st.session_state.t_name = "Bierpong Meisterschaft"
if 't_date' not in st.session_state: st.session_state.t_date = str(date.today())
if 'players' not in st.session_state: st.session_state.players = ['Spieler 1', 'Spieler 2', 'Spieler 3', 'Spieler 4', 'Spieler 5']
if 'matches' not in st.session_state: st.session_state.matches = generate_fresh_matches()
if 'live' not in st.session_state: st.session_state.live = None
if 'confirm_abort' not in st.session_state: st.session_state.confirm_abort = False
if 'confirm_delete' not in st.session_state: st.session_state.confirm_delete = None

# URL überprüfen für dauerhaften Login
if 'admin_auth' not in st.session_state:
    if st.query_params.get("admin") == "true":
        st.session_state.admin_auth = True
    else:
        st.session_state.admin_auth = False

def get_basic_standings():
    stats = []
    for i, p in enumerate(st.session_state.players):
        s = n = 0
        for m in st.session_state.matches:
            t1, t2 = m['t1_score'], m['t2_score']
            if t1 is not None and t2 is not None:
                if i in [m['t1_p1'], m['t1_p2']]:
                    if t1 > t2: s += 1
                    else: n += 1
                elif i in [m['t2_p1'], m['t2_p2']]:
                    if t2 > t1: s += 1
                    else: n += 1
        stats.append({'NAME': p, 'S': s, 'N': n, 'SCORE': s - n})
    df = pd.DataFrame(stats).sort_values(by=['SCORE', 'S'], ascending=[False, False]).reset_index(drop=True)
    df.index += 1
    df.insert(0, 'RANG', df.index)
    return df[['RANG', 'NAME', 'S', 'N']]

# --- ZUSCHAUER / MASTER LOGIK IN DER SIDEBAR ---
with st.sidebar:
    if not st.session_state.admin_auth:
        st.header("👀 Zuschauer-Modus")
        pwd = st.text_input("🔒 Admin Passwort:", type="password")
        if pwd == "acg987":
            st.session_state.admin_auth = True
            st.query_params["admin"] = "true" 
            st.rerun()
            
        st.write("---")
        st.write("**Aktuelles Turnier:**")
        all_t = get_tournament_list()
        if all_t:
            sel_view = st.selectbox("Turnier auswählen", options=list(all_t.keys()), format_func=lambda x: all_t[x])
            if st.button("🔄 Manuell Aktualisieren", use_container_width=True):
                load_tournament(sel_view)
                st.rerun()
                
            if has_autorefresh and st.session_state.current_tournament_id == sel_view:
                st_autorefresh(interval=5000, limit=None, key="viewer_refresh")
                load_tournament(sel_view)
        else:
            st.caption("Keine Turniere gefunden.")
            
    else:
        st.header("👑 Master-Modus")
        if st.button("🚪 Logout (Zurück zum Zuschauer-Modus)", use_container_width=True):
            st.session_state.admin_auth = False
            if "admin" in st.query_params:
                del st.query_params["admin"] 
            st.rerun()
        
    st.write("---")
    st.write(f"**Live: {st.session_state.t_name}**")
    if st.session_state.current_tournament_id:
        st.dataframe(get_basic_standings(), hide_index=True, use_container_width=True)
    else:
        st.caption("Bitte lade oder erstelle erst ein Turnier.")

# 4. Spiel-Logik
def save_step():
    l = st.session_state.live
    l['history'].append(copy.deepcopy({
        't1_cups': l['t1_cups'], 't2_cups': l['t2_cups'],
        'nachwurf': l['nachwurf'], 'possession': l['possession'],
        'balls_back': l['balls_back'], 'pending_bomb': l.get('pending_bomb', False),
        'pending_double_win': l.get('pending_double_win', False),
        'pending_last_cup': l.get('pending_last_cup', False),
        'pending_penalty': l.get('pending_penalty', None),
        'single_nachwurf_team': l.get('single_nachwurf_team', None),
        'single_nachwurf_shooter': l.get('single_nachwurf_shooter', None),
        'last_cup_hitter': l.get('last_cup_hitter', None),
        't1_last_scorer': l.get('t1_last_scorer', None),
        't2_last_scorer': l.get('t2_last_scorer', None),
        'game_state': l.get('game_state', 'playing'),
        'cups_at_turn_start': l.get('cups_at_turn_start'),
        'stats': l['stats'], 'action_log': l['action_log'],
        'bombs_events': l['bombs_events'], 'clutch_nachwurf_events': l['clutch_nachwurf_events']
    }))

def check_game_over():
    l = st.session_state.live
    
    # 1. OVERTIME (Beide Teams auf 0)
    if l['t1_cups'] == 0 and l['t2_cups'] == 0: 
        l['game_state'] = 'nachwurf_erfolgreich'
        return

    # 2. TEAM 1 GEWINNT (Sie haben T2 auf 0 gebracht)
    if l['t2_cups'] == 0 and l['t1_cups'] > 0:
        if l['starter'] == 2: 
            # Team 2 startete. Team 1 hat Nachwurf und trifft auf 0 -> Sieg Team 1!
            l['game_state'] = 't1_won'
        elif l['starter'] == 1:
            # Team 1 startete. Warten auf Nachwurf von Team 2.
            if l['nachwurf'] is None and l.get('single_nachwurf_team') != 2: 
                l['game_state'] = 't1_won'

    # 3. TEAM 2 GEWINNT (Sie haben T1 auf 0 gebracht)
    elif l['t1_cups'] == 0 and l['t2_cups'] > 0:
        if l['starter'] == 1: 
            # Team 1 startete. Team 2 hat Nachwurf und trifft auf 0 -> Sieg Team 2!
            l['game_state'] = 't2_won'
        elif l['starter'] == 2:
            # Team 2 startete. Warten auf Nachwurf von Team 1.
            if l['nachwurf'] is None and l.get('single_nachwurf_team') != 1: 
                l['game_state'] = 't2_won'

def change_possession(new_poss):
    live = st.session_state.live
    if live['t1_cups'] > 0 and live['t2_cups'] > 0:
        live['cups_at_turn_start'] = {'t1_cups': live['t1_cups'], 't2_cups': live['t2_cups']}
    live['possession'] = new_poss
    if new_poss == 1: live['stats']['turns_t1'] += 1
    else: live['stats']['turns_t2'] += 1

def log_action(text):
    st.session_state.live['action_log'].append(text)

def do_hit(team_hitting, amount, hits=[], misses=[], bombe_thrower=None, is_balls_back=False, is_clutch_nachwurf=False):
    save_step()
    live = st.session_state.live
    names = st.session_state.players
    m = st.session_state.matches[live['match_id']]
    
    live['balls_back'] = is_balls_back
    t_name = f"{names[m['t1_p1']]} & {names[m['t1_p2']]}" if team_hitting == 1 else f"{names[m['t2_p1']]} & {names[m['t2_p2']]}"
    turn = live['stats'][f'turns_t{team_hitting}']
    
    # Letzten Torschützen (Vollstrecker) speichern
    scorer = bombe_thrower if bombe_thrower is not None else (hits[-1] if hits else None)
    if scorer is not None:
        if team_hitting == 1: live['t1_last_scorer'] = scorer
        else: live['t2_last_scorer'] = scorer
        
    if team_hitting == 1: live['t2_cups'] = max(0, live['t2_cups'] - amount)
    else: live['t1_cups'] = max(0, live['t1_cups'] - amount)
    
    s_txt = f"(Stand: {live['t1_cups']}:{live['t2_cups']})"
    if amount == 1: log_action(f"[{t_name} | Zug {turn}] 🎯 Einzeltreffer von {names[hits[0]]} {s_txt}")
    elif amount == 2: log_action(f"[{t_name} | Zug {turn}] ✌️ Doppeltreffer von {names[hits[0]]} & {names[hits[1]]} {s_txt}")
    elif amount == 3: 
        log_action(f"[{t_name} | Zug {turn}] 💣 Dreifachtreffer! Zweiter Ball von {names[bombe_thrower]} {s_txt}")
        live['bombs_events'].append(bombe_thrower)

    if is_clutch_nachwurf and ((team_hitting == 1 and live['t2_cups'] == 0) or (team_hitting == 2 and live['t1_cups'] == 0)):
        live['clutch_nachwurf_events'].append(scorer)
    
    for p in hits: live['stats'][f'p{p}_h'] += 1; live['stats'][f'p{p}_t'] += 1
    for p in misses: live['stats'][f'p{p}_t'] += 1
        
    # Ballbesitz-Wechsel (wenn kein Balls Back)
    if not is_balls_back: 
        change_possession(2 if team_hitting == 1 else 1)
        if live.get('nachwurf') == team_hitting: live['nachwurf'] = None
        if live.get('single_nachwurf_team') == team_hitting: live['single_nachwurf_team'] = None
        
    # Nachwurf prüfen
    if live['t2_cups'] == 0 and live['starter'] == 1 and live['nachwurf'] is None and live.get('single_nachwurf_team') != 2:
        live['nachwurf'] = 2
        if is_balls_back: change_possession(2) # Ball geht zwingend an Gegner für Nachwurf
        log_action(f"🚨 NACHWURF für {names[m['t2_p1']]} & {names[m['t2_p2']]}!")
    elif live['t1_cups'] == 0 and live['starter'] == 2 and live['nachwurf'] is None and live.get('single_nachwurf_team') != 1:
        live['nachwurf'] = 1
        if is_balls_back: change_possession(1)
        log_action(f"🚨 NACHWURF für {names[m['t1_p1']]} & {names[m['t1_p2']]}!")
        
    check_game_over()
    sync_to_cloud()

def do_miss(team):
    save_step()
    live = st.session_state.live
    live['balls_back'] = False
    m = st.session_state.matches[live['match_id']]
    names = st.session_state.players
    t_name = f"{names[m['t1_p1']]} & {names[m['t1_p2']]}" if team == 1 else f"{names[m['t2_p1']]} & {names[m['t2_p2']]}"
    turn = live['stats'][f'turns_t{team}']
    
    s_txt = f"(Stand: {live['t1_cups']}:{live['t2_cups']})"
    log_action(f"[{t_name} | Zug {turn}] 🚫 Kein Treffer {s_txt}")
    
    if team == 1:
        live['stats'][f"p{m['t1_p1']}_t"] += 1; live['stats'][f"p{m['t1_p2']}_t"] += 1
        change_possession(2)
    else:
        live['stats'][f"p{m['t2_p1']}_t"] += 1; live['stats'][f"p{m['t2_p2']}_t"] += 1
        change_possession(1)
        
    if live.get('nachwurf') == team: live['nachwurf'] = None
    check_game_over()
    sync_to_cloud()

def do_miss_single(team, shooter_idx):
    save_step()
    live = st.session_state.live
    live['balls_back'] = False
    names = st.session_state.players
    turn = live['stats'][f'turns_t{team}']
    
    s_txt = f"(Stand: {live['t1_cups']}:{live['t2_cups']})"
    log_action(f"[Team {team} | Zug {turn}] 🚫 Nachwurf verfehlt von {names[shooter_idx]} {s_txt}")
    live['stats'][f"p{shooter_idx}_t"] += 1
    
    live['single_nachwurf_team'] = None 
    change_possession(2 if team == 1 else 1)
    check_game_over()
    sync_to_cloud()

def do_penalty(team, culprit_idx):
    save_step()
    live = st.session_state.live
    names = st.session_state.players
    turn = live['stats'][f'turns_t{team}']
    
    if team == 1: live['t1_cups'] = max(0, live['t1_cups'] - 1)
    else: live['t2_cups'] = max(0, live['t2_cups'] - 1)
    
    s_txt = f"(Stand: {live['t1_cups']}:{live['t2_cups']})"
    log_action(f"[Team {team} | Zug {turn}] ⚠️ Fehler von {names[culprit_idx]} (-1 Becher) {s_txt}")
    
    live['stats'][f'p{culprit_idx}_f'] += 1
    live['pending_penalty'] = None
    check_game_over()
    sync_to_cloud()


# 5. TABS
if st.session_state.admin_auth:
    tab1, tab2, tab3, tab4 = st.tabs(["⚙️ Setup / Archiv", "🎮 Live Spiel", "🏆 Tabelle & Spielplan", "📊 Statistiken"])
else:
    tab3, tab4 = st.tabs(["🏆 Tabelle & Spielplan", "📊 Statistiken"])


if st.session_state.admin_auth:
    # --- TAB 1: SETUP ---
    with tab1:
        st.subheader("📁 Turnier-Verwaltung")
        
        st.write("**Bestehendes Turnier laden**")
        all_t = get_tournament_list()
        if all_t:
            col_l1, col_l2 = st.columns([3, 1])
            with col_l1:
                sel_load = st.selectbox("Wähle ein Turnier aus der Datenbank:", options=list(all_t.keys()), format_func=lambda x: all_t[x])
            with col_l2:
                st.write("") 
                st.write("")
                if st.button("📂 Turnier laden", use_container_width=True):
                    load_tournament(sel_load)
                    st.success(f"Turnier '{all_t[sel_load]}' geladen!")
                    st.rerun()
        else:
            st.info("Noch keine Turniere in der Datenbank.")
            
        st.divider()
        
        st.write("**Neues Turnier anlegen**")
        c1, c2 = st.columns(2)
        with c1:
            new_name = st.text_input("Name für das neue Turnier", "Neues Turnier")
            new_date = st.date_input("Datum", date.today())
        with c2:
            st.write("Spieler:")
            new_p = []
            for i in range(5):
                new_p.append(st.text_input(f"Slot {i+1}", value=f"Spieler {i+1}", key=f"new_p{i}"))
                
        if st.button("🆕 Neues Turnier erstellen & speichern", type="primary"):
            new_id = f"turnier_{int(time.time())}"
            st.session_state.current_tournament_id = new_id
            st.session_state.t_name = new_name
            st.session_state.t_date = str(new_date)
            st.session_state.players = new_p
            st.session_state.matches = generate_fresh_matches()
            st.session_state.live = None
            sync_to_cloud()
            st.success(f"Turnier '{new_name}' erfolgreich erstellt! Du kannst jetzt zu 'Live Spiel' wechseln.")
            st.rerun()

        st.divider()
        
        st.write("**🗑️ Turnier löschen**")
        if all_t:
            col_d1, col_d2 = st.columns([3, 1])
            with col_d1:
                sel_del = st.selectbox("Welches Turnier soll gelöscht werden?", options=list(all_t.keys()), format_func=lambda x: all_t[x], key="del_box")
            with col_d2:
                st.write("")
                st.write("")
                if st.button("🗑️ Löschen", use_container_width=True):
                    st.session_state.confirm_delete = sel_del
                    st.rerun()

            if st.session_state.confirm_delete == sel_del:
                st.error(f"⚠️ Bist du sicher, dass '{all_t[sel_del]}' unwiderruflich gelöscht werden soll?")
                cd1, cd2 = st.columns(2)
                if cd1.button("✔️ Ja, endgültig löschen", type="primary", use_container_width=True):
                    if db_connected:
                        db.collection('bierpong_turniere').document(sel_del).delete()
                        st.session_state.confirm_delete = None
                        if st.session_state.current_tournament_id == sel_del:
                            st.session_state.current_tournament_id = None
                        st.success("Turnier erfolgreich gelöscht.")
                        st.rerun()
                if cd2.button("❌ Abbrechen", use_container_width=True):
                    st.session_state.confirm_delete = None
                    st.rerun()

    # --- TAB 2: LIVE SPIEL ---
    with tab2:
        if not st.session_state.current_tournament_id:
            st.warning("⚠️ Bitte lade zuerst ein Turnier im Setup-Reiter oder erstelle ein neues.")
        elif st.session_state.live is None:
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
                if st.button("✏️ Spiel im Live-Modus bearbeiten", use_container_width=True):
                    st.session_state.live = copy.deepcopy(sel_m['live_backup'])
                    sel_m['t1_score'] = None
                    sel_m['t2_score'] = None
                    sync_to_cloud()
                    st.rerun()
            else:
                if st.button("▶️ Spiel starten", type="primary", use_container_width=True):
                    st.session_state.live = {
                        'match_id': sel_id, 'starter': None, 'possession': None,
                        't1_cups': 10, 't2_cups': 10, 'nachwurf': None, 
                        'balls_back': False, 'pending_bomb': False, 'bomb_team': None,
                        'pending_double_win': False, 'pending_last_cup': False, 'pending_penalty': None,
                        'single_nachwurf_team': None, 'single_nachwurf_shooter': None, 'last_cup_hitter': None,
                        't1_last_scorer': None, 't2_last_scorer': None,
                        'last_scorer': None, 'action_log': [], 'history': [], 'game_state': 'playing',
                        'cups_at_turn_start': {'t1_cups': 10, 't2_cups': 10},
                        'bombs_events': [], 'clutch_nachwurf_events': [],
                        'stats': {
                            'turns_t1': 0, 'turns_t2': 0,
                            f"p{sel_m['t1_p1']}_h": 0, f"p{sel_m['t1_p1']}_t": 0, f"p{sel_m['t1_p1']}_f": 0,
                            f"p{sel_m['t1_p2']}_h": 0, f"p{sel_m['t1_p2']}_t": 0, f"p{sel_m['t1_p2']}_f": 0,
                            f"p{sel_m['t2_p1']}_h": 0, f"p{sel_m['t2_p1']}_t": 0, f"p{sel_m['t2_p1']}_f": 0,
                            f"p{sel_m['t2_p2']}_h": 0, f"p{sel_m['t2_p2']}_t": 0, f"p{sel_m['t2_p2']}_f": 0,
                        }
                    }
                    sync_to_cloud()
                    st.rerun()

        else:
            live = st.session_state.live
            m = st.session_state.matches[live['match_id']]
            names = st.session_state.players
            i_p1, i_p2, i_p3, i_p4 = m['t1_p1'], m['t1_p2'], m['t2_p1'], m['t2_p2']
            p1, p2, p3, p4 = names[i_p1], names[i_p2], names[i_p3], names[i_p4]

            if live['starter'] is None:
                st.info("🪨✂️📄 Wer fängt an?")
                cA, cB = st.columns(2)
                if cA.button(f"{p1} & {p2} beginnen", use_container_width=True): 
                    live['starter'] = 1; live['possession'] = 1; live['stats']['turns_t1'] = 1
                    log_action(f"🏁 {p1} & {p2} fangen an.")
                    sync_to_cloud(); st.rerun()
                if cB.button(f"{p3} & {p4} beginnen", use_container_width=True): 
                    live['starter'] = 2; live['possession'] = 2; live['stats']['turns_t2'] = 1
                    log_action(f"🏁 {p3} & {p4} fangen an.")
                    sync_to_cloud(); st.rerun()
                st.button("❌ Spiel abbrechen", on_click=lambda: st.session_state.update(live=None))
            
            else:
                bg_t1 = "transparent"
                bg_t2 = "transparent"
                
                if live['game_state'] == 't1_won': bg_t1 = "#d4edda"; bg_t2 = "#f8d7da"
                elif live['game_state'] == 't2_won': bg_t1 = "#f8d7da"; bg_t2 = "#d4edda"
                else:
                    if live['possession'] == 1: bg_t1 = "#e6f0fa"
                    elif live['possession'] == 2: bg_t2 = "#e6f0fa"

                if live['game_state'] == 'nachwurf_erfolgreich': st.success("🔥 NACHWURF ERFOLGREICH! Spiel geht weiter.")
                elif live['game_state'] in ['t1_won', 't2_won']: st.success("🎉 SPIEL BEENDET!")
                elif live.get('single_nachwurf_team') or live['nachwurf']: st.error(f"🚨 NACHWURF FÜR TEAM {live.get('single_nachwurf_team') or live['nachwurf']}!")
                elif live['balls_back']: st.success("🔥 BALLS BACK! Nochmal werfen.")

                pct_p1 = get_pct(live['stats'][f'p{i_p1}_h'], live['stats'][f'p{i_p1}_t'])
                pct_p2 = get_pct(live['stats'][f'p{i_p2}_h'], live['stats'][f'p{i_p2}_t'])
                pct_p3 = get_pct(live['stats'][f'p{i_p3}_h'], live['stats'][f'p{i_p3}_t'])
                pct_p4 = get_pct(live['stats'][f'p{i_p4}_h'], live['stats'][f'p{i_p4}_t'])

                disp1, disp_vs, disp2 = st.columns([5, 1, 5])
                
                with disp1:
                    st.markdown(f"<div style='background-color:{bg_t1}; padding:15px; border-radius:10px;'>"
                                f"<div style='text-align: center; line-height: 1.1; margin-bottom: 5px;'>"
                                f"<span style='font-size: 55px; font-weight: bold;'>{live['t1_cups']}</span><span style='font-size: 16px;'> Becher</span></div>"
                                f"<p style='text-align:center; color:gray; font-size:14px; margin:0;'>{'🏁 Starter' if live['starter']==1 else '🛡️ Hat Nachwurf'} | Zug: {live['stats']['turns_t1']}</p>"
                                f"<h3 style='text-align: center; margin-bottom:5px;'>{'👑 ' if live['game_state']=='t1_won' else ''}{p1} & {p2}</h3>"
                                f"<p style='text-align:center; font-size:14px; margin:0;'>{p1}: {live['stats'][f'p{i_p1}_h']} ({pct_p1}%) | {p2}: {live['stats'][f'p{i_p2}_h']} ({pct_p2}%)</p>"
                                f"</div>", unsafe_allow_html=True)

                with disp_vs:
                    st.markdown("<h3 style='text-align: center; margin-top: 45px; color: gray;'>VS</h3>", unsafe_allow_html=True)
                    
                with disp2:
                    st.markdown(f"<div style='background-color:{bg_t2}; padding:15px; border-radius:10px;'>"
                                f"<div style='text-align: center; line-height: 1.1; margin-bottom: 5px;'>"
                                f"<span style='font-size: 55px; font-weight: bold;'>{live['t2_cups']}</span><span style='font-size: 16px;'> Becher</span></div>"
                                f"<p style='text-align:center; color:gray; font-size:14px; margin:0;'>{'🏁 Starter' if live['starter']==2 else '🛡️ Hat Nachwurf'} | Zug: {live['stats']['turns_t2']}</p>"
                                f"<h3 style='text-align: center; margin-bottom:5px;'>{'👑 ' if live['game_state']=='t2_won' else ''}{p3} & {p4}</h3>"
                                f"<p style='text-align:center; font-size:14px; margin:0;'>{p3}: {live['stats'][f'p{i_p3}_h']} ({pct_p3}%) | {p4}: {live['stats'][f'p{i_p4}_h']} ({pct_p4}%)</p>"
                                f"</div>", unsafe_allow_html=True)

                st.write("---")

                if live['game_state'] == 'playing':
                    if live.get('pending_penalty'):
                        team = live['pending_penalty']
                        st.warning(f"⚠️ Wer aus Team {team} hat den Fehler begangen?")
                        c_f1, c_f2 = st.columns(2)
                        if team == 1:
                            if c_f1.button(f"Schuld war {p1}", use_container_width=True): do_penalty(1, i_p1); st.rerun()
                            if c_f2.button(f"Schuld war {p2}", use_container_width=True): do_penalty(1, i_p2); st.rerun()
                        else:
                            if c_f1.button(f"Schuld war {p3}", use_container_width=True): do_penalty(2, i_p3); st.rerun()
                            if c_f2.button(f"Schuld war {p4}", use_container_width=True): do_penalty(2, i_p4); st.rerun()

                    elif live.get('pending_bomb', False):
                        st.warning("💣 DREIFACHTREFFER! Welcher Spieler hat den ZWEITEN Ball versenkt?")
                        bp1, bp2 = st.columns(2)
                        is_n = bool(live['nachwurf'] or live.get('single_nachwurf_team'))
                        if live['bomb_team'] == 1:
                            if bp1.button(f"{p1}", use_container_width=True): do_hit(1, 3, hits=[i_p1, i_p2], bombe_thrower=i_p1, is_balls_back=not is_n, is_clutch_nachwurf=is_n); live['pending_bomb'] = False; st.rerun()
                            if bp2.button(f"{p2}", use_container_width=True): do_hit(1, 3, hits=[i_p1, i_p2], bombe_thrower=i_p2, is_balls_back=not is_n, is_clutch_nachwurf=is_n); live['pending_bomb'] = False; st.rerun()
                        else:
                            if bp1.button(f"{p3}", use_container_width=True): do_hit(2, 3, hits=[i_p3, i_p4], bombe_thrower=i_p3, is_balls_back=not is_n, is_clutch_nachwurf=is_n); live['pending_bomb'] = False; st.rerun()
                            if bp2.button(f"{p4}", use_container_width=True): do_hit(2, 3, hits=[i_p3, i_p4], bombe_thrower=i_p4, is_balls_back=not is_n, is_clutch_nachwurf=is_n); live['pending_bomb'] = False; st.rerun()
                    
                    elif live.get('pending_double_win', False):
                        st.warning("✌️ Doppeltreffer zum Sieg! Wer hat den ZWEITEN Becher getroffen?")
                        cw1, cw2 = st.columns(2)
                        is_n = bool(live['nachwurf'] or live.get('single_nachwurf_team'))
                        if live['bomb_team'] == 1: 
                            if cw1.button(f"{p1} war der Letzte", use_container_width=True): do_hit(1, 2, hits=[i_p2, i_p1], misses=[], is_clutch_nachwurf=is_n, is_balls_back=False); live['pending_double_win'] = False; st.rerun()
                            if cw2.button(f"{p2} war der Letzte", use_container_width=True): do_hit(1, 2, hits=[i_p1, i_p2], misses=[], is_clutch_nachwurf=is_n, is_balls_back=False); live['pending_double_win'] = False; st.rerun()
                        else:
                            if cw1.button(f"{p3} war der Letzte", use_container_width=True): do_hit(2, 2, hits=[i_p4, i_p3], misses=[], is_clutch_nachwurf=is_n, is_balls_back=False); live['pending_double_win'] = False; st.rerun()
                            if cw2.button(f"{p4} war der Letzte", use_container_width=True): do_hit(2, 2, hits=[i_p3, i_p4], misses=[], is_clutch_nachwurf=is_n, is_balls_back=False); live['pending_double_win'] = False; st.rerun()

                    elif live.get('pending_last_cup', False):
                        st.warning("🏆 Letzter Treffer! In welchem Wurf wurde der Becher getroffen?")
                        c_w1, c_w2 = st.columns(2)
                        team = 1 if live['possession'] == 1 else 2
                        hitter_idx = live['last_cup_hitter']
                        partner_idx = i_p2 if hitter_idx == i_p1 else (i_p1 if hitter_idx == i_p2 else (i_p4 if hitter_idx == i_p3 else i_p3))
                        is_n = bool(live['nachwurf'] or live.get('single_nachwurf_team'))
                        
                        if c_w1.button("Im 1. Wurf (Gegner hat 1 Nachwurf)", use_container_width=True):
                            if team == 1 and live['starter'] == 1: live['single_nachwurf_team'] = 2
                            if team == 2 and live['starter'] == 2: live['single_nachwurf_team'] = 1
                            do_hit(team, 1, hits=[hitter_idx], misses=[], is_clutch_nachwurf=is_n, is_balls_back=False)
                            live['pending_last_cup'] = False; st.rerun()
                        
                        if c_w2.button("Im 2. Wurf (Gegner hat 2 Nachwürfe)", use_container_width=True):
                            do_hit(team, 1, hits=[hitter_idx], misses=[partner_idx], is_clutch_nachwurf=is_n, is_balls_back=False) 
                            live['pending_last_cup'] = False; st.rerun()

                    elif live.get('single_nachwurf_team') == 1 and live['possession'] == 1:
                        if live.get('single_nachwurf_shooter') is None:
                            st.warning("🚨 Euer Team hat nur EINEN EINZIGEN Nachwurf! Wer wirft?")
                            sn1, sn2 = st.columns(2)
                            if sn1.button(f"🎯 {p1} wirft", use_container_width=True): save_step(); live['single_nachwurf_shooter'] = i_p1; sync_to_cloud(); st.rerun()
                            if sn2.button(f"🎯 {p2} wirft", use_container_width=True): save_step(); live['single_nachwurf_shooter'] = i_p2; sync_to_cloud(); st.rerun()
                        else:
                            shooter_idx = live['single_nachwurf_shooter']
                            st.info(f"Nachwurf von {names[shooter_idx]}")
                            snc1, snc2 = st.columns(2)
                            if snc1.button("🎯 Treffer!", use_container_width=True): do_hit(1, 1, hits=[shooter_idx], misses=[], is_clutch_nachwurf=True); st.rerun()
                            if snc2.button("🚫 Verfehlt (Verloren)", use_container_width=True): do_miss_single(1, shooter_idx); st.rerun()

                    elif live.get('single_nachwurf_team') == 2 and live['possession'] == 2:
                        if live.get('single_nachwurf_shooter') is None:
                            st.warning("🚨 Euer Team hat nur EINEN EINZIGEN Nachwurf! Wer wirft?")
                            sn1, sn2 = st.columns(2)
                            if sn1.button(f"🎯 {p3} wirft", use_container_width=True): save_step(); live['single_nachwurf_shooter'] = i_p3; sync_to_cloud(); st.rerun()
                            if sn2.button(f"🎯 {p4} wirft", use_container_width=True): save_step(); live['single_nachwurf_shooter'] = i_p4; sync_to_cloud(); st.rerun()
                        else:
                            shooter_idx = live['single_nachwurf_shooter']
                            st.info(f"Nachwurf von {names[shooter_idx]}")
                            snc1, snc2 = st.columns(2)
                            if snc1.button("🎯 Treffer!", use_container_width=True): do_hit(2, 1, hits=[shooter_idx], misses=[], is_clutch_nachwurf=True); st.rerun()
                            if snc2.button("🚫 Verfehlt (Verloren)", use_container_width=True): do_miss_single(2, shooter_idx); st.rerun()

                    else:
                        colL, colR = st.columns(2)
                        with colL:
                            if live['possession'] == 1:
                                st.button("🚫 Kein Treffer (Wechsel)", use_container_width=True, on_click=lambda: do_miss(1))
                                c_h1, c_h2 = st.columns(2)
                                is_n = bool(live['nachwurf'])
                                if c_h1.button(f"🎯 Treffer {p1}", use_container_width=True): 
                                    if live['t2_cups'] == 1: save_step(); live['pending_last_cup'] = True; live['last_cup_hitter'] = i_p1; sync_to_cloud(); st.rerun()
                                    else: do_hit(1, 1, hits=[i_p1], misses=[i_p2], is_clutch_nachwurf=is_n); st.rerun()
                                if c_h2.button(f"🎯 Treffer {p2}", use_container_width=True): 
                                    if live['t2_cups'] == 1: save_step(); live['pending_last_cup'] = True; live['last_cup_hitter'] = i_p2; sync_to_cloud(); st.rerun()
                                    else: do_hit(1, 1, hits=[i_p2], misses=[i_p1], is_clutch_nachwurf=is_n); st.rerun()
                                
                                if live['t2_cups'] > 1:
                                    c_s1, c_s2 = st.columns(2)
                                    if c_s1.button("✌️ Doppel (-2)", use_container_width=True): 
                                        if live['t2_cups'] == 2: save_step(); live['pending_double_win'] = True; live['bomb_team'] = 1; sync_to_cloud(); st.rerun()
                                        else: do_hit(1, 2, hits=[i_p1, i_p2], is_balls_back=not is_n, is_clutch_nachwurf=is_n); st.rerun()
                                    if c_s2.button("💣 Dreifach (-3)", use_container_width=True): 
                                        save_step(); live['pending_bomb'] = True; live['bomb_team'] = 1; sync_to_cloud(); st.rerun()
                            st.write("")
                            if st.button("⚠️ Fehler Team 1", use_container_width=True): save_step(); live['pending_penalty'] = 1; sync_to_cloud(); st.rerun()

                        with colR:
                            if live['possession'] == 2:
                                st.button("🚫 Kein Treffer (Wechsel)", use_container_width=True, on_click=lambda: do_miss(2))
                                c_h3, c_h4 = st.columns(2)
                                is_n = bool(live['nachwurf'])
                                if c_h3.button(f"🎯 Treffer {p3}", use_container_width=True): 
                                    if live['t1_cups'] == 1: save_step(); live['pending_last_cup'] = True; live['last_cup_hitter'] = i_p3; sync_to_cloud(); st.rerun()
                                    else: do_hit(2, 1, hits=[i_p3], misses=[i_p4], is_clutch_nachwurf=is_n); st.rerun()
                                if c_h4.button(f"🎯 Treffer {p4}", use_container_width=True): 
                                    if live['t1_cups'] == 1: save_step(); live['pending_last_cup'] = True; live['last_cup_hitter'] = i_p4; sync_to_cloud(); st.rerun()
                                    else: do_hit(2, 1, hits=[i_p4], misses=[i_p3], is_clutch_nachwurf=is_n); st.rerun()
                                
                                if live['t1_cups'] > 1:
                                    c_s3, c_s4 = st.columns(2)
                                    if c_s3.button("✌️ Doppel (-2)", use_container_width=True): 
                                        if live['t1_cups'] == 2: save_step(); live['pending_double_win'] = True; live['bomb_team'] = 2; sync_to_cloud(); st.rerun()
                                        else: do_hit(2, 2, hits=[i_p3, i_p4], is_balls_back=not is_n, is_clutch_nachwurf=is_n); st.rerun()
                                    if c_s4.button("💣 Dreifach (-3)", use_container_width=True): 
                                        save_step(); live['pending_bomb'] = True; live['bomb_team'] = 2; sync_to_cloud(); st.rerun()
                            st.write("")
                            if st.button("⚠️ Fehler Team 2", use_container_width=True): save_step(); live['pending_penalty'] = 2; sync_to_cloud(); st.rerun()

                st.write("---")
                ctrl1, ctrl2, ctrl3 = st.columns(3)
                with ctrl1:
                    if st.button("↩️ Undo", use_container_width=True, disabled=not live['history']):
                        last = live['history'].pop()
                        live.update(last)
                        sync_to_cloud()
                        st.rerun()
                        
                with ctrl2:
                    if st.session_state.confirm_abort:
                        st.warning("Wirklich abbrechen?")
                        cy, cn = st.columns(2)
                        if cy.button("✔️ Ja", use_container_width=True): st.session_state.live = None; st.session_state.confirm_abort = False; sync_to_cloud(); st.rerun()
                        if cn.button("❌ Nein", use_container_width=True): st.session_state.confirm_abort = False; st.rerun()
                    else:
                        if st.button("❌ Spiel Abbrechen", use_container_width=True): st.session_state.confirm_abort = True; st.rerun()
                            
                with ctrl3:
                    if live['game_state'] in ['t1_won', 't2_won']:
                        if st.button("💾 Ergebnis speichern & Schließen", use_container_width=True, type="primary"):
                            m['t1_score'] = live['t1_cups']
                            m['t2_score'] = live['t2_cups']
                            m['stats'] = copy.deepcopy(live['stats'])
                            
                            if live['game_state'] == 't1_won': m['last_scorer'] = live.get('t1_last_scorer')
                            else: m['last_scorer'] = live.get('t2_last_scorer')
                            
                            m['action_log'] = copy.deepcopy(live['action_log'])
                            m['bombs_events'] = copy.deepcopy(live['bombs_events'])
                            m['clutch_nachwurf_events'] = copy.deepcopy(live['clutch_nachwurf_events'])
                            
                            if live['game_state'] == 't1_won': m['winner_turns'] = live['stats']['turns_t1'] 
                            else: m['winner_turns'] = live['stats']['turns_t2']
                            
                            m['live_backup'] = copy.deepcopy(live)
                            st.session_state.live = None
                            sync_to_cloud()
                            st.rerun()
                    elif live['game_state'] == 'nachwurf_erfolgreich':
                        if st.button("🔄 Spielstand zurücksetzen (Verlängerung)", use_container_width=True, type="primary"):
                            log_action("🔄 Nachwurf erfolgreich! Spielstand auf Beginn der Runde zurückgesetzt.")
                            live['t1_cups'] = live['cups_at_turn_start']['t1_cups']
                            live['t2_cups'] = live['cups_at_turn_start']['t2_cups']
                            live['nachwurf'] = None 
                            live['single_nachwurf_team'] = None
                            live['single_nachwurf_shooter'] = None
                            live['game_state'] = 'playing'
                            live['possession'] = live['starter'] 
                            if live['starter'] == 1: live['stats']['turns_t1'] += 1
                            else: live['stats']['turns_t2'] += 1
                            sync_to_cloud()
                            st.rerun()
                    else:
                        st.button("💾 Ergebnis speichern", use_container_width=True, disabled=True)

# --- TAB 3: TABELLE & SPIELPLAN (Für ALLE sichtbar) ---
with tab3:
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

    df_table = pd.DataFrame(player_stats).sort_values(by=['Score'], ascending=False).reset_index(drop=True)
    df_table.index += 1
    df_table.insert(0, 'RANG', df_table.index.map(lambda x: ["1 🏆", "2 🥈", "3 🥉", "4", "5"][x-1] if x<=5 else str(x)))
    
    def style_df(val):
        if val == 'Eliminated': return 'color: #9C0006; font-weight: bold'
        if val == 'Titel drin': return 'color: #008000; font-weight: bold'
        if val == '👑 MEISTER': return 'background-color: #FFD966; color: black; font-weight: bold'
        if isinstance(val, int) and val > 0: return 'color: #008000; font-weight: bold'
        if isinstance(val, int) and val < 0: return 'color: #FF0000; font-weight: bold'
        if isinstance(val, str) and 'S' in val and val != "STATUS": return 'color: #008000; font-weight: bold'
        if isinstance(val, str) and 'N' in val and val != "NAME" and val != "STATUS": return 'color: #FF0000; font-weight: bold'
        return ''

    st.dataframe(df_table[['RANG', 'NAME', 'SP', 'S', 'N', 'DIFF', 'S%', 'SERIE', ' ', 'STATUS']].style.map(style_df), hide_index=True, use_container_width=True)

    st.divider()
    st.subheader("📅 Spielplan")
    
    match_export = []
    for m in matches:
        p1, p2 = players[m['t1_p1']], players[m['t1_p2']]
        p3, p4 = players[m['t2_p1']], players[m['t2_p2']]
        
        if m['t1_score'] is not None:
            if m['t1_score'] > m['t2_score']: t1_c, t2_c = "#198754", "#dc3545"
            elif m['t2_score'] > m['t1_score']: t1_c, t2_c = "#dc3545", "#198754"
            else: t1_c, t2_c = "inherit", "inherit"
            
            match_export.append({'Spiel': f"Spiel {m['id']+1}", 'Team 1': f"{p1} & {p2}", 'Team 2': f"{p3} & {p4}", 'Ergebnis': f"{m['t1_score']} : {m['t2_score']}"})
            
            st.markdown(f"<div style='padding:10px; background-color:#f8f9fa; border-radius:5px; margin-bottom:5px; text-align:center; font-size:16px;'>"
                        f"<b>Spiel {m['id']+1}:</b> &nbsp;&nbsp;&nbsp; <span style='color:{t1_c}; font-weight:bold;'>{p1} & {p2}</span> "
                        f"&nbsp;&nbsp;&nbsp;<b>{m['t1_score']} : {m['t2_score']}</b>&nbsp;&nbsp;&nbsp; "
                        f"<span style='color:{t2_c}; font-weight:bold;'>{p3} & {p4}</span></div>", 
                        unsafe_allow_html=True)
            with st.expander("📄 Spielbericht anzeigen"):
                if m.get('action_log'):
                    for entry in m['action_log']: st.caption(entry)
                else: st.caption("Kein Log vorhanden")
        elif st.session_state.live and st.session_state.live['match_id'] == m['id']:
            match_export.append({'Spiel': f"Spiel {m['id']+1}", 'Team 1': f"{p1} & {p2}", 'Team 2': f"{p3} & {p4}", 'Ergebnis': "LÄUFT GERADE"})
            st.warning(f"🔴 LÄUFT GERADE: Spiel {m['id']+1} | {p1} & {p2} VS {p3} & {p4}")
        else:
            match_export.append({'Spiel': f"Spiel {m['id']+1}", 'Team 1': f"{p1} & {p2}", 'Team 2': f"{p3} & {p4}", 'Ergebnis': "- : -"})
            st.write(f"⚪ Spiel {m['id']+1} | {p1} & {p2} VS {p3} & {p4}")
            
    df_matches = pd.DataFrame(match_export)

# --- TAB 4: STATISTIKEN & EXCEL EXPORT ---
with tab4:
    st.subheader("📊 Einzel- & Event-Statistiken")
    
    ind_stats = []
    for i, p in enumerate(st.session_state.players):
        hits = throws = gw = fehler = bombs = clutch = 0
        for m in st.session_state.matches:
            if m['t1_score'] is not None and m['stats'] is not None:
                hits += m['stats'].get(f'p{i}_h', 0)
                throws += m['stats'].get(f'p{i}_t', 0)
                fehler += m['stats'].get(f'p{i}_f', 0)
                if m.get('last_scorer') == i: gw += 1
                bombs += sum(1 for b in m.get('bombs_events', []) if b == i)
                clutch += sum(1 for c in m.get('clutch_nachwurf_events', []) if c == i)
        
        quote = (hits / throws * 100) if throws > 0 else 0.0
        ind_stats.append({
            'NAME': p, 'TREFFER': hits, 'WÜRFE': throws, 'QUOTE_VAL': quote, 'QUOTE': f"{quote:.2f} %", 
            'SIEGTREFFER': gw, 'DREIFACHBECHER-TREFFER': bombs, 'NACHWURF RETTER': clutch, 'FEHLER': fehler
        })
    
    df_ind = pd.DataFrame(ind_stats)
    
    c_s1, c_s2 = st.columns(2)
    with c_s1:
        st.write("**🎯 Trefferquoten**")
        df_quote = df_ind.sort_values(by=['QUOTE_VAL', 'TREFFER'], ascending=[False, False]).reset_index(drop=True)
        df_quote.index += 1
        df_quote.insert(0, 'RANG', df_quote.index)
        st.dataframe(df_quote[['RANG', 'NAME', 'TREFFER', 'WÜRFE', 'QUOTE']], hide_index=True, use_container_width=True)

    with c_s2:
        st.write("**🔪 Vollstrecker (Game Winners)**")
        df_gw = df_ind[df_ind['SIEGTREFFER'] > 0].sort_values(by='SIEGTREFFER', ascending=False).reset_index(drop=True)
        if not df_gw.empty:
            df_gw.index += 1
            df_gw.insert(0, 'RANG', df_gw.index)
            st.dataframe(df_gw[['RANG', 'NAME', 'SIEGTREFFER']], hide_index=True, use_container_width=True)
        else: st.caption("Noch kein Ereignis.")

    st.write("---")
    col_e1, col_e2, col_e3 = st.columns(3)
    
    with col_e1:
        st.write("**💣 Dreifachbecher-Treffer**")
        df_bomb = df_ind[df_ind['DREIFACHBECHER-TREFFER'] > 0].sort_values(by='DREIFACHBECHER-TREFFER', ascending=False).reset_index(drop=True)
        if not df_bomb.empty:
            df_bomb.index += 1
            df_bomb.insert(0, 'RANG', df_bomb.index)
            st.dataframe(df_bomb[['RANG', 'NAME', 'DREIFACHBECHER-TREFFER']], hide_index=True, use_container_width=True)
        else: st.caption("Noch kein Ereignis.")
            
    with col_e2:
        st.write("**🚑 Nachwurf Retter**")
        df_clutch = df_ind[df_ind['NACHWURF RETTER'] > 0].sort_values(by='NACHWURF RETTER', ascending=False).reset_index(drop=True)
        if not df_clutch.empty:
            df_clutch.index += 1
            df_clutch.insert(0, 'RANG', df_clutch.index)
            st.dataframe(df_clutch[['RANG', 'NAME', 'NACHWURF RETTER']], hide_index=True, use_container_width=True)
        else: st.caption("Noch kein Ereignis.")
            
    with col_e3:
        st.write("**🤡 Dummkopf (Fehler)**")
        df_dk = df_ind[df_ind['FEHLER'] > 0].sort_values(by='FEHLER', ascending=False).reset_index(drop=True)
        if not df_dk.empty:
            df_dk.index += 1
            df_dk.insert(0, 'RANG', df_dk.index)
            st.dataframe(df_dk[['RANG', 'NAME', 'FEHLER']], hide_index=True, use_container_width=True)
        else: st.caption("Noch kein Fehler begangen.")

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
            st.caption("Noch keine Spiele absolviert.")

    with col_m2:
        st.write("**⚡ Schnellste Siege (Blitzkrieg - Top 3)**")
        if match_data:
            df_bk = pd.DataFrame(match_data).sort_values(by='ZÜGE (SIEGER)', ascending=True).head(3).reset_index(drop=True)
            df_bk.index += 1
            df_bk.insert(0, 'RANG', df_bk.index)
            st.dataframe(df_bk[['RANG', 'SPIEL', 'ZÜGE (SIEGER)', 'ERGEBNIS']], hide_index=True, use_container_width=True)
        else:
            st.caption("Noch keine Spiele absolviert.")

    st.write("---")
    # EXCEL EXPORT (Alle Tabellen)
    st.subheader("💾 Turnier Archivieren")
    st.write("Lade dir das komplette Turnier als Excel-Datei herunter.")
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_table[['RANG', 'NAME', 'SP', 'S', 'N', 'DIFF', 'S%', 'SERIE', 'STATUS']].to_excel(writer, sheet_name="Tabelle", index=False)
        df_matches.to_excel(writer, sheet_name="Spielplan", index=False)
        df_quote[['RANG', 'NAME', 'TREFFER', 'WÜRFE', 'QUOTE']].to_excel(writer, sheet_name="Trefferquoten", index=False)
        if not df_gw.empty: df_gw[['RANG', 'NAME', 'SIEGTREFFER']].to_excel(writer, sheet_name="Vollstrecker", index=False)
        if not df_bomb.empty: df_bomb[['RANG', 'NAME', 'DREIFACHBECHER-TREFFER']].to_excel(writer, sheet_name="Dreifachbecher", index=False)
        if not df_clutch.empty: df_clutch[['RANG', 'NAME', 'NACHWURF RETTER']].to_excel(writer, sheet_name="Nachwurf Retter", index=False)
        if not df_dk.empty: df_dk[['RANG', 'NAME', 'FEHLER']].to_excel(writer, sheet_name="Dummkopf", index=False)
        if match_data: 
            df_hs[['RANG', 'SPIEL', 'ERGEBNIS', 'DIFF', 'ZÜGE (SIEGER)']].to_excel(writer, sheet_name="Höchste Siege", index=False)
            df_bk[['RANG', 'SPIEL', 'ZÜGE (SIEGER)', 'ERGEBNIS']].to_excel(writer, sheet_name="Schnellste Siege", index=False)
        
    st.download_button(
        label="📥 Gesamtes Turnier als Excel speichern",
        data=buffer.getvalue(),
        file_name=f"Bierpong_Turnier_{st.session_state.t_date}.xlsx",
        mime="application/vnd.ms-excel",
        type="primary"
    )
