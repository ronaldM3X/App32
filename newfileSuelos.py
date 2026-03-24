import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import io

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Geotecnia Master v25.0", layout="wide", page_icon="🏗️")

# Estilos para mejorar la interfaz (TDAH friendly)
st.markdown("""
    <style>
    .stTable { font-size: 1.1rem; }
    .stMetric { border: 1px solid #e1e4e8; padding: 10px; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# 2. PANEL DE CONTROL (BARRA LATERAL)
st.sidebar.title("👨‍🏫 Configuración")
modo = st.sidebar.radio("Selecciona el Modo de Trabajo:", ("Metas (Laboratorio)", "Académico (Base Vs=1)"))
st.sidebar.markdown("---")
if modo == "Metas (Laboratorio)":
    st.sidebar.success("✅ Vs es dinámico basado en Ws y Gs.")
else:
    st.sidebar.warning("📙 Vs está fijado en 1.0 (Convención teórica).")

st.title(f"🏗️ Geotecnia Master - Modo {modo.split()[0]}")
st.markdown("---")

# 3. PESTAÑAS PRINCIPALES
tabs = st.tabs(["🧩 Gravimetría & Fases", "🗂️ Perfil de Esfuerzos", "📈 Plasticidad (SUCS)", "📥 Descargar Reporte"])

# --- PESTAÑA 1: GRAVIMETRÍA ---
with tabs[0]:
    dicc = {
        "gs": "Gs (Gravedad específica)", "e": "e (Relación de vacíos)", "n": "n (Porosidad %)",
        "w": "w (Contenido de humedad %)", "s": "S (Grado de saturación %)", "wm": "Wt (Peso total)",
        "ws": "Ws (Peso sólidos)", "ww": "Ww (Peso agua)", "vt": "Vt (Volumen total)",
        "vs": "Vs (Volumen sólidos)", "vv": "Vv (Volumen vacíos)", "vw": "Vw (Volumen agua)",
        "va": "Va (Volumen aire)", "gh": "γ (Peso unitario húmedo)", "gd": "γd (Peso unitario seco)"
    }

    st.subheader("📥 Paso 1: Datos de Entrada")
    seleccionados = st.multiselect("Selecciona las variables que conoces:", options=list(dicc.keys()), format_func=lambda x: dicc[x])
    
    inputs = {}
    cols_in = st.columns(3)
    for i, clave in enumerate(seleccionados):
        inputs[clave] = cols_in[i%3].number_input(f"{dicc[clave]}", value=0.0, format="%.4f", key=f"in_{clave}")

    if st.button("🚀 Calcular Estado Inicial"):
        d = {k: 0.0 for k in dicc.keys()}
        if modo == "Académico (Base Vs=1)": d['vs'] = 1.0
        
        for k, v in inputs.items():
            d[k] = v / 100 if k in ['w', 'n', 's'] and v > 1.0 else v
        
        # Lógica de convergencia inicial
        for _ in range(100):
            if d['gs'] > 0 and d['ws'] > 0 and d['vs'] == 0: d['vs'] = d['ws'] / d['gs']
            if d['gs'] > 0 and d['vs'] > 0: d['ws'] = d['gs'] * d['vs']
            if d['ws'] > 0 and d['w'] > 0: d['ww'] = d['ws'] * d['w']
            if d['ww'] > 0: d['vw'] = d['ww']
            if d['e'] > 0 and d['vs'] > 0: d['vv'] = d['e'] * d['vs']
            if d['vw'] > 0 and d['vv'] > 0: d['s'] = d['vw'] / d['vv']
            if d['s'] > 0 and d['e'] > 0 and d['gs'] > 0: d['w'] = (d['s'] * d['e']) / d['gs']

        st.session_state.base_calc = d.copy()
        st.session_state.slider_key = np.random.randint(1, 9999)
        st.rerun()

    if 'base_calc' in st.session_state:
        st.markdown("---")
        c_sim, c_res = st.columns([1.3, 1.7])
        bc = st.session_state.base_calc
        sk = st.session_state.slider_key

        with c_sim:
            st.subheader("🕹️ Paso 2: Simulador Dinámico")
            
            # Inicialización de valores para sliders
            e_def = float(bc['e']) if bc['e'] > 0 else 0.650
            w_def = float(bc['w']*100) if bc['w'] > 0 else 15.0
            ws_def = float(bc['ws']) if bc['ws'] > 0 else 2.65
            gs_val = bc['gs'] if bc['gs'] > 0 else 2.65

            # SLIDERS (La fuente de la verdad)
            e_val = st.slider("Relación de vacíos (e)", 0.01, 5.0, e_def, step=0.001, key=f"sl_e_{sk}")
            w_val = st.slider("Humedad (w %)", 0.0, 100.0, w_def, step=0.1, key=f"sl_w_{sk}") / 100
            
            # Ws deshabilitado en Modo Académico porque depende de Vs=1
            ws_val = st.slider("Peso de Sólidos (Ws)", 0.1, 2000.0, ws_def, key=f"sl_ws_{sk}", disabled=(modo == "Académico (Base Vs=1)"))
            
            # RE-CÁLCULO TOTAL (Sincronización Física)
            final = {k: 0.0 for k in dicc.keys()}
            final['gs'] = gs_val
            final['e'] = e_val
            final['w'] = w_val
            
            # Lógica de Volumen de Sólidos según el modo elegido
            if modo == "Académico (Base Vs=1)":
                final['vs'] = 1.0
                final['ws'] = final['gs'] * final['vs'] # Ws se adapta a la base unitaria
            else:
                final['ws'] = ws_val
                final['vs'] = final['ws'] / final['gs'] # Vs es el resultado real del laboratorio
            
            # Cálculo de vacíos y agua (Aquí se cumple la relación S - w)
            final['vv'] = final['e'] * final['vs']
            final['ww'] = final['ws'] * final['w']
            final['vw'] = final['ww']
            
            # Grado de saturación resultante
            final['s'] = final['vw'] / final['vv'] if final['vv'] > 0 else 0
            
            # Control de saturación física (Límite 100%)
            if final['s'] > 1.0:
                final['s'] = 1.0
                final['vv'] = final['vw']
                final['e'] = final['vv'] / final['vs']
                st.warning("⚠️ Suelo Saturado: El agua ha desplazado todo el aire.")
            
            # Variables secundarias
            final['vt'] = final['vs'] + final['vv']
            final['va'] = max(0.0, final['vv'] - final['vw'])
            final['wm'] = final['ws'] + final['ww']
            final['n'] = final['vv'] / final['vt']

            if st.button("🔄 Reiniciar Simulación"):
                del st.session_state.base_calc
                st.rerun()

        with c_res:
            st.subheader("📊 Resultados de la Simulación")
            gh_val = (final['wm']/final['vt'])*9.81 if final['vt'] > 0 else 0
            gd_val = (final['ws']/final['vt'])*9.81 if final['vt'] > 0 else 0
            
            res_df = pd.DataFrame({
                "Propiedad": list(dicc.values()), 
                "Valor": [
                    f"{final['gs']:.3f}", f"{final['e']:.4f}", f"{final['n']*100:.2f}%", 
                    f"{final['w']*100:.2f}%", f"{final['s']*100:.2f}%", f"{final['wm']:.3f} g", 
                    f"{final['ws']:.3f} g", f"{final['ww']:.3f} g", f"{final['vt']:.3f} cm³", 
                    f"{final['vs']:.3f} cm³", f"{final['vv']:.3f} cm³", f"{final['vw']:.3f} cm³", 
                    f"{final['va']:.3f} cm³", f"{gh_val:.2f} kN/m³", f"{gd_val:.2f} kN/m³"
                ]
            })
            st.table(res_df)
            st.session_state.df_grav = res_df
            
            # Gráfico de Fases
            fig = go.Figure(data=[
                go.Bar(name='Sólidos', x=['Fases'], y=[final['vs']], marker_color='#7E5109', text=[f"Vs: {final['vs']:.2f}"]),
                go.Bar(name='Agua', x=['Fases'], y=[final['vw']], marker_color='#3498DB', text=[f"Vw: {final['vw']:.2f}"]),
                go.Bar(name='Aire', x=['Fases'], y=[final['va']], marker_color='#BDC3C7', text=[f"Va: {final['va']:.2f}"])
            ])
            fig.update_layout(barmode='stack', height=350, margin=dict(t=10,b=10)); st.plotly_chart(fig, use_container_width=True)

# --- PESTAÑA 2: ESFUERZOS GEOSTÁTICOS ---
with tabs[1]:
    st.header("🗂️ Perfil de Esfuerzos (σ, u, σ')")
    c1, c2 = st.columns([1, 2])
    with c1:
        n_est = st.number_input("Número de Estratos", 1, 10, 2)
        nf = st.number_input("Nivel Freático (m)", 0.0, 100.0, 2.0)
        datos_estratos = []
        for i in range(int(n_est)):
            h = st.number_input(f"Espesor H{i+1} (m)", 0.1, 50.0, 3.0, key=f"h_{i}")
            g = st.number_input(f"γ{i+1} (kN/m³)", 1.0, 25.0, 18.0, key=f"g_{i}")
            datos_estratos.append({'h': h, 'g': g})

    # Cálculo de puntos críticos
    prof = [0.0]
    acum = 0
    for e in datos_estratos:
        acum += e['h']
        prof.append(acum)
    if nf not in prof: prof.append(nf)
    prof = sorted([p for p in prof if p <= acum])
    
    st_l, u_l, se_l, s_acu = [], [], [], 0
    for i, z in enumerate(prof):
        if i > 0:
            dz = z - prof[i-1]
            z_mid = (z + prof[i-1])/2
            curr_z = 0
            for e in datos_estratos:
                if z_mid <= curr_z + e['h']:
                    s_acu += dz * e['g']
                    break
                curr_z += e['h']
        u = (z - nf) * 9.81 if z > nf else 0
        st_l.append(s_acu); u_l.append(u); se_l.append(s_acu - u)

    with c2:
        df_p = pd.DataFrame({"Profundidad (m)": prof, "σ Total (kPa)": st_l, "u (kPa)": u_l, "σ' Efectivo (kPa)": se_l})
        st.dataframe(df_p, use_container_width=True)
        st.session_state.df_pres = df_p
        fig_p = go.Figure()
        fig_p.add_trace(go.Scatter(x=st_l, y=prof, name='σ Total', line=dict(color='brown')))
        fig_p.add_trace(go.Scatter(x=u_l, y=prof, name='Presión Poros (u)', line=dict(color='blue', dash='dash')))
        fig_p.add_trace(go.Scatter(x=se_l, y=prof, name='σ\' Efectivo', fill='tonextx', line=dict(color='green')))
        fig_p.update_yaxes(autorange="reversed", title="Z (m)"); st.plotly_chart(fig_p, use_container_width=True)

# --- PESTAÑA 3: PLASTICIDAD ---
with tabs[2]:
    st.header("📈 Carta de Plasticidad")
    cl, cr = st.columns([1, 2])
    with cl:
        ll = st.number_input("Límite Líquido (LL)", 0, 150, 40)
        lp = st.number_input("Límite Plástico (LP)", 0, 100, 20)
        ip = ll - lp
        st.metric("Índice de Plasticidad (IP)", ip)
        st.session_state.df_lim = pd.DataFrame({"Parámetro": ["LL", "LP", "IP"], "Valor": [ll, lp, ip]})
    with cr:
        xv = np.linspace(0, 100, 100)
        linea_a = 0.73 * (xv - 20)
        fig_c = go.Figure()
        fig_c.add_trace(go.Scatter(x=xv, y=linea_a, name='Línea A', line=dict(color='black')))
        fig_c.add_trace(go.Scatter(x=[ll], y=[ip], mode='markers+text', text=["Suelo"], marker=dict(size=12, color='red')))
        fig_c.update_xaxes(title="Límite Líquido (LL)", range=[0, 100]); fig_c.update_yaxes(title="Índice Plasticidad (IP)", range=[0, 60])
        st.plotly_chart(fig_c, use_container_width=True)

# --- PESTAÑA 4: REPORTE ---
with tabs[3]:
    st.header("📥 Descargar Reporte Consolidado")
    if st.button("📊 Generar Archivo de Excel"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            if 'df_grav' in st.session_state: st.session_state.df_grav.to_excel(writer, sheet_name='Gravimetria', index=False)
            if 'df_pres' in st.session_state: st.session_state.df_pres.to_excel(writer, sheet_name='Presiones', index=False)
            if 'df_lim' in st.session_state: st.session_state.df_lim.to_excel(writer, sheet_name='Plasticidad', index=False)
        st.download_button("💾 Descargar Excel", output.getvalue(), "Reporte_Geotecnico_Completo.xlsx")
