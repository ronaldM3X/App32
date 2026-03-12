import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io

# Configuración de la App
st.set_page_config(page_title="Geotecnia Master Suite", layout="wide", page_icon="🏗️")

st.title("🏗️ Geotecnia Master: Suite Integral Definitiva")
st.markdown("---")

# --- NAVEGACIÓN POR PESTAÑAS ---
tabs = st.tabs(["🧩 Gravimetría Total", "🗂️ Perfiles de Presión", "📈 Plasticidad & USCS", "📥 Exportar"])

# --- PESTAÑA 1: RELACIONES DE FASE (EL INVENTARIO COMPLETO) ---
with tabs[0]:
    st.header("Inventario de Propiedades Físicas")
    
    opc = {"gs": "Gs", "e": "e", "n": "n (%)", "w": "w (%)", "s": "S (%)", "wm": "Wm (g)", "ws": "Ws (g)", "vt": "Vt (cm³)"}
    seleccionados = st.multiselect("Datos conocidos:", options=list(opc.keys()), format_func=lambda x: opc[x])
    
    inputs = {}
    if seleccionados:
        cols = st.columns(min(len(seleccionados), 4))
        for i, clave in enumerate(seleccionados):
            inputs[clave] = cols[i % 4].number_input(f"{opc[clave]}", value=0.0, format="%.3f", key=f"in_final_{clave}")

    if st.button("🚀 Inicializar Análisis Completo"):
        gs = inputs.get("gs", 2.65); e = inputs.get("e", 0.0); n = inputs.get("n", 0.0)/100
        w = inputs.get("w", 0.0)/100; s = inputs.get("s", 0.0)/100; wm = inputs.get("wm", 0.0)
        ws = inputs.get("ws", 0.0); vt = inputs.get("vt", 0.0)
        
        for _ in range(12):
            if wm > 0 and ws > 0: ww = wm - ws
            if ws > 0 and gs > 0:
                vs = ws / (gs * 1.0)
                if vt > 0 and e == 0: e = (vt - vs)/vs
            if e > 0 and n == 0: n = e/(1+e)
            if n > 0 and e == 0: e = n/(1-n)
            if gs > 0 and e > 0 and s > 0 and w == 0: w = (s*e)/gs
            if gs > 0 and w > 0 and e > 0 and s == 0: s = (w*gs)/e
        
        st.session_state.master_base = {"ws": ws if ws > 0 else 160.0, "vt": vt if vt > 0 else 100.0, "gs": gs if gs > 0 else 2.65, "w": w, "e": e, "s": s}

    if 'master_base' in st.session_state:
        st.markdown("---")
        c_ctrl, c_disp = st.columns([1, 2.5])
        with c_ctrl:
            st.subheader("🕹️ Simulador")
            var = st.radio("Modificar Variable:", ["Humedad (w)", "Saturación (S)", "Rel. Vacíos (e)"])
            if var == "Humedad (w)":
                val = st.slider("w (%)", 0.0, 70.0, float(st.session_state.master_base['w']*100))
                w_v = val/100; e_v = st.session_state.master_base['e']; s_v = (w_v * st.session_state.master_base['gs']) / e_v
            elif var == "Saturación (S)":
                val = st.slider("S (%)", 0.0, 100.0, float(st.session_state.master_base['s']*100))
                s_v = val/100; e_v = st.session_state.master_base['e']; w_v = (s_v * e_v) / st.session_state.master_base['gs']
            else:
                val = st.slider("e (Compactación)", 0.1, 2.5, float(st.session_state.master_base['e']))
                e_v = val; w_v = st.session_state.master_base['w']; s_v = (w_v * st.session_state.master_base['gs']) / e_v

            # Fórmulas de recálculo
            ws_v = st.session_state.master_base['ws']; gs_v = st.session_state.master_base['gs']
            vs_v = ws_v / (gs_v * 1.0); vv_v = vs_v * e_v; vt_v = vs_v + vv_v
            vw_v = vv_v * s_v; ww_v = vw_v * 1.0; wm_v = ws_v + ww_v; va_v = vv_v - vw_v
            if va_v < 0: va_v = 0; vw_v = vv_v; s_v = 1.0; wm_v = ws_v + (vw_v*1.0); w_v = (s_v*e_v)/gs_v

        with c_disp:
            res_v = {
                "Categoría": ["Peso", "Peso", "Peso", "Volumen", "Volumen", "Volumen", "Relación", "Relación", "P. Unitario", "P. Unitario"],
                "Variable": ["Wm (Húmedo)", "Ws (Seco)", "Ww (Agua)", "Vt (Total)", "Vs (Sólidos)", "Vv (Vacíos)", "e", "S (%)", "γ (kN/m³)", "γd (kN/m³)"],
                "Valor": [f"{wm_v:.2f} g", f"{ws_v:.2f} g", f"{ww_v:.2f} g", f"{vt_v:.2f} cm³", f"{vs_v:.2f} cm³", f"{vv_v:.2f} cm³", f"{e_v:.3f}", f"{s_v*100:.1f} %", f"{(wm_v/vt_v)*9.81:.2f}", f"{(ws_v/vt_v)*9.81:.2f}"]
            }
            st.table(pd.DataFrame(res_v))
            fig = go.Figure(data=[go.Bar(name='Sólidos', x=['Fases'], y=[vs_v], marker_color='#7E5109'),
                                  go.Bar(name='Agua', x=['Fases'], y=[vw_v], marker_color='#3498DB'),
                                  go.Bar(name='Aire', x=['Fases'], y=[va_v], marker_color='#BDC3C7')])
            fig.update_layout(barmode='stack', height=300)
            st.plotly_chart(fig, use_container_width=True)

