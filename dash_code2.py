import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURAZIONE TERMINALE ---
st.set_page_config(page_title="QUANT TERMINAL v2.0 - Polymarket", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #E0E0E0; }
    .stMetric { background-color: #161B22; padding: 20px; border-radius: 10px; border: 1px solid #30363D; }
    </style>
    """, unsafe_allow_html=True)

base_path = os.path.dirname(__file__)
json_path = os.path.join(base_path, 'paper_portfolio.json')

# --- MOTORE DI ELABORAZIONE ---
@st.cache_data
def load_and_crunch_data():
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    df = pd.DataFrame(data['history'])
    if df.empty: return data, df, pd.DataFrame()

    # Formattazione Tempi
    df['dt_entrata'] = pd.to_datetime(df['timestamp'], unit='s')
    df['dt_uscita'] = pd.to_datetime(df['exit_timestamp'], unit='s')
    df['giorno_sett'] = df['dt_uscita'].dt.day_name()
    df['ora'] = df['dt_uscita'].dt.hour
    df['durata_h'] = (df['dt_uscita'] - df['dt_entrata']).dt.total_seconds() / 3600
    
    # Ordinamento e Equity
    df = df.sort_values('dt_uscita').reset_index(drop=True)
    df['cum_pnl'] = df['pnl'].cumsum()
    df['rolling_max'] = df['cum_pnl'].cummax()
    df['drawdown'] = df['cum_pnl'] - df['rolling_max']
    
    # Leaderboard Processing
    leaders = df.groupby('leader').agg(
        Profitto_Tot=('pnl', 'sum'),
        Trade_Tot=('pnl', 'count'),
        Win_Rate=('pnl', lambda x: (x > 0).mean() * 100),
        ROI_Medio=('pnl_pct', 'mean')
    ).reset_index()
    
    return data, df, leaders

try:
    data, df, leaders = load_and_crunch_data()
except Exception as e:
    st.error(f"Errore caricamento dati: {e}")
    st.stop()
# --- HEADER BLOOMBERG ---
st.title("📟 POLYMARKET QUANTITATIVE TERMINAL v2.0")
s = data['stats']
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("NET PNL", f"${data['balance'] - 100:.2f}", f"{(data['balance']-100):.1f}%")
c2.metric("WIN RATE", f"{(s['wins']/s['exits']*100):.2f}%")
c3.metric("PROFIT FACTOR", f"{(s['total_profit']/abs(s['total_loss'])):.2f}x")
c4.metric("TOTAL TRADES", s['exits'])
c5.metric("MAX DRAWDOWN", f"${df['drawdown'].min():.2f}", delta_color="inverse")

st.divider()

# --- NAVIGAZIONE SCHEDE ---
t1, t2, t3, t4 = st.tabs(["📈 EQUITY & RISK", "🎯 LEADERBOARD", "📅 ANALISI TEMPORALE", "📋 LEDGER DETTAGLIATO"])

with t1:
    col_left, col_right = st.columns([7, 3])
    with col_left:
        st.subheader("Performance Cumulativa & Rischio")
        fig_eq = make_subplots(specs=[[{"secondary_y": True}]])
        fig_eq.add_trace(go.Scatter(x=df['dt_uscita'], y=df['cum_pnl'], name="Equity", line=dict(color='#00FF41', width=3)), secondary_y=False)
        fig_eq.add_trace(go.Scatter(x=df['dt_uscita'], y=df['drawdown'], name="Drawdown", fill='tozeroy', fillcolor='rgba(255,0,0,0.1)', line=dict(color='red', width=1)), secondary_y=True)
        fig_eq.update_layout(template="plotly_dark", height=500)
        st.plotly_chart(fig_eq, use_container_width=True)
    with col_right:
        st.subheader("Distribuzione Esiti")
        fig_reasons = px.pie(df, names='exit_reason', hole=0.5, template="plotly_dark")
        st.plotly_chart(fig_reasons, use_container_width=True)

with t2:
    st.subheader("Analisi Leader Professionale")
    # Bubble chart corretta
    fig_lead = px.scatter(leaders[leaders['Trade_Tot'] > 1], x="Win_Rate", y="Profitto_Tot", 
                          size="Trade_Tot", color="Profitto_Tot", hover_name="leader",
                          template="plotly_dark", title="Matrice Efficienza Leader")
    st.plotly_chart(fig_lead, use_container_width=True)
    st.dataframe(leaders.sort_values('Profitto_Tot', ascending=False), use_container_width=True)

with t3:
    st.subheader("Deep Dive Temporale")
    c_a, c_b = st.columns(2)
    with c_a:
        st.write("**Performance per Ora del Giorno**")
        hourly = df.groupby('ora')['pnl'].sum().reset_index()
        st.plotly_chart(px.bar(hourly, x='ora', y='pnl', template="plotly_dark"), use_container_width=True)
    with c_b:
        st.write("**Performance Avanzata per Giorno della Settimana**")
        # Analisi avanzata richiesta: Profitto medio e frequenza
        day_analysis = df.groupby('giorno_sett').agg(
            Profitto_Medio=('pnl', 'mean'),
            Volume_Trade=('pnl', 'count')
        ).reindex(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'])
        fig_day_pro = px.bar(day_analysis.reset_index(), x='giorno_sett', y='Profitto_Medio', 
                             color='Volume_Trade', template="plotly_dark", title="Efficienza Media Giornaliera")
        st.plotly_chart(fig_day_pro, use_container_width=True)

with t4:
    st.subheader("Registro Operazioni Master")
    st.dataframe(df.sort_values('dt_uscita', ascending=False), use_container_width=True)
