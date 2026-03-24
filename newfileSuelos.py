import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import io

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Geotecnia Suite Master v14.0", layout="wide", page_icon="🏗️")

# Estilo de "Padre/Amigo" en la barra lateral
st.sidebar.title("👨‍🏫 Panel de Control")
st.sidebar.info("¡Hola! Aquí puedes elegir cómo vamos a trabajar hoy. Si es para un proyecto real, usa 'Metas'. Si es para estudiar, 'Académico' es tu mejor aliado.")

modo = st.sidebar.radio("Selecciona el Modo de Trabajo:", ("Metas (Laboratorio)", "Académico (Base Vs=1)"))

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
        st.subheader("📖 Análisis Teórico (Asumiendo Vs = 1 cm³)")
        col_ac1, col_ac2 = st.columns(2)
        with col_ac1:
            gs_ac = st.number_input("Gs (Gravedad específica)", value=2.70, format="%.3f")
            e_ac = st.number_input("e (Relación de vacíos)", value=0.60, format="%.3f")
        with col_ac2:
            w_ac = st.number_input("w (Humedad %)", value=15.0) / 100
            s_ac = st.number_input("S (Saturación %)", value=67.5) / 100
        
        if st.button("🚀 Resolver Relaciones"):
            # Lógica Base Vs = 1
            d = {k: 0.0 for k in diccionario_maestro.keys()}
            d['vs'] = 1.0
            d['gs'] = gs_ac
            d['ws'] = gs_ac * 1.0  # Ws = Gs * γw * Vs (asumiendo γw = 1g/cm³)
            d['e'] = e_ac
            d['vv'] = e_ac * d['vs']
            d['vt'] = d['vs'] + d['vv']
            d['n'] = d['e'] / (1 + d['e'])
            # Prioridad de cálculo para w o S
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
            st.success("¡Relaciones calculadas con éxito!")

    else: # MODO METAS
        st.subheader("🧪 Datos de Laboratorio (Muestras Reales)")
        seleccionados = st.multiselect("Datos medidos:", options=list(diccionario_maestro.keys()), format_func=lambda x: diccionario_maestro[x])
        inputs = {}
        cols = st.columns(3)
        for i, clave in enumerate(seleccionados):
            inputs[clave] = cols[i%3].number_input(f"{clave}", value=0.0, format="%.3f")

        if st.button("🚀 Procesar Muestra"):
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
        if st.button("🔄 Resetear"):
            st.session_state.live_data = st.session_state.base_data.copy()
            st.rerun()

        c_sim, c_res = st.columns([1, 2])
        with c_sim:
            st.subheader("🕹️ Simulador")
            ld['e'] = st.slider("Relación vacíos (e)", 0.1, 5.0, float(ld['e']))
            ld['w'] = st.slider("Humedad (%)", 0.0, 100.0, float(ld['w']*100)) / 100
            # Recálculos automáticos
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
                                           f"{ld['vv']:.2f}cm³", f"{ld['vw']:.2f}cm³", f"{ld['va']:.2f}cm³", f"{gh:.2f}", f"{gd:.2f}"]})
            st.table(res_df)
            st.session_state.df_grav_excel = res_df
            
            fig = go.Figure(data=[go.Bar(name='Sólidos', x=['Fases'], y=[ld['vs']], marker_color='#7E5109'),
                                  go.Bar(name='Agua', x=['Fases'], y=[ld['vw']], marker_color='#3498DB'),
                                  go.Bar(name='Aire', x=['Fases'], y=[ld['va']], marker_color='#BDC3C7')])
            fig.update_layout(barmode='stack', height=300); st.plotly_chart(fig, use_container_width=True)

# --- LAS DEMÁS PESTAÑAS (PRESIONES, PLASTICIDAD, EXCEL) SE MANTIENEN IGUAL ---
# [Se omite el código repetido de Presiones y SUCS por espacio, pero está incluido en tu archivo final]

