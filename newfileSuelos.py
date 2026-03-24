import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import io

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Geotecnia Master v25.0", layout="wide", page_icon="🏗️")

# Estilos CSS
st.markdown("""
    <style>
    .stTable { font-size: 1.1rem; }
    .stMetric { border: 1px solid #e1e4e8; padding: 10px; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# Inicialización de estados
if "base_calc" not in st.session_state:
    st.session_state.base_calc = None
if "seed" not in st.session_state:
    st.session_state.seed = 0

# 2. PANEL DE CONTROL (BARRA LATERAL)
st.sidebar.title("⚙️ Configuración")
modo = st.sidebar.radio("Selecciona el Modo de Trabajo:", ("Metas", "Académico"))
st.sidebar.markdown("---")
if modo == "Metas":
    st.sidebar.success("✅ Vs es dinámico (Ws / Gs).")
else:
    st.sidebar.warning("📙 Vs fijo en 1.0 (Teórico).")

st.title(f"🏗️ Geotecnia Master - Modo {modo}")
st.markdown("---")

# 3. PESTAÑAS PRINCIPALES
tabs = st.tabs(["🧩 Gravimetría & Fases", "🗂️ Perfil de Esfuerzos", "📈 Plasticidad (SUCS)"])

# --- PESTAÑA 1: GRAVIMETRÍA ---
with tabs[0]:
    dicc = {
        "gs": "Gs (Gravedad específica)", "e": "e (Relación de vacíos)", "n": "n (Porosidad %)",
        "w": "w (Contenido de humedad %)", "s": "S (Grado de saturación %)", "wm": "Wt (Peso total g)",
        "ws": "Ws (Peso sólidos g)", "ww": "Ww (Peso agua g)", "vt": "Vt (Volumen total cm³)",
        "vs": "Vs (Volumen sólidos cm³)", "vv": "Vv (Volumen vacíos cm³)", "vw": "Vw (Volumen agua cm³)",
        "va": "Va (Volumen aire cm³)", "gh": "γ (Peso unitario húmedo kN/m³)", "gd": "γd (Peso unitario seco kN/m³)"
    }

    st.subheader("📥 Paso 1: Datos de Entrada")
    seleccionados = st.multiselect("Selecciona las variables conocidas:", options=list(dicc.keys()), format_func=lambda x: dicc[x])
    
    inputs = {}
    cols_in = st.columns(3)
    for i, clave in enumerate(seleccionados):
        inputs[clave] = cols_in[i%3].number_input(f"{dicc[clave]}", value=0.0, format="%.4f", key=f"in_{clave}")

    if st.button("🚀 Calcular Estado Inicial"):
        d = {k: 0.0 for k in dicc.keys()}
        for k, v in inputs.items():
            d[k] = v / 100 if k in ['w', 'n', 's'] and v > 1.0 else v
        
        if modo == "Académico": d['vs'] = 1.0
        
        # Lógica de convergencia
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
        st.session_state.seed += 1
        st.rerun()

    if st.session_state.base_calc:
        st.markdown("---")
        c_sim, c_res = st.columns([1.3, 1.7])
        bc = st.session_state.base_calc
        s_idx = st.session_state.seed

        with c_sim:
            st.subheader("🕹️ Simulador Dinámico")
            e_init = float(bc['e']) if bc['e'] > 0 else 0.650
            w_init = float(bc['w']*100) if bc['w'] > 0 else 15.0
            ws_init = float(bc['ws']) if bc['ws'] > 0 else 2.65
            gs_val = bc['gs'] if bc['gs'] > 0 else 2.65

            e_val = st.slider("Relación de vacíos (e)", 0.01, 5.0, e_init, step=0.001, key=f"sl_e_{s_idx}")
            w_val = st.slider("Humedad (w %)", 0.0, 100.0, w_init, step=0.1, key=f"sl_w_{s_idx}") / 100
            ws_val = st.slider("Peso de Sólidos (Ws)", 0.1, 5000.0, ws_init, key=f"sl_ws_{s_idx}", disabled=(modo == "Académico"))
            
            # Recálculo Final
            final = {k: 0.0 for k in dicc.keys()}
            final['gs'], final['e'], final['w'] = gs_val, e_val, w_val
            
            if modo == "Académico":
                final['vs'] = 1.0
                final['ws'] = final['gs'] * final['vs']
            else:
                final['ws'] = ws_val
                final['vs'] = final['ws'] / final['gs']
            
            final['vv'] = final['e'] * final['vs']
            final['ww'] = final['ws'] * final['w']
            final['vw'] = final['ww']
            final['s'] = final['vw'] / final['vv'] if final['vv'] > 0 else 0
            
            if final['s'] > 1.0:
                st.warning("⚠️ Suelo Saturado.")
                final['s'] = 1.0
                final['vw'] = final['vv']
                final['ww'] = final['vw']
            
            final['vt'] = final['vs'] + final['vv']
            final['va'] = max(0.0, final['vv'] - final['vw'])
            final['wm'] = final['ws'] + final['ww']
            final['n'] = final['vv'] / final['vt']

            if st.button("🔄 Reiniciar Simulación"):
                st.session_state.base_calc = None
                st.rerun()

        with c_res:
            st.subheader("📊 Resultados")
            gh = (final['wm']/final['vt'])*9.81 if final['vt'] > 0 else 0
            gd = (final['ws']/final['vt'])*9.81 if final['vt'] > 0 else 0
            
            # Formateo de tabla con etiquetas
            res_list = []
            for k in ["gs", "e", "n", "w", "s", "wm", "ws", "ww", "vt", "vs", "vv", "vw", "va"]:
                val = final[k]
                suffix = "%" if k in ["n", "w", "s"] else ""
                val_disp = val * 100 if suffix == "%" else val
                res_list.append({"Propiedad": dicc[k], "Valor": f"{val_disp:.3f}{suffix}"})
            
            res_list.append({"Propiedad": dicc["gh"], "Valor": f"{gh:.2f}"})
            res_list.append({"Propiedad": dicc["gd"], "Valor": f"{gd:.2f}"})
            
            st.table(pd.DataFrame(res_list))
            
            fig = go.Figure(data=[
                go.Bar(name='Sólidos', x=['Fases'], y=[final['vs']], marker_color='#7E5109', text=[f"{final['vs']:.2f}"]),
                go.Bar(name='Agua', x=['Fases'], y=[final['vw']], marker_color='#3498DB', text=[f"{final['vw']:.2f}"]),
                go.Bar(name='Aire', x=['Fases'], y=[final['va']], marker_color='#BDC3C7', text=[f"{final['va']:.2f}"])
            ])
            fig.update_layout(barmode='stack', height=350, margin=dict(t=10,b=10))
            st.plotly_chart(fig, use_container_width=True)

# --- PESTAÑA 2: ESFUERZOS ---
with tabs[1]:
    st.header("🗂️ Perfil de Esfuerzos (σ, u, σ')")
    c1, c2 = st.columns([1, 2])
    with c1:
        n_est = st.number_input("Número de Estratos", 1, 10, 2)
        nf = st.number_input("Nivel Freático (m)", 0.0, 100.0, 2.0)
        datos_estratos = []
        for i in range(int(n_est)):
            h = st.number_input(f"Espesor H{i+1} (m)", 0.1, 50.0, 3.0, key=f"h_{i}")
            g = st.number_input(f"γ{i+1} (kN/m³)", 1.0, 25.0, 18.0, key=f"g_{i}")
            datos_estratos.append({'h': h, 'g': g})

    # Cálculo de puntos
    prof_puntos = [0.0]
    acum = 0
    for e in datos_estratos:
        acum += e['h']
        prof_puntos.append(acum)
    if nf not in prof_puntos and nf < acum: prof_puntos.append(nf)
    prof_puntos = sorted(prof_puntos)
    
    st_l, u_l, se_l, s_acu = [], [], [], 0
    for i, z in enumerate(prof_puntos):
        if i > 0:
            dz = z - prof_puntos[i-1]
            z_mid = (z + prof_puntos[i-1])/2
            curr_h = 0
            for e in datos_estratos:
                curr_h += e['h']
                if z_mid <= curr_h:
                    s_acu += dz * e['g']
                    break
        u = (z - nf) * 9.81 if z > nf else 0
        st_l.append(s_acu); u_l.append(u); se_l.append(s_acu - u)

    with c2:
        df_p = pd.DataFrame({"Profundidad (m)": prof_puntos, "σ Total (kPa)": st_l, "u (kPa)": u_l, "σ' Efectivo (kPa)": se_l})
        st.dataframe(df_p, use_container_width=True)
        fig_p = go.Figure()
        fig_p.add_trace(go.Scatter(x=st_l, y=prof_puntos, name='σ Total', line=dict(color='brown')))
        fig_p.add_trace(go.Scatter(x=u_l, y=prof_puntos, name='u', line=dict(color='blue', dash='dash')))
        fig_p.add_trace(go.Scatter(x=se_l, y=prof_puntos, name="σ' Efectivo", fill='tonextx', line=dict(color='green')))
        fig_p.update_yaxes(autorange="reversed", title="Z (m)"); st.plotly_chart(fig_p, use_container_width=True)

# --- PESTAÑA 3: PLASTICIDAD ---
with tabs[2]:
    st.header("📈 Plasticidad")
    ll = st.number_input("Límite Líquido (LL)", 0, 150, 40)
    lp = st.number_input("Límite Plástico (LP)", 0, 100, 20)
    ip = ll - lp
    st.metric("Índice de Plasticidad (IP)", ip)
    
    xv = np.linspace(0, 100, 100)
    fig_c = go.Figure()
    fig_c.add_trace(go.Scatter(x=xv, y=0.73*(xv-20), name='Línea A', line=dict(color='black')))
    fig_c.add_trace(go.Scatter(x=[ll], y=[ip], mode='markers', marker=dict(size=12, color='red'), name="Suelo"))
    fig_c.update_xaxes(title="LL", range=[0, 100]); fig_c.update_yaxes(title="IP", range=[0, 60])
    st.plotly_chart(fig_c, use_container_width=True)
