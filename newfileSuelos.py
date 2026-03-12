import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import io

# Configuración de la App
st.set_page_config(page_title="Geotecnia Suite Ultimate v7.0", layout="wide", page_icon="🏗️")

st.title("🏗️ Geotecnia Master: Suite Ultimate v7.0")
st.markdown("---")

tabs = st.tabs(["🧩 Gravimetría", "🗂️ Perfil de Presiones", "📈 Carta de Plasticidad", "📥 Reporte Final"])

# --- PESTAÑA 1: GRAVIMETRÍA ---
with tabs[0]:
    st.header("Propiedades Físicas y Relaciones de Fase")
    diccionario_maestro = {
        "gs": "Gs (Gravedad específica)", "e": "e (Relación de vacíos)", "n": "n (Porosidad %)",
        "w": "w (Contenido de humedad %)", "s": "S (Grado de saturación %)", "wm": "Wm (Peso húmedo)",
        "ws": "Ws (Peso seco)", "ww": "Ww (Peso del agua)", "vt": "Vt (Volumen total)",
        "vs": "Vs (Volumen sólidos)", "vv": "Vv (Volumen vacíos)", "vw": "Vw (Volumen agua)",
        "va": "Va (Volumen aire)", "gh": "γ (Peso unitario húmedo)", "gd": "γd (Peso unitario seco)"
    }
    
    seleccionados = st.multiselect("Datos de entrada:", options=list(diccionario_maestro.keys()), format_func=lambda x: diccionario_maestro[x])
    inputs = {}
    if seleccionados:
        cols = st.columns(3)
        for i, clave in enumerate(seleccionados):
            inputs[clave] = cols[i % 3].number_input(f"Valor de {clave}", value=0.0, format="%.3f")

    if st.button("🚀 Calcular Gravimetría"):
        d = {k: inputs.get(k, 0.0) for k in diccionario_maestro.keys()}
        # Ajuste de unidades para cálculo
        d['n'] /= 100; d['w'] /= 100; d['s'] /= 100
        for _ in range(20): # Iteraciones para resolver dependencias
            if d['wm'] > 0 and d['ws'] > 0 and d['ww'] == 0: d['ww'] = d['wm'] - d['ws']
            if d['ws'] > 0 and d['ww'] > 0 and d['wm'] == 0: d['wm'] = d['ws'] + d['ww']
            if d['ws'] > 0 and d['gs'] > 0 and d['vs'] == 0: d['vs'] = d['ws'] / (d['gs'] * 9.81)
            if d['vt'] > 0 and d['vs'] > 0 and d['vv'] == 0: d['vv'] = d['vt'] - d['vs']
            if d['vv'] > 0 and d['vs'] > 0 and d['e'] == 0: d['e'] = d['vv'] / d['vs']
            if d['e'] > 0 and d['n'] == 0: d['n'] = d['e'] / (1 + d['e'])
            if d['gs'] > 0 and d['w'] > 0 and d['e'] > 0 and d['s'] == 0: d['s'] = (d['w'] * d['gs']) / d['e']
            if d['wm'] > 0 and d['vt'] > 0 and d['gh'] == 0: d['gh'] = d['wm'] / d['vt']
            if d['ws'] > 0 and d['vt'] > 0 and d['gd'] == 0: d['gd'] = d['ws'] / d['vt']
        
        st.session_state.df_grav_excel = pd.DataFrame({"Variable": [diccionario_maestro[k] for k in d], "Valor": [f"{v:.3f}" for v in d.values()]})
        st.success("Cálculos completados.")
        st.table(st.session_state.df_grav_excel)

