import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import io

# 1. CONFIGURACIÓN E IDENTIDAD
st.set_page_config(page_title="Geotecnia Master v25.0", layout="wide")

# Gestión de Modos (Metas y Académico)
if "m_prev" not in st.session_state: st.session_state.m_prev = "Metas"
modo = st.sidebar.radio("Modo de Trabajo:", ("Metas", "Académico"))

# Hard Reset al cambiar de modo para evitar que Vs=1 persista
if modo != st.session_state.m_prev:
    st.session_state.m_prev = modo
    for k in list(st.session_state.keys()):
        if k != "m_prev": del st.session_state[k]
    st.rerun()

LABELS = {
    "gs": "Gs (Gravedad específica)", "e": "e (Relación de vacíos)", "n": "n (Porosidad %)",
    "w": "w (Contenido de humedad %)", "s": "S (Grado de saturación %)", "wm": "Wt (Peso total g)",
    "ws": "Ws (Peso sólidos g)", "ww": "Ww (Peso agua g)", "vt": "Vt (Volumen total cm³)",
    "vs": "Vs (Volumen sólidos cm³)", "vv": "Vv (Volumen vacíos cm³)", "vw": "Vw (Volumen agua cm³)",
    "va": "Va (Volumen aire cm³)", "gh": "γ (Húmedo kN/m³)", "gd": "γd (Seco kN/m³)"
}

st.title(f"🏗️ Geotecnia Master - {modo}")

t_grav, t_esf, t_plas, t_rep = st.tabs(["🧩 Gravimetría", "🗂️ Esfuerzos", "📈 Plasticidad", "📥 Reporte"])

# --- PESTAÑA 1: GRAVIMETRÍA ---
with t_grav:
    c1, c2 = st.columns([1, 1.3])
    with c1:
        st.subheader("📥 Entrada de Datos")
        sel = st.multiselect("Variables conocidas:", options=list(LABELS.keys()), format_func=lambda x: LABELS[x])
        d_in = {k: st.number_input(LABELS[k], value=0.0, format="%.4f", key=f"p1_{k}") for k in sel}
        
        if st.button("🚀 Calcular"):
            base = {k: 0.0 for k in LABELS.keys()}
            for k, v in d_in.items():
                base[k] = v / 100 if k in ['w', 'n', 's'] and v > 1.0 else v
            
            # Motor de convergencia inicial
            for _ in range(100):
                if base['gs'] > 0 and base['ws'] > 0 and base['vs'] == 0: base['vs'] = base['ws'] / base['gs']
                if base['ws'] > 0 and base['w'] > 0 and base['ww'] == 0: base['ww'] = base['ws'] * base['w']
                if base['vs'] > 0 and base['e'] > 0 and base['vv'] == 0: base['vv'] = base['e'] * base['vs']
                if base['vs'] > 0 and base['vv'] >= 0: base['vt'] = base['vs'] + base['vv']
            st.session_state.db = base
            st.rerun()

    if "db" in st.session_state:
        with c2:
            st.subheader("🕹️ Simulador Físico")
            b = st.session_state.db
            
            # Sliders independientes
            e_s = st.slider("Relación de vacíos (e)", 0.01, 4.0, float(b['e']) if b['e']>0 else 0.65)
            w_s = st.slider("Humedad (w %)", 0.0, 100.0, float(b['w']*100) if b['w']>0 else 15.0) / 100
            ws_s = st.slider("Peso Sólidos (Ws)", 0.1, 5000.0, float(b['ws']) if b['ws']>0 else 2.65, disabled=(modo=="Académico"))
            
            # LEYES FÍSICAS ESTRICTAS
            Gs = b['gs'] if b['gs'] > 0 else 2.65
            if modo == "Académico":
                Vs, Ws = 1.0, Gs
            else:
                Ws = ws_s
                Vs = Ws / Gs # Vs SIEMPRE depende de Ws y Gs
            
            Vv = e_s * Vs
            Vt = Vs + Vv
            Ww = Ws * w_s
            Vw = Ww
            S = Vw / Vv if Vv > 0 else 0
            if S > 1.0: S, Vw, Ww = 1.0, Vv, Vv # Límite físico de saturación
            
            res = {
                "gs": Gs, "e": e_s, "n": Vv/Vt, "w": w_s, "s": S, "wm": Ws+Ww, "ws": Ws, "ww": Ww,
                "vt": Vt, "vs": Vs, "vv": Vv, "vw": Vw, "va": max(0, Vv-Vw),
                "gh": ((Ws+Ww)/Vt)*9.81, "gd": (Ws/Vt)*9.81
            }
            
            st.table(pd.DataFrame([{"Propiedad": LABELS[k], "Valor": f"{res[k]*100:.2f}%" if "%" in LABELS[k] else f"{res[k]:.4f}"} for k in LABELS]))
            st.session_state.f_g = res

        fig_f = go.Figure(data=[
            go.Bar(name='Sólidos', x=['Fases'], y=[Vs], marker_color='#7E5109', text=f"Vs: {Vs:.3f}"),
            go.Bar(name='Agua', x=['Fases'], y=[Vw], marker_color='#3498DB', text=f"Vw: {Vw:.3f}"),
            go.Bar(name='Aire', x=['Fases'], y=[max(0, Vv-Vw)], marker_color='#BDC3C7', text=f"Va: {max(0, Vv-Vw):.3f}")
        ])
        fig_f.update_layout(barmode='stack', height=350, title="Diagrama de Fases"); st.plotly_chart(fig_f, use_container_width=True)

