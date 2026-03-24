import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import io

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Geotecnia Suite Master v15.0", layout="wide", page_icon="🏗️")

# Barra lateral con personalidad
st.sidebar.title("👨‍🏫 Panel de Control")
st.sidebar.info("¡Hola! Aquí elegimos el camino. 'Metas' para tus datos de laboratorio y 'Académico' para resolver problemas teóricos asumiendo Vs=1.")

modo = st.sidebar.radio("Modo de Trabajo:", ("Metas (Laboratorio)", "Académico (Base Vs=1)"))

st.title(f"🏗️ Geotecnia Master - Modo {modo.split()[0]}")
st.markdown("---")

tabs = st.tabs(["🧩 Gravimetría & Simulación", "🗂️ Perfil de Presiones", "📈 Plasticidad & SUCS", "📥 Reporte Final"])

# --- PESTAÑA 1: GRAVIMETRÍA ---
with tabs[0]:
    diccionario_maestro = {
        "gs": "Gs (Gravedad específica)", "e": "e (Relación de vacíos)", "n": "n (Porosidad %)",
        "w": "w (Contenido de humedad %)", "s": "S (Grado de saturación %)", "wm": "Peso total muestra (Wt)",
        "ws": "Peso de los sólidos (Ws)", "ww": "Peso del agua (Ww)", "vt": "Vt (Volumen total)",
        "vs": "Vs (Volumen sólidos)", "vv": "Vv (Volumen vacíos)", "vw": "Vw (Volumen agua)",
        "va": "Va (Volumen aire)", "gh": "γ (Peso unitario húmedo)", "gd": "γd (Peso unitario seco)"
    }

    if modo == "Académico (Base Vs=1)":
        st.subheader("📖 Análisis Teórico (Base Vs = 1 cm³)")
        st.write("Ingresa los parámetros conocidos para deducir las relaciones de fase:")
        col_ac1, col_ac2 = st.columns(2)
        with col_ac1:
            # Valores inicializados en 0.0 para que tú los escojas
            gs_ac = st.number_input("Gs (Gravedad específica)", value=0.0, format="%.3f")
            e_ac = st.number_input("e (Relación de vacíos)", value=0.0, format="%.3f")
        with col_ac2:
            w_ac = st.number_input("w (Humedad %)", value=0.0) / 100
            s_ac = st.number_input("S (Saturación %)", value=0.0) / 100
        
        if st.button("🚀 Calcular Relaciones Teóricas"):
            if gs_ac == 0:
                st.error("¡Oye! Necesito al menos la Gs para empezar a trabajar. No puedo adivinarla todavía.")
            else:
                d = {k: 0.0 for k in diccionario_maestro.keys()}
                d['vs'] = 1.0
                d['gs'] = gs_ac
                d['ws'] = gs_ac * 1.0  # γw = 1g/cm³
                d['e'] = e_ac
                d['vv'] = e_ac * d['vs']
                d['vt'] = d['vs'] + d['vv']
                d['n'] = d['e'] / (1 + d['e']) if (1 + d['e']) > 0 else 0
                
                # Lógica de prioridad: Si das humedad, calculo saturación; si no, viceversa.
                if w_ac > 0:
                    d['w'] = w_ac
                    d['ww'] = d['ws'] * w_ac
                    d['vw'] = d['ww'] / 1.0
                    d['s'] = d['vw'] / d['vv'] if d['vv'] > 0 else 0
                else:
                    d['s'] = s_ac
                    d['vw'] = d['vv'] * s_ac
                    d['ww'] = d['vw'] * 1.0
                    d['w'] = d['ww'] / d['ws'] if d['ws'] > 0 else 0
                
                d['va'] = max(0.0, d['vv'] - d['vw'])
                d['wm'] = d['ws'] + d['ww']
                st.session_state.base_data = d.copy()
                st.session_state.live_data = d.copy()

    else: # MODO METAS
        st.subheader("🧪 Procesamiento de Datos Reales")
        seleccionados = st.multiselect("Datos medidos en laboratorio:", options=list(diccionario_maestro.keys()), format_func=lambda x: diccionario_maestro[x])
        inputs = {}
        cols_in = st.columns(3)
        for i, clave in enumerate(seleccionados):
            inputs[clave] = cols_in[i%3].number_input(f"Valor de {clave}", value=0.0, format="%.3f")

        if st.button("🚀 Calcular Propiedades"):
            d = {k: inputs.get(k, 0.0) for k in diccionario_maestro.keys()}
            for pct in ['w', 'n', 's']:
                if d[pct] > 1.0: d[pct] /= 100
            for _ in range(30):
                if d['ws'] > 0 and d['gs'] > 0: d['vs'] = d['ws'] / d['gs']
                if d['wm'] > 0 and d['ws'] > 0: d['ww'] = d['wm'] - d['ws']
                if d['ws'] > 0 and d['w'] > 0: d['ww'] = d['ws'] * d['w']
                if d['vt'] > 0 and d['vs'] > 0: d['vv'] = d['vt'] - d['vs']
                if d['vv'] > 0 and d['vs'] > 0: d['e'] = d['vv'] / d['vs']
                if d['e'] > 0: d['n'] = d['e'] / (1 + d['e'])
                if d['gs'] > 0 and d['w'] > 0 and d['e'] > 0: d['s'] = (d['w'] * d['gs']) / d['e']
                if d['ww'] > 0: d['vw'] = d['ww'] / 1.0
                if d['vv'] > 0 and d['vw'] > 0: d['va'] = d['vv'] - d['vw']
                if d['ws'] > 0 and d['ww'] > 0: d['wm'] = d['ws'] + d['ww']
            st.session_state.base_data = d.copy()
            st.session_state.live_data = d.copy()

    # --- SIMULADOR COMÚN ---
    if 'live_data' in st.session_state:
        ld = st.session_state.live_data
        st.markdown("---")
        if st.button("🔄 Limpiar y Resetear"):
            st.session_state.live_data = st.session_state.base_data.copy()
            st.rerun()

        c_sim, c_res = st.columns([1.2, 1.8])
        with c_sim:
            st.subheader("🕹️ Ajustes")
            ld['e'] = st.slider("Relación vacíos (e)", 0.01, 5.0, float(ld['e']) if ld['e'] > 0 else 0.5)
            ld['w'] = st.slider("Humedad (%)", 0.0, 100.0, float(ld['w']*100)) / 100
            ld['vv'] = ld['vs'] * ld['e']
            ld['ww'] = ld['ws'] * ld['w']
            ld['vw'] = ld['ww'] / 1.0
            ld['s'] = (ld['vw'] / ld['vv']) if ld['vv'] > 0 else 0
            ld['va'] = max(0.0, ld['vv'] - ld['vw'])
            ld['vt'] = ld['vs'] + ld['vv']
            ld['wm'] = ld['ws'] + ld['ww']
            st.session_state.live_data = ld

        with c_res:
            gh = (ld['wm']/ld['vt'])*9.81 if ld['vt'] > 0 else 0
            gd = (ld['ws']/ld['vt'])*9.81 if ld['vt'] > 0 else 0
            res_df = pd.DataFrame({"Propiedad": list(diccionario_maestro.values()), 
                                  "Valor": [f"{ld['gs']:.2f}", f"{ld['e']:.3f}", f"{ld['n']*100:.1f}%", f"{ld['w']*100:.2f}%", f"{ld['s']*100:.1f}%", 
                                           f"{ld['wm']:.2f}g", f"{ld['ws']:.2f}g", f"{ld['ww']:.2f}g", f"{ld['vt']:.2f}cm³", f"{ld['vs']:.2f}cm³", 
                                           f"{ld['vv']:.2f}cm³", f"{ld['vw']:.2f}cm³", f"{ld['va']:.2f}cm³", f"{gh:.2f} kN/m³", f"{gd:.2f} kN/m³"]})
            st.table(res_df)
            st.session_state.df_grav_excel = res_df
            
            fig = go.Figure(data=[go.Bar(name='Sólidos', x=['Fases'], y=[ld['vs']], marker_color='#7E5109'),
                                  go.Bar(name='Agua', x=['Fases'], y=[ld['vw']], marker_color='#3498DB'),
                                  go.Bar(name='Aire', x=['Fases'], y=[ld['va']], marker_color='#BDC3C7')])
            fig.update_layout(barmode='stack', height=350, margin=dict(t=0,b=0)); st.plotly_chart(fig, use_container_width=True)