# --- PESTAÑA 2: PERFIL DE PRESIONES CON GRÁFICO ---
with tabs[1]:
    st.header("Análisis de Esfuerzos Geostáticos")
    col_in, col_gr = st.columns([1, 2])
    
    with col_in:
        n_est = st.number_input("Estratos", 1, 10, 2)
        nf = st.number_input("Nivel Freático (m)", 0.0, 100.0, 2.0)
        estratos = []
        for i in range(int(n_est)):
            st.subheader(f"Estrato {i+1}")
            h = st.number_input(f"Espesor H (m)", 0.1, 50.0, 3.0, key=f"h_{i}")
            g = st.number_input(f"Peso Unitario γ (kN/m³)", 10.0, 25.0, 18.0, key=f"g_{i}")
            estratos.append({'h': h, 'g': g})

    z_plot, stot, u_plot, sef = [0], [0], [0], [0]
    z_curr, s_curr = 0, 0
    for e in estratos:
        # Punto intermedio (opcional para suavidad) y punto final del estrato
        z_curr += e['h']
        s_curr += e['g'] * e['h']
        u_curr = (z_curr - nf) * 9.81 if z_curr > nf else 0
        z_plot.append(z_curr); stot.append(s_curr); u_plot.append(u_curr); sef.append(s_curr - u_curr)

    with col_gr:
        fig_p = go.Figure()
        fig_p.add_trace(go.Scatter(x=stot, y=z_plot, name='σ Total', line=dict(color='blue', width=3)))
        fig_p.add_trace(go.Scatter(x=u_plot, y=z_plot, name='u (Poros)', line=dict(color='cyan', dash='dash')))
        fig_p.add_trace(go.Scatter(x=sef, y=z_plot, name='σ Efectivo', line=dict(color='red', width=3)))
        fig_p.update_yaxes(autorange="reversed", title="Profundidad (m)")
        fig_p.update_xaxes(title="Presión (kN/m²)", side="top")
        fig_p.update_layout(title="Perfil de Esfuerzos", hovermode="y unified")
        st.plotly_chart(fig_p, use_container_width=True)
        
    st.session_state.df_pres_excel = pd.DataFrame({"Z (m)": z_plot, "σ Total": stot, "u": u_plot, "σ Efectivo": sef})

# --- PESTAÑA 3: CARTA DE PLASTICIDAD ---
with tabs[2]:
    st.header("Clasificación de Finos (Carta de Plasticidad)")
    c1, c2 = st.columns([1, 2])
    with c1:
        ll = st.number_input("Límite Líquido (LL)", 0, 120, 45)
        lp = st.number_input("Límite Plástico (LP)", 0, 100, 20)
        ip = ll - lp
        st.metric("Índice de Plasticidad (IP)", ip)
        
        # Lógica de clasificación simplificada
        if ll < 50:
            tipo = "Baja Plasticidad (L)"
            if ip > 7 and ip > 0.73*(ll-20): clas = "CL"
            elif ip < 4 or ip < 0.73*(ll-20): clas = "ML"
            else: clas = "CL-ML"
        else:
            tipo = "Alta Plasticidad (H)"
            clas = "CH" if ip > 0.73*(ll-20) else "MH"
        st.subheader(f"Resultado: {clas}")
        st.session_state.df_lim_excel = pd.DataFrame({"Parámetro": ["LL", "LP", "IP", "SUCS"], "Valor": [ll, lp, ip, clas]})

    with c2:
        x_line = np.linspace(0, 100, 100)
        linea_a = 0.73 * (x_line - 20)
        linea_u = 0.9 * (x_line - 8)
        
        fig_c = go.Figure()
        fig_c.add_trace(go.Scatter(x=x_line, y=linea_a, name='Línea A', line=dict(color='black')))
        fig_c.add_trace(go.Scatter(x=x_line, y=linea_u, name='Línea U', line=dict(color='grey', dash='dot')))
        fig_c.add_trace(go.Scatter(x=[ll], y=[ip], name='Suelo Muestreado', marker=dict(color='red', size=12)))
        fig_c.add_vline(x=50, line_dash="dash", line_color="green")
        fig_c.update_xaxes(range=[0, 100], title="Límite Líquido (LL)")
        fig_c.update_yaxes(range=[0, 60], title="Índice de Plasticidad (IP)")
        fig_c.update_layout(title="Ubicación en Carta de Plasticidad")
        st.plotly_chart(fig_c, use_container_width=True)

# --- PESTAÑA 4: EXPORTACIÓN ---
with tabs[3]:
    st.header("Centro de Descargas")
    if st.button("📦 Preparar Archivo Excel"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            if 'df_grav_excel' in st.session_state:
                st.session_state.df_grav_excel.to_excel(writer, sheet_name='Gravimetria', index=False)
            if 'df_pres_excel' in st.session_state:
                st.session_state.df_pres_excel.to_excel(writer, sheet_name='Esfuerzos', index=False)
            if 'df_lim_excel' in st.session_state:
                st.session_state.df_lim_excel.to_excel(writer, sheet_name='Plasticidad', index=False)
        
        st.download_button(
            label="💾 Descargar Reporte Completo",
            data=output.getvalue(),
            file_name="Proyecto_Geotecnico_Final.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
