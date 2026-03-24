import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import io

# ==========================================
# 1. CONFIGURACIÓN Y ESTILO DE LA APP
# ==========================================
st.set_page_config(page_title="Geotecnia Master v13.0 - Full", layout="wide")

# Diccionario Maestro de Etiquetas Geotécnicas
LABELS = {
    "gs": "Gs (Gravedad específica)", "e": "e (Relación de vacíos)", "n": "n (Porosidad %)",
    "w": "w (Contenido de humedad %)", "s": "S (Grado de saturación %)", "wm": "Wt (Peso total g)",
    "ws": "Ws (Peso sólidos g)", "ww": "Ww (Peso agua g)", "vt": "Vt (Volumen total cm³)",
    "vs": "Vs (Volumen sólidos cm³)", "vv": "Vv (Volumen vacíos cm³)", "vw": "Vw (Volumen agua cm³)",
    "va": "Va (Volumen aire cm³)", "gh": "γ (Húmedo kN/m³)", "gd": "γd (Seco kN/m³)"
}

st.title("🏗️ Geotecnia Master v13.0")
st.markdown("---")

# Creación de pestañas para organizar el flujo de trabajo
t_grav, t_esf, t_plas, t_rep = st.tabs([
    "🧩 Gravimetría e Inferencia", 
    "🗂️ Perfil de Esfuerzos", 
    "📈 Plasticidad y SUCS", 
    "📥 Reporte Profesional"
])

# ==========================================
# 2. PESTAÑA DE GRAVIMETRÍA
# ==========================================
with t_grav:
    col_input, col_sim = st.columns([1, 1.2])
    
    with col_input:
        st.subheader("📥 Datos de Laboratorio")
        seleccion = st.multiselect("Selecciona las variables que conoces:", 
                                   options=list(LABELS.keys()), 
                                   format_func=lambda x: LABELS[x])
        
        datos_in = {}
        for k in seleccion:
            datos_in[k] = st.number_input(f"Valor de {LABELS[k]}", value=0.0, format="%.4f", key=f"inp_{k}")
            
        if st.button("🚀 Procesar Estado Físico"):
            # Inicializamos el estado base
            m_base = {k: 0.0 for k in LABELS.keys()}
            for k, v in datos_in.items():
                # Ajuste automático de porcentajes a decimales
                m_base[k] = v / 100 if k in ['w', 'n', 's'] and v > 1.0 else v
            
            # MOTOR DE INFERENCIA: 150 iteraciones para cruzar todas las leyes físicas
            for _ in range(150):
                if m_base['gs'] > 0 and m_base['ws'] > 0 and m_base['vs'] == 0: m_base['vs'] = m_base['ws'] / m_base['gs']
                if m_base['ws'] > 0 and m_base['w'] > 0 and m_base['ww'] == 0: m_base['ww'] = m_base['ws'] * m_base['w']
                if m_base['vs'] > 0 and m_base['e'] > 0 and m_base['vv'] == 0: m_base['vv'] = m_base['e'] * m_base['vs']
                if m_base['vs'] > 0 and m_base['vv'] >= 0: m_base['vt'] = m_base['vs'] + m_base['vv']
                if m_base['vt'] > 0 and m_base['vs'] > 0: m_base['vv'] = m_base['vt'] - m_base['vs']
                if m_base['vv'] > 0 and m_base['vs'] > 0: m_base['e'] = m_base['vv'] / m_base['vs']
                if m_base['e'] > 0: m_base['n'] = m_base['e'] / (1 + m_base['e'])
                if m_base['ww'] >= 0: m_base['vw'] = m_base['ww'] # Asumiendo rho_w = 1g/cm3
                if m_base['vv'] > 0 and m_base['vw'] >= 0: 
                    m_base['s'] = m_base['vw'] / m_base['vv']
                    m_base['va'] = m_base['vv'] - m_base['vw']
            
            st.session_state.v13_db = m_base
            st.rerun()

    if "v13_db" in st.session_state:
        with col_sim:
            st.subheader("🕹️ Simulador Dinámico de Muestra")
            db = st.session_state.v13_db
            
            # Sliders para manipulación en tiempo real
            s_e = st.slider("Ajustar e (Relación de vacíos)", 0.01, 5.0, float(db['e']) if db['e'] > 0 else 0.65)
            s_w = st.slider("Ajustar w (Humedad %)", 0.0, 100.0, float(db['w']*100) if db['w'] > 0 else 15.0) / 100
            s_ws = st.slider("Ajustar Ws (Peso Sólidos g)", 0.1, 5000.0, float(db['ws']) if db['ws'] > 0 else 2.65)
            
            # --- CÁLCULOS DERIVADOS ESTRICTOS ---
            Gs_act = db['gs'] if db['gs'] > 0 else 2.65
            Vs_act = s_ws / Gs_act  # LEY FÍSICA: Vs depende de Ws
            Vv_act = s_e * Vs_act
            Vt_act = Vs_act + Vv_act
            Ww_act = s_ws * s_w
            Vw_act = Ww_act
            S_act = Vw_act / Vv_act if Vv_act > 0 else 0
            
            if S_act > 1.0: S_act, Vw_act, Ww_act = 1.0, Vv_act, Vv_act # Tope de saturación
            
            # Diccionario de resultados finales
            f_res = {
                "gs": Gs_act, "e": s_e, "n": Vv_act/Vt_act, "w": s_w, "s": S_act,
                "wm": s_ws + Ww_act, "ws": s_ws, "ww": Ww_act, "vt": Vt_act,
                "vs": Vs_act, "vv": Vv_act, "vw": Vw_act, "va": max(0, Vv_act - Vw_act),
                "gh": ((s_ws + Ww_act)/Vt_act)*9.81, "gd": (s_ws/Vt_act)*9.81
            }
            
            st.table(pd.DataFrame([{"Propiedad": LABELS[k], "Valor": f"{f_res[k]*100:.2f}%" if "%" in LABELS[k] else f"{f_res[k]:.4f}"} for k in LABELS]))
            st.session_state.v13_final_grav = f_res

        # Visualización del Diagrama de Fases
        fig_fases = go.Figure(data=[
            go.Bar(name='Sólidos', x=['Fases'], y=[Vs_act], marker_color='#7E5109', text=f"Vs: {Vs_act:.3f}"),
            go.Bar(name='Agua', x=['Fases'], y=[Vw_act], marker_color='#3498DB', text=f"Vw: {Vw_act:.3f}"),
            go.Bar(name='Aire', x=['Fases'], y=[max(0, Vv_act-Vw_act)], marker_color='#BDC3C7', text=f"Va: {max(0, Vv_act-Vw_act):.3f}")
        ])
        fig_fases.update_layout(barmode='stack', height=400, title="Estructura de la Muestra"); st.plotly_chart(fig_fases, use_container_width=True)