# --- PESTAÑA 2: PERFIL DE PRESIONES ---
with tabs[1]:
    st.header("Esfuerzos Geostáticos")
    col_p1, col_p2 = st.columns([1, 2])
    with col_p1:
        n_estratos = st.number_input("Estratos", 1, 10, 2)
        nf = st.number_input("Nivel Freático (m)", 0.0, 100.0, 0.0)
        datos_estratos = []
        for i in range(int(n_estratos)):
            h = st.number_input(f"H {i+1} (m)", 0.0, 50.0, 0.0, key=f"z_h{i}")
            g = st.number_input(f"γ {i+1} (kN/m³)", 0.0, 25.0, 0.0, key=f"z_g{i}")
            datos_estratos.append({'h': h, 'g': g})

    puntos = sorted(list(set([0.0, nf] + [sum(e['h'] for e in datos_estratos[:i+1]) for i in range(len(datos_estratos))])))
    puntos = [p for p in puntos if p <= sum(e['h'] for e in datos_estratos)]
    z_list, st_list, u_list, se_list = [], [], [], []
    sigma_acu = 0
    for i in range(len(puntos)):
        z = puntos[i]
        if i > 0:
            dz = z - puntos[i-1]
            z_temp = 0
            for e in datos_estratos:
                if z <= z_temp + e['h'] + 0.01:
                    sigma_acu += dz * e['g']; break
                z_temp += e['h']
        u = (z - nf) * 9.81 if z > nf else 0
        z_list.append(z); st_list.append(round(sigma_acu,2)); u_list.append(round(u,2)); se_list.append(round(sigma_acu-u,2))

    with col_p2:
        df_pres = pd.DataFrame({"Z (m)": z_list, "σ Total": st_list, "u": u_list, "σ' Efectivo": se_list})
        st.dataframe(df_pres, use_container_width=True)
        st.session_state.df_pres_excel = df_pres
        fig_p = go.Figure()
        fig_p.add_trace(go.Scatter(x=st_list, y=z_list, name='σ Total', line=dict(color='brown')))
        fig_p.add_trace(go.Scatter(x=u_list, y=z_list, name='u', line=dict(color='blue', dash='dash')))
        fig_p.add_trace(go.Scatter(x=se_list, y=z_list, name="σ' Ef.", fill='tonextx', line=dict(color='green')))
        fig_p.update_yaxes(autorange="reversed", title="Z (m)"); st.plotly_chart(fig_p, use_container_width=True)

