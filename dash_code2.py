import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# --- CONFIGURAZIONE PERCORSO FILE ---
# Questa parte istruisce Python a cercare il file nella stessa cartella dello script
base_path = os.path.dirname(__file__)
json_path = os.path.join(base_path, 'paper_portfolio.json')

# Configura la pagina
st.set_page_config(page_title="Dashboard Paper Trading", layout="wide")
st.title("📈 Dashboard Analisi Paper Trading")

# --- CARICAMENTO DATI ---
try:
    with open(json_path, 'r') as f:
        data = json.load(f)
except FileNotFoundError:
    st.error(f"❌ Errore: Il file '{json_path}' non è stato trovato.")
    st.info("Assicurati che il file 'paper_portfolio.json' sia caricato nella stessa cartella di questo script su GitHub.")
    st.stop()

# --- 1. SEZIONE METRICHE (Riepilogo) ---
stats = data.get("stats", {})
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Saldo Attuale", f"${data.get('balance', 0):.2f}")
with col2:
    st.metric("Saldo Iniziale", f"${data.get('starting_balance', 0):.2f}")
with col3:
    win_rate = (stats.get('wins', 0) / stats.get('exits', 1)) * 100
    st.metric("Win Rate", f"{win_rate:.1f}%", f"{stats.get('wins', 0)} ✅ / {stats.get('losses', 0)} ❌")
with col4:
    net_pnl = data.get('balance', 0) - data.get('starting_balance', 0)
    st.metric("Profitto Netto", f"${net_pnl:.2f}", f"{(net_pnl/data.get('starting_balance',1))*100:.1f}% ROI")

st.divider()

# --- 2. SEZIONE TABELLE ---
tab1, tab2 = st.tabs(["📜 Storico (Trade Conclusi)", "🔍 Posizioni Aperte"])

with tab1:
    st.subheader("Registro Storico Completo")
    if data.get("history"):
        df_history = pd.DataFrame(data["history"])
        # Converte i timestamp in date leggibili
        df_history['Data Entrata'] = pd.to_datetime(df_history['timestamp'], unit='s').dt.strftime('%Y-%m-%d %H:%M')
        df_history['Data Uscita'] = pd.to_datetime(df_history['exit_timestamp'], unit='s').dt.strftime('%Y-%m-%d %H:%M')
        
        # Selezione colonne per pulizia visuale
        cols = ['Data Entrata', 'market', 'side', 'entry_price', 'exit_price', 'pnl', 'pnl_pct', 'exit_reason', 'Data Uscita']
        df_history = df_history[[c for c in cols if c in df_history.columns]]
        
        # Colorazione righe (Verde per profitto, Rosso per perdita)
        st.dataframe(df_history.sort_values(by='Data Uscita', ascending=False), use_container_width=True)
    else:
        st.info("Nessuna operazione conclusa trovata.")

with tab2:
    st.subheader("Operazioni Attualmente in Corso")
    if data.get("positions"):
        df_positions = pd.DataFrame(data["positions"])
        df_positions['Data Entrata'] = pd.to_datetime(df_positions['timestamp'], unit='s').dt.strftime('%Y-%m-%d %H:%M')
        
        cols_pos = ['Data Entrata', 'market', 'side', 'entry_price', 'size', 'cost']
        df_positions = df_positions[[c for c in cols_pos if c in df_positions.columns]]
        
        st.dataframe(df_positions.sort_values(by='Data Entrata', ascending=False), use_container_width=True)
    else:
        st.info("Nessuna posizione aperta al momento.")
