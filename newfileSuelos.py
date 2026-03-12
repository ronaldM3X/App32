import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io

# Configuración inicial
st.set_page_config(page_title="Geotecnia Master: Universal Solver", layout="wide")

st.title("🏗️ Geotecnia Master: Motor de Resolución Universal")
st.markdown("Solucionador para Relaciones de Fase, Perfiles de Presión y Carta de Plasticidad.")

# --- BARRA LATERAL: ENTRADA DE DATOS PARA RELACIONES DE FASE ---
st.sidebar.header("📥 Datos para Fase de Suelos")
st.sidebar.info("Para problemas del tipo 2-1 al 2-15, introduce los datos conocidos aquí.")

in_gs = st.sidebar.number_input("Gs (Gravedad Específica)", value=0.0, step=0.01)
in_e = st.sidebar.number_input("e (Relación de Vacíos)", value=0.0, step=0.001)
in_n = st.sidebar.number_input("n (Porosidad) [%]", value=0.0, step=0.1) / 100
in_w = st.sidebar.number_input("w (Humedad) [%]", value=0.0, step=0.1) / 100
in_s = st.sidebar.number_input("S (Saturación) [%]", value=0.0, step=0.1) / 100
in_gh = st.sidebar.number_input("γ (Peso Húmedo) [kN/m³]", value=0.0, step=0.1)
in_gd = st.sidebar.number_input("γd (Peso Seco) [kN/m³]", value=0.0, step=0.1)

# Pestañas principales
tabs = st.tabs(["🧩 Relaciones de Fase", "🗂️ Perfiles de Presión", "📈 Carta Casagrande", "📥 Exportar"])

# --- TAB 1: RELACIONES DE FASE ---
with tabs[0]:
    st.header("Resolución de Índices y Propiedades")
    
    # Motor de Inferencia (Lógica de Despeje)
    gs, e, n, w, s, gh, gd = in_gs, in_e, in_n, in_w, in_s, in_gh, in_gd
    gw = 9.81  # kN/m3
    
    for _ in range(4): # Varias pasadas para encadenar fórmulas
        if e > 0 and n == 0: n = e / (1 + e)
        if n > 0 and e == 0: e = n / (1 - n)
        if s > 0 and e > 0 and w > 0 and gs == 0: gs = (s * e) / w
        if s > 0 and e > 0 and gs > 0 and w == 0: w = (s * e) / gs
        if w > 0 and gs > 0 and s > 0 and e == 0: e = (w * gs) / s
        if w > 0 and gs > 0 and e > 0 and s == 0: s = (w * gs) / e
        if gs > 0 and e > 0 and gd == 0: gd = (gs * gw) / (1 + e)
        if gd > 0 and gs > 0 and e == 0: e = ((gs * gw) / gd) - 1
        if gd > 0 and w > 0 and gh == 0: gh = gd * (1 + w)
        if gh > 0 and w > 0 and gd == 0: gd = gh / (1 + w)

    if gs > 0 or e > 0 or gh > 0:
        res_fase = pd.DataFrame({
            "Parámetro": ["Gs", "e", "n (%)", "w (%)", "S (%)", "γ (kN/m³)", "γd (kN/m³)"],
            "Valor": [f"{gs:.2f}", f"{e:.3f}", f"{n*100:.1f}%", f"{w*100:.1f}%", f"{s*100:.1f}%", f"{gh:.2f}", f"{gd:.2f}"]
        })
        st.table(res_fase)
        
        # Diagrama de fases unitario
        vs = 1.0
        vv = e * vs
        vw = s * vv
        va = vv - vw
        st.subheader("📊 Diagrama de Fases (Vs = 1 unitario)")
        st.bar_chart(pd.DataFrame({"Fase": ["Muestra"], "Aire": [va], "Agua": [vw], "Sólidos": [vs]}).set_index("Fase"), color=["#BDC3C7", "#3498DB", "#7E5109"])
    else:
        st.warning("Introduce datos en la barra lateral para resolver.")

# --- TAB 2: PERFILES DE PRESIÓN ---
with tabs[1]:
    st.header("Cálculo de Presiones (Ejercicios 2-16 a 2-19)")
    c1, c2 = st.columns([1, 1.5])
    with c1:
        n_capas = st.number_input("Número de capas", 1, 5, 2)
        nf = st.number_input("Profundidad Nivel Freático (m)", 0.0, 50.0, 3.0)
        capas_data = []
        for i in range(int(n_capas)):
            st.markdown(f"**Capa {i+1}**")
            h_i = st.number_input(f"Espesor (m) {i+1}", 0.1, 100.0, 5.0, key=f"hi{i}")
            g_i = st.number_input(f"γ (kN/m³) {i+1}", 0.1, 30.0, 18.0, key=f"gi{i}")
            capas_data.append({"h": h_i, "g": g_i})
    with c2:
        z_v, st_v, u_v, se_v = [0], [0], [0], [0]
        z_acc, st_acc = 0, 0
        for cp in capas_data:
            z_acc += cp['h']
            st_acc += cp['g'] * cp['h']
            u_acc = (z_acc - nf) * 9.81 if z_acc > nf else 0
            z_v.append(z_acc); st_v.append(st_acc); u_v.append(u_acc); se_v.append(st_acc - u_acc)
        
        df_p = pd.DataFrame({"Prof (m)": z_v, "σ Total": st_v, "u": u_v, "σ' Efectivo": se_v})
        st.table(df_p)
        st.line_chart(df_p.set_index("Prof (m)"))

# --- TAB 3: CARTA CASAGRANDE ---
with tabs[2]:
    st.header("Carta de Plasticidad")
    cl_ll = st.number_input("Límite Líquido (LL)", 0.0, 150.0, 40.0)
    cl_lp = st.number_input("Límite Plástico (LP)", 0.0, 100.0, 20.0)
    cl_ip = cl_ll - cl_lp
    
    fig = go.Figure()
    lx = list(range(20, 101))
    ly = [0.73*(x-20) for x in lx]
    fig.add_trace(go.Scatter(x=lx, y=ly, mode='lines', name='Línea A', line=dict(color='black', dash='dash')))
    fig.add_trace(go.Scatter(x=[cl_ll], y=[cl_ip], mode='markers', marker=dict(color='red', size=15), name='Tu Suelo'))
    fig.update_layout(xaxis_title="LL", yaxis_title="IP", xaxis=dict(range=[0,100]), yaxis=dict(range=[0,60]))
    st.plotly_chart(fig, use_container_width=True)

# --- TAB 4: EXPORTAR ---
with tabs[3]:
    st.header("Reporte Excel")
    if st.button("Generar Reporte"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            pd.DataFrame({"Proyecto": ["Mi Calculo Geotecnico"]}).to_excel(writer, sheet_name='Info')
        st.download_button(label="📥 Descargar Excel", data=output.getvalue(), file_name="geotecnia_pro.xlsx")