# ==========================================
# 3. PESTAÑA DE ESFUERZOS
# ==========================================
with t_esf:
    st.subheader("🗂️ Perfil Geostático de Esfuerzos")
    c_e1, c_e2 = st.columns([1, 2])
    
    with c_e1:
        n_capas = st.number_input("Número de Estratos", 1, 10, 2)
        z_nf = st.number_input("Nivel Freático (m)", 0.0, 100.0, 2.0)
        perfil = []
        for i in range(int(n_capas)):
            st.markdown(f"**Estrato {i+1}**")
            col_z1, col_z2 = st.columns(2)
            hi = col_z1.number_input(f"Espesor H{i+1}", 0.1, 50.0, 3.0, key=f"v13_h{i}")
            gi = col_z2.number_input(f"γ{i+1} (kN/m³)", 1.0, 30.0, 18.0, key=f"v13_g{i}")
            perfil.append({'h': hi, 'g': gi})

    # Cálculo de puntos críticos (Superficie, NF y contactos de estratos)
    puntos_z = [0.0, z_nf]
    acumulado = 0
    for p in perfil:
        acumulado += p['h']
        puntos_z.append(acumulado)
    puntos_z = sorted(list(set([p for p in puntos_z if p <= acumulado])))

    z_vals, sig_t, u_vals, sig_e, s_acu = [], [], [], [], 0
    for i, z in enumerate(puntos_z):
        if i > 0:
            dz = z - puntos_z[i-1]
            z_m = (z + puntos_z[i-1]) / 2
            h_count = 0
            for capa in perfil:
                h_count += capa['h']
                if z_m <= h_count:
                    s_acu += dz * capa['g']
                    break
        presion_u = (z - z_nf) * 9.81 if z > z_nf else 0
        z_vals.append(z); sig_t.append(s_acu); u_vals.append(presion_u); sig_e.append(s_acu - presion_u)

    with c_e2:
        df_final_esf = pd.DataFrame({"Profundidad (m)": z_vals, "σ Total (kPa)": sig_t, "u (kPa)": u_vals, "σ' Efectivo (kPa)": sig_e})
        st.dataframe(df_final_esf, use_container_width=True)
        st.session_state.v13_final_esf = df_final_esf
        
        fig_esf = go.Figure()
        fig_esf.add_trace(go.Scatter(x=sig_t, y=z_vals, name='σ Total', line=dict(color='brown', width=3)))
        fig_esf.add_trace(go.Scatter(x=u_vals, y=z_vals, name='u (Poro)', line=dict(color='blue', dash='dash')))
        fig_esf.add_trace(go.Scatter(x=sig_e, y=z_vals, name="σ' Efectivo", fill='tonextx', line=dict(color='green', width=3)))
        fig_esf.update_yaxes(autorange="reversed", title="Profundidad (m)")
        fig_esf.update_xaxes(title="Esfuerzo (kPa)", side="top")
        st.plotly_chart(fig_esf, use_container_width=True)