# --- PESTAÑA 2: ESFUERZOS (Restaurada) ---
with t_esf:
    st.subheader("🗂️ Perfil de Esfuerzos")
    ca, cb = st.columns([1, 2])
    with ca:
        n_est = st.number_input("Estratos", 1, 10, 2)
        nf = st.number_input("Nivel Freático (m)", 0.0, 100.0, 2.0)
        datos = []
        for i in range(int(n_est)):
            h = st.number_input(f"H{i+1} (m)", 0.1, 50.0, 3.0, key=f"h_{i}")
            g = st.number_input(f"γ{i+1}", 1.0, 25.0, 18.0, key=f"g_{i}")
            datos.append({'h': h, 'g': g})

    pts = sorted(list(set([0.0, nf] + [sum(d['h'] for d in datos[:i+1]) for i in range(len(datos))])))
    z_l, st_l, u_l, se_l, acu = [], [], [], [], 0
    for i, z in enumerate(pts):
        if i > 0:
            dz = z - pts[i-1]
            z_m = (z + pts[i-1])/2
            h_acc = 0
            for d in datos:
                h_acc += d['h']
                if z_m <= h_acc: acu += dz * d['g']; break
        u = (z - nf) * 9.81 if z > nf else 0
        z_l.append(z); st_l.append(acu); u_l.append(u); se_l.append(acu - u)

    with cb:
        df_e = pd.DataFrame({"Z(m)": z_l, "σ Total": st_l, "u": u_l, "σ' Efec": se_l})
        st.dataframe(df_e); st.session_state.f_e = df_e
        fig_e = go.Figure()
        fig_e.add_trace(go.Scatter(x=st_l, y=z_l, name='Total', line=dict(color='brown')))
        fig_e.add_trace(go.Scatter(x=u_l, y=z_l, name='u', line=dict(color='blue')))
        fig_e.add_trace(go.Scatter(x=se_l, y=z_l, name='Efectivo', fill='tonextx', line=dict(color='green')))
        fig_e.update_yaxes(autorange="reversed"); st.plotly_chart(fig_e, use_container_width=True)

# --- PESTAÑA 3: PLASTICIDAD (Restaurada) ---
with t_plas:
    st.subheader("📈 Plasticidad (SUCS)")
    cll, clp = st.columns(2)
    ll = cll.number_input("LL", 0, 150, 40)
    lp = clp.number_input("LP", 0, 100, 20)
    ip = ll - lp
    st.metric("IP", ip)
    xv = np.linspace(0, 100, 100)
    fig_p = go.Figure()
    fig_p.add_trace(go.Scatter(x=xv, y=0.73*(xv-20), name='Línea A', line=dict(color='black')))
    fig_p.add_trace(go.Scatter(x=[ll], y=[ip], mode='markers', marker=dict(size=12, color='red'), name="Suelo"))
    st.plotly_chart(fig_p); st.session_state.f_p = pd.DataFrame({"Dato": ["LL", "LP", "IP"], "Valor": [ll, lp, ip]})

# --- PESTAÑA 4: EXCEL (Restaurado) ---
with t_rep:
    if st.button("📊 Generar Excel"):
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as wr:
            if "f_g" in st.session_state: pd.DataFrame([{"Propiedad": LABELS[k], "Valor": st.session_state.f_g[k]} for k in LABELS]).to_excel(wr, sheet_name='Gravimetria')
            if "f_e" in st.session_state: st.session_state.f_e.to_excel(wr, sheet_name='Esfuerzos')
            if "f_p" in st.session_state: st.session_state.f_p.to_excel(wr, sheet_name='Plasticidad')
        st.download_button("💾 Descargar", buf.getvalue(), "Reporte.xlsx")
        
