import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io

st.set_page_config(page_title="Geotecnia Dynamic Pro", layout="wide")

st.title("🏗️ Geotecnia Master: Simulador Dinámico")
st.markdown("---")

tabs = st.tabs(["🔄 Simulador de Fases", "🗂️ Perfiles de Presión", "📈 Plasticidad", "📥 Exportar"])

with tabs[0]:
    st.header("Relaciones Gravimétricas Dinámicas")
    
    # 1. ENTRADA DE DATOS INICIAL
    opciones = {
        "gs": "Gs", "e": "e", "w": "w (%)", "s": "S (%)", 
        "wm": "Wm (g)", "ws": "Ws (g)", "vt": "Vt (cm³)"
    }
    
    col_sel, col_val = st.columns([1, 2])
    with col_sel:
        seleccionados = st.multiselect("Datos base para el suelo:", options=list(opciones.keys()), format_func=lambda x: opciones[x])
    
    inputs = {}
    if seleccionados:
        c_ins = st.columns(len(seleccionados))
        for i, clave in enumerate(seleccionados):
            inputs[clave] = c_ins[i].number_input(f"{opciones[clave]}", value=0.0, step=0.01)

    # 2. MOTOR DE CÁLCULO BASE
    if st.button("🚀 Inicializar Suelo"):
        st.session_state.calulado = True
        # (Lógica simplificada para obtener el estado inicial)
        gs = inputs.get("gs", 2.65); ws = inputs.get("ws", 0.0); vt = inputs.get("vt", 100.0)
        wm = inputs.get("wm", 0.0); w_in = inputs.get("w", 0.0)/100
        
        # Si no hay pesos, creamos un suelo unitario
        if ws == 0: ws = 160.0; vt = 100.0 
        if wm == 0 and w_in > 0: wm = ws * (1 + w_in)
        elif wm == 0: wm = ws * 1.15 # Asunción inicial

        st.session_state.ws_base = ws
        st.session_state.vt_base = vt
        st.session_state.gs_base = gs
        st.session_state.wm_base = wm

    # 3. BARRA DE AJUSTE EN VIVO (Simulación física)
    if 'ws_base' in st.session_state:
        st.markdown("### 🎚️ Ajuste Físico en Tiempo Real")
        st.info("Mueve la barra para ver cómo reacciona el suelo (el volumen y los sólidos permanecen constantes).")
        
        # El slider controla la HUMEDAD (w)
        w_sim = st.slider("Ajustar Contenido de Humedad (w %)", 0.0, 50.0, 
                         float((st.session_state.wm_base - st.session_state.ws_base)/st.session_state.ws_base * 100))
        
        # --- LEYES FÍSICAS EN VIVO ---
        w_dec = w_sim / 100
        ws = st.session_state.ws_base
        vt = st.session_state.vt_base
        gs = st.session_state.gs_base
        
        ww = ws * w_dec          # El peso del agua cambia con la humedad
        wm_actual = ws + ww      # El peso total se corrige solo
        vs = ws / (gs * 1.0)     # El volumen de sólidos es constante (Ley física)
        vw = ww / 1.0            # El volumen de agua cambia
        vv = vt - vs             # El volumen de vacíos es constante
        va = vv - vw             # El aire se ajusta según el agua disponible
        s_actual = (vw / vv) * 100 if vv > 0 else 0
        e_actual = vv / vs
        
        # Validación de saturación física
        if va < 0:
            st.error(f"⚠️ ¡Límite físico alcanzado! El suelo no puede aceptar más agua (Saturación > 100%).")
            va = 0; vw = vv; s_actual = 100.0; wm_actual = ws + (vw * 1.0)

        # 4. RESULTADOS DINÁMICOS
        c1, c2, c3 = st.columns(3)
        c1.metric("Peso Total (Wm)", f"{wm_actual:.2f} g")
        c2.metric("Saturación (S)", f"{s_actual:.1f} %")
        c3.metric("Rel. Vacíos (e)", f"{e_actual:.3f}")

        # DIAGRAMA DINÁMICO
        fig = go.Figure(data=[
            go.Bar(name='Sólidos', x=['Fases'], y=[vs], marker_color='#7E5109'),
            go.Bar(name='Agua', x=['Fases'], y=[vw], marker_color='#3498DB'),
            go.Bar(name='Aire', x=['Fases'], y=[va], marker_color='#BDC3C7')
        ])
        fig.update_layout(barmode='stack', title="Comportamiento del Suelo en Vivo", height=400)
        st.plotly_chart(fig, use_container_width=True)



# (Las demás pestañas se mantienen igual que la versión anterior)
