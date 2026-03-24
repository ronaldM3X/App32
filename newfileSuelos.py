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
st.info("Ingresa los datos mínimos de laboratorio. El motor intentará deducir el resto mediante leyes físicas.")

tabs = st.tabs(["🧩 Gravimetría Inteligente", "🗂️ Perfil de Esfuerzos", "📈 Plasticidad", "📥 Reporte"])

# --- PESTAÑA 1: MOTOR DE INFERENCIA DE FASES ---
with tabs[0]:
    c1, c2 = st.columns([1, 1.2])
    with c1:
        st.subheader("📥 Entrada de Datos")
        sel = st.multiselect("Datos conocidos:", options=list(LABELS.keys()), format_func=lambda x: LABELS[x])
        inputs = {k: st.number_input(LABELS[k], value=0.0, format="%.4f", key=f"raw_{k}") for k in sel}
        
        if st.button("🚀 Ejecutar Motor de Inferencia"):
            # Inicializamos el diccionario con los datos del usuario
            d = {k: 0.0 for k in LABELS.keys()}
            for k, v in inputs.items():
                d[k] = v / 100 if k in ['w', 'n', 's'] and v > 1.0 else v
            
            # MOTOR DE CONVERGENCIA (150 iteraciones para asegurar que todas las leyes se crucen)
            for _ in range(150):
                # Relaciones de Pesos
                if d['ws'] > 0 and d['ww'] >= 0: d['wm'] = d['ws'] + d['ww']
                if d['wm'] > 0 and d['ws'] > 0: d['ww'] = d['wm'] - d['ws']
                if d['ws'] > 0 and d['w'] > 0 and d['ww'] == 0: d['ww'] = d['ws'] * d['w']
                if d['ww'] > 0 and d['ws'] > 0: d['w'] = d['ww'] / d['ws']
                
                # Relaciones de Gs y Vs
                if d['gs'] > 0 and d['ws'] > 0 and d['vs'] == 0: d['vs'] = d['ws'] / d['gs']
                if d['gs'] > 0 and d['vs'] > 0 and d['ws'] == 0: d['ws'] = d['gs'] * d['vs']
                if d['ws'] > 0 and d['vs'] > 0: d['gs'] = d['ws'] / d['vs']
                
                # Relaciones de Volúmenes y e/n
                if d['vs'] > 0 and d['vv'] > 0: d['vt'] = d['vs'] + d['vv']; d['e'] = d['vv'] / d['vs']
                if d['vt'] > 0 and d['vs'] > 0: d['vv'] = d['vt'] - d['vs']
                if d['e'] > 0: d['n'] = d['e'] / (1 + d['e'])
                if d['n'] > 0: d['e'] = d['n'] / (1 - d['n'])
                if d['e'] > 0 and d['vs'] > 0: d['vv'] = d['e'] * d['vs']
                if d['n'] > 0 and d['vt'] > 0: d['vv'] = d['n'] * d['vt']
                
                # Agua y Saturación (Densidad agua = 1 g/cm³)
                if d['ww'] >= 0: d['vw'] = d['ww']
                if d['vw'] >= 0: d['ww'] = d['vw']
                if d['vv'] > 0 and d['vw'] >= 0: d['s'] = d['vw'] / d['vv']; d['va'] = d['vv'] - d['vw']
                if d['s'] > 0 and d['vv'] > 0: d['vw'] = d['s'] * d['vv']
                
                # La gran ecuación: Se * e = w * Gs
                if d['s'] > 0 and d['e'] > 0 and d['gs'] > 0 and d['w'] == 0: d['w'] = (d['s'] * d['e']) / d['gs']
                if d['w'] > 0 and d['gs'] > 0 and d['e'] > 0 and d['s'] == 0: d['s'] = (d['w'] * d['gs']) / d['e']
                if d['s'] > 0 and d['e'] > 0 and d['w'] > 0 and d['gs'] == 0: d['gs'] = (d['s'] * d['e']) / d['w']
                
                # Pesos Unitarios (Convertir g/cm³ a kN/m³ multiplicando por 9.81)
                if d['wm'] > 0 and d['vt'] > 0: d['gh'] = (d['wm'] / d['vt']) * 9.81
                if d['ws'] > 0 and d['vt'] > 0: d['gd'] = (d['ws'] / d['vt']) * 9.81

            st.session_state.master = d
            st.rerun()

    if "master" in st.session_state:
        with c2:
            m = st.session_state.master
            st.subheader("📊 Resultados Deducidos")
            
            # Tabla de resultados
            res_list = []
            for k, label in LABELS.items():
                val = m[k]
                txt = f"{val*100:.2f}%" if "%" in label else f"{val:.4f}"
                res_list.append({"Propiedad": label, "Valor": txt})
            
            st.table(pd.DataFrame(res_list))
            
            # Diagrama de Fases
            fig = go.Figure(data=[
                go.Bar(name='Sólidos', x=['Fases'], y=[m['vs']], marker_color='#7E5109', text=f"Vs: {m['vs']:.2f}"),
                go.Bar(name='Agua', x=['Fases'], y=[m['vw']], marker_color='#3498DB', text=f"Vw: {m['vw']:.2f}"),
                go.Bar(name='Aire', x=['Fases'], y=[max(0, m['va'])], marker_color='#BDC3C7', text=f"Va: {m['va']:.2f}")
            ])
            fig.update_layout(barmode='stack', height=400, title="Estado Físico de la Muestra")
            st.plotly_chart(fig, use_container_width=True)

