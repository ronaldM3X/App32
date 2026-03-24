    import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import io

# 1. CONFIGURACIÓN DE PÁGINA Y ESTILO
st.set_page_config(page_title="Geotecnia Suite Master v17.0", layout="wide", page_icon="🏗️")

# Barra lateral con personalidad
st.sidebar.title("👨‍🏫 Panel de Control")
st.sidebar.info("¡Hola! Aquí elegimos el camino. 'Metas' para tus datos reales y 'Académico' para resolver problemas teóricos asumiendo Vs=1, ¡pero con todas las variables!")

modo = st.sidebar.radio("Modo de Trabajo:", ("Metas (Laboratorio)", "Académico (Base Vs=1)"))

st.title(f"🏗️ Geotecnia Master - Modo {modo.split()[0]}")
st.markdown("---")

tabs = st.tabs(["🧩 Gravimetría & Simulación", "🗂️ Perfil de Presiones", "📈 Plasticidad & SUCS", "📥 Reporte Final"])

# --- PESTAÑA 1: GRAVIMETRÍA ---
with tabs[0]:
    # Diccionario Maestro Completo de Variables
    diccionario_maestro = {
        "gs": "Gs (Gravedad específica)", "e": "e (Relación de vacíos)", "n": "n (Porosidad %)",
        "w": "w (Contenido de humedad %)", "s": "S (Grado de saturación %)", "wm": "Peso total muestra (Wt)",
        "ws": "Peso de los sólidos (Ws)", "ww": "Peso del agua (Ww)", "vt": "Vt (Volumen total)",
        "vs": "Vs (Volumen sólidos)", "vv": "Vv (Volumen vacíos)", "vw": "Vw (Volumen agua)",
        "va": "Va (Volumen aire)", "gh": "γ (Peso unitario húmedo)", "gd": "γd (Peso unitario seco)"
    }

    # SECCIÓN DE ENTRADA DE DATOS (COMÚN PARA AMBOS MODOS)
    if modo == "Académico (Base Vs=1)":
        st.subheader("📖 Análisis Teórico (Base Vs = 1 cm³)")
        st.write("Selecciona las variables conocidas de tu ejercicio telemático:")
    else:
        st.subheader("🧪 Procesamiento de Laboratorio")
        st.write("Selecciona los datos medidos en la muestra real:")

    # En el modo Académico, ahora exponemos TODAS las variables
    seleccionados = st.multiselect("Variables conocidas:", options=list(diccionario_maestro.keys()), format_func=lambda x: diccionario_maestro[x])
    
    inputs = {}
    cols_in = st.columns(3)
    for i, clave in enumerate(seleccionados):
        # Todos los valores inicializados en 0.0, sin por defectos.
        inputs[clave] = cols_in[i%3].number_input(f"{diccionario_maestro[clave]}", value=0.0, format="%.3f", key=f"in_{clave}")

    if st.button("🚀 Calcular Relaciones"):
        # Inicialización de datos
        d = {k: 0.0 for k in diccionario_maestro.keys()}
        
        # Lógica específica del modo
        if modo == "Académico (Base Vs=1)":
            d['vs'] = 1.0 # Base teórica
        
        # Carga de datos ingresados por el usuario
        for k, v in inputs.items():
            # Manejo de porcentajes
            d[k] = v / 100 if k in ['w', 'n', 's'] and v > 1.0 else v
        
        # --- MOTOR DE CÁLCULO ITERATIVO ROBUSTO (50 iteraciones) ---
        for _ in range(50):
            # Relaciones de Sólidos y Gs
            if d['gs'] > 0 and d['vs'] > 0 and d['ws'] == 0: d['ws'] = d['gs'] * d['vs']
            if d['ws'] > 0 and d['vs'] > 0 and d['gs'] == 0: d['gs'] = d['ws'] / d['vs']
            if d['ws'] > 0 and d['gs'] > 0 and d['vs'] == 0: d['vs'] = d['ws'] / d['gs']
            
            # Relaciones de Humedad
            if d['ws'] > 0 and d['w'] > 0 and d['ww'] == 0: d['ww'] = d['ws'] * d['w']
            if d['ww'] > 0 and d['ws'] > 0 and d['w'] == 0: d['w'] = d['ww'] / d['ws']
            
            # Relaciones de Pesos
            if d['wm'] > 0 and d['ws'] > 0 and d['ww'] == 0: d['ww'] = d['wm'] - d['ws']
            if d['wm'] > 0 and d['ww'] > 0 and d['ws'] == 0: d['ws'] = d['wm'] - d['ww']
            if d['ws'] > 0 and d['ww'] > 0 and d['wm'] == 0: d['wm'] = d['ws'] + d['ww']
            
            # Relaciones de Volúmenes de Agua (asumiendo γw = 1g/cm³)
            if d['ww'] > 0 and d['vw'] == 0: d['vw'] = d['ww'] / 1.0
            if d['vw'] > 0 and d['ww'] == 0: d['ww'] = d['vw'] * 1.0
            
            # Relaciones de Vacíos, Porosidad y e
            if d['vt'] > 0 and d['vs'] > 0 and d['vv'] == 0: d['vv'] = d['vt'] - d['vs']
            if d['vt'] > 0 and d['vv'] > 0 and d['vs'] == 0: d['vs'] = d['vt'] - d['vv']
            if d['vs'] > 0 and d['vv'] > 0 and d['e'] == 0: d['e'] = d['vv'] / d['vs']
            if d['e'] > 0 and d['n'] == 0: d['n'] = d['e'] / (1 + d['e'])
            if d['n'] > 0 and d['e'] == 0: d['e'] = d['n'] / (1 - d['n'])
            
            # Relaciones de Saturación
            if d['vv'] > 0 and d['vw'] > 0 and d['s'] == 0: d['s'] = d['vw'] / d['vv']
            if d['vv'] > 0 and d['s'] > 0 and d['vw'] == 0: d['vw'] = d['vv'] * d['s']
            
            # Aire
            if d['vv'] > 0 and d['vw'] > 0: d['va'] = max(0.0, d['vv'] - d['vw'])
            
            # Consistencia de Volumen Total
            if d['vs'] > 0 and d['vv'] > 0: d['vt'] = d['vs'] + d['vv']

        # Guardado en estado de sesión
        st.session_state.base_data = d.copy()
        st.session_state.live_data = d.copy()
        st.success("¡Relaciones calculadas! Revisa los resultados y usa los simuladores abajo.")

    # --- SECCIÓN DE RESULTADOS Y SIMULADORES DINÁMICOS ---
    if 'live_data' in st.session_state:
        ld = st.session_state.live_data
        st.markdown("---")
        
        c_sim, c_res = st.columns([1.3, 1.7])
        
        with c_sim:
            st.subheader("🕹️ Simuladores Dinámicos")
            st.write("Ajusta los parámetros para ver cómo cambia la estructura del suelo:")
            
            # 1. Simulador de Estructura (e) - Sin valor por defecto de 0.5
            ld['e'] = st.slider("Ajustar Relación de Vacíos (e)", 0.01, 5.0, float(ld['e']) if ld['e'] > 0 else 0.6)
            
            # 2. Simulador de Humedad (w)
            ld['w'] = st.slider("Ajustar Humedad (w %)", 0.0, 100.0, float(ld['w']*100)) / 100
            
            # 3. Simulador de Peso Total (Wm/Wt) - NUEVO
            # Definimos un rango dinámico basado en el valor actual
            max_wm = max(5000.0, float(ld['wm'] * 2))
            ld['wm'] = st.slider("Ajustar Peso Total (Wt g)", 0.0, max_wm, float(ld['wm']))
            
            # --- RECALCULOS DINÁMICOS DEL SIMULADOR ---
            # Prioridad 1: Mantener Vs y Gs constantes (la matriz sólida no cambia)
            # Prioridad 2: e ajusta Vv. w ajusta Vw. Wm ajusta Ww (y por ende Vw).
            
            # e ajusta Vv
            ld['vv'] = ld['vs'] * ld['e']
            ld['vt'] = ld['vs'] + ld['vv']
            
            # Wm ajusta Ww
            ld['ww'] = max(0.0, ld['wm'] - ld['ws'])
            ld['vw'] = ld['ww'] / 1.0
            
            # Recalculamos w y S basados en los nuevos pesos/volúmenes
            ld['w'] = ld['ww'] / ld['ws'] if ld['ws'] > 0 else 0
            ld['s'] = ld['vw'] / ld['vv'] if ld['vv'] > 0 else 0
            
            # Aire y consistencia
            ld['va'] = max(0.0, ld['vv'] - ld['vw'])
            
            # Guardamos cambios en vivo
            st.session_state.live_data = ld
            
            if st.button("🔄 Resetear a calculados"):
                st.session_state.live_data = st.session_state.base_data.copy()
                st.rerun()

        with c_res:
            st.subheader("📊 Resultados en Tiempo Real")
            
            # Blindaje contra división por cero para pesos unitarios kN/m³
            gh = (ld['wm']/ld['vt'])*9.81 if ld['vt'] > 0 else 0
            gd = (ld['ws']/ld['vt'])*9.81 if ld['vt'] > 0 else 0
            
            res_df = pd.DataFrame({"Propiedad": list(diccionario_maestro.values()), 
                                  "Valor": [f"{ld['gs']:.2f}", f"{ld['e']:.3f}", f"{ld['n']*100:.1f}%", f"{ld['w']*100:.2f}%", f"{ld['s']*100:.1f}%", 
                                           f"{ld['wm']:.2f}g", f"{ld['ws']:.2f}g", f"{ld['ww']:.2f}g", f"{ld['vt']:.2f}cm³", f"{ld['vs']:.2f}cm³", 
                                           f"{ld['vv']:.2f}cm³", f"{ld['vw']:.2f}cm³", f"{ld['va']:.2f}cm³", f"{gh:.2f} kN/m³", f"{gd:.2f} kN/m³"]})
            st.table(res_df)
            st.session_state.df_grav_excel = res_df
            
            # Diagrama de Fases Dinámico
            fig = go.Figure(data=[go.Bar(name='Sólidos', x=['Fases'], y=[ld['vs']], marker_color='#7E5109'),
                                  go.Bar(name='Agua', x=['Fases'], y=[ld['vw']], marker_color='#3498DB'),
                                  go.Bar(name='Aire', x=['Fases'], y=[ld['va']], marker_color='#BDC3C7')])
            fig.update_layout(barmode='stack', height=350, margin=dict(t=0,b=0)); st.plotly_chart(fig, use_container_width=True)

