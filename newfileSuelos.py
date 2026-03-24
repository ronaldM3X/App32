import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import io

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="Geotecnia Master v25.0", layout="wide", page_icon="🏗️")

# Diccionario Maestro de Etiquetas
DICC_LABELS = {
    "gs": "Gs (Gravedad específica)", "e": "e (Relación de vacíos)", "n": "n (Porosidad %)",
    "w": "w (Contenido de humedad %)", "s": "S (Grado de saturación %)", "wm": "Wt (Peso total g)",
    "ws": "Ws (Peso sólidos g)", "ww": "Ww (Peso agua g)", "vt": "Vt (Volumen total cm³)",
    "vs": "Vs (Volumen sólidos cm³)", "vv": "Vv (Volumen vacíos cm³)", "vw": "Vw (Volumen agua cm³)",
    "va": "Va (Volumen aire cm³)", "gh": "γ (Húmedo kN/m³)", "gd": "γd (Seco kN/m³)"
}

# --- LÓGICA DE LIMPIEZA DE MEMORIA (HARD RESET) ---
if "modo_previo" not in st.session_state:
    st.session_state.modo_previo = "Metas"

st.sidebar.title("⚙️ Configuración")
modo_actual = st.sidebar.radio("Selecciona el Modo:", ("Metas", "Académico"))

# Si el usuario cambia el modo, se borra TODO el estado para evitar que Vs=1 persista
if modo_actual != st.session_state.modo_previo:
    st.session_state.modo_previo = modo_actual
    for key in list(st.session_state.keys()):
        if key != "modo_previo":
            del st.session_state[key]
    st.rerun()

if "base_calc" not in st.session_state:
    st.session_state.base_calc = None

st.title(f"🏗️ Geotecnia Master - Modo {modo_actual}")
st.markdown("---")

tabs = st.tabs(["🧩 Gravimetría & Fases", "🗂️ Perfil de Esfuerzos", "📈 Plasticidad", "📥 Reporte Excel"])

