import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import io

# 1. IDENTIDAD Y CONFIGURACIÓN
st.set_page_config(page_title="Geotecnia Master Pro", layout="wide", page_icon="🏗️")

LABELS = {
    "gs": "Gs (Gravedad específica)", "e": "e (Relación de vacíos)", "n": "n (Porosidad %)",
    "w": "w (Contenido de humedad %)", "s": "S (Grado de saturación %)", "wm": "Wt (Peso total g)",
    "ws": "Ws (Peso sólidos g)", "ww": "Ww (Peso agua g)", "vt": "Vt (Volumen total cm³)",
    "vs": "Vs (Volumen sólidos cm³)", "vv": "Vv (Volumen vacíos cm³)", "vw": "Vw (Volumen agua cm³)",
    "va": "Va (Volumen aire cm³)", "gh": "γ (Húmedo kN/m³)", "gd": "γd (Seco kN/m³)"
}

st.title("🏗️ Geotecnia Master - Motor de Inferencia")
st.markdown("---")

tabs = st.tabs(["🧩 Gravimetría Inteligente", "🗂️ Perfil de Esfuerzos", "📈 Plasticidad", "📥 Reporte"])

# --- PESTAÑA 1: MOTOR DE INFERENCIA ---
with tabs[0]:
    c1, c2 = st.columns([1, 1.2])
    with c1:
        st.subheader("📥 Entrada de Datos")
        sel = st.multiselect("Datos conocidos:", options=list(LABELS.keys()), format_func=lambda x: LABELS[x])
        inputs = {k: st.number_input(LABELS[k], value=0.0, format="%.4f", key=f"raw_{k}") for k in sel}
        
        if st.button("🚀 Ejecutar Inferencia"):
            d = {k: 0.0 for k in LABELS.keys()}
            for k, v in inputs.items():
                d[k] = v / 100 if k in ['w', 'n', 's'] and v > 1.0 else v
            
            for _ in range(150):
                if d['ws'] > 0 and d['ww'] >= 0: d['wm'] = d['ws'] + d['ww']
                if d['wm'] > 0 and d['ws'] > 0: d['ww'] = d['wm'] - d['ws']
                if d['ws'] > 0 and d['w'] > 0 and d['ww'] == 0: d['ww'] = d['ws'] * d['w']
                if d['gs'] > 0 and d['ws'] > 0 and d['vs'] == 0: d['vs'] = d['ws'] / d['gs']
                if d['gs'] > 0 and d['vs'] > 0 and d['ws'] == 0: d['ws'] = d['gs'] * d['vs']
                if d['vs'] > 0 and d['vv'] > 0: d['vt'] = d['vs'] + d['vv']; d['e'] = d['vv'] / d['vs']
                if d['vt'] > 0 and d['vs'] > 0: d['vv'] = d['vt'] - d['vs']
                if d['e'] > 0: d['n'] = d['e'] / (1 + d['e'])
                if d['n'] > 0: d['e'] = d['n'] / (1 - d['n'])
                if d['ww'] >= 0: d['vw'] = d['ww']
                if d['vv'] > 0 and d['vw'] >= 0: d['s'] = d['vw'] / d['vv']; d['va'] = d['vv'] - d['vw']
                if d['s'] > 0 and d['e'] > 0 and d['gs'] > 0 and d['w'] == 0: d['w'] = (d['s'] * d['e']) / d['gs']
                if d['wm'] > 0 and d['vt'] > 0: d['gh'] = (d['wm'] / d['vt']) * 9.81
                if d['ws'] > 0 and d['vt'] > 0: d['gd'] = (d['ws'] / d['vt']) * 9.81

            st.session_state.master = d
            st.rerun()

    if "master" in st.session_state:
        with c2:
            m = st.session_state.master
            st.table(pd.DataFrame([{"Propiedad": LABELS[k], "Valor": f"{m[k]*100:.2f}%" if "%" in LABELS[k] else f"{m[k]:.4f}"} for k in LABELS]))
            fig = go.Figure(data=[
                go.Bar(name='Sólidos', x=['Fases'], y=[m['vs']], marker_color='#7E5109'),
                go.Bar(name='Agua', x=['Fases'], y=[m['vw']], marker_color='#3498DB'),
                go.Bar(name='Aire', x=['Fases'], y=[max(0, m['va'])], marker_color='#BDC3C7')
            ])
            fig.update_layout(barmode='stack', height=350)
            st.plotly_chart(fig, use_container_width=True)

