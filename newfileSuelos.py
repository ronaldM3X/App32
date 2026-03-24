import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import io

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Geotecnia Suite Master v23.4", layout="wide", page_icon="🏗️")

# Estilo CSS para mejorar la estética
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 10px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR / CONTROL ---
st.sidebar.title("👨‍🏫 Panel de Control")
modo = st.sidebar.radio("Selecciona el Modo:", ("Metas (Laboratorio)", "Académico (Base Vs=1)"))
st.sidebar.markdown("---")
st.sidebar.info("Este software permite simular cambios en las fases del suelo manteniendo la consistencia física.")

st.title(f"🏗️ Geotecnia Master - Modo {modo.split()[0]}")

# --- PESTAÑAS PRINCIPALES ---
tabs = st.tabs(["🧩 Gravimetría & Fases", "🗂️ Perfil de Presiones", "📈 Plasticidad & SUCS", "📥 Reporte Final"])

# --- PESTAÑA 1: GRAVIMETRÍA Y DIAGRAMA DE FASES ---
with tabs[0]:
    diccionario_maestro = {
        "gs": "Gs (Gravedad específica)",
        "e": "e (Relación de vacíos)",
        "n": "n (Porosidad %)",
        "w": "w (Contenido de humedad %)",
        "s": "S (Grado de saturación %)",
        "wm": "Wt (Peso total)",
        "ws": "Ws (Peso sólidos)",
        "ww": "Ww (Peso agua)",
        "vt": "Vt (Volumen total)",
        "vs": "Vs (Volumen sólidos)",
        "vv": "Vv (Volumen vacíos)",
        "vw": "Vw (Volumen agua)",
        "va": "Va (Volumen aire)",
        "gh": "γ (Unitario húmedo)",
        "gd": "γd (Unitario seco)"
    }

    st.subheader("📥 1. Entrada de Datos Iniciales")
    col_sel, col_empty = st.columns([2, 1])
    with col_sel:
        seleccionados = st.multiselect(
            "Selecciona las variables que conoces de tu muestra:",
            options=list(diccionario_maestro.keys()),
            format_func=lambda x: diccionario_maestro[x]
        )

    inputs = {}
    if seleccionados:
        cols = st.columns(3)
        for i, clave in enumerate(seleccionados):
            inputs[clave] = cols[i % 3].number_input(
                f"{diccionario_maestro[clave]}", 
                value=0.0, 
                format="%.4f",
                key=f"input_{clave}"
            )

    if st.button("🚀 Calcular Base Geotécnica"):
        d = {k: 0.0 for k in diccionario_maestro.keys()}
        
        if modo == "Académico (Base Vs=1)":
            d['vs'] = 1.0
        
        for k, v in inputs.items():
            if k in ['w', 'n', 's'] and v > 1.5:
                d[k] = v / 100
            else:
                d[k] = v

        # --- MOTOR DE RETROALIMENTACIÓN RECURSIVO ---
        for _ in range(50):
            if d['gs'] > 0 and d['ws'] > 0 and d['vs'] == 0: d['vs'] = d['ws'] / d['gs']
            if d['gs'] > 0 and d['vs'] > 0 and d['ws'] == 0: d['ws'] = d['gs'] * d['vs']
            if d['ws'] > 0 and d['vs'] > 0 and d['gs'] == 0: d['gs'] = d['ws'] / d['vs']
            
            if d['ws'] > 0 and d['w'] > 0 and d['ww'] == 0: d['ww'] = d['ws'] * d['w']
            if d['ws'] > 0 and d['ww'] > 0 and d['w'] == 0: d['w'] = d['ww'] / d['ws']
            if d['ww'] > 0: d['vw'] = d['ww']
            if d['vw'] > 0: d['ww'] = d['vw']
            
            if d['vt'] > 0 and d['vs'] > 0 and d['vv'] == 0: d['vv'] = d['vt'] - d['vs']
            if d['vt'] > 0 and d['vv'] > 0 and d['vs'] == 0: d['vs'] = d['vt'] - d['vv']
            if d['vs'] > 0 and d['vv'] > 0 and d['vt'] == 0: d['vt'] = d['vs'] + d['vv']
            
            if d['vv'] > 0 and d['vs'] > 0 and d['e'] == 0: d['e'] = d['vv'] / d['vs']
            if d['e'] > 0 and d['vs'] > 0 and d['vv'] == 0: d['vv'] = d['e'] * d['vs']
            if d['vt'] > 0 and d['vv'] > 0 and d['n'] == 0: d['n'] = d['vv'] / d['vt']
            if d['e'] > 0 and d['n'] == 0: d['n'] = d['e'] / (1 + d['e'])
            if d['n'] > 0 and d['e'] == 0: d['e'] = d['n'] / (1 - d['n'])
            
            if d['vw'] > 0 and d['vv'] > 0 and d['s'] == 0: d['s'] = d['vw'] / d['vv']
            if d['s'] > 0 and d['vv'] > 0 and d['vw'] == 0: d['vw'] = d['s'] * d['vv']
            
            if d['wm'] > 0 and d['ws'] > 0 and d['ww'] == 0: d['ww'] = d['wm'] - d['ws']
            if d['wm'] > 0 and d['ww'] > 0 and d['ws'] == 0: d['ws'] = d['wm'] - d['ww']
            if d['ws'] > 0 and d['ww'] > 0 and d['wm'] == 0: d['wm'] = d['ws'] + d['ww']
            if d['vv'] > 0 and d['vw'] > 0 and d['va'] == 0: d['va'] = max(0.0, d['vv'] - d['vw'])
            
            if d['wm'] > 0 and d['vt'] > 0 and d['gh'] == 0: d['gh'] = d['wm'] / d['vt']
            if d['ws'] > 0 and d['vt'] > 0 and d['gd'] == 0: d['gd'] = d['ws'] / d['vt']

        st.session_state.base_calc = d.copy()
        st.session_state.slider_key = np.random.randint(1, 9999)
        st.rerun()

    if 'base_calc' in st.session_state:
        st.markdown("---")
        col_sim, col_res = st.columns([1.2, 1.8])
        bc = st.session_state.base_calc
        sk = st.session_state.slider_key

        with col_sim:
            st.subheader("🕹️ 2. Simulador de Estados")
            e_val = st.slider("Relación de vacíos (e)", 0.1, 5.0, float(bc['e']) if bc['e'] > 0 else 0.70, key=f"s_e_{sk}")
            w_val = st.slider("Contenido de humedad (w %)", 0.0, 100.0, float(bc['w']*100), key=f"s_w_{sk}") / 100
            s_val = st.slider("Grado de saturación (S %)", 0.0, 100.0, float(bc['s']*100), key=f"s_s_{sk}") / 100
            
            ws_inicial = bc['ws']
            if ws_inicial == 0 and modo == "Metas (Laboratorio)":
                ws_inicial = bc['wm'] / (1 + bc['w']) if bc['wm'] > 0 else 160.0
            elif ws_inicial == 0:
                ws_inicial = 160.0
                
            ws_val = st.slider("Peso de los sólidos (Ws)", 10.0, 5000.0, float(ws_inicial), key=f"s_ws_{sk}")

            f = {k: 0.0 for k in diccionario_maestro.keys()}
            f['gs'] = bc['gs'] if bc['gs'] > 0 else 2.65
            f['e'], f['ws'] = e_val, ws_val
            
            if modo == "Académico (Base Vs=1)":
                f['vs'] = 1.0
                f['ws'] = f['gs'] * f['vs']
            else:
                f['vs'] = f['ws'] / f['gs']
            
            f['vv'] = f['e'] * f['vs']
            f['vt'] = f['vs'] + f['vv']
            
            if s_val > 0:
                f['s'] = s_val
                f['vw'] = f['s'] * f['vv']
                f['ww'] = f['vw']
                f['w'] = f['ww'] / f['ws']
            else:
                f['w'] = w_val
                f['ww'] = f['ws'] * f['w']
                f['vw'] = f['ww']
                f['s'] = f['vw'] / f['vv'] if f['vv'] > 0 else 0

            f['va'] = max(0.0, f['vv'] - f['vw'])
            f['wm'] = f['ws'] + f['ww']
            f['n'] = f['vv'] / f['vt']
            f['gh'] = f['wm'] / f['vt']
            f['gd'] = f['ws'] / f['vt']

            if st.button("🔄 Resetear Muestra"):
                del st.session_state.base_calc
                st.rerun()

        with col_res:
            st.subheader("📊 Resultados de las Fases")
            res_data = {
                "Propiedad": [diccionario_maestro[k] for k in diccionario_maestro.keys()],
                "Valor": [
                    f"{f['gs']:.3f}", f"{f['e']:.4f}", f"{f['n']*100:.2f}%", f"{f['w']*100:.2f}%",
                    f"{f['s']*100:.2f}%", f"{f['wm']:.2f} g", f"{f['ws']:.2f} g", f"{f['ww']:.2f} g",
                    f"{f['vt']:.2f} cm³", f"{f['vs']:.2f} cm³", f"{f['vv']:.2f} cm³", f"{f['vw']:.2f} cm³",
                    f"{f['va']:.2f} cm³", f"{f['gh']*9.81:.2f} kN/m³", f"{f['gd']*9.81:.2f} kN/m³"
                ]
            }
            st.table(pd.DataFrame(res_data))
            st.session_state.df_excel = pd.DataFrame(res_data)

            fig = go.Figure(data=[
                go.Bar(name='Sólidos', x=['Fases'], y=[f['vs']], marker_color='#7E5109', width=0.5),
                go.Bar(name='Agua', x=['Fases'], y=[f['vw']], marker_color='#3498DB', width=0.5),
                go.Bar(name='Aire', x=['Fases'], y=[f['va']], marker_color='#BDC3C7', width=0.5)
            ])
            fig.update_layout(barmode='stack', title='Distribución de Volúmenes', height=400, showlegend=True)
            st.plotly_chart(fig, use_container_width=True)

