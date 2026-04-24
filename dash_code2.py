import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Polymarket Bot Analytics", layout="wide")
base_path = os.path.dirname(__file__)
json_path = os.path.join(base_path, 'paper_portfolio.json')

def load_data():
    with open(json_path, 'r') as f:
        return json.load(f)

try:
    data = load_data()
except Exception as e:
    st.error(f"Errore nel caricamento: {e}")
    st.stop()

# --- ELABORAZIONE DATI ---
df = pd.DataFrame(data['history'])
df['dt_uscita'] = pd.to_datetime(df['exit_timestamp'], unit='s')
df['ora'] = df['dt_uscita'].dt.hour
df['giorno_settimana'] = df['dt_uscita'].dt.day_name()
df = df.sort_values('dt_uscita')
df['cum_pnl'] = df['pnl'].cumsum()

# --- UI - HEADER ---
st.title("🚀 Analisi Avanzata Bot Polymarket")
stats = data['stats']
c1, c2, c3, c4 = st.columns(4)
c1.metric("Bilancio Finale", f"${data['balance']:.2f}")
c2.metric("Win Rate", f"{(stats['wins']/stats['exits']*100):.1f}%")
c3.metric("Profitto Totale", f"${stats['total_profit']:.2f}", delta_color="normal")
c4.metric("Max Perdita Singola", f"-${stats['total_loss']:.2f}")

st.divider()

# --- GRAFICI ---
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📈 Curva di Crescita (Equity Curve)")
    fig_equity = px.line(df, x='dt_uscita', y='cum_pnl', 
                         title="Andamento del Profitto nel Tempo",
                         labels={'cum_pnl': 'Profitto Cumulativo ($)', 'dt_uscita': 'Data'})
    st.plotly_chart(fig_equity, use_container_width=True)

with col_right:
    st.subheader("⏰ Performance per Ora (UTC)")
    hourly_pnl = df.groupby('ora')['pnl'].sum().reset_index()
    fig_hour = px.bar(hourly_pnl, x='ora', y='pnl', 
                      title="Profitto Totale suddiviso per Fascia Oraria",
                      labels={'pnl': 'Profitto ($)', 'ora': 'Ora del giorno'})
    st.plotly_chart(fig_hour, use_container_width=True)

st.divider()

# --- ANALISI DETTAGLIATA ---
st.subheader("📊 Analisi per Giorno della Settimana")
day_pnl = df.groupby('giorno_settimana')['pnl'].agg(['sum', 'count']).reset_index()
fig_day = px.bar(day_pnl, x='giorno_settimana', y='sum', color='count',
                 title="Dove guadagna di più il bot?",
                 labels={'sum': 'Profitto Totale ($)', 'giorno_settimana': 'Giorno', 'count': 'Num. Trade'})
st.plotly_chart(fig_day, use_container_width=True)

# --- TABELLE ---
st.divider()
st.subheader("📋 Storico Trade Completo")
st.dataframe(df[['dt_uscita', 'market', 'side', 'entry_price', 'exit_price', 'pnl', 'pnl_pct', 'exit_reason']], 
             use_container_width=True)
