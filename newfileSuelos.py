import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import io

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Geotecnia Suite Master v21.5", layout="wide", page_icon="🏗️")

# Barra lateral con personalidad
st.sidebar.title("👨‍🏫 Panel de Control")
st.sidebar.markdown("---")
modo = st.sidebar.radio("Selecciona el Modo:", ("Metas (Laboratorio)", "Académico (Base Vs=1)"))
st.sidebar.info(f"Modo actual: **{modo}**. Recuerda que en Académico, Ww siempre será igual a Vw.")

st.title(f"🏗️ Geotecnia Master - Modo {modo.split()[0]}")
st.markdown("---")

tabs = st.tabs(["🧩 Gravimetría & Simulación", "🗂️ Perfil de Presiones", "📈 Plasticidad & SUCS", "📥 Reporte Final"])

# --- PESTAÑA 1: GRAVIMETRÍA & SIMULACIÓN ---
with tabs[0]:
    diccionario_maestro = {
        "gs": "Gs (Gravedad específica)", "e": "e (Relación de vacíos)", "n": "n (Porosidad %)",
        "w": "w (Contenido de humedad %)", "s": "S (Grado de saturación %)", "wm": "Peso total muestra (Wt)",
        "ws": "Peso de los sólidos (Ws)", "ww": "Peso del agua (Ww)", "vt": "Vt (Volumen total)",
        "vs": "Vs (Volumen sólidos)", "vv": "Vv (Volumen vacíos)", "vw": "Vw (Volumen agua)",
        "va": "Va (Volumen aire)", "gh": "γ (Peso unitario húmedo)", "gd": "γd (Peso unitario seco)"
    }

    st.subheader("📥 Entrada de Datos")
    seleccionados = st.multiselect("Selecciona las variables conocidas:", options=list(diccionario_maestro.keys()), format_func=lambda x: diccionario_maestro[x])
    
    inputs = {}
    cols_in = st.columns(3)
    for i, clave in enumerate(seleccionados):
        inputs[clave] = cols_in[i%3].number_input(f"{diccionario_maestro[clave]}", value=0.0, format="%.4f", key=f"main_in_{clave}")

    if st.button("🚀 Calcular Relaciones"):
        d = {k: 0.0 for k in diccionario_maestro.keys()}
        if modo == "Académico (Base Vs=1)": 
            d['vs'] = 1.0
        
        for k, v in inputs.items():
            # Convertir porcentajes si el usuario mete valores > 1
            d[k] = v / 100 if k in ['w', 'n', 's'] and v > 1.0 else v
        
        # MOTOR DE CÁLCULO ITERATIVO (Relaciones Fundamentales)
        for _ in range(100):
            # Identidad Crítica: Densidad del agua = 1.0
            if d['ww'] > 0: d['vw'] = d['ww']
            if d['vw'] > 0: d['ww'] = d['vw']
            
            if d['gs'] > 0 and d['vs'] > 0: d['ws'] = d['gs'] * d['vs']
            if d['ws'] > 0 and d['vs'] > 0: d['gs'] = d['ws'] / d['vs']
            if d['ws'] > 0 and d['w'] > 0: d['ww'] = d['ws'] * d['w']; d['vw'] = d['ww']
            if d['ww'] > 0 and d['ws'] > 0: d['w'] = d['ww'] / d['ws']
            if d['vt'] > 0 and d['vs'] > 0: d['vv'] = d['vt'] - d['vs']
            if d['vs'] > 0 and d['vv'] > 0: d['e'] = d['vv'] / d['vs']
            if d['e'] > 0: d['n'] = d['e'] / (1 + d['e'])
            if d['n'] > 0: d['e'] = d['n'] / (1 - d['n'])
            if d['vv'] > 0 and d['vw'] > 0: d['s'] = d['vw'] / d['vv']
            if d['vv'] > 0 and d['s'] > 0: d['vw'] = d['vv'] * d['s']; d['ww'] = d['vw']
            if d['ws'] > 0 and d['ww'] > 0: d['wm'] = d['ws'] + d['ww']
            if d['vt'] == 0 and d['vs'] > 0 and d['vv'] > 0: d['vt'] = d['vs'] + d['vv']
            if d['vv'] > 0 and d['vw'] > 0: d['va'] = max(0.0, d['vv'] - d['vw'])

        st.session_state.base_data = d.copy()
        st.session_state.live_data = d.copy()
        st.session_state.slider_key = np.random.randint(1, 1000)
        st.rerun()

    if 'live_data' in st.session_state:
        ld = st.session_state.live_data
        st.markdown("---")
        c_sim, c_res = st.columns([1.3, 1.7])
        
        with c_sim:
            st.subheader("🕹️ Simulador Dinámico")
            k = st.session_state.get('slider_key', 0)
            
            # Ajustes Dinámicos
            ld['e'] = st.slider("Ajustar Relación de Vacíos (e)", 0.01, 5.0, float(ld['e']) if ld['e'] > 0 else 0.5, key=f"e_{k}")
            ld['w'] = st.slider("Ajustar Humedad (w %)", 0.0, 100.0, float(ld['w']*100), key=f"w_{k}") / 100
            
            # Simulador de Peso de Sólidos (Ws)
            val_ws_ini = float(ld['ws']) if ld['ws'] > 0 else 2.65
            ld['ws'] = st.slider("Ajustar Peso de Sólidos (Ws g)", 0.1, max(15.0, val_ws_ini*3), val_ws_ini, key=f"ws_{k}")
            
            # LÓGICA DE SIMULACIÓN (Recálculo instantáneo)
            ld['vv'] = ld['vs'] * ld['e']
            ld['vt'] = ld['vs'] + ld['vv']
            if ld['vs'] > 0: ld['gs'] = ld['ws'] / ld['vs']
            
            # Aplicación de Densidad del agua = 1.0
            ld['ww'] = ld['ws'] * ld['w']
            ld['vw'] = ld['ww'] # Ww = Vw
            
            if ld['vv'] > 0: ld['s'] = ld['vw'] / ld['vv']
            ld['wm'] = ld['ws'] + ld['ww']
            ld['va'] = max(0.0, ld['vv'] - ld['vw'])
            
            st.session_state.live_data = ld
            if st.button("🔄 Resetear"):
                st.session_state.live_data = st.session_state.base_data.copy()
                st.session_state.slider_key = np.random.randint(1001, 2000)
                st.rerun()

        with c_res:
            st.subheader("📊 Resultados")
            gh = (ld['wm']/ld['vt'])*9.81 if ld['vt'] > 0 else 0
            gd = (ld['ws']/ld['vt'])*9.81 if ld['vt'] > 0 else 0
            
            res_df = pd.DataFrame({"Propiedad": list(diccionario_maestro.values()), 
                                  "Valor": [f"{ld['gs']:.3f}", f"{ld['e']:.4f}", f"{ld['n']*100:.2f}%", f"{ld['w']*100:.2f}%", f"{ld['s']*100:.2f}%", 
                                           f"{ld['wm']:.3f} g", f"{ld['ws']:.3f} g", f"{ld['ww']:.3f} g", f"{ld['vt']:.3f} cm³", f"{ld['vs']:.3f} cm³", 
                                           f"{ld['vv']:.3f} cm³", f"{ld['vw']:.3f} cm³", f"{ld['va']:.3f} cm³", f"{gh:.2f} kN/m³", f"{gd:.2f} kN/m³"]})
            st.table(res_df)
            st.session_state.df_grav_excel = res_df
            
            fig = go.Figure(data=[go.Bar(name='Sólidos', x=['Fases'], y=[ld['vs']], marker_color='#7E5109'),
                                  go.Bar(name='Agua', x=['Fases'], y=[ld['vw']], marker_color='#3498DB'),
                                  go.Bar(name='Aire', x=['Fases'], y=[ld['va']], marker_color='#BDC3C7')])
            fig.update_layout(barmode='stack', height=300, margin=dict(t=0,b=0)); st.plotly_chart(fig, use_container_width=True)