# --- PESTAÑA 2: PERFIL DE PRESIONES ---
with tabs[1]:
    st.header("🗂️ Cálculo de Esfuerzos Geostáticos")
    col_p1, col_p2 = st.columns([1, 2])
    
    with col_p1:
        n_estratos = st.number_input("Número de estratos:", 1, 10, 2)
        nf = st.number_input("Nivel Freático (m):", 0.0, 100.0, 2.0)
        
        estratos_data = []
        for i in range(int(n_estratos)):
            st.markdown(f"**Estrato {i+1}**")
            h = st.number_input(f"Espesor H (m) - {i+1}", 0.1, 50.0, 3.0, key=f"h_{i}")
            gamma = st.number_input(f"Peso Unitario γ (kN/m³) - {i+1}", 1.0, 30.0, 18.0, key=f"g_{i}")
            estratos_data.append({'h': h, 'g': gamma})

    z_acum_frontera = 0
    fronteras = []
    for e in estratos_data:
        z_acum_frontera += e['h']
        fronteras.append(z_acum_frontera)
    
    todos_puntos = sorted(list(set([0, nf] + fronteras)))
    todos_puntos = [p for p in todos_puntos if p <= sum(e['h'] for e in estratos_data)]

    st_list, u_list, se_list = [], [], []

    for z in todos_puntos:
        current_sigma = 0
        z_ref = 0
        for e in estratos_data:
            if z > z_ref:
                espesor = min(e['h'], z - z_ref)
                current_sigma += espesor * e['g']
                z_ref += e['h']
        
        current_u = (z - nf) * 9.81 if z > nf else 0
        st_list.append(current_sigma)
        u_list.append(current_u)
        se_list.append(current_sigma - current_u)

    with col_p2:
        df_presiones = pd.DataFrame({
            "Profundidad (m)": todos_puntos,
            "σ Total (kPa)": st_list,
            "u (kPa)": u_list,
            "σ' Efectivo (kPa)": se_list
        })
        st.dataframe(df_presiones.style.format("{:.2f}"))
        
        fig_p = go.Figure()
        fig_p.add_trace(go.Scatter(x=st_list, y=todos_puntos, name='σ Total', line=dict(color='brown', width=3)))
        fig_p.add_trace(go.Scatter(x=u_list, y=todos_puntos, name='u (Agua)', line=dict(color='blue', dash='dash')))
        fig_p.add_trace(go.Scatter(x=se_list, y=todos_puntos, name="σ' Efectivo", fill='tonextx', line=dict(color='green', width=3)))
        
        fig_p.update_yaxes(autorange="reversed", title="Profundidad (m)")
        fig_p.update_xaxes(title="Presión (kPa)", side="top")
        fig_p.update_layout(height=500, title="Perfil de Esfuerzos Geostáticos")
        st.plotly_chart(fig_p, use_container_width=True)