# --- PESTAÑA 2: ESFUERZOS (CORREGIDA) ---
with tabs[1]:
    st.subheader("🗂️ Perfil Geostático")
    ca, cb = st.columns([1, 2])
    with ca:
        n_estratos = st.number_input("Estratos", 1, 15, 2)
        nf = st.number_input("Nivel Freático (m)", 0.0, 100.0, 2.0)
        capas = []
        for i in range(int(n_estratos)):
            h = st.number_input(f"H {i+1} (m)", 0.1, 100.0, 3.0, key=f"h{i}")
            g = st.number_input(f"γ {i+1} (kN/m³)", 1.0, 30.0, 18.0, key=f"g{i}")
            capas.append({'h': h, 'g': g})

    pts = sorted(list(set([0.0, nf] + [sum(c['h'] for c in capas[:i+1]) for i in range(len(capas))])))
    z_plot, st_plot, u_plot, se_plot, sigma_acu = [], [], [], [], 0
    for i, z in enumerate(pts):
        if i > 0:
            dz = z - pts[i-1]
            z_mid = (z + pts[i-1]) / 2
            for c in capas:
                if z_mid <= sum(cp['h'] for cp in capas[:capas.index(c)+1]):
                    sigma_acu += dz * c['g']
                    break
        presion_u = (z - nf) * 9.81 if z > nf else 0
        z_plot.append(z); st_plot.append(sigma_acu); u_plot.append(presion_u); se_plot.append(sigma_acu - presion_u)

    with cb:
        # AQUÍ ESTABA EL ERROR: Las variables ahora coinciden exactamente
        df_esf = pd.DataFrame({"Z (m)": z_plot, "σ Total": st_plot, "u": u_plot, "σ' Efec": se_plot})
        st.dataframe(df_esf)
        st.session_state.res_esf = df_esf
        fig_e = go.Figure()
        fig_e.add_trace(go.Scatter(x=st_plot, y=z_plot, name='Total', line=dict(color='brown')))
        fig_e.add_trace(go.Scatter(x=u_plot, y=z_plot, name='u', line=dict(color='blue')))
        fig_e.add_trace(go.Scatter(x=se_plot, y=z_plot, name='Efectivo', fill='tonextx', line=dict(color='green')))
        fig_e.update_yaxes(autorange="reversed"); st.plotly_chart(fig_e, use_container_width=True)

# --- PESTAÑA 3: PLASTICIDAD ---
with tabs[2]:
    st.subheader("📈 Plasticidad")
    ll = st.number_input("Límite Líquido", 0, 150, 40)
    lp = st.number_input("Límite Plástico", 0, 100, 20)
    ip = ll - lp
    st.metric("IP", ip)
    xv = np.linspace(0, 100, 100)
    fig_p = go.Figure()
    fig_p.add_trace(go.Scatter(x=xv, y=0.73*(xv-20), name='Línea A', line=dict(color='black')))
    fig_p.add_trace(go.Scatter(x=[ll], y=[ip], mode='markers', marker=dict(size=12, color='red')))
    st.plotly_chart(fig_p); st.session_state.res_plas = pd.DataFrame({"Dato": ["LL", "LP", "IP"], "Valor": [ll, lp, ip]})

# --- PESTAÑA 4: REPORTE ---
with tabs[3]:
    if st.button("📊 Descargar Todo"):
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as wr:
            if "master" in st.session_state: pd.DataFrame([{"Prop": LABELS[k], "Val": st.session_state.master[k]} for k in LABELS]).to_excel(wr, sheet_name='Gravimetria')
            if "res_esf" in st.session_state: st.session_state.res_esf.to_excel(wr, sheet_name='Esfuerzos', index=False)
            if "res_plas" in st.session_state: st.session_state.res_plas.to_excel(wr, sheet_name='Plasticidad', index=False)
        st.download_button("💾 Reporte.xlsx", buf.getvalue(), "Reporte_Suelos.xlsx")
