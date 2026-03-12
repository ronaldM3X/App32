
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io

# Configuración de la App
st.set_page_config(page_title="Geotecnia Master Pro", layout="wide", page_icon="🏗️")

st.title("🏗️ Geotecnia Master: Suite Integral v3.0")
st.markdown("---")

# --- MENÚ DE NAVEGACIÓN ---
tabs = st.tabs(["🧩 Relaciones de Fase", "🗂️ Perfiles de Presión", "📈 Plasticidad & USCS", "📥 Exportar"])

# --- PESTAÑA 1: RELACIONES DE FASE (MOTOR + SIMULADOR DINÁMICO) ---
with tabs[0]:
    st.header("Relaciones Gravimétricas y Volumétricas")
    
    # Simbología técnica
    with st.expander("ℹ️ Simbología y Glosario"):
        st.write("""
        * **Gs**: Gravedad específica | **e**: Relación de vacíos | **n**: Porosidad (%)
        * **w**: Humedad (%) | **S**: Saturación (%) | **γ**: Peso unitario húmedo
        * **γd**: Peso unitario seco | **Wm**: Peso total húmedo | **Ws**: Peso seco
        * **Vt**: Volumen total
        """)

    opciones_nombres = {
        "gs": "Gs", "e": "e", "n": "n (%)", "w": "w (%)", "s": "S (%)",
        "gh": "γ (kN/m³)", "gd": "γd (kN/m³)", "wm": "Wm (Peso total)", 
        "ws": "Ws (Peso seco/horno)", "vt": "Vt (Volumen total)"
    }
    
    seleccionados = st.multiselect("¿Qué datos conoces?", options=list(opciones_nombres.keys()), format_func=lambda x: opciones_nombres[x])
    
    inputs = {}
    if seleccionados:
        cols = st.columns(3)
        for i, clave in enumerate(seleccionados):
            inputs[clave] = cols[i % 3].number_input(f"{opciones_nombres[clave]}", value=0.0, step=0.01, format="%.3f")

    if st.button("🚀 Calcular y Activar Simulador"):
        # Extracción de datos
        gs = inputs.get("gs", 0.0); e = inputs.get("e", 0.0); n = inputs.get("n", 0.0)/100
        w = inputs.get("w", 0.0)/100; s = inputs.get("s", 0.0)/100; gh = inputs.get("gh", 0.0)
        gd = inputs.get("gd", 0.0); wm = inputs.get("wm", 0.0); ws = inputs.get("ws", 0.0); vt = inputs.get("vt", 0.0)
        gw = 9.81; pasos = []

        # Motor de resolución (10 iteraciones para encadenar fórmulas)
        for _ in range(10):
            if wm > 0 and ws > 0: ww = wm - ws
            if ws > 0 and 'ww' in locals() and ww > 0 and w == 0: w = ww / ws; pasos.append(f"w = Ww/Ws = {w*100:.2f}%")
            unit_w = 1.0 if (vt > 0 and vt < 5000) or (ws > 0 and ws > 50) else 9.81
            if ws > 0 and gs > 0:
                vs = ws / (gs * unit_w)
                if vt > 0 and e == 0: e = (vt - vs) / vs; pasos.append(f"e = (Vt - Vs)/Vs = {e:.3f}")
            if e > 0 and n == 0: n = e/(1+e); pasos.append(f"n = e/(1+e) = {n:.3f}")
            if n > 0 and e == 0: e = n/(1-n); pasos.append(f"e = n/(1-n) = {e:.3f}")
            if s > 0 and e > 0 and gs > 0 and w == 0: w = (s*e)/gs; pasos.append(f"w = (S*e)/Gs = {w:.3f}")
            if w > 0 and gs > 0 and e > 0 and s == 0: s = (w*gs)/e; pasos.append(f"S = (w*Gs)/e = {s:.3f}")
            if gs > 0 and e > 0 and gd == 0: gd = (gs*gw)/(1+e); pasos.append(f"γd = (Gs*gw)/(1+e) = {gd:.2f}")
            if gd > 0 and w > 0 and gh == 0: gh = gd*(1+w); pasos.append(f"γ = γd*(1+w) = {gh:.2f}")

        # Guardar estado para el simulador en vivo
        st.session_state.suelo = {"ws": ws if ws > 0 else 160.0, "vt": vt if vt > 0 else 100.0, "gs": gs if gs > 0 else 2.65, "w": w, "pasos": pasos}

    if 'suelo' in st.session_state:
        st.markdown("---")
        st.subheader("🎚️ Ajuste Físico en Vivo")
        w_sim = st.slider("Variar Humedad (w %)", 0.0, 60.0, float(st.session_state.suelo['w'] * 100))
        
        # Recálculo físico instantáneo
        ws_v = st.session_state.suelo['ws']; vt_v = st.session_state.suelo['vt']; gs_v = st.session_state.suelo['gs']
        w_v = w_sim / 100; ww_v = ws_v * w_v; vs_v = ws_v / (gs_v * 1.0)
        vw_v = ww_v / 1.0; vv_v = vt_v - vs_v; va_v = vv_v - vw_v
        
        if va_v < 0:
            st.warning("⚠️ Saturación alcanzada."); va_v = 0; vw_v = vv_v
        
        # Resultados y Diagrama
        c1, c2 = st.columns([1, 2])
        c1.metric("Saturación (S)", f"{(vw_v/vv_v)*100:.1f}%")
        c1.metric("Peso Total (Wm)", f"{ws_v + ww_v:.2f}")
        
        fig_f = go.Figure(data=[
            go.Bar(name='Sólidos', x=['Suelo'], y=[vs_v], marker_color='#7E5109'),
            go.Bar(name='Agua', x=['Suelo'], y=[vw_v], marker_color='#3498DB'),
            go.Bar(name='Aire', x=['Suelo'], y=[va_v], marker_color='#BDC3C7')
        ])
        fig_f.update_layout(barmode='stack', height=350, title="Simulación de Fases")
        c2.plotly_chart(fig_f, use_container_width=True)
        with st.expander("📖 Ver procedimiento detallado"):
            for p in st.session_state.suelo['pasos']: st.write(f"🔹 {p}")

