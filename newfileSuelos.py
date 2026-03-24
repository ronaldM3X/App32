import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import io

# 1. CONFIGURACIÓN Y REINICIO DE MEMORIA
st.set_page_config(page_title="Geotecnia Master v25.0", layout="wide")

if "m_act" not in st.session_state: st.session_state.m_act = "Metas"
modo = st.sidebar.radio("Modo de Trabajo:", ("Metas", "Académico"))

# Hard Reset al cambiar modo para limpiar el Vs de la memoria
if modo != st.session_state.m_act:
    st.session_state.m_act = modo
    for key in list(st.session_state.keys()):
        if key != "m_act": del st.session_state[key]
    st.rerun()

LABELS = {
    "gs": "Gs (Gravedad específica)", "e": "e (Relación de vacíos)", "n": "n (Porosidad %)",
    "w": "w (Contenido de humedad %)", "s": "S (Grado de saturación %)", "wm": "Wt (Peso total g)",
    "ws": "Ws (Peso sólidos g)", "ww": "Ww (Peso agua g)", "vt": "Vt (Volumen total cm³)",
    "vs": "Vs (Volumen sólidos cm³)", "vv": "Vv (Volumen vacíos cm³)", "vw": "Vw (Volumen agua cm³)",
    "va": "Va (Volumen aire cm³)", "gh": "γ (Húmedo kN/m³)", "gd": "γd (Seco kN/m³)"
}

st.title(f"🏗️ Geotecnia Master - {modo}")

tabs = st.tabs(["🧩 Gravimetría", "🗂️ Esfuerzos", "📈 Plasticidad", "📥 Excel"])

# --- PESTAÑA 1: GRAVIMETRÍA (Lógica Física Estricta) ---
with tabs[0]:
    c1, c2 = st.columns([1, 1.2])
    with c1:
        st.subheader("📥 Entrada de Laboratorio")
        sel = st.multiselect("Conocidos:", options=list(LABELS.keys()), format_func=lambda x: LABELS[x])
        d_in = {k: st.number_input(LABELS[k], value=0.0, format="%.4f", key=f"in_{k}") for k in sel}
        
        if st.button("🚀 Procesar Datos"):
            res = {k: 0.0 for k in LABELS.keys()}
            for k, v in d_in.items():
                res[k] = v / 100 if k in ['w', 'n', 's'] and v > 1.0 else v
            
            # Motor de convergencia basado en leyes físicas
            for _ in range(100):
                if res['gs'] > 0 and res['ws'] > 0 and res['vs'] == 0: res['vs'] = res['ws'] / res['gs']
                if res['ws'] > 0 and res['w'] > 0 and res['ww'] == 0: res['ww'] = res['ws'] * res['w']
                if res['vs'] > 0 and res['e'] > 0 and res['vv'] == 0: res['vv'] = res['e'] * res['vs']
                if res['vs'] > 0 and res['vv'] >= 0: res['vt'] = res['vs'] + res['vv']
            st.session_state.datos_base = res
            st.rerun()

    if "datos_base" in st.session_state:
        with c2:
            st.subheader("🕹️ Simulador de Fases")
            db = st.session_state.datos_base
            
            # Sliders con keys únicas para evitar el "ghosting" de valores viejos
            e_dyn = st.slider("Relación de vacíos (e)", 0.01, 4.0, float(db['e']) if db['e']>0 else 0.65)
            w_dyn = st.slider("Humedad (w %)", 0.0, 100.0, float(db['w']*100) if db['w']>0 else 15.0) / 100
            ws_dyn = st.slider("Peso Sólidos (Ws)", 0.1, 5000.0, float(db['ws']) if db['ws']>0 else 2.65, disabled=(modo=="Académico"))
            
            # --- LEYES FÍSICAS NO NEGOCIABLES ---
            Gs = db['gs'] if db['gs'] > 0 else 2.65
            if modo == "Académico":
                Vs = 1.0
                Ws = Gs * Vs
            else:
                Ws = ws_dyn
                Vs = Ws / Gs # Vs SIEMPRE sigue a Ws en modo Metas
            
            Vv = e_dyn * Vs
            Vt = Vs + Vv
            Ww = Ws * w_dyn
            Vw = Ww
            S = Vw / Vv if Vv > 0 else 0
            if S > 1.0: S, Vw, Ww = 1.0, Vv, Vv # Saturación máxima
            
            calc = {
                "gs": Gs, "e": e_dyn, "n": Vv/Vt, "w": w_dyn, "s": S, "wm": Ws+Ww, "ws": Ws, "ww": Ww,
                "vt": Vt, "vs": Vs, "vv": Vv, "vw": Vw, "va": max(0, Vv-Vw),
                "gh": ((Ws+Ww)/Vt)*9.81, "gd": (Ws/Vt)*9.81
            }
            
            st.table(pd.DataFrame([{"Propiedad": LABELS[k], "Valor": f"{calc[k]*100:.2f}%" if "%" in LABELS[k] else f"{calc[k]:.4f}"} for k in LABELS]))
            st.session_state.final_g = calc

        fig = go.Figure(data=[
            go.Bar(name='Sólidos', x=['Fases'], y=[Vs], marker_color='#7E5109', text=f"Vs: {Vs:.3f}"),
            go.Bar(name='Agua', x=['Fases'], y=[Vw], marker_color='#3498DB', text=f"Vw: {Vw:.3f}"),
            go.Bar(name='Aire', x=['Fases'], y=[max(0, Vv-Vw)], marker_color='#BDC3C7', text=f"Va: {max(0, Vv-Vw):.3f}")
        ])
        fig.update_layout(barmode='stack', height=350, title="Diagrama de Fases Dinámico")
        st.plotly_chart(fig, use_container_width=True)