# --- PESTAÑA 2: PERFIL DE PRESIONES ---
with tabs[1]:
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

    # Cálculo de puntos críticos (superficie, NF y fronteras de estratos)
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
        df_p = pd.DataFrame({"Z (m)": z_l, "σ Total (kPa)": st_l, "u (kPa)": u_l, "σ' Ef. (kPa)": se_l})
        st.dataframe(df_p, use_container_width=True)
        st.session_state.df_pres_excel = df_p
        fig_p = go.Figure()
        fig_p.add_trace(go.Scatter(x=st_l, y=z_l, name='Total', line=dict(color='brown')))
        fig_p.add_trace(go.Scatter(x=u_l, y=z_l, name='Neutro', line=dict(color='blue', dash='dash')))
        fig_p.add_trace(go.Scatter(x=se_l, y=z_l, name='Efectivo', fill='tonextx', line=dict(color='green')))
        fig_p.update_yaxes(autorange="reversed", title="Profundidad (m)"); st.plotly_chart(fig_p, use_container_width=True)

# --- PESTAÑA 3: PLASTICIDAD & SUCS ---
with tabs[2]:
    st.header("Clasificación de Suelos Finos")
    cl1, cl2 = st.columns([1, 2])
    with cl1:
        ll = st.number_input("Límite Líquido (LL)", 0, 150, 0)
        lp = st.number_input("Límite Plástico (LP)", 0, 100, 0)
        ip = ll - lp
        st.metric("Índice de Plasticidad (IP)", ip)
        
        lin_a = 0.73 * (ll - 20)
        if ll == 0: s_t = "Sin datos"
        elif ll < 50:
            if ip > 7 and ip >= lin_a: s_t = "CL (Arcilla de baja plasticidad)"
            elif ip < 4 or ip < lin_a: s_t = "ML (Limo de baja plasticidad)"
            else: s_t = "CL-ML (Suelo dual)"
        else:
            if ip >= lin_a: s_t = "CH (Arcilla de alta plasticidad)"
            else: s_t = "MH (Limo de alta plasticidad)"
        
        st.success(f"Clasificación SUCS Sugerida: **{s_t}**")
        st.session_state.df_lim_excel = pd.DataFrame({"LL": [ll], "LP": [lp], "IP": [ip], "SUCS": [s_t]})
    
    with cl2:
        fig_c = go.Figure()
        x_v = np.linspace(0,100,100)
        fig_c.add_trace(go.Scatter(x=x_v, y=0.73*(x_v-20), name='Línea A', line=dict(color='black')))
        if ll > 0: 
            fig_c.add_trace(go.Scatter(x=[ll], y=[ip], mode='markers', marker=dict(size=15, color='red'), name='Muestra'))
        fig_c.update_xaxes(title="Límite Líquido", range=[0,100]); fig_c.update_yaxes(title="Índice Plasticidad", range=[0,60])
        st.plotly_chart(fig_c, use_container_width=True)

# --- PESTAÑA 4: REPORTE FINAL ---
with tabs[3]:
    st.header("Generación de Reporte")
    st.write("Haz clic en el botón de abajo para consolidar todos los cálculos en un archivo de Excel.")
    
    if st.button("📥 Descargar Reporte Consolidado"):
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
            if 'df_grav_excel' in st.session_state: st.session_state.df_grav_excel.to_excel(writer, sheet_name='Gravimetría')
            if 'df_pres_excel' in st.session_state: st.session_state.df_pres_excel.to_excel(writer, sheet_name='Presiones')
            if 'df_lim_excel' in st.session_state: st.session_state.df_lim_excel.to_excel(writer, sheet_name='Plasticidad')
        
        st.download_button(
            label="💾 Guardar archivo .xlsx",
            data=out.getvalue(),
            file_name="Reporte_Geotecnia_Master.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