# --- PESTAÑA 1: GRAVIMETRÍA ---
with tabs[0]:
    st.subheader("📥 Paso 1: Datos de Entrada")
    seleccionados = st.multiselect("Variables conocidas:", options=list(DICC_LABELS.keys()), format_func=lambda x: DICC_LABELS[x])
    
    inputs = {}
    cols_in = st.columns(3)
    for i, clave in enumerate(seleccionados):
        inputs[clave] = cols_in[i%3].number_input(f"{DICC_LABELS[clave]}", value=0.0, format="%.4f", key=f"input_{clave}")

    if st.button("🚀 Calcular Estado Inicial"):
        d = {k: 0.0 for k in DICC_LABELS.keys()}
        for k, v in inputs.items():
            d[k] = v / 100 if k in ['w', 'n', 's'] and v > 1.0 else v
        
        # En modo Académico forzamos Vs=1, en Metas NO.
        if modo_actual == "Académico": d['vs'] = 1.0
        
        for _ in range(100):
            if d['gs'] > 0 and d['ws'] > 0 and d['vs'] == 0: d['vs'] = d['ws'] / d['gs']
            if d['gs'] > 0 and d['vs'] > 0 and d['ws'] == 0: d['ws'] = d['gs'] * d['vs']
            if d['ws'] > 0 and d['w'] > 0 and d['ww'] == 0: d['ww'] = d['ws'] * d['w']
            if d['ww'] > 0: d['vw'] = d['ww']
            if d['vt'] > 0 and d['vs'] > 0 and d['vv'] == 0: d['vv'] = d['vt'] - d['vs']
            if d['vv'] > 0 and d['vs'] > 0 and d['e'] == 0: d['e'] = d['vv'] / d['vs']
            if d['vs'] > 0 and d['vv'] >= 0: d['vt'] = d['vs'] + d['vv']
            if d['ws'] > 0 and d['ww'] >= 0: d['wm'] = d['ws'] + d['ww']

        st.session_state.base_calc = d
        st.rerun()

    if st.session_state.base_calc:
        st.markdown("---")
        c_sim, c_res = st.columns([1.2, 1.8])
        bc = st.session_state.base_calc

        with c_sim:
            st.subheader("🕹️ Simulador Dinámico")
            # Extraemos valores del Paso 1 para inicializar sliders
            e_def = float(bc['e']) if bc['e'] > 0 else 0.650
            w_def = float(bc['w']*100) if bc['w'] > 0 else 15.0
            ws_def = float(bc['ws']) if bc['ws'] > 0 else 2.650
            gs_val = bc['gs'] if bc['gs'] > 0 else 2.650

            e_v = st.slider("Relación de vacíos (e)", 0.01, 5.0, e_def)
            w_v = st.slider("Humedad (w %)", 0.0, 100.0, w_def) / 100
            ws_v = st.slider("Peso Sólidos (Ws)", 0.1, 5000.0, ws_def, disabled=(modo_actual == "Académico"))
            
            # --- CÁLCULO FINAL SEGURO ---
            res = {k: 0.0 for k in DICC_LABELS.keys()}
            res['gs'], res['e'], res['w'] = gs_val, e_v, w_v
            
            if modo_actual == "Académico":
                res['vs'] = 1.0
                res['ws'] = gs_val * 1.0
            else:
                # Aquí Vs es dinámico y depende de Ws
                res['ws'] = ws_v
                res['vs'] = res['ws'] / res['gs']
            
            res['vv'] = res['e'] * res['vs']
            res['vt'] = res['vs'] + res['vv']
            res['ww'] = res['ws'] * res['w']
            res['vw'] = res['ww']
            res['s'] = res['vw'] / res['vv'] if res['vv'] > 0 else 0
            
            if res['s'] > 1.0:
                st.warning("⚠️ Saturación ajustada a 100%.")
                res['s'], res['vw'] = 1.0, res['vv']
                res['ww'] = res['vw']
            
            res['va'] = max(0.0, res['vv'] - res['vw'])
            res['wm'] = res['ws'] + res['ww']
            res['n'] = res['vv'] / res['vt']
            res['gh'] = (res['wm']/res['vt'])*9.81 if res['vt'] > 0 else 0
            res['gd'] = (res['ws']/res['vt'])*9.81 if res['vt'] > 0 else 0

            if st.button("🔄 Reiniciar Datos"):
                st.session_state.base_calc = None
                st.rerun()

        with c_res:
            st.subheader("📊 Resultados")
            filas = []
            for k, label in DICC_LABELS.items():
                val = res[k]
                txt = f"{val*100:.2f}%" if "%" in label else f"{val:.4f}"
                filas.append({"Propiedad": label, "Valor": txt})
            
            df_final = pd.DataFrame(filas)
            st.table(df_final)
            st.session_state.df_grav = df_final
            
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
    c1, c2 = st.columns([1, 2])
    with c1:
        n_est = st.number_input("Número de Estratos", 1, 10, 2)
        nf = st.number_input("Nivel Freático (m)", 0.0, 100.0, 2.0)
        estratos = []
        for i in range(int(n_est)):
            h = st.number_input(f"H{i+1} (m)", 0.1, 50.0, 3.0, key=f"hz_{i}")
            g = st.number_input(f"γ{i+1} (kN/m³)", 1.0, 25.0, 18.0, key=f"gz_{i}")
            estratos.append({'h': h, 'g': g})

    puntos = sorted(list(set([0.0, nf] + [sum([e['h'] for e in estratos[:i+1]]) for i in range(len(estratos))])))
    puntos = [p for p in puntos if p <= sum([e['h'] for e in estratos])]
    
    z_l, st_l, u_l, se_l = [], [], [], []
    s_acu = 0
    for i in range(len(puntos)):
        z = puntos[i]
        if i > 0:
            dz = z - puntos[i-1]
            z_mid = (z + puntos[i-1])/2
            h_acc = 0
            for e in estratos:
                h_acc += e['h']
                if z_mid <= h_acc:
                    s_acu += dz * e['g']
                    break
        u = (z - nf) * 9.81 if z > nf else 0
        z_l.append(z); st_l.append(s_acu); u_l.append(u); se_l.append(s_acu - u)

    with c2:
        df_esf = pd.DataFrame({"Z (m)": z_l, "σ Total": st_l, "u": u_l, "σ' Efec.": se_l})
        st.dataframe(df_esf)
        st.session_state.df_esf = df_esf
        fig_p = go.Figure()
        fig_p.add_trace(go.Scatter(x=st_l, y=z_l, name='Total', line=dict(color='brown')))
        fig_p.add_trace(go.Scatter(x=u_l, y=z_l, name='u', line=dict(color='blue', dash='dash')))
        fig_p.add_trace(go.Scatter(x=se_l, y=z_l, name='Efectivo', fill='tonextx', line=dict(color='green')))
        fig_p.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_p, use_container_width=True)

# --- PESTAÑA 3: PLASTICIDAD ---
with tabs[2]:
    st.header("📈 Plasticidad")
    ll = st.number_input("LL", 0, 150, 40)
    lp = st.number_input("LP", 0, 100, 20)
    ip = ll - lp
    st.metric("IP", ip)
    st.session_state.df_plas = pd.DataFrame({"Dato": ["LL", "LP", "IP"], "Valor": [ll, lp, ip]})
    xv = np.linspace(0, 100, 100)
    fig_c = go.Figure()
    fig_c.add_trace(go.Scatter(x=xv, y=0.73*(xv-20), name='Línea A', line=dict(color='black')))
    fig_c.add_trace(go.Scatter(x=[ll], y=[ip], mode='markers', marker=dict(size=12, color='red')))
    st.plotly_chart(fig_c)

# --- PESTAÑA 4: EXCEL ---
with tabs[3]:
    st.subheader("📥 Generar Reporte")
    if st.button("📊 Preparar Excel"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            if 'df_grav' in st.session_state: st.session_state.df_grav.to_excel(writer, sheet_name='Gravimetria', index=False)
            if 'df_esf' in st.session_state: st.session_state.df_esf.to_excel(writer, sheet_name='Esfuerzos', index=False)
            if 'df_plas' in st.session_state: st.session_state.df_plas.to_excel(writer, sheet_name='Plasticidad', index=False)
        st.download_button("💾 Descargar Excel", output.getvalue(), "Reporte_Geotecnico.xlsx")
    