# --- PESTAÑA 3: PLASTICIDAD & SUCS ---
with tabs[2]:
    st.header("Clasificación SUCS")
    cl1, cl2 = st.columns([1, 2])
    with cl1:
        ll = st.number_input("LL", 0, 150, 0); lp = st.number_input("LP", 0, 100, 0); ip = ll - lp
        st.metric("IP", ip)
        linea_a = 0.73 * (ll - 20)
        if ll == 0: s_tipo = "Pendiente de datos"
        elif ll < 50:
            if ip > 7 and ip >= linea_a: s_tipo = "CL"
            elif ip < 4 or ip < linea_a: s_tipo = "ML"
            else: s_tipo = "CL-ML"
        else:
            if ip >= linea_a: s_tipo = "CH"
            else: s_tipo = "MH"
        st.subheader(f"Tipo: {s_tipo}")
        st.session_state.df_lim_excel = pd.DataFrame({"LL": [ll], "LP": [lp], "IP": [ip], "SUCS": [s_tipo]})
    with cl2:
        fig_c = go.Figure()
        x_val = np.linspace(0,100,100)
        fig_c.add_trace(go.Scatter(x=x_val, y=0.73*(x_val-20), name='Línea A', line=dict(color='black')))
        if ll > 0:
            fig_c.add_trace(go.Scatter(x=[ll], y=[ip], mode='markers', marker=dict(size=15, color='red')))
        fig_c.update_xaxes(title="Límite Líquido", range=[0,100]); fig_c.update_yaxes(title="IP", range=[0,60])
        st.plotly_chart(fig_c, use_container_width=True)

# --- PESTAÑA 4: EXPORTACIÓN ---
with tabs[3]:
    st.header("Reporte Final")
    if st.button("📥 Generar Archivo Excel"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            if 'df_grav_excel' in st.session_state: st.session_state.df_grav_excel.to_excel(writer, sheet_name='Gravimetria')
            if 'df_pres_excel' in st.session_state: st.session_state.df_pres_excel.to_excel(writer, sheet_name='Presiones')
            if 'df_lim_excel' in st.session_state: st.session_state.df_lim_excel.to_excel(writer, sheet_name='Plasticidad')
        st.download_button("Descargar_Geotecnia.xlsx", output.getvalue(), "reporte_final.xlsx")
        
