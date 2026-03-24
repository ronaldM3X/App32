import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Geotecnia Master v25.0", layout="wide", page_icon="🏗️")

# Estilos CSS
st.markdown("""
    <style>
    .stTable { font-size: 1.1rem; }
    .stMetric { border: 1px solid #e1e4e8; padding: 10px; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# Inicialización de estados para evitar persistencia de errores
if "base_calc" not in st.session_state:
    st.session_state.base_calc = None
if "refresh_key" not in st.session_state:
    st.session_state.refresh_key = 0

# 2. PANEL DE CONTROL
st.sidebar.title("⚙️ Configuración")
modo = st.sidebar.radio("Selecciona el Modo de Trabajo:", ("Metas", "Académico"))
st.sidebar.markdown("---")

st.title(f"🏗️ Geotecnia Master - Modo {modo}")
st.markdown("---")

tabs = st.tabs(["🧩 Gravimetría & Fases", "🗂️ Perfil de Esfuerzos", "📈 Plasticidad (SUCS)"])

# --- PESTAÑA 1: GRAVIMETRÍA ---
with tabs[0]:
    dicc = {
        "gs": "Gs (Gravedad específica)", "e": "e (Relación de vacíos)", "n": "n (Porosidad %)",
        "w": "w (Contenido de humedad %)", "s": "S (Grado de saturación %)", "wm": "Wt (Peso total g)",
        "ws": "Ws (Peso sólidos g)", "ww": "Ww (Peso agua g)", "vt": "Vt (Volumen total cm³)",
        "vs": "Vs (Volumen sólidos cm³)", "vv": "Vv (Volumen vacíos cm³)", "vw": "Vw (Volumen agua cm³)",
        "va": "Va (Volumen aire cm³)", "gh": "γ (Húmedo kN/m³)", "gd": "γd (Seco kN/m³)"
    }

    st.subheader("📥 Paso 1: Datos de Entrada")
    seleccionados = st.multiselect("Variables conocidas:", options=list(dicc.keys()), format_func=lambda x: dicc[x])
    
    inputs = {}
    cols_in = st.columns(3)
    for i, clave in enumerate(seleccionados):
        inputs[clave] = cols_in[i%3].number_input(f"{dicc[clave]}", value=0.0, format="%.4f", key=f"in_{clave}")

    if st.button("🚀 Calcular Estado Inicial"):
        d = {k: 0.0 for k in dicc.keys()}
        for k, v in inputs.items():
            d[k] = v / 100 if k in ['w', 'n', 's'] and v > 1.0 else v
        
        # Lógica de convergencia inicial
        for _ in range(100):
            if d['gs'] > 0 and d['ws'] > 0 and d['vs'] == 0: d['vs'] = d['ws'] / d['gs']
            if d['gs'] > 0 and d['vs'] > 0 and d['ws'] == 0: d['ws'] = d['gs'] * d['vs']
            if d['ws'] > 0 and d['w'] > 0 and d['ww'] == 0: d['ww'] = d['ws'] * d['w']
            if d['ww'] > 0: d['vw'] = d['ww']
            if d['vt'] > 0 and d['vs'] > 0: d['vv'] = d['vt'] - d['vs']
            if d['vv'] > 0 and d['vs'] > 0: d['e'] = d['vv'] / d['vs']
            if d['vw'] > 0 and d['vv'] > 0: d['s'] = d['vw'] / d['vv']
            if d['vs'] > 0 and d['vv'] > 0: d['vt'] = d['vs'] + d['vv']

        st.session_state.base_calc = d
        st.session_state.refresh_key += 1
        st.rerun()

    if st.session_state.base_calc:
        st.markdown("---")
        c_sim, c_res = st.columns([1.3, 1.7])
        bc = st.session_state.base_calc
        rk = st.session_state.refresh_key

        with c_sim:
            st.subheader("🕹️ Simulador Dinámico")
            
            # Valores base para los sliders
            e_base = float(bc['e']) if bc['e'] > 0 else 0.650
            w_base = float(bc['w']*100) if bc['w'] > 0 else 15.0
            ws_base = float(bc['ws']) if bc['ws'] > 0 else 2.650
            gs_base = bc['gs'] if bc['gs'] > 0 else 2.650

            # Sliders con LLAVE DINÁMICA para forzar actualización
            e_val = st.slider("Relación de vacíos (e)", 0.01, 5.0, e_base, step=0.001, key=f"e_sl_{rk}")
            w_val = st.slider("Humedad (w %)", 0.0, 100.0, w_base, step=0.1, key=f"w_sl_{rk}") / 100
            
            # Ws es editable solo en Metas. En Académico se bloquea porque Vs=1 manda.
            ws_val = st.slider("Peso Sólidos (Ws)", 0.1, 5000.0, ws_base, key=f"ws_sl_{rk}", disabled=(modo == "Académico"))
            
            # --- CÁLCULO DE SALIDA (Aquí se resuelve el error de Vs) ---
            res = {k: 0.0 for k in dicc.keys()}
            res['gs'] = gs_base
            res['e'] = e_val
            res['w'] = w_val
            
            if modo == "Académico":
                res['vs'] = 1.0
                res['ws'] = res['gs'] * res['vs']
            else:
                # EN MODO METAS: Vs es consecuencia de Ws y Gs, NO es 1.
                res['ws'] = ws_val
                res['vs'] = res['ws'] / res['gs']
            
            res['vv'] = res['e'] * res['vs']
            res['ww'] = res['ws'] * res['w']
            res['vw'] = res['ww']
            res['s'] = res['vw'] / res['vv'] if res['vv'] > 0 else 0
            
            if res['s'] > 1.0:
                st.warning("⚠️ Saturación > 100%.")
                res['s'] = 1.0
                res['vw'] = res['vv']
                res['ww'] = res['vw']
            
            res['vt'] = res['vs'] + res['vv']
            res['va'] = max(0.0, res['vv'] - res['vw'])
            res['wm'] = res['ws'] + res['ww']
            res['n'] = res['vv'] / res['vt']

            if st.button("🔄 Reiniciar"):
                st.session_state.base_calc = None
                st.rerun()

        with c_res:
            st.subheader("📊 Resultados")
            gh = (res['wm']/res['vt'])*9.81 if res['vt'] > 0 else 0
            gd = (res['ws']/res['vt'])*9.81 if res['vt'] > 0 else 0
            
            tabla_data = []
            for k in ["gs", "e", "n", "w", "s", "wm", "ws", "ww", "vt", "vs", "vv", "vw", "va"]:
                v = res[k]
                if k in ["n", "w", "s"]:
                    tabla_data.append({"Propiedad": dicc[k], "Valor": f"{v*100:.2f}%"})
                else:
                    tabla_data.append({"Propiedad": dicc[k], "Valor": f"{v:.3f}"})
            
            tabla_data.append({"Propiedad": dicc["gh"], "Valor": f"{gh:.2f}"})
            tabla_data.append({"Propiedad": dicc["gd"], "Valor": f"{gd:.2f}"})
            
            st.table(pd.DataFrame(tabla_data))
            
            # Gráfico de fases
            fig = go.Figure(data=[
                go.Bar(name='Sólidos', x=['Fases'], y=[res['vs']], marker_color='#7E5109', text=[f"Vs: {res['vs']:.2f}"]),
                go.Bar(name='Agua', x=['Fases'], y=[res['vw']], marker_color='#3498DB', text=[f"Vw: {res['vw']:.2f}"]),
                go.Bar(name='Aire', x=['Fases'], y=[res['va']], marker_color='#BDC3C7', text=[f"Va: {res['va']:.2f}"])
            ])
            fig.update_layout(barmode='stack', height=350, margin=dict(t=10,b=10))
            st.plotly_chart(fig, use_container_width=True)

# --- PESTAÑA 2: ESFUERZOS ---
with tabs[1]:
    st.header("🗂️ Perfil de Esfuerzos")
    col_a, col_b = st.columns([1, 2])
    with col_a:
        n_est = st.number_input("Número de Estratos", 1, 10, 2)
        nf = st.number_input("Nivel Freático (m)", 0.0, 100.0, 2.0)
        estratos = []
        for i in range(int(n_est)):
            h = st.number_input(f"H{i+1} (m)", 0.1, 50.0, 3.0, key=f"prof_{i}")
            g = st.number_input(f"γ{i+1} (kN/m³)", 1.0, 25.0, 18.0, key=f"gam_{i}")
            estratos.append({'h': h, 'g': g})

    # Puntos de cálculo
    puntos = [0.0]
    total_h = 0
    for e in estratos:
        total_h += e['h']
        puntos.append(total_h)
    if nf not in puntos and nf < total_h: puntos.append(nf)
    puntos = sorted(puntos)

    z_l, sigma_l, u_l, effective_l = [], [], [], []
    sigma_acum = 0
    for i in range(len(puntos)):
        z = puntos[i]
        if i > 0:
            dz = z - puntos[i-1]
            z_m = (z + puntos[i-1])/2
            h_curr = 0
            for e in estratos:
                h_curr += e['h']
                if z_m <= h_curr:
                    sigma_acum += dz * e['g']
                    break
        u = (z - nf) * 9.81 if z > nf else 0
        z_l.append(z); sigma_l.append(sigma_acum); u_l.append(u); effective_l.append(sigma_acum - u)

    with col_b:
        st.dataframe(pd.DataFrame({"Z (m)": z_l, "σ Total": sigma_l, "u": u_l, "σ' Efec.": effective_l}))
        fig_p = go.Figure()
        fig_p.add_trace(go.Scatter(x=sigma_l, y=z_l, name='σ Total', line=dict(color='brown')))
        fig_p.add_trace(go.Scatter(x=u_l, y=z_l, name='u', line=dict(color='blue', dash='dash')))
        fig_p.add_trace(go.Scatter(x=effective_l, y=z_l, name="σ' Efec.", fill='tonextx', line=dict(color='green')))
        fig_p.update_yaxes(autorange="reversed", title="Profundidad (m)")
        st.plotly_chart(fig_p, use_container_width=True)

# --- PESTAÑA 3: PLASTICIDAD ---
with tabs[2]:
    st.header("📈 Carta de Plasticidad")
    ll = st.number_input("LL", 0, 150, 40)
    lp = st.number_input("LP", 0, 100, 20)
    ip = ll - lp
    st.metric("IP", ip)
    xv = np.linspace(0, 100, 100)
    fig_c = go.Figure()
    fig_c.add_trace(go.Scatter(x=xv, y=0.73*(xv-20), name='Línea A', line=dict(color='black')))
    fig_c.add_trace(go.Scatter(x=[ll], y=[ip], mode='markers', marker=dict(size=12, color='red'), name="Suelo"))
    fig_c.update_xaxes(title="LL", range=[0, 100]); fig_c.update_yaxes(title="IP", range=[0, 60])
    st.plotly_chart(fig_c, use_container_width=True)
    
