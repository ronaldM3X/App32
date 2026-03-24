import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import io

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Geotecnia Master v25.0", layout="wide", page_icon="🏗️")

st.markdown("""
    <style>
    .stTable { font-size: 1.1rem; }
    .stMetric { border: 1px solid #e1e4e8; padding: 10px; border-radius: 8px; }
    .critical-alert { color: #ff4b4b; font-weight: bold; border: 2px solid #ff4b4b; padding: 10px; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# 2. PANEL DE CONTROL
st.sidebar.title("👨‍🏫 Configuración")
modo = st.sidebar.radio("Selecciona el Modo de Trabajo:", ("Metas", "Académico"))
st.sidebar.markdown("---")

st.title(f"🏗️ Geotecnia Master - Modo {modo}")
st.markdown("---")

tabs = st.tabs(["🧩 Gravimetría & Fases", "🗂️ Perfil de Esfuerzos", "📈 Plasticidad (SUCS)", "📥 Reporte"])

# --- PESTAÑA 1: GRAVIMETRÍA ---
with tabs[0]:
    dicc = {
        "gs": "Gs", "e": "e", "n": "n %", "w": "w %", "s": "S %", 
        "wm": "Wt", "ws": "Ws", "ww": "Ww", "vt": "Vt", "vs": "Vs", 
        "vv": "Vv", "vw": "Vw", "va": "Va", "gh": "γ", "gd": "γd"
    }

    st.subheader("📥 Paso 1: Datos de Entrada")
    seleccionados = st.multiselect("Variables conocidas:", options=list(dicc.keys()), format_func=lambda x: dicc[x])
    
    inputs = {}
    cols_in = st.columns(3)
    for i, clave in enumerate(seleccionados):
        inputs[clave] = cols_in[i%3].number_input(f"{dicc[clave]}", value=0.0, format="%.4f", key=f"in_{clave}")

    if st.button("🚀 Calcular Estado Inicial"):
        # Inicializar con NaN para saber qué falta
        d = {k: 0.0 for k in dicc.keys()}
        for k, v in inputs.items():
            d[k] = v / 100 if k in ['w', 'n', 's'] and v > 1.0 else v
        
        if modo == "Académico": d['vs'] = 1.0
        
        # Iteración de convergencia mejorada
        for _ in range(150):
            if d['gs'] > 0 and d['ws'] > 0 and d['vs'] == 0: d['vs'] = d['ws'] / d['gs']
            if d['gs'] > 0 and d['vs'] > 0 and d['ws'] == 0: d['ws'] = d['gs'] * d['vs']
            if d['ws'] > 0 and d['w'] > 0 and d['ww'] == 0: d['ww'] = d['ws'] * d['w']
            if d['ww'] > 0: d['vw'] = d['ww']
            if d['vt'] > 0 and d['vs'] > 0: d['vv'] = d['vt'] - d['vs']
            if d['vv'] > 0 and d['vs'] > 0: d['e'] = d['vv'] / d['vs']
            if d['vw'] > 0 and d['vv'] > 0: d['s'] = d['vw'] / d['vv']
            if d['vs'] > 0 and d['vv'] > 0: d['vt'] = d['vs'] + d['vv']

        st.session_state.base_calc = d
        st.rerun()

    if 'base_calc' in st.session_state:
        st.markdown("---")
        c_sim, c_res = st.columns([1.3, 1.7])
        bc = st.session_state.base_calc

        with c_sim:
            st.subheader("🕹️ Simulador Dinámico")
            
            # BLOQUE CRÍTICO: Aquí corregimos que Vs no sea siempre 1
            # Si es Metas, intentamos usar el Vs real calculado.
            e_init = float(bc['e']) if bc['e'] > 0 else 0.65
            w_init = float(bc['w']*100) if bc['w'] > 0 else 15.0
            ws_init = float(bc['ws']) if bc['ws'] > 0 else 2.65
            gs_val = bc['gs'] if bc['gs'] > 0 else 2.65

            e_val = st.slider("Relación de vacíos (e)", 0.01, 5.0, e_init, step=0.001)
            w_val = st.slider("Humedad (w %)", 0.0, 100.0, w_init, step=0.1) / 100
            ws_val = st.slider("Peso Sólidos (Ws)", 0.1, 5000.0, ws_init, disabled=(modo=="Académico"))

            # Recálculo físico estricto
            final = {k: 0.0 for k in dicc.keys()}
            final['gs'] = gs_val
            final['e'] = e_val
            final['w'] = w_val
            
            if modo == "Académico":
                final['vs'] = 1.0
                final['ws'] = gs_val * 1.0
            else:
                final['ws'] = ws_val
                final['vs'] = ws_val / gs_val

            final['vv'] = final['e'] * final['vs']
            final['vt'] = final['vs'] + final['vv']
            final['ww'] = final['ws'] * final['w']
            final['vw'] = final['ww']
            final['s'] = final['vw'] / final['vv'] if final['vv'] > 0 else 0

            # --- ALERTA DE PADRE: SATURACIÓN ---
            if final['s'] > 1.0001:
                st.error("⚠️ ¡CUIDADO! Saturación mayor al 100%. Revisa tus datos, el agua no cabe en los vacíos.")
                # Forzamos consistencia para el gráfico
                final['s'] = 1.0
                final['vw'] = final['vv']
                final['ww'] = final['vw']

            final['va'] = max(0.0, final['vv'] - final['vw'])
            final['wm'] = final['ws'] + final['ww']
            final['n'] = final['vv'] / final['vt']

        with c_res:
            st.subheader("📊 Resultados")
            gh_val = (final['wm']/final['vt'])*9.81 if final['vt'] > 0 else 0
            gd_val = (final['ws']/final['vt'])*9.81 if final['vt'] > 0 else 0
            
            res_df = pd.DataFrame({
                "Propiedad": list(dicc.values()), 
                "Valor": [
                    f"{final['gs']:.3f}", f"{final['e']:.4f}", f"{final['n']*100:.2f}%", 
                    f"{final['w']*100:.2f}%", f"{final['s']*100:.2f}%", f"{final['wm']:.3f}", 
                    f"{final['ws']:.3f}", f"{final['ww']:.3f}", f"{final['vt']:.3f}", 
                    f"{final['vs']:.3f}", f"{final['vv']:.3f}", f"{final['vw']:.3f}", 
                    f"{final['va']:.3f}", f"{gh_val:.2f}", f"{gd_val:.2f}"
                ]
            })
            st.table(res_df)
            
            fig = go.Figure(data=[
                go.Bar(name='Sólidos', x=['Fases'], y=[final['vs']], marker_color='#7E5109'),
                go.Bar(name='Agua', x=['Fases'], y=[final['vw']], marker_color='#3498DB'),
                go.Bar(name='Aire', x=['Fases'], y=[final['va']], marker_color='#BDC3C7')
            ])
            fig.update_layout(barmode='stack', height=300); st.plotly_chart(fig, use_container_width=True)

# --- PESTAÑA 3: PLASTICIDAD (Con Línea U) ---
with tabs[2]:
    st.header("📈 Carta de Plasticidad")
    cl, cr = st.columns([1, 2])
    with cl:
        ll = st.number_input("Límite Líquido (LL)", 0, 150, 40)
        lp = st.number_input("Límite Plástico (LP)", 0, 100, 20)
        ip = ll - lp
        st.metric("Índice de Plasticidad (IP)", ip)
        
        # Validación Línea U
        ip_u = 0.9 * (ll - 8)
        if ip > ip_u:
            st.warning("⚠️ El punto está por encima de la Línea U. Datos probablemente erróneos.")

    with cr:
        xv = np.linspace(8, 100, 100)
        linea_a = 0.73 * (xv - 20)
        linea_u = 0.9 * (xv - 8)
        fig_c = go.Figure()
        fig_c.add_trace(go.Scatter(x=xv, y=linea_a, name='Línea A (Clasificación)', line=dict(color='black')))
        fig_c.add_trace(go.Scatter(x=xv, y=linea_u, name='Línea U (Límite Físico)', line=dict(color='red', dash='dot')))
        fig_c.add_trace(go.Scatter(x=[ll], y=[ip], mode='markers', marker=dict(size=15, color='blue'), name="Tu Suelo"))
        fig_c.update_xaxes(title="LL"); fig_c.update_yaxes(title="IP"); st.plotly_chart(fig_c)
        
