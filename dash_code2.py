import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURAZIONE ESTETICA BLOOMBERG ---
st.set_page_config(page_title="POLY-QUANT TERMINAL v3.0", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #00FF41; font-family: 'Courier New', Courier, monospace; }
    .stMetric { background-color: #0c0c0c; border: 1px solid #00FF41; padding: 15px; border-radius: 0px; }
    [data-testid="stMetricValue"] { color: #00FF41 !important; font-size: 1.8rem !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background-color: #111; border: 1px solid #333; color: white; border-radius: 0px; }
    .stTabs [aria-selected="true"] { border-color: #00FF41; color: #00FF41; }
    </style>
    """, unsafe_allow_html=True)

base_path = os.path.dirname(__file__)
json_path = os.path.join(base_path, 'paper_portfolio.json')

# --- MOTORE DI ELABORAZIONE DATI ---
@st.cache_data
def load_and_process_data():
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # --- 1. Storico (Operazioni Chiuse) ---
    df_h = pd.DataFrame(data['history'])
    df_h['dt_entrata'] = pd.to_datetime(df_h['timestamp'], unit='s')
    df_h['dt_uscita'] = pd.to_datetime(df_h['exit_timestamp'], unit='s')
    df_h['giorno_sett'] = df_h['dt_uscita'].dt.day_name()
    df_h['ora'] = df_h['dt_uscita'].dt.hour
    df_h = df_h.sort_values('dt_uscita').reset_index(drop=True)
    
    # Calcoli Finanziari
    df_h['cum_pnl'] = df_h['pnl'].cumsum()
    df_h['rolling_max'] = df_h['cum_pnl'].cummax()
    df_h['drawdown'] = df_h['cum_pnl'] - df_h['rolling_max']
    
    # --- 2. Posizioni Aperte ---
    df_p = pd.DataFrame(data['positions'])
    
    # --- 3. Leaderboard ---
    leaders = df_h.groupby('leader').agg(
        Profitto_Tot=('pnl', 'sum'),
        Trade_Tot=('pnl', 'count'),
        Win_Rate=('pnl', lambda x: (x > 0).mean() * 100),
        ROI_Medio=('pnl_pct', 'mean')
    ).reset_index()
    
    return data, df_h, df_p, leaders

try:
    data, df, df_pos, leaders = load_and_process_data()
except Exception as e:
    st.error(f"SYSTEM BOOT ERROR: {e}")
    st.stop()

# --- HEADER: GESTIONE CAPITALE E PERFORMANCE ---
st.markdown("### 📟 **MONEY MANAGEMENT TERMINAL**")

# Riga 1: Capitale
c1, c2, c3, c4 = st.columns(4)
saldo_attuale = data['balance']
capitale_impegnato = df_pos['cost'].sum() if not df_pos.empty else 0
margine_libero = saldo_attuale - capitale_impegnato
esposizione_pct = (capitale_impegnato / saldo_attuale) * 100

c1.metric("CAPITALE TOTALE (SALDO)", f"${saldo_attuale:.2f}")
c2.metric("CAPITALE IMPEGNATO", f"${capitale_impegnato:.2f}")
c3.metric("MARGINE LIBERO", f"${margine_libero:.2f}")
c4.metric("ESPOSIZIONE", f"{esposizione_pct:.1f}%")

st.markdown("<br>", unsafe_allow_html=True) # Piccolo spazio divisorio

# Riga 2: Performance
m1, m2, m3, m4 = st.columns(4)
s = data['stats']
m1.metric("TRADE VINTI", f"✅ {s['wins']}")
m2.metric("TRADE PERSI", f"❌ {s['losses']}")
m3.metric("WIN RATE", f"{(s['wins']/s['exits']*100):.1f}%")
m4.metric("PROFIT FACTOR", f"{(s['total_profit']/abs(s['total_loss'])):.2f}x")

st.divider()

# --- TAB NAVIGATION ---
t1, t2, t3, t4, t5 = st.tabs(["📈 PERFORMANCE", "🛡️ RISK & CAPITAL", "🎯 LEADERS", "📅 TIME ANALYTICS", "📜 LEDGER"])

with t1:
    st.subheader("Equity Curve & Dynamic Drawdown")
    fig_eq = make_subplots(specs=[[{"secondary_y": True}]])
    fig_eq.add_trace(go.Scatter(x=df['dt_uscita'], y=df['cum_pnl'], name="Equity ($)", line=dict(color='#00FF41', width=3)), secondary_y=False)
    fig_eq.add_trace(go.Scatter(x=df['dt_uscita'], y=df['drawdown'], name="Drawdown", fill='tozeroy', fillcolor='rgba(255,0,0,0.2)', line=dict(color='red', width=1)), secondary_y=True)
    # ALTEZZA RIDOTTA A 350
    fig_eq.update_layout(template="plotly_dark", height=350, margin=dict(l=0,r=0,b=0,t=30))
    st.plotly_chart(fig_eq, use_container_width=True)

with t2:
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.subheader("Distribuzione Profitto per Trade")
        # ALTEZZA RIDOTTA A 300
        fig_hist = px.histogram(df, x="pnl", color_discrete_sequence=['#00FF41'], template="plotly_dark", height=300)
        st.plotly_chart(fig_hist, use_container_width=True)
    with col_r2:
        st.subheader("Efficienza Segnale (Exit Reasons)")
        # ALTEZZA RIDOTTA A 300
        fig_pie = px.pie(df, names='exit_reason', hole=0.5, template="plotly_dark", height=300)
        st.plotly_chart(fig_pie, use_container_width=True)

with t3:
    st.subheader("Wallet Leaderboard (Bubble Matrix)")
    # ALTEZZA RIDOTTA A 350
    fig_lead = px.scatter(leaders, x="Win_Rate", y="Profitto_Tot", size="Trade_Tot", color="ROI_Medio", 
                          hover_name="leader", template="plotly_dark", size_max=60, height=350, 
                          labels={"Profitto_Tot":"Profitto Totale ($)", "Win_Rate":"Win Rate (%)"})
    st.plotly_chart(fig_lead, use_container_width=True)
    st.dataframe(leaders.sort_values('Profitto_Tot', ascending=False).style.background_gradient(cmap='Greens'), use_container_width=True)

with t4:
    st.subheader("Analisi Efficienza Temporale")
    c_t1, c_t2 = st.columns(2)
    with c_t1:
        st.write("**Profitto Medio per Giorno della Settimana**")
        order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        day_stats = df.groupby('giorno_sett')['pnl'].mean().reindex(order).reset_index()
        # ALTEZZA RIDOTTA A 300
        fig_day = px.bar(day_stats, x='giorno_sett', y='pnl', template="plotly_dark", height=300)
        st.plotly_chart(fig_day, use_container_width=True)
    with c_t2:
        st.write("**Heatmap Oraria (Profitto Totale)**")
        hourly_stats = df.groupby('ora')['pnl'].sum().reset_index()
        # ALTEZZA RIDOTTA A 300
        fig_hour = px.bar(hourly_stats, x='ora', y='pnl', template="plotly_dark", height=300)
        st.plotly_chart(fig_hour, use_container_width=True)

with t5:
    st.subheader("Registro Dettagliato Operazioni Master")
    st.dataframe(df.sort_values('dt_uscita', ascending=False), use_container_width=True)
