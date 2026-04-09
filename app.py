import streamlit as st
import pandas as pd

# 1. Seiten-Design einstellen
st.set_page_config(page_title="Bierpong Meister-Turnier", page_icon="🍺", layout="wide")
st.title("👑 Bierpong Meister-Turnier")

# 2. Speicher der App initialisieren (Session State)
# Im Gegensatz zu Excel muss eine Web-App sich Daten aktiv "merken"
if 'players' not in st.session_state:
    st.session_state.players = ['Spieler 1', 'Spieler 2', 'Spieler 3', 'Spieler 4', 'Spieler 5']

if 'matches' not in st.session_state:
    # Die 15 festen Spiele aus unserer Logik
    games_logic = [
        [0, 1, 2, 3], [1, 2, 3, 4], [2, 3, 4, 0], [3, 4, 0, 1], [4, 0, 1, 2],
        [0, 2, 1, 3], [1, 3, 2, 4], [2, 4, 3, 0], [3, 0, 4, 1], [4, 1, 0, 2],
        [0, 3, 1, 2], [1, 4, 2, 3], [2, 0, 3, 4], [3, 1, 4, 0], [4, 2, 0, 1]
    ]
    matches = []
    for i, game in enumerate(games_logic):
        matches.append({
            "Spiel": i + 1,
            "T1_P1": game[0], "T1_P2": game[1],
            "T2_P1": game[2], "T2_P2": game[3],
            "Tore_T1": None, "Tore_T2": None
        })
    st.session_state.matches = matches

# 3. Das Seitenmenü (Sidebar) für die Spielernamen
with st.sidebar:
    st.header("⚙️ Einstellungen")
    st.write("Namen ändern:")
    for i in range(5):
        # Textfeld für jeden Spieler
        st.session_state.players[i] = st.text_input(f"Slot {i+1}", value=st.session_state.players[i])

# 4. Die Reiter (Tabs) im Hauptbereich
tab1, tab2 = st.tabs(["📝 Spielplan & Eingabe", "🏆 Tabelle & Statistiken"])

# TAB 1: DER SPIELPLAN
with tab1:
    st.subheader("Spielergebnisse")
    st.write("Trage hier die getroffenen Becher (max. 10) ein.")
    
    # Für jedes Spiel eine Zeile generieren
    for i, match in enumerate(st.session_state.matches):
        col1, col2, col3, col4, col5 = st.columns([1, 3, 2, 3, 1])
        
        # Namen aus dem Speicher holen
        p1 = st.session_state.players[match["T1_P1"]]
        p2 = st.session_state.players[match["T1_P2"]]
        p3 = st.session_state.players[match["T2_P1"]]
        p4 = st.session_state.players[match["T2_P2"]]
        
        with col1:
            st.write(f"**Spiel {match['Spiel']}**")
        with col2:
            st.write(f"{p1} & {p2}")
        with col3:
            # Layout für die Eingabefelder nebeneinander
            t1_col, trenner, t2_col = st.columns([2, 1, 2])
            with t1_col:
                t1_input = st.number_input("T1", min_value=0, max_value=10, key=f"t1_{i}", value=match["Tore_T1"], label_visibility="collapsed")
            with trenner:
                st.write(":")
            with t2_col:
                t2_input = st.number_input("T2", min_value=0, max_value=10, key=f"t2_{i}", value=match["Tore_T2"], label_visibility="collapsed")
            
            # Werte im Hintergrund speichern
            st.session_state.matches[i]["Tore_T1"] = t1_input
            st.session_state.matches[i]["Tore_T2"] = t2_input
        with col4:
            st.write(f"{p3} & {p4}")
        with col5:
            st.write(" ") # Platzhalter für spätere Features wie "Bombe"

# TAB 2: DIE TABELLE (Wird im nächsten Schritt befüllt)
with tab2:
    st.subheader("Die Meister-Tabelle")
    st.info("Die App ist erfolgreich online! Im nächsten Schritt übertragen wir unsere komplette Excel-Mathematik (inkl. Status, Serien und Top-Duos) in diesen Bereich.")