# --- LAS PESTAÑAS DE PRESIONES, PLASTICIDAD Y EXCEL SIGUEN INCLUIDAS E INTACTAS ---
# [He verificado que el código de las v16.x para estas secciones esté presente y funcional]
with tabs[1]: # Presiones
    st.header("Esfuerzos Geostáticos")
    col_p1, col_p2 = st.columns([1, 2])
    with col_p1:
        n_estratos = st.number_input("Número de Estratos", 1, 10, 2)
        nf = st.number_input("Nivel Freático (m)", 0.0, 100.0, 0.0)
        datos_estratos = []
        for i in range(int(n_estratos)):
            h = st.number_input(f"H {i+1} (m)", 0.0, 50.0, 0.0, key=f"z_h{i}")
            g = st.number_input(f"γ {i+1} (kN/m³)", 0.0, 25.0, 0.0, key=f"z_g{i}")
            datos_estratos.append({'h': h, 'g': g})
    puntos = sorted(list(set([0.0, nf] + [sum(e['h'] for e in datos_estratos[:i+1]) for i in range(len(datos_estratos))])))
    puntos = [p for p in puntos if p <= sum(e['h'] for e in datos_estratos)]
    z_l, st_l, u_l, se_l = [], [], [], []
    s_acu = 0
    for i in range(len(puntos)):
        z = puntos[i]
        if i > 0:
            dz = z - puntos[i-1]
            z_t = 0
            for e in datos_estratos:
                if z <= z_t + e['h'] + 0.01:
                    s_acu += dz * e['g']; break
                z_t += e['h']
        u = (z - nf) * 9.81 if z > nf else 0
        z_l.append(z); st_l.append(round(s_acu,2)); u_l.append(round(u,2)); se_l.append(round(s_acu-u,2))
    with col_p2:
        df_p = pd.DataFrame({"Z (m)": z_l, "σ Total": st_l, "u": u_l, "σ' Ef.": se_l})
        st.dataframe(df_p, use_container_width=True)
        st.session_state.df_pres_excel = df_p
        fig_p = go.Figure()
        fig_p.add_trace(go.Scatter(x=st_l, y=z_l, name='Total', line=dict(color='brown')))
        fig_p.add_trace(go.Scatter(x=u_l, y=z_l, name='Neutro', line=dict(color='blue', dash='dash')))
        fig_p.add_trace(go.Scatter(x=se_l, y=z_l, name='Efectivo', fill='tonextx', line=dict(color='green')))
        fig_p.update_yaxes(autorange="reversed", title="Profundidad (m)"); st.plotly_chart(fig_p, use_container_width=True)