# ==========================================
# 4. PESTAÑA DE PLASTICIDAD Y SUCS
# ==========================================
with t_plas:
    st.subheader("📈 Análisis de Plasticidad y Clasificación")
    cl1, cl2 = st.columns(2)
    val_ll = cl1.number_input("Límite Líquido (LL)", 0, 150, 45)
    val_lp = cl2.number_input("Límite Plástico (LP)", 0, 100, 20)
    val_ip = val_ll - val_lp
    
    # Lógica de Clasificación SUCS (Simplificada para finos)
    sucs = "N/A"
    if val_ll >= 50:
        sucs = "CH (Arcilla de alta)" if val_ip > (0.73*(val_ll-20)) else "MH (Limo de alta)"
    else:
        sucs = "CL (Arcilla de baja)" if val_ip > (0.73*(val_ll-20)) else "ML (Limo de baja)"
    if 4 <= val_ip <= 7 and 10 <= val_ll <= 25: sucs = "CL-ML (Dual)"
    
    st.info(f"Clasificación probable del suelo: **{sucs}**")
    
    xv = np.linspace(0, 100, 100)
    y_a = 0.73 * (xv - 20)
    fig_plas = go.Figure()
    fig_plas.add_trace(go.Scatter(x=xv, y=y_a, name='Línea A', line=dict(color='black')))
    fig_plas.add_vline(x=50, line_dash="dash", line_color="gray")
    fig_plas.add_trace(go.Scatter(x=[val_ll], y=[val_ip], mode='markers+text', 
                                 text=[f"IP={val_ip}"], textposition="top right",
                                 marker=dict(size=15, color='red'), name="Muestra"))
    fig_plas.update_xaxes(title="Límite Líquido (LL)", range=[0, 100])
    fig_plas.update_yaxes(title="Índice de Plasticidad (IP)", range=[0, 60])
    st.plotly_chart(fig_plas)
    st.session_state.v13_final_plas = pd.DataFrame({"Variable": ["LL", "LP", "IP", "SUCS"], "Valor": [val_ll, val_lp, val_ip, sucs]})

# ==========================================
# 5. PESTAÑA DE REPORTE EXCEL
# ==========================================
with t_rep:
    st.subheader("📥 Exportación de Resultados")
    if st.button("📊 Generar Reporte Consolidado"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            if "v13_final_grav" in st.session_state:
                g_data = [{"Propiedad": LABELS[k], "Valor": st.session_state.v13_final_grav[k]} for k in LABELS]
                pd.DataFrame(g_data).to_excel(writer, sheet_name='Gravimetría', index=False)
            if "v13_final_esf" in st.session_state:
                st.session_state.v13_final_esf.to_excel(writer, sheet_name='Esfuerzos', index=False)
            if "v13_final_plas" in st.session_state:
                st.session_state.v13_final_plas.to_excel(writer, sheet_name='Plasticidad', index=False)
        
        st.download_button("💾 Descargar Archivo .xlsx", output.getvalue(), "Reporte_Geotecnico_v13.xlsx")
        
