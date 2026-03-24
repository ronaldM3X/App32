import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Geotecnia Master v25.0", layout="wide", page_icon="🏗️")

# Estilos
st.markdown("<style>.stTable { font-size: 1.1rem; }</style>", unsafe_allow_html=True)

# --- REINICIO DE ESTADO AL CAMBIAR DE MODO ---
if "ultimo_modo" not in st.session_state:
    st.session_state.ultimo_modo = "Metas"
if "base_calc" not in st.session_state:
    st.session_state.base_calc = None
if "counter" not in st.session_state:
    st.session_state.counter = 0

# 2. PANEL DE CONTROL
st.sidebar.title("⚙️ Configuración")
modo_actual = st.sidebar.radio("Selecciona el Modo:", ("Metas", "Académico"))

# Si el usuario cambia el modo, reseteamos todo para evitar basura en memoria
if modo_actual != st.session_state.ultimo_modo:
    st.session_state.ultimo_modo = modo_actual
    st.session_state.base_calc = None
    st.session_state.counter += 1
    st.rerun()

st.title(f"🏗️ Geotecnia Master - Modo {modo_actual}")
st.markdown("---")

tabs = st.tabs(["🧩 Gravimetría & Fases", "🗂️ Perfil de Esfuerzos", "📈 Plasticidad"])