# --- PESTAÑA 2: PERFILES DE PRESIÓN ---
with tabs[1]:
    st.header("Esfuerzos Geostáticos Verticales")
    cp1, cp2 = st.columns([1, 1.5])
    with cp1:
        n_est = st.number_input("N° Estratos", 1, 5, 2)
        nf = st.number_input("Nivel Freático (m)", 0.0, 50.0, 2.0)
        est = []
        for i in range(int(n_est)):
            st.markdown(f"**Capa {i+1}**")
            cols_e = st.columns(2)
            h_e = cols_e[0].number_input(f"H (m)", 0.1, 50.0, 3.0, key=f"hp_{i}")
            g_e = cols_e[1].number_input(f"γ (kN/m³)", 10.0, 25.0, 18.0, key=f"gp_{i}")
            est.append({'h': h_e, 'g': g_e})

    z, stot, u, sef = [0], [0], [0], [0]
    za, sta = 0, 0
    for e in est:
        za += e['h']; sta += e['g']*e['h']
        ua = (za-nf)*9.81 if za > nf else 0
        z.append(za); stot.append(sta); u.append(ua); sef.append(sta-ua)

    with cp2:
        fig_p = go.Figure()
        fig_p.add_trace(go.Scatter(x=stot, y=z, name='σ Total', line=dict(color='brown')))
        fig_p.add_trace(go.Scatter(x=u, y=z, name='Presión u', line=dict(color='blue')))
        fig_p.add_trace(go.Scatter(x=sef, y=z, name="σ' Ef.", fill='tonextx', line=dict(color='green')))
        fig_p.update_yaxes(autorange="reversed", title="Z (m)")
        st.plotly_chart(fig_p, use_container_width=True)
        st.table(pd.DataFrame({"Z": z, "Total": stot, "u": u, "Efectivo": sef}))

# --- PESTAÑA 3: PLASTICIDAD & USCS ---
with tabs[2]:
    st.header("Clasificación de Suelos Finos")
    cl1, cl2 = st.columns([1, 2])
    with cl1:
        ll = st.number_input("Límite Líquido", 0, 120, 45)
        lp = st.number_input("Límite Plástico", 0, 80, 20)
        ip = ll - lp
        st.metric("IP", f"{ip}")
        if ll < 50:
            clas = "CL" if ip > 7 and ip >= 0.73*(ll-20) else "ML"
        else:
            clas = "CH" if ip >= 0.73*(ll-20) else "MH"
        st.success(f"**Clasificación USCS:** {clas}")

    with cl2:
        fig_c = go.Figure()
        fig_c.add_trace(go.Scatter(x=[20, 100], y=[0, 0.73*80], mode='lines', name='Línea A', line=dict(color='black')))
        fig_c.add_trace(go.Scatter(x=[ll], y=[ip], mode='markers', marker=dict(size=15, color='red')))
        fig_c.update_layout(xaxis_title="LL", yaxis_title="IP", height=400)
        st.plotly_chart(fig_c, use_container_width=True)

# --- PESTAÑA 4: EXPORTAR ---
with tabs[3]:
    st.header("Reporte Excel")
    if st.button("📥 Generar Archivo"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            pd.DataFrame({"Nota": ["Análisis Geotécnico Completo"]}).to_excel(writer)
        st.download_button("Descargar Reporte.xlsx", output.getvalue(), "reporte_suelos.xlsx")
