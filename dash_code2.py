import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURAZIONE E CARICAMENTO ---
st.set_page_config(page_title="PRO Analytics - Polymarket Bot", layout="wide")
base_path = os.path.dirname(__file__)
json_path = os.path.join(base_path, 'paper_portfolio.json')

@st.cache_data
def load_and_process():
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # Processo Storico
    df = pd.DataFrame(data['history'])
    df['dt_entrata'] = pd.to_datetime(df['timestamp'], unit='s')
    df['dt_uscita'] = pd.to_datetime(df['exit_timestamp'], unit='s')
    df['durata_ore'] = (df['dt_uscita'] - df['dt_entrata']).dt.total_seconds() / 3600
    df['giorno'] = df['dt_uscita'].dt.date
    df['ora'] = df['dt_uscita'].dt.hour
    
    # Pulizia nomi Leader
    df['leader_short'] = df['leader'].str[:6] + "..." + df['leader'].str[-4:]
    
    return data, df

data, df = load_and_process()

# --- HEADER STATS ---
st.title("🛡️ Terminale di Analisi Professionale")
s = data['stats']
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Capitale Totale", f"${data['balance']:.2f}")
c2.metric("Win Rate Globale", f"{(s['wins']/s['exits']*100):.1f}%")
c3.metric("Profitto Netto", f"${s['realized_pnl']:.2f}")
c4.metric("Trade Chiusi", s['exits'])
c5.metric("ROI Totale", f"{((data['balance']-100)/100*100):.1f}%")

st.divider()

# --- TABS ---
t1, t2, t3 = st.tabs(["📊 Leaderboard Wallet", "📈 Analisi Strategia", "📋 Registro Trade Dettagliato"])

with t1:
    st.subheader("Classifica Performance Wallet Leader")
    # Aggregazione Pro per Leader
    leader_stats = df.groupby('leader').agg({
        'pnl': ['sum', 'count', 'mean'],
        'pnl_pct': 'mean',
        'durata_ore': 'mean'
    })
    leader_stats.columns = ['Profitto_Totale', 'Num_Trade', 'Profitto_Medio_$', 'ROI_Medio_%', 'Durata_Media_Ore']
    
    # Calcolo Win Rate per Leader
    wins = df[df['pnl'] > 0].groupby('leader').size()
    leader_stats['Win_Rate_%'] = (wins / leader_stats['Num_Trade'] * 100).fillna(0).round(1)
    
    st.dataframe(leader_stats.sort_values('Profitto_Totale', ascending=False), use_container_width=True)
    
    # Grafico Profitto per Leader
    fig_lead = px.bar(leader_stats.reset_index(), x='leader', y='Profitto_Totale', color='Win_Rate_%',
                     title="Contributo al Profitto per ogni Leader")
    st.plotly_chart(fig_lead, use_container_width=True)

with t2:
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Distribuzione Oraria dei Profitti")
        hourly = df.groupby('ora')['pnl'].sum().reset_index()
        st.plotly_chart(px.bar(hourly, x='ora', y='pnl'), use_container_width=True)
    
    with col_b:
        st.subheader("Motivi di Chiusura Trade")
        reasons = df['exit_reason'].value_counts().reset_index()
        st.plotly_chart(px.pie(reasons, names='exit_reason', values='count', hole=0.4), use_container_width=True)

with t3:
    st.subheader("Tutti i dati tecnici dei trade conclusi")
    # Tabella con TUTTE le informazioni
    cols_pro = ['dt_entrata', 'dt_uscita', 'market', 'side', 'entry_price', 'exit_price', 'cost', 'pnl', 'pnl_pct', 'durata_ore', 'exit_reason', 'leader']
    st.dataframe(df[cols_pro].sort_values('dt_uscita', ascending=False), use_container_width=True)