# --- PESTAÑA 2: ESFUERZOS ---
with tabs[1]:
    st.subheader("🗂️ Cálculo de Presiones Geostáticas")
    col_a, col_b = st.columns([1, 2])
    with col_a:
        n_est = st.number_input("Número de estratos", 1, 10, 2)
        nf = st.number_input("Nivel Freático (m)", 0.0, 100.0, 2.0)
        capas = []
        for i in range(int(n_est)):
            h = st.number_input(f"Espesor H{i+1} (m)", 0.1, 50.0, 2.0, key=f"h{i}")
            g = st.number_input(f"Peso Unitario γ{i+1}", 1.0, 25.0, 18.0, key=f"g{i}")
            capas.append({'h': h, 'g': g})

    # Puntos críticos (superficie, cambios de estrato y NF)
    pts = sorted(list(set([0.0, nf] + [sum(c['h'] for c in capas[:i+1]) for i in range(len(capas))])))
    z_l, sig_t, u_l, sig_e = [], [], [], []
    total_sig = 0
    for i, z in enumerate(pts):
        if i > 0:
            dz = z - pts[i-1]
            z_m = (z + pts[i-1])/2
            h_acc = 0
            for c in capas:
                h_acc += c['h']
                if z_m <= h_acc: total_sig += dz * c['g']; break
        pres_u = (z - nf) * 9.81 if z > nf else 0
        z_l.append(z); sig_t.append(total_sig); u_l.append(pres_u); sig_e.append(total_sig - pres_u)

    with col_b:
        df_esf = pd.DataFrame({"Z (m)": z_l, "Total (kPa)": sig_t, "u (kPa)": u_l, "Efectivo (kPa)": sig_e})
        st.dataframe(df_esf, use_container_width=True)
        st.session_state.final_e = df_esf
        fig_e = go.Figure()
        fig_e.add_trace(go.Scatter(x=sig_t, y=z_l, name='σ Total', line=dict(color='brown')))
        fig_e.add_trace(go.Scatter(x=u_l, y=z_l, name='u', line=dict(color='blue')))
        fig_e.add_trace(go.Scatter(x=sig_e, y=z_l, name="σ' Efectivo", fill='tonextx', line=dict(color='green')))
        fig_e.update_yaxes(autorange="reversed", title="Profundidad (m)")
        st.plotly_chart(fig_e, use_container_width=True)

# --- PESTAÑA 3: PLASTICIDAD ---
with tabs[2]:
    st.subheader("📈 Carta de Plasticidad (SUCS)")
    c_ll, c_lp = st.columns(2)
    ll = c_ll.number_input("Límite Líquido (LL)", 0, 150, 40)
    lp = c_lp.number_input("Límite Plástico (LP)", 0, 100, 20)
    ip = ll - lp
    st.metric("Índice de Plasticidad (IP)", ip)
    
    xv = np.linspace(0, 100, 100)
    y_a = 0.73 * (xv - 20)
    fig_p = go.Figure()
    fig_p.add_trace(go.Scatter(x=xv, y=y_a, name='Línea A', line=dict(color='black')))
    fig_p.add_trace(go.Scatter(x=[ll], y=[ip], mode='markers+text', text="Suelo", textposition="top right", marker=dict(size=12, color='red')))
    fig_p.update_xaxes(title="Límite Líquido", range=[0, 100])
    fig_p.update_yaxes(title="Índice de Plasticidad", range=[0, 60])
    st.plotly_chart(fig_p)
    st.session_state.final_p = pd.DataFrame({"Variable": ["LL", "LP", "IP"], "Valor": [ll, lp, ip]})

# --- PESTAÑA 4: REPORTE ---
with tabs[3]:
    if st.button("📊 Generar Reporte Excel"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            if "final_g" in st.session_state: 
                pd.DataFrame([{"Propiedad": LABELS[k], "Valor": st.session_state.final_g[k]} for k in LABELS]).to_excel(writer, sheet_name='Gravimetria', index=False)
            if "final_e" in st.session_state: st.session_state.final_e.to_excel(writer, sheet_name='Esfuerzos', index=False)
            if "final_p" in st.session_state: st.session_state.final_p.to_excel(writer, sheet_name='Plasticidad', index=False)
        st.download_button("💾 Descargar Excel", output.getvalue(), "Reporte_Geotecnico.xlsx")
        