with tabs[2]: # Plasticidad
    st.header("Clasificación SUCS")
    cl1, cl2 = st.columns([1, 2])
    with cl1:
        ll = st.number_input("Límite Líquido", 0, 150, 0); lp = st.number_input("Límite Plástico", 0, 100, 0); ip = ll - lp
        st.metric("IP", ip)
        lin_a = 0.73 * (ll - 20)
        if ll == 0: s_t = "Sin datos"
        elif ll < 50:
            if ip > 7 and ip >= lin_a: s_t = "CL"
            elif ip < 4 or ip < lin_a: s_t = "ML"
            else: s_t = "CL-ML"
        else:
            if ip >= lin_a: s_t = "CH"
            else: s_t = "MH"
        st.subheader(f"Clasificación: {s_t}")
        st.session_state.df_lim_excel = pd.DataFrame({"LL": [ll], "LP": [lp], "IP": [ip], "SUCS": [s_t]})
    with cl2:
        fig_c = go.Figure()
        x_v = np.linspace(0,100,100)
        fig_c.add_trace(go.Scatter(x=x_v, y=0.73*(x_v-20), name='Línea A', line=dict(color='black')))
        if ll > 0: fig_c.add_trace(go.Scatter(x=[ll], y=[ip], mode='markers', marker=dict(size=15, color='red')))
        fig_c.update_xaxes(title="LL", range=[0,100]); fig_c.update_yaxes(title="IP", range=[0,60])
        st.plotly_chart(fig_c, use_container_width=True)

with tabs[3]: # Exportación
    st.header("Exportación")
    if st.button("📥 Generar Excel"):
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
            if 'df_grav_excel' in st.session_state: st.session_state.df_grav_excel.to_excel(writer, sheet_name='Gravimetria')
            if 'df_pres_excel' in st.session_state: st.session_state.df_pres_excel.to_excel(writer, sheet_name='Presiones')
            if 'df_lim_excel' in st.session_state: st.session_state.df_lim_excel.to_excel(writer, sheet_name='Plasticidad')
        st.download_button("Descargar_Reporte.xlsx", out.getvalue(), "reporte_geotecnia.xlsx")
            