# --- PESTAÑA 2: PERFILES DE PRESIÓN ---
with tabs[1]:
    st.header("Esfuerzos Geostáticos")
    c1, c2 = st.columns([1, 1.5])
    with c1:
        n_est = st.number_input("Estratos", 1, 5, 2); nf = st.number_input("N.F. (m)", 0.0, 50.0, 2.5)
        est = []
        for i in range(int(n_est)):
            co = st.columns(2); h = co[0].number_input(f"H{i+1}", 0.1, 50.0, 3.0, key=f"hp_f_{i}")
            g = co[1].number_input(f"γ{i+1}", 10.0, 25.0, 18.0, key=f"gp_f_{i}"); est.append({'h': h, 'g': g})
    z, stot, u, sef = [0], [0], [0], [0]; za, sta = 0, 0
    for e in est:
        za += e['h']; sta += e['g']*e['h']; ua = (za-nf)*9.81 if za > nf else 0
        z.append(za); stot.append(sta); u.append(ua); sef.append(sta-ua)
    with c2:
        fig_p = go.Figure()
        fig_p.add_trace(go.Scatter(x=stot, y=z, name='σ Total', line=dict(color='brown')))
        fig_p.add_trace(go.Scatter(x=u, y=z, name='u', line=dict(color='blue')))
        fig_p.add_trace(go.Scatter(x=sef, y=z, name="σ' Ef.", fill='tonextx', line=dict(color='green')))
        fig_p.update_yaxes(autorange="reversed", title="Profundidad (m)")
        st.plotly_chart(fig_p, use_container_width=True)
        st.dataframe(pd.DataFrame({"Z(m)": z, "σ Total": stot, "u": u, "σ'": sef}))

# --- PESTAÑA 3: PLASTICIDAD & USCS ---
with tabs[2]:
    st.header("Clasificación de Suelos Finos")
    cl1, cl2 = st.columns([1, 2])
    with cl1:
        ll = st.number_input("Límite Líquido", 0, 120, 45); lp = st.number_input("Límite Plástico", 0, 80, 20); ip = ll - lp
        st.metric("IP", f"{ip}")
        if ll < 50: clas = "CL" if ip > 7 and ip >= 0.73*(ll-20) else "ML"
        else: clas = "CH" if ip >= 0.73*(ll-20) else "MH"
        st.success(f"**Resultado USCS:** {clas}")
    with cl2:
        fig_c = go.Figure(); fig_c.add_trace(go.Scatter(x=[20, 100], y=[0, 0.73*80], mode='lines', name='Línea A'))
        fig_c.add_trace(go.Scatter(x=[ll], y=[ip], mode='markers', marker=dict(size=15, color='red')))
        fig_c.update_layout(xaxis_title="LL", yaxis_title="IP"); st.plotly_chart(fig_c, use_container_width=True)

# --- PESTAÑA 4: EXPORTAR ---
with tabs[3]:
    st.header("Reporte Técnico")
    if st.button("📥 Generar Archivo Excel"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            pd.DataFrame(res_v if 'res_v' in locals() else {"Nota": ["Inicialice gravimetría primero"]}).to_excel(writer, sheet_name='Gravimetria')
            pd.DataFrame({"Z": z, "Total": stot, "u": u, "Efectivo": sef}).to_excel(writer, sheet_name='Presiones')
        st.download_button("Descargar Reporte_Final.xlsx", output.getvalue(), "reporte_geotecnico.xlsx")
    