# --- PESTAÑA 1: GRAVIMETRÍA ---
with tabs[0]:
    dicc = {
        "gs": "Gs", "e": "e", "n": "n %", "w": "w %", "s": "S %", "wm": "Wt (g)",
        "ws": "Ws (g)", "ww": "Ww (g)", "vt": "Vt (cm³)", "vs": "Vs (cm³)",
        "vv": "Vv (cm³)", "vw": "Vw (cm³)", "va": "Va (cm³)", "gh": "γ (kN/m³)", "gd": "γd (kN/m³)"
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
            # Manejo de porcentajes
            d[k] = v / 100 if k in ['w', 'n', 's'] and v > 1.0 else v
        
        # SI ES ACADÉMICO, FORZAMOS Vs=1 DESDE AQUÍ
        if modo_actual == "Académico": d['vs'] = 1.0
        
        # Convergencia de 100 ciclos para despejar variables
        for _ in range(100):
            if d['gs'] > 0 and d['ws'] > 0 and d['vs'] == 0: d['vs'] = d['ws'] / d['gs']
            if d['gs'] > 0 and d['vs'] > 0 and d['ws'] == 0: d['ws'] = d['gs'] * d['vs']
            if d['ws'] > 0 and d['w'] > 0 and d['ww'] == 0: d['ww'] = d['ws'] * d['w']
            if d['vt'] > 0 and d['vs'] > 0 and d['vv'] == 0: d['vv'] = d['vt'] - d['vs']
            if d['vv'] > 0 and d['vs'] > 0 and d['e'] == 0: d['e'] = d['vv'] / d['vs']
            if d['ws'] > 0 and d['ww'] >= 0: d['wm'] = d['ws'] + d['ww']
            if d['vs'] > 0 and d['vv'] >= 0: d['vt'] = d['vs'] + d['vv']

        st.session_state.base_calc = d
        st.session_state.counter += 1
        st.rerun()

    if st.session_state.base_calc:
        st.markdown("---")
        c_sim, c_res = st.columns([1.2, 1.8])
        bc = st.session_state.base_calc
        c = st.session_state.counter

        with c_sim:
            st.subheader("🕹️ Simulador Dinámico")
            
            # Valores por defecto extraídos del Paso 1
            e_def = float(bc['e']) if bc['e'] > 0 else 0.650
            w_def = float(bc['w']*100) if bc['w'] > 0 else 15.0
            ws_def = float(bc['ws']) if bc['ws'] > 0 else 2.650
            gs_val = bc['gs'] if bc['gs'] > 0 else 2.650

            # Sliders con KEY ÚNICA para romper la memoria de Streamlit
            e_val = st.slider("Relación de vacíos (e)", 0.01, 5.0, e_def, step=0.001, key=f"e_s_{c}")
            w_val = st.slider("Humedad (w %)", 0.0, 100.0, w_def, step=0.1, key=f"w_s_{c}") / 100
            
            # Ws bloqueado en Académico porque Vs=1 manda. En Metas es libre.
            ws_val = st.slider("Peso Sólidos (Ws)", 0.1, 5000.0, ws_def, key=f"ws_s_{c}", disabled=(modo_actual == "Académico"))
            
            # --- CÓMPUTO FINAL ---
            res = {k: 0.0 for k in dicc.keys()}
            res['gs'] = gs_val
            res['e'] = e_val
            res['w'] = w_val
            
            if modo_actual == "Académico":
                res['vs'] = 1.0
                res['ws'] = res['gs'] * res['vs']
            else:
                # AQUÍ SE CORRIGE EL ERROR: Vs es dependiente, NO fijo.
                res['ws'] = ws_val
                res['vs'] = res['ws'] / res['gs']
            
            res['vv'] = res['e'] * res['vs']
            res['vt'] = res['vs'] + res['vv']
            res['ww'] = res['ws'] * res['w']
            res['vw'] = res['ww']
            res['s'] = res['vw'] / res['vv'] if res['vv'] > 0 else 0
            
            # Validación saturación
            if res['s'] > 1.0:
                st.warning("⚠️ Suelo saturado (S=100%).")
                res['s'], res['vw'] = 1.0, res['vv']
                res['ww'] = res['vw']
            
            res['va'] = max(0.0, res['vv'] - res['vw'])
            res['wm'] = res['ws'] + res['ww']
            res['n'] = res['vv'] / res['vt']

            if st.button("🔄 Reiniciar Todo"):
                st.session_state.base_calc = None
                st.rerun()

        with c_res:
            st.subheader("📊 Resultados Finales")
            gh = (res['wm']/res['vt'])*9.81 if res['vt'] > 0 else 0
            gd = (res['ws']/res['vt'])*9.81 if res['vt'] > 0 else 0
            
            # Generación de tabla con nombres completos
            filas = []
            for k, nombre in dicc.items():
                if k in ["gh", "gd"]: continue
                val = res[k]
                formato = f"{val*100:.2f}%" if "%" in nombre else f"{val:.3f}"
                filas.append({"Propiedad": nombre, "Valor": formato})
            
            filas.append({"Propiedad": dicc["gh"], "Valor": f"{gh:.2f}"})
            filas.append({"Propiedad": dicc["gd"], "Valor": f"{gd:.2f}"})
            
            st.table(pd.DataFrame(filas))
            
            # Gráfico de Fases
            fig = go.Figure(data=[
                go.Bar(name='Sólidos', x=['Fases'], y=[res['vs']], marker_color='#7E5109', text=[f"Vs: {res['vs']:.2f}"]),
                go.Bar(name='Agua', x=['Fases'], y=[res['vw']], marker_color='#3498DB', text=[f"Vw: {res['vw']:.2f}"]),
                go.Bar(name='Aire', x=['Fases'], y=[res['va']], marker_color='#BDC3C7', text=[f"Va: {res['va']:.2f}"])
            ])
            fig.update_layout(barmode='stack', height=350)
            st.plotly_chart(fig, use_container_width=True)

# --- PESTAÑA 2: ESFUERZOS ---
with tabs[1]:
    st.header("🗂️ Perfil de Esfuerzos")
    # Lógica de esfuerzos restaurada
    c1, c2 = st.columns([1, 2])
    with c1:
        n_est = st.number_input("Número de Estratos", 1, 10, 2)
        nf = st.number_input("Nivel Freático (m)", 0.0, 100.0, 2.0)
        estratos = []
        for i in range(int(n_est)):
            h = st.number_input(f"H{i+1} (m)", 0.1, 50.0, 3.0, key=f"pz_{i}")
            g = st.number_input(f"γ{i+1}", 1.0, 25.0, 18.0, key=f"pg_{i}")
            estratos.append({'h': h, 'g': g})

    puntos = [0.0]
    acu = 0
    for e in estratos:
        acu += e['h']
        puntos.append(acu)
    if nf not in puntos and nf < acu: puntos.append(nf)
    puntos = sorted(puntos)

    z_l, sigma_l, u_l, eff_l = [], [], [], []
    s_acu = 0
    for i in range(len(puntos)):
        z = puntos[i]
        if i > 0:
            dz = z - puntos[i-1]
            z_m = (z + puntos[i-1])/2
            curr_h = 0
            for e in estratos:
                curr_h += e['h']
                if z_m <= curr_h:
                    s_acu += dz * e['g']
                    break
        u = (z - nf) * 9.81 if z > nf else 0
        z_l.append(z); sigma_l.append(s_acu); u_l.append(u); eff_l.append(s_acu - u)

    with c2:
        st.dataframe(pd.DataFrame({"Z (m)": z_l, "σ Total": sigma_l, "u": u_l, "σ' Efec.": eff_l}))
        fig_p = go.Figure()
        fig_p.add_trace(go.Scatter(x=sigma_l, y=z_l, name='Total', line=dict(color='brown')))
        fig_p.add_trace(go.Scatter(x=u_l, y=z_l, name='u', line=dict(color='blue', dash='dash')))
        fig_p.add_trace(go.Scatter(x=eff_l, y=z_l, name='Efectivo', fill='tonextx', line=dict(color='green')))
        fig_p.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_p, use_container_width=True)

# --- PESTAÑA 3: PLASTICIDAD ---
with tabs[2]:
    st.header("📈 Plasticidad")
    ll = st.number_input("LL", 0, 150, 40)
    lp = st.number_input("LP", 0, 100, 20)
    ip = ll - lp
    st.metric("IP", ip)
    xv = np.linspace(0, 100, 100)
    fig_c = go.Figure()
    fig_c.add_trace(go.Scatter(x=xv, y=0.73*(xv-20), name='Línea A', line=dict(color='black')))
    fig_c.add_trace(go.Scatter(x=[ll], y=[ip], mode='markers', marker=dict(size=12, color='red')))
    fig_c.update_xaxes(title="LL", range=[0, 100]); fig_c.update_yaxes(title="IP", range=[0, 60])
    st.plotly_chart(fig_c, use_container_width=True)
                
