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
        "gs": "Gs (Gravedad específica)", "e": "e (Relación de vacíos)", "n": "n (Porosidad %)",
        "w": "w (Contenido de humedad %)", "s": "S (Grado de saturación %)", "wm": "Wt (Peso total)",
        "ws": "Ws (Peso sólidos)", "ww": "Ww (Peso agua)", "vt": "Vt (Volumen total)",
        "vs": "Vs (Volumen sólidos)", "vv": "Vv (Volumen vacíos)", "vw": "Vw (Volumen agua)",
        "va": "Va (Volumen aire)", "gh": "γ (Peso unitario húmedo)", "gd": "γd (Peso unitario seco)"
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
        
        if modo == "Académico": d['vs'] = 1.0
        
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
        st.rerun()

    if 'base_calc' in st.session_state:
        st.markdown("---")
        c_sim, c_res = st.columns([1.3, 1.7])
        bc = st.session_state.base_calc

        with c_sim:
            st.subheader("🕹️ Simulador Dinámico")
            e_init = float(bc['e']) if bc['e'] > 0 else 0.65
            w_init = float(bc['w']*100) if bc['w'] > 0 else 15.0
            ws_init = float(bc['ws']) if bc['ws'] > 0 else 2.65
            gs_val = bc['gs'] if bc['gs'] > 0 else 2.65

            e_val = st.slider("Relación de vacíos (e)", 0.01, 5.0, e_init, step=0.001)
            w_val = st.slider("Humedad (w %)", 0.0, 100.0, w_init, step=0.1) / 100
            ws_val = st.slider("Peso Sólidos (Ws)", 0.1, 5000.0, ws_init, disabled=(modo=="Académico"))

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

            if final['s'] > 1.0:
                st.warning("⚠️ Suelo saturado (S > 100%).")
                final['s'], final['vw'] = 1.0, final['vv']
                final['ww'] = final['vw']

            final['va'] = max(0.0, final['vv'] - final['vw'])
            final['wm'] = final['ws'] + final['ww']
            final['n'] = final['vv'] / final['vt']

        with c_res:
            st.subheader("📊 Resultados")
            gh_val = (final['wm']/final['vt'])*9.81 if final['vt'] > 0 else 0
            gd_val = (final['ws']/final['vt'])*9.81 if final['vt'] > 0 else 0
            
            res_df = pd.DataFrame({
                "Propiedad": [dicc[k] for k in final.keys() if k in dicc], 
                "Valor": [
                    f"{final['gs']:.3f}", f"{final['e']:.4f}", f"{final['n']*100:.2f}%", 
                    f"{final['w']*100:.2f}%", f"{final['s']*100:.2f}%", f"{final['wm']:.3f} g", 
                    f"{final['ws']:.3f} g", f"{final['ww']:.3f} g", f"{final['vt']:.3f} cm³", 
                    f"{final['vs']:.3f} cm³", f"{final['vv']:.3f} cm³", f"{final['vw']:.3f} cm³", 
                    f"{final['va']:.3f} cm³", f"{gh_val:.2f} kN/m³", f"{gd_val:.2f} kN/m³"
                ]
            })
            st.table(res_df)
            
            fig = go.Figure(data=[
                go.Bar(name='Sólidos', x=['Fases'], y=[final['vs']], marker_color='#7E5109'),
                go.Bar(name='Agua', x=['Fases'], y=[final['vw']], marker_color='#3498DB'),
                go.Bar(name='Aire', x=['Fases'], y=[final['va']], marker_color='#BDC3C7')
            ])
            fig.update_layout(barmode='stack', height=300); st.plotly_chart(fig, use_container_width=True)

# --- PESTAÑA 2: ESFUERZOS GEOSTÁTICOS ---
with tabs[1]:
    st.header("🗂️ Perfil de Esfuerzos")
    c1, c2 = st.columns([1, 2])
    with c1:
        n_est = st.number_input("Número de Estratos", 1, 10, 2)
        nf = st.number_input("Nivel Freático (m)", 0.0, 100.0, 2.0)
        datos_estratos = []
        for i in range(int(n_est)):
            h = st.number_input(f"Espesor H{i+1} (m)", 0.1, 50.0, 3.0, key=f"h_{i}")
            g = st.number_input(f"γ{i+1} (kN/m³)", 1.0, 25.0, 18.0, key=f"g_{i}")
            datos_estratos.append({'h': h, 'g': g})

    prof, st_l, u_l, se_l, s_acu = [0.0], [0.0], [0.0], [0.0], 0
    curr_z = 0
    puntos_interes = [0.0]
    for e in datos_estratos:
        curr_z += e['h']
        puntos_interes.append(curr_z)
    if nf not in puntos_interes: puntos_interes.append(nf)
    puntos_interes = sorted([p for p in puntos_interes if p <= sum(e['h'] for e in datos_estratos)])

    prof_final, st_final, u_final, se_final = [0.0], [0.0], [0.0], [0.0]
    s_acu = 0
    for i in range(1, len(puntos_interes)):
        z_inf = puntos_interes[i]
        z_sup = puntos_interes[i-1]
        dz = z_inf - z_sup
        z_mid = (z_inf + z_sup) / 2
        
        temp_z = 0
        gamma_actual = 0
        for e in datos_estratos:
            temp_z += e['h']
            if z_mid <= temp_z:
                gamma_actual = e['g']
                break
        
        s_acu += dz * gamma_actual
        u = (z_inf - nf) * 9.81 if z_inf > nf else 0
        
        prof_final.append(z_inf)
        st_final.append(s_acu)
        u_final.append(u)
        se_final.append(s_acu - u)

    with c2:
        df_p = pd.DataFrame({"Z (m)": prof_final, "σ Total": st_final, "u": u_final, "σ' Efec.": se_final})
        st.dataframe(df_p)
        fig_p = go.Figure()
        fig_p.add_trace(go.Scatter(x=st_final, y=prof_final, name='σ Total', line=dict(color='brown')))
        fig_p.add_trace(go.Scatter(x=u_final, y=prof_final, name='u', line=dict(color='blue', dash='dash')))
        fig_p.add_trace(go.Scatter(x=se_final, y=prof_final, name="σ' Efec.", fill='tonextx', line=dict(color='green')))
        fig_p.update_yaxes(autorange="reversed", title="Profundidad (m)"); st.plotly_chart(fig_p)

# --- PESTAÑA 3: PLASTICIDAD ---
with tabs[2]:
    st.header("📈 Carta de Plasticidad")
    ll = st.number_input("Límite Líquido (LL)", 0, 150, 40)
    lp = st.number_input("Límite Plástico (LP)", 0, 100, 20)
    ip = ll - lp
    st.metric("IP", ip)
    xv = np.linspace(0, 100, 100)
    fig_c = go.Figure()
    fig_c.add_trace(go.Scatter(x=xv, y=0.73*(xv-20), name='Línea A', line=dict(color='black')))
    fig_c.add_trace(go.Scatter(x=[ll], y=[ip], mode='markers+text', text=["Suelo"], marker=dict(size=12, color='red')))
    st.plotly_chart(fig_c)
    
