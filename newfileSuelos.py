import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io

# Configuración inicial
st.set_page_config(page_title="Geotecnia Master Pro", layout="wide")

st.title("🏗️ Geotecnia Master: Suite Completa de Suelos")
st.markdown("Cálculos Gravimétricos, Límites de Atterberg y Reportes Profesionales.")

# --- PESTAÑAS PRINCIPALES ---
tab1, tab2, tab3 = st.tabs(["📊 Fase de Suelos", "🧪 Plasticidad", "📥 Exportar Reporte"])

# --- LÓGICA COMPARTIDA (Inicialización) ---
w_nat, e, n, s, ip, ll, lp = 0, 0, 0, 0, 0, 0, 0

# --- PESTAÑA 1: GRAVIMETRÍA ---
with tab1:
    st.header("Análisis de Fases y Pesos Unitarios")
    col_in1, col_in2 = st.columns(2)
    
    with col_in1:
        wm = st.number_input("Peso Húmedo (Wm) [g]", value=1150.0, step=0.1)
        ws = st.number_input("Peso Seco (Ws) [g]", value=950.0, step=0.1)
    with col_in2:
        vt = st.number_input("Volumen Total (Vt) [cm³]", value=600.0, step=0.1)
        gs = st.number_input("Gravedad Específica (Gs)", value=2.65, step=0.01)

    try:
        # Cálculos de fase
        ww = wm - ws
        vs = ws / gs
        vw = ww / 1.0
        vv = vt - vs
        va = vv - vw
        
        # Relaciones
        e = vv / vs
        n = (vv / vt) * 100
        w_nat = (ww / ws) * 100
        s = (vw / vv) * 100
        
        # Pesos unitarios
        gm = wm / vt
        gd = ws / vt
        gsat = ((gs + e) * 1.0) / (1 + e)

        # Visualización
        st.subheader("🖼️ Diagrama de Fases (Proporciones)")
        df_fases = pd.DataFrame({"Fase": ["Muestra"], "Aire": [va], "Agua": [vw], "Sólidos": [vs]})
        st.bar_chart(df_fases.set_index("Fase"), color=["#BDC3C7", "#3498DB", "#7E5109"])

        # Métricas
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("e (Rel. Vacíos)", f"{e:.3f}")
        m2.metric("n (Porosidad)", f"{n:.1f}%")
        m3.metric("w (Humedad)", f"{w_nat:.1f}%")
        m4.metric("S (Saturación)", f"{s:.1f}%")
        
        st.info(f"**Pesos Unitarios (g/cm³):** Húmedo: {gm:.2f} | Seco: {gd:.2f} | Saturado: {gsat:.2f}")

    except:
        st.warning("Ajuste los datos para ver los resultados.")

# --- PESTAÑA 2: PLASTICIDAD ---
with tab2:
    st.header("Límites de Atterberg")
    col_l1, col_l2 = st.columns([1, 2])
    
    with col_l1:
        ll = st.number_input("Límite Líquido (LL)", value=45.0)
        lp = st.number_input("Límite Plástico (LP)", value=20.0)
        ip = ll - lp
        st.metric("Índice Plasticidad (IP)", f"{ip:.1f}%")
        
        # Clasificación rápida
        if ip > (0.73 * (ll - 20)) and ll >= 50: clas = "CH (Arcilla Alta P.)"
        elif ip > (0.73 * (ll - 20)) and ll < 50: clas = "CL (Arcilla Baja P.)"
        else: clas = "Limo / Orgánico"
        st.success(f"Clasificación Sugerida: {clas}")

    with col_l2:
        # Carta de Plasticidad con Plotly (Dispersión)
        fig = go.Figure()
        linea_a_x = list(range(20, 101))
        linea_a_y = [0.73 * (x - 20) for x in linea_a_x]
        
        fig.add_trace(go.Scatter(x=linea_a_x, y=linea_a_y, mode='lines', name='Línea A', line=dict(color='black', dash='dash')))
        fig.add_trace(go.Scatter(x=[ll], y=[ip], mode='markers', marker=dict(color='red', size=15), name='Tu Suelo'))
        
        fig.update_layout(title="Carta de Casagrande", xaxis_title="LL", yaxis_title="IP", xaxis=dict(range=[0,100]), yaxis=dict(range=[0,60]))
        st.plotly_chart(fig, use_container_width=True)

# --- PESTAÑA 3: EXPORTACIÓN ---
with tab3:
    st.header("Generar Reporte Profesional")
    st.write("Presiona el botón para descargar los resultados en formato Excel.")

    # Preparar datos para Excel
    datos_reporte = pd.DataFrame({
        "Parámetro": ["Wm", "Ws", "Vt", "Gs", "e", "n", "w (%)", "S (%)", "LL", "LP", "IP"],
        "Valor": [wm, ws, vt, gs, round(e,3), round(n,2), round(w_nat,2), round(s,2), ll, lp, ip]
    })

    def crear_excel(df):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Resultados')
        return output.getvalue()

    excel_file = crear_excel(datos_reporte)
    
    st.download_button(
        label="📥 Descargar Reporte (.xlsx)",
        data=excel_file,
        file_name="informe_suelos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    st.table(datos_reporte)