# --- PESTAÑA 3: PLASTICIDAD Y CLASIFICACIÓN ---
with tabs[2]:
    st.header("📈 Límites de Atterberg y Clasificación SUCS")
    col_c1, col_c2 = st.columns([1, 2])
    
    with col_c1:
        ll = st.number_input("Límite Líquido (LL):", 0, 150, 40)
        lp = st.number_input("Límite Plástico (LP):", 0, 100, 20)
        p200 = st.number_input("% Pasa Tamiz No. 200:", 0.0, 100.0, 60.0)
        
        ip = ll - lp
        st.metric("Índice de Plasticidad (IP)", f"{ip}%")
        
        if p200 >= 50:
            if ll < 50:
                sucs = "CL o ML" if ip > 7 and ip >= 0.73*(ll-20) else "ML o OL"
            else:
                sucs = "CH o MH" if ip >= 0.73*(ll-20) else "MH o OH"
            st.success(f"Suelo Fino: **{sucs}**")
        else:
            st.info("Suelo Grueso (Requiere Granulometría Completa)")

    with col_c2:
        ll_plot = np.linspace(0, 100, 100)
        linea_a = 0.73 * (ll_plot - 20)
        linea_a = np.maximum(0, linea_a)
        
        fig_c = go.Figure()
        fig_c.add_trace(go.Scatter(x=ll_plot, y=linea_a, name='Línea A (IP=0.73(LL-20))', line=dict(color='black')))
        fig_c.add_trace(go.Scatter(x=[ll], y=[ip], name='Tu Muestra', mode='markers', marker=dict(size=15, color='red')))
        
        fig_c.update_layout(title="Carta de Plasticidad de Casagrande", xaxis_title="LL", yaxis_title="IP", height=450)
        fig_c.add_shape(type="line", x0=50, y0=0, x1=50, y1=60, line=dict(color="Gray", dash="dash"))
        st.plotly_chart(fig_c, use_container_width=True)

# --- PESTAÑA 4: REPORTE FINAL ---
with tabs[3]:
    st.header("📥 Generación de Reporte Técnico")
    if 'df_excel' in st.session_state:
        st.write("Vista previa de los datos a exportar:")
        st.dataframe(st.session_state.df_excel)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            st.session_state.df_excel.to_excel(writer, index=False, sheet_name='Resultados_Fases')
            if 'df_presiones' in locals():
                df_presiones.to_excel(writer, index=False, sheet_name='Perfil_Esfuerzos')
        
        st.download_button(
            label="💾 Descargar Reporte en Excel",
            data=output.getvalue(),
            file_name="Reporte_Geotecnico_Suite.xlsx",
            mime="application/vnd.ms-excel"
        )
    else:
        st.warning("Primero realiza cálculos en la pestaña de Gravimetría.")
