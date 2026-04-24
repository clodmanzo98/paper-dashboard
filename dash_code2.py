import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURAZIONE TERMINALE ---
st.set_page_config(page_title="Polymarket Quant Terminal", layout="wide", initial_sidebar_state="collapsed")
st.markdown("<style> .stMetric {background-color: #1E1E1E; padding: 15px; border-radius: 5px; border: 1px solid #333;} </style>", unsafe_allow_html=True)

base_path = os.path.dirname(__file__)
json_path = os.path.join(base_path, 'paper_portfolio.json')

# --- MOTORE DATI ---
@st.cache_data
def load_quant_data():
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    df = pd.DataFrame(data['history'])
    if df.empty:
        return data, df
    
    # Parsing temporale
    df['dt_entrata'] = pd.to_datetime(df['timestamp'], unit='s')
    df['dt_uscita'] = pd.to_datetime(df['exit_timestamp'], unit='s')
    df['durata_ore'] = (df['dt_uscita'] - df['dt_entrata']).dt.total_seconds() / 3600
    df['data_uscita_short'] = df['dt_uscita'].dt.date
    
    # Ordinamento cronologico strettissimo
    df = df.sort_values('dt_uscita').reset_index(drop=True)
    
    # Calcoli Finanziari Complessi
    df['cum_pnl'] = df['pnl'].cumsum()
    df['rolling_max'] = df['cum_pnl'].cummax()
    df['drawdown'] = df['cum_pnl'] - df['rolling_max']
    
    # Formattazione Leader
    df['leader_short'] = df['leader'].str[:6] + "..." + df['leader'].str[-4:]
    
    return data, df

try:
    data, df = load_quant_data()
except Exception as e:
    st.error(f"Errore critico lettura dati: {e}")
    st.stop()

# --- CALCOLO METRICHE AVANZATE ---
vittorie = df[df['pnl'] > 0]
sconfitte = df[df['pnl'] <= 0]

gross_profit = vittorie['pnl'].sum()
gross_loss = abs(sconfitte['pnl'].sum())
profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')

avg_win = vittorie['pnl'].mean() if not vittorie.empty else 0
avg_loss = abs(sconfitte['pnl'].mean()) if not sconfitte.empty else 0
risk_reward = avg_win / avg_loss if avg_loss != 0 else float('inf')

max_dd = df['drawdown'].min()

# --- HEADER BLOOMBERG ---
st.markdown("## 📟 **POLYMARKET QUANTITATIVE TERMINAL**")

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Net Profit (PNL)", f"${data['balance'] - data['starting_balance']:.2f}")
c2.metric("Win Rate", f"{(len(vittorie)/len(df)*100):.2f}%")
c3.metric("Profit Factor", f"{profit_factor:.2f}x", help="Rapporto tra vincite totali e perdite totali. > 1.5 è eccellente.")
c4.metric("Avg Risk/Reward", f"{risk_reward:.2f}", help="Quanto vinci in media rispetto a quanto perdi in media.")
c5.metric("Max Drawdown", f"${max_dd:.2f}", help="La perdita massima subita dal picco più alto.")
c6.metric("Total Trades", len(df))

st.divider()

# --- RIGA GRAFICI 1: ANDAMENTO E RISCHIO ---
col_eq, col_daily = st.columns([7, 3])

with col_eq:
    st.subheader("📈 Equity Curve & Drawdown")
    # Grafico combinato come i veri terminali
    fig_eq = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Linea Profitto
    fig_eq.add_trace(
        go.Scatter(x=df['dt_uscita'], y=df['cum_pnl'], name="Cumulative PNL", line=dict(color='#00ff88', width=2)),
        secondary_y=False,
    )
    # Area Drawdown (Perdite dal picco)
    fig_eq.add_trace(
        go.Scatter(x=df['dt_uscita'], y=df['drawdown'], name="Drawdown", fill='tozeroy', fillcolor='rgba(255, 0, 0, 0.2)', line=dict(color='red', width=1)),
        secondary_y=True,
    )
    fig_eq.update_layout(height=400, template="plotly_dark", margin=dict(l=0, r=0, t=30, b=0))
    fig_eq.update_yaxes(title_text="Profitto Netto ($)", secondary_y=False)
    fig_eq.update_yaxes(title_text="Drawdown ($)", showgrid=False, secondary_y=True)
    st.plotly_chart(fig_eq, use_container_width=True)

with col_daily:
    st.subheader("📊 Rendimenti Giornalieri")
    daily_pnl = df.groupby('data_uscita_short')['pnl'].sum().reset_index()
    daily_pnl['Color'] = np.where(daily_pnl['pnl'] > 0, '#00ff88', '#ff3333')
    
    fig_daily = go.Figure(data=[
        go.Bar(x=daily_pnl['data_uscita_short'], y=daily_pnl['pnl'], marker_color=daily_pnl['Color'])
    ])
    fig_daily.update_layout(height=400, template="plotly_dark", margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig_daily, use_container_width=True)

st.divider()

# --- RIGA GRAFICI 2: ANALISI LEADER E TRADE ---
col_lead, col_dur = st.columns([5, 5])

with col_lead:
    st.subheader("🎯 Matrice Performance Leader")
    # Raggruppamento solido e sicuro per i leader
    leader_df = df.groupby('leader_short').agg(
        Tot_Profitto=('pnl', 'sum'),
        Num_Trades=('pnl', 'count'),
        Win_Rate=('pnl', lambda x: (x > 0).mean() * 100)
    ).reset_index()
    
    # Rimuovi chi ha fatto 1 solo trade per non sballare il grafico
    leader_df = leader_df[leader_df['Num_Trades'] > 1]
    
    # Bubble Chart
    fig_matrix = px.scatter(leader_df, x="Win_Rate", y="Tot_Profitto", size="Num_Trades", color="leader_short",
                            hover_name="leader_short", size_max=40, template="plotly_dark",
                            labels={"Win_Rate": "Win Rate (%)", "Tot_Profitto": "Profitto Totale ($)"})
    fig_matrix.add_hline(y=0, line_dash="dot", line_color="red")
    fig_matrix.add_vline(x=50, line_dash="dot", line_color="gray")
    fig_matrix.update_layout(height=400, margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig_matrix, use_container_width=True)

with col_dur:
    st.subheader("⏱️ Analisi Holding Time (Durata vs PNL)")
    # Identifica outlier pazzeschi
    fig_dur = px.scatter(df, x="durata_ore", y="pnl", color=df["pnl"] > 0,
                         color_discrete_map={True: '#00ff88', False: '#ff3333'},
                         labels={"durata_ore": "Ore a Mercato", "pnl": "Profitto/Perdita ($)", "color": "In Profitto"},
                         template="plotly_dark")
    fig_dur.update_layout(height=400, margin=dict(l=0, r=0, t=30, b=0), showlegend=False)
    st.plotly_chart(fig_dur, use_container_width=True)

st.divider()

# --- DATA TABLE AVANZATA ---
st.subheader("🗄️ Terminal Data Ledger")
view_cols = ['dt_entrata', 'dt_uscita', 'leader_short', 'market', 'side', 'entry_price', 'exit_price', 'durata_ore', 'pnl', 'exit_reason']
st.dataframe(df[view_cols].sort_values('dt_uscita', ascending=False).style.format({
    'entry_price': '{:.3f}', 'exit_price': '{:.3f}', 'pnl': '${:.2f}', 'durata_ore': '{:.1f}h'
}), use_container_width=True, height=400)