# --- PESTAÑA 2: PERFIL DE ESFUERZOS ---
with tabs[1]:
    st.subheader("🗂️ Perfil Geostático")
    ca, cb = st.columns([1, 2])
    with ca:
        n_estratos = st.number_input("Estratos", 1, 15, 2)
        nf = st.number_input("Nivel Freático (m)", 0.0, 100.0, 2.0)
        capas = []
        for i in range(int(n_estratos)):
            cols = st.columns(2)
            h = cols[0].number_input(f"H {i+1} (m)", 0.1, 100.0, 3.0, key=f"h{i}")
            g = cols[1].number_input(f"γ {i+1}", 1.0, 30.0, 18.0, key=f"g{i}")
            capas.append({'h': h, 'g': g})

    # Cálculo de puntos críticos
    profundidades = [0.0]
    acum = 0
    for c in capas:
        acum += c['h']
        profundidades.append(acum)
    if nf not in profundidades and nf < acum: profundidades.append(nf)
    profundidades.sort()

    z_plot, st_plot, u_plot, se_plot, sigma_acu = [], [], [], [], 0
    for i, z in enumerate(profundidades):
        if i > 0:
            dz = z - profundidades[i-1]
            z_mid = (z + profundidades[i-1]) / 2
            h_curr = 0
            for c in capas:
                h_curr += c['h']
                if z_mid <= h_curr:
                    sigma_acu += dz * c['g']
                    break
        presion_u = (z - nf) * 9.81 if z > nf else 0
        z_plot.append(z); st_plot.append(sigma_acu); u_plot.append(presion_u); se_plot.append(sigma_acu - presion_u)

    with cb:
        df_esf = pd.DataFrame({"Z (m)": z_plot, "σ Total": st_l, "u": u_l, "σ' Efec": se_l})
        st.dataframe(df_esf)
        fig_e = go.Figure()
        fig_e.add_trace(go.Scatter(x=st_plot, y=z_plot, name='σ Total', line=dict(color='brown')))
        fig_e.add_trace(go.Scatter(x=u_plot, y=z_plot, name='u', line=dict(color='blue')))
        fig_e.add_trace(go.Scatter(x=se_plot, y=z_plot, name="σ' Efectivo", fill='tonextx', line=dict(color='green')))
        fig_e.update_yaxes(autorange="reversed", title="Profundidad (m)")
        st.plotly_chart(fig_e, use_container_width=True)

# --- PESTAÑA 3: PLASTICIDAD ---
with tabs[2]:
    st.subheader("📈 Análisis de Plasticidad")
    c_ll, c_lp = st.columns(2)
    ll = c_ll.number_input("Límite Líquido", 0, 150, 40)
    lp = c_lp.number_input("Límite Plástico", 0, 100, 20)
    ip = ll - lp
    st.metric("Índice de Plasticidad", ip)
    
    xv = np.linspace(0, 100, 100)
    y_linea_a = 0.73 * (xv - 20)
    fig_p = go.Figure()
    fig_p.add_trace(go.Scatter(x=xv, y=y_linea_a, name='Línea A', line=dict(color='black')))
    fig_p.add_trace(go.Scatter(x=[ll], y=[ip], mode='markers', marker=dict(size=14, color='red'), name="Muestra"))
    fig_p.update_xaxes(title="LL", range=[0, 100]); fig_p.update_yaxes(title="IP", range=[0, 60])
    st.plotly_chart(fig_p)

# --- PESTAÑA 4: REPORTE EXCEL ---
with tabs[3]:
    if st.button("📊 Generar Reporte Final"):
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
            if "master" in st.session_state:
                m_data = [{"Propiedad": LABELS[k], "Valor": st.session_state.master[k]} for k in LABELS]
                pd.DataFrame(m_data).to_excel(writer, sheet_name='Gravimetria', index=False)
            pd.DataFrame({"Z": z_plot, "Total": st_plot, "Poro": u_plot, "Efec": se_plot}).to_excel(writer, sheet_name='Esfuerzos', index=False)
        st.download_button("💾 Descargar Archivo", buf.getvalue(), "Reporte_Geotecnico_Pro.xlsx")
                    
