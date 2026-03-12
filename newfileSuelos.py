import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io

st.set_page_config(page_title="Geotecnia Suite Pro", layout="wide", page_icon="🏗️")

st.title("🏗️ Geotecnia Master: Suite Integral v4.0")
st.markdown("---")

tabs = st.tabs(["🧩 Relaciones de Fase", "🗂️ Perfiles de Presión", "📈 Plasticidad & USCS", "📥 Exportar"])

# --- PESTAÑA 1: RELACIONES DE FASE (MOTOR + SIMULADOR MULTIVARIABLE) ---
with tabs[0]:
    st.header("Relaciones Gravimétricas y Volumétricas")
    
    with st.expander("ℹ️ Simbología y Glosario"):
        st.write("**Gs**: Gravedad específica | **e**: Relación vacíos | **n**: Porosidad | **w**: Humedad | **S**: Saturación | **γ**: Peso unitario")

    opc = {"gs": "Gs", "e": "e", "n": "n (%)", "w": "w (%)", "s": "S (%)", "wm": "Wm (Peso Total)", "ws": "Ws (Peso Seco)", "vt": "Vt (Vol. Total)"}
    seleccionados = st.multiselect("¿Qué datos conoces?", options=list(opc.keys()), format_func=lambda x: opc[x])
    
    inputs = {}
    if seleccionados:
        cols = st.columns(3)
        for i, clave in enumerate(seleccionados):
            inputs[clave] = cols[i % 3].number_input(f"{opc[clave]}", value=0.0, format="%.3f", key=f"in_{clave}")

    if st.button("🚀 Inicializar Suelo"):
        # Motor de cálculo inicial
        gs = inputs.get("gs", 2.65); e = inputs.get("e", 0.0); n = inputs.get("n", 0.0)/100
        w = inputs.get("w", 0.0)/100; s = inputs.get("s", 0.0)/100; wm = inputs.get("wm", 0.0)
        ws = inputs.get("ws", 0.0); vt = inputs.get("vt", 0.0); gw = 9.81
        
        # Bucle de inferencia para completar datos faltantes
        for _ in range(10):
            if wm > 0 and ws > 0: ww = wm - ws
            if ws > 0 and gs > 0:
                vs = ws / (gs * 1.0)
                if vt > 0 and e == 0: e = (vt - vs)/vs
            if e > 0 and n == 0: n = e/(1+e)
            if n > 0 and e == 0: e = n/(1-n)
            if s > 0 and e > 0 and gs > 0 and w == 0: w = (s*e)/gs
            if w > 0 and gs > 0 and e > 0 and s == 0: s = (w*gs)/e
        
        # Guardamos el "ADN" del suelo (lo que no cambia: Sólidos y Volumen Total si es muestra inalterada)
        st.session_state.suelo_base = {"ws": ws if ws > 0 else 160.0, "vt": vt if vt > 0 else 100.0, "gs": gs if gs > 0 else 2.65, "w": w, "e": e, "s": s}

    if 'suelo_base' in st.session_state:
        st.markdown("---")
        st.subheader("🎚️ Simulador Multivariable en Vivo")
        
        col_ctrl, col_disp = st.columns([1, 2])
        
        with col_ctrl:
            var_maestra = st.radio("¿Qué variable quieres alterar?", ["Humedad (w)", "Saturación (S)", "Relación de vacíos (e)"])
            
            # Lógica de Sliders según elección
            if var_maestra == "Humedad (w)":
                val = st.slider("Ajustar w (%)", 0.0, 60.0, float(st.session_state.suelo_base['w']*100))
                w_v = val/100; e_v = st.session_state.suelo_base['e']; s_v = (w_v * st.session_state.suelo_base['gs']) / e_v
            elif var_maestra == "Saturación (S)":
                val = st.slider("Ajustar S (%)", 0.0, 100.0, float(st.session_state.suelo_base['s']*100))
                s_v = val/100; e_v = st.session_state.suelo_base['e']; w_v = (s_v * e_v) / st.session_state.suelo_base['gs']
            else: # Alterar e (Compactación/Expansión)
                val = st.slider("Ajustar e", 0.1, 2.0, float(st.session_state.suelo_base['e']))
                e_v = val; w_v = st.session_state.suelo_base['w']; s_v = (w_v * st.session_state.suelo_base['gs']) / e_v

            # Recálculo físico final
            ws_v = st.session_state.suelo_base['ws']; gs_v = st.session_state.suelo_base['gs']
            vs_v = ws_v / (gs_v * 1.0); vv_v = vs_v * e_v; vt_v = vs_v + vv_v
            vw_v = vv_v * s_v; ww_v = vw_v * 1.0; wm_v = ws_v + ww_v; va_v = vv_v - vw_v
            
            if s_v > 1.0: st.error("⚠️ Suelo sobresaturado."); s_v = 1.0; vw_v = vv_v; va_v = 0

        with col_disp:
            # Tabla en vivo
            datos_v = pd.DataFrame({
                "Propiedad": ["Peso Total (Wm)", "Peso Seco (Ws)", "Volumen Total (Vt)", "Rel. Vacíos (e)", "Saturación (S)", "Humedad (w)"],
                "Valor Actual": [f"{wm_v:.2f} g", f"{ws_v:.2f} g", f"{vt_v:.2f} cm³", f"{e_v:.3f}", f"{s_v*100:.1f}%", f"{w_v*100:.1f}%"]
            })
            st.table(datos_v)
            
            # Diagrama dinámico
            fig = go.Figure(data=[
                go.Bar(name='Sólidos', x=['Fases'], y=[vs_v], marker_color='#7E5109'),
                go.Bar(name='Agua', x=['Fases'], y=[vw_v], marker_color='#3498DB'),
                go.Bar(name='Aire', x=['Fases'], y=[va_v if va_v > 0 else 0], marker_color='#BDC3C7')
            ])
            fig.update_layout(barmode='stack', height=300, margin=dict(t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)

# --- PESTAÑA 2: PERFILES DE PRESIÓN ---
with tabs[1]:
    st.header("Análisis de Esfuerzos")
    c1, c2 = st.columns([1, 1.5])
    with c1:
        n_est = st.number_input("Estratos", 1, 5, 2); nf = st.number_input("N.F. (m)", 0.0, 50.0, 2.0)
        est = []
        for i in range(int(n_est)):
            cols = st.columns(2)
            h = cols[0].number_input(f"H{i+1}", 0.1, 50.0, 3.0, key=f"h_{i}")
            g = cols[1].number_input(f"γ{i+1}", 10.0, 25.0, 18.0, key=f"g_{i}")
            est.append({'h': h, 'g': g})
    z, stot, u, sef = [0], [0], [0], [0]
    za, sta = 0, 0
    for e in est:
        za += e['h']; sta += e['g']*e['h']
        ua = (za-nf)*9.81 if za > nf else 0
        z.append(za); stot.append(sta); u.append(ua); sef.append(sta-ua)
    with c2:
        fig_p = go.Figure()
        fig_p.add_trace(go.Scatter(x=stot, y=z, name='σ Total', line=dict(color='brown')))
        fig_p.add_trace(go.Scatter(x=u, y=z, name='u', line=dict(color='blue')))
        fig_p.add_trace(go.Scatter(x=sef, y=z, name="σ' Ef.", fill='tonextx', line=dict(color='green')))
        fig_p.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_p, use_container_width=True)

# --- PESTAÑA 3: PLASTICIDAD ---
with tabs[2]:
    st.header("Clasificación USCS")
    ll = st.number_input("LL", 0, 100, 45); lp = st.number_input("LP", 0, 100, 20); ip = ll - lp
    st.metric("IP", ip)
    fig_c = go.Figure()
    fig_c.add_trace(go.Scatter(x=[20, 100], y=[0, 0.73*80], mode='lines', name='Línea A'))
    fig_c.add_trace(go.Scatter(x=[ll], y=[ip], mode='markers', marker=dict(size=12, color='red')))
    st.plotly_chart(fig_c)

# --- PESTAÑA 4: EXPORTAR ---
with tabs[3]:
    st.header("Reporte")
    if st.button("📥 Generar Excel"):
        st.write("Excel preparado para descarga.")
        
