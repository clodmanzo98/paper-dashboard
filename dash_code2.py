import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- SETUP PAGINA ---
st.set_page_config(page_title="QUANT TERMINAL v4.0", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #00FF41; font-family: 'Consolas', monospace; }
    .stMetric { background-color: #0c0c0c; border: 1px solid #00FF41; padding: 10px; border-radius: 0px; }
    [data-testid="stMetricValue"] { font-size: 1.5rem !important; }
    .compact-text { font-size: 0.8rem; }
    div[data-testid="stExpander"] { border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

base_path = os.path.dirname(__file__)
json_path = os.path.join(base_path, 'paper_portfolio.json')

@st.cache_data
def load_data():
    with open(json_path, 'r') as f:
        data = json.load(f)
    df_h = pd.DataFrame(data['history'])
    df_h['dt_uscita'] = pd.to_datetime(df_h['exit_timestamp'], unit='s')
    df_h = df_h.sort_values('dt_uscita').reset_index(drop=True)
    df_h['cum_pnl'] = df_h['pnl'].cumsum()
    df_h['drawdown'] = df_h['cum_pnl'] - df_h['cum_pnl'].cummax()
    
    leaders = df_h.groupby('leader').agg(
        Profitto_Tot=('pnl', 'sum'),
        Trade_Tot=('pnl', 'count'),
        Win_Rate=('pnl', lambda x: (x > 0).mean() * 100)
    ).reset_index()
    
    return data, df_h, leaders

try:
    data, df, leaders = load_data()
except Exception as e:
    st.error(f"BOOT ERROR: {e}")
    st.stop()

# --- HEADER: METRICHE RICHIESTE ---
st.markdown("### 📟 **CAPITAL & PERFORMANCE OVERVIEW**")
m1, m2, m3, m4, m5 = st.columns(5)
s = data['stats']
m1.metric("CAPITALE TOTALE", f"${data['balance']:.2f}")
m2.metric("TRADE VINTI", f"✅ {s['wins']}")
m3.metric("TRADE PERSI", f"❌ {s['losses']}")
m4.metric("WIN RATE", f"{(s['wins']/s['exits']*100):.1f}%")
m5.metric("PROFIT FACTOR", f"{(s['total_profit']/abs(s['total_loss'])):.2f}x")

st.divider()

# --- LAYOUT COMPATTO GRAFICI ---
c1, c2 = st.columns([6, 4])

with c1:
    st.markdown("<p class='compact-text'>EQUITY CURVE & DRAWDOWN</p>", unsafe_allow_html=True)
    fig_eq = make_subplots(specs=[[{"secondary_y": True}]])
    fig_eq.add_trace(go.Scatter(x=df['dt_uscita'], y=df['cum_pnl'], name="Equity", line=dict(color='#00FF41', width=2)), secondary_y=False)
    fig_eq.add_trace(go.Scatter(x=df['dt_uscita'], y=df['drawdown'], name="DD", fill='tozeroy', fillcolor='rgba(255,0,0,0.1)', line=dict(color='red', width=1)), secondary_y=True)
    fig_eq.update_layout(template="plotly_dark", height=300, margin=dict(l=0,r=0,b=0,t=20), showlegend=False)
    st.plotly_chart(fig_eq, use_container_width=True)

with c2:
    st.markdown("<p class='compact-text'>LEADER PERFORMANCE MATRIX</p>", unsafe_allow_html=True)
    fig_lead = px.scatter(leaders, x="Win_Rate", y="Profitto_Tot", size="Trade_Tot", color="Profitto_Tot", 
                          template="plotly_dark", size_max=30)
    fig_lead.update_layout(height=300, margin=dict(l=0,r=0,b=0,t=20))
    st.plotly_chart(fig_lead, use_container_width=True)

# --- TABELLE E ANALISI BASSO PROFILO ---
t1, t2, t3 = st.tabs(["📋 LEDGER TRADE", "🎯 ANALISI WALLET", "🕒 TEMPI & GIORNI"])

with t1:
    st.dataframe(df[['dt_uscita', 'market', 'side', 'entry_price', 'exit_price', 'pnl', 'exit_reason']].sort_values('dt_uscita', ascending=False), 
                 use_container_width=True, height=300)

with t2:
    st.dataframe(leaders.sort_values('Profitto_Tot', ascending=False), use_container_width=True)

with t3:
    df['giorno'] = df['dt_uscita'].dt.day_name()
    day_stats = df.groupby('giorno')['pnl'].sum().reset_index()
    st.plotly_chart(px.bar(day_stats, x='giorno', y='pnl', template="plotly_dark", height=250), use_container_width=True)
