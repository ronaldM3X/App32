import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import io

# 1. CONFIGURACIÓN E INICIALIZACIÓN
st.set_page_config(page_title="Geotecnia Master v25.0", layout="wide")

# Forzar limpieza si se cambia el modo
if "m_previo" not in st.session_state:
    st.session_state.m_previo = "Metas"

st.sidebar.title("⚙️ Configuración")
modo = st.sidebar.radio("Modo de Trabajo:", ("Metas", "Académico"))

if modo != st.session_state.m_previo:
    st.session_state.m_previo = modo
    st.session_state.clear()
    st.rerun()

# 2. DICCIONARIO DE ETIQUETAS (RESTAURADO)
LABELS = {
    "gs": "Gs (Gravedad específica)", "e": "e (Relación de vacíos)", "n": "n (Porosidad %)",
    "w": "w (Contenido de humedad %)", "s": "S (Grado de saturación %)", "wm": "Wt (Peso total g)",
    "ws": "Ws (Peso sólidos g)", "ww": "Ww (Peso agua g)", "vt": "Vt (Volumen total cm³)",
    "vs": "Vs (Volumen sólidos cm³)", "vv": "Vv (Volumen vacíos cm³)", "vw": "Vw (Volumen agua cm³)",
    "va": "Va (Volumen aire cm³)", "gh": "γ (Húmedo kN/m³)", "gd": "γd (Seco kN/m³)"
}

st.title(f"🏗️ Geotecnia Master - {modo}")
st.markdown("---")

t1, t2, t3, t4 = st.tabs(["🧩 Gravimetría", "🗂️ Esfuerzos", "📈 Plasticidad", "📥 Excel"])

# --- PESTAÑA 1: GRAVIMETRÍA ---
with t1:
    col_in, col_sim = st.columns([1, 1])
    
    with col_in:
        st.subheader("Paso 1: Entrada")
        sel = st.multiselect("Variables:", options=list(LABELS.keys()), format_func=lambda x: LABELS[x])
        d_in = {}
        for k in sel:
            d_in[k] = st.number_input(LABELS[k], value=0.0, format="%.4f", key=f"p1_{k}")
        
        if st.button("🚀 Calcular Base"):
            # Inicializar valores
            calc = {k: 0.0 for k in LABELS.keys()}
            for k, v in d_in.items():
                calc[k] = v / 100 if k in ['w', 'n', 's'] and v > 1.0 else v
            
            # Motor de convergencia pura
            for _ in range(200):
                if calc['gs'] > 0 and calc['ws'] > 0 and calc['vs'] == 0: calc['vs'] = calc['ws'] / calc['gs']
                if calc['ws'] > 0 and calc['w'] > 0 and calc['ww'] == 0: calc['ww'] = calc['ws'] * calc['w']
                if calc['vt'] > 0 and calc['vs'] > 0 and calc['vv'] == 0: calc['vv'] = calc['vt'] - calc['vs']
                if calc['vv'] > 0 and calc['vs'] > 0 and calc['e'] == 0: calc['e'] = calc['vv'] / calc['vs']
                if calc['vs'] > 0 and calc['vv'] >= 0: calc['vt'] = calc['vs'] + calc['vv']
            
            st.session_state.base = calc
            st.rerun()

    if "base" in st.session_state:
        with col_sim:
            st.subheader("🕹️ Simulador Dinámico")
            b = st.session_state.base
            
            # Sliders con valores base del Paso 1
            e_val = st.slider("Ajustar e", 0.01, 5.0, float(b['e']) if b['e'] > 0 else 0.65)
            w_val = st.slider("Ajustar w %", 0.0, 100.0, float(b['w']*100) if b['w'] > 0 else 15.0) / 100
            ws_val = st.slider("Ajustar Ws (g)", 0.1, 5000.0, float(b['ws']) if b['ws'] > 0 else 2.65, 
                               disabled=(modo=="Académico"))
            
            # --- CÁLCULO FÍSICO FINAL (SIN MEMORIA) ---
            Gs = b['gs'] if b['gs'] > 0 else 2.65
            
            if modo == "Académico":
                Vs = 1.0
                Ws = Gs * Vs
            else:
                Ws = ws_val
                Vs = Ws / Gs  # AQUÍ: Vs se recalcula siempre, no puede ser 1 a menos que Ws == Gs
            
            Vv = e_val * Vs
            Vt = Vs + Vv
            Ww = Ws * w_val
            Vw = Ww
            S = Vw / Vv if Vv > 0 else 0
            
            if S > 1.0:
                st.warning("⚠️ Saturación > 100% corregida.")
                S, Vw, Ww = 1.0, Vv, Vv
            
            final_res = {
                "gs": Gs, "e": e_val, "n": Vv/Vt, "w": w_val, "s": S,
                "wm": Ws + Ww, "ws": Ws, "ww": Ww, "vt": Vt, "vs": Vs,
                "vv": Vv, "vw": Vw, "va": max(0, Vv-Vw),
                "gh": ((Ws+Ww)/Vt)*9.81, "gd": (Ws/Vt)*9.81
            }
            
            if st.button("Reiniciar"):
                st.session_state.clear()
                st.rerun()

        st.markdown("---")
        c_res, c_gra = st.columns([1, 1])
        
        with c_res:
            st.subheader("📊 Tabla de Resultados")
            filas = []
            for k, label in LABELS.items():
                v = final_res[k]
                formato = f"{v*100:.2f}%" if "%" in label else f"{v:.4f}"
                filas.append({"Propiedad": label, "Valor": formato})
            
            df_final = pd.DataFrame(filas)
            st.table(df_final)
            st.session_state.df_excel = df_final

        with c_gra:
            fig = go.Figure(data=[
                go.Bar(name='Sólidos', x=['Fases'], y=[Vs], marker_color='#7E5109', text=f"{Vs:.3f}"),
                go.Bar(name='Agua', x=['Fases'], y=[Vw], marker_color='#3498DB', text=f"{Vw:.3f}"),
                go.Bar(name='Aire', x=['Fases'], y=[max(0, Vv-Vw)], marker_color='#BDC3C7', text=f"{max(0, Vv-Vw):.3f}")
            ])
            fig.update_layout(barmode='stack', height=400, title="Diagrama de Fases")
            st.plotly_chart(fig, use_container_width=True)

# --- PESTAÑA 2: ESFUERZOS ---
with t2:
    st.subheader("Perfil de Esfuerzos Geostáticos")
    # Lógica simplificada y funcional
    n = st.number_input("Número de Estratos", 1, 10, 2)
    nf = st.number_input("Nivel Freático (m)", 0.0, 50.0, 2.0)
    est = []
    for i in range(int(n)):
        c1, c2 = st.columns(2)
        h = c1.number_input(f"H {i+1} (m)", 0.1, 50.0, 2.0, key=f"h{i}")
        g = c2.number_input(f"γ {i+1} (kN/m³)", 1.0, 30.0, 18.0, key=f"g{i}")
        est.append({'h': h, 'g': g})
    
    # Cálculo de puntos críticos
    zs = [0.0]
    acu_h = 0
    for e in est:
        acu_h += e['h']
        zs.append(acu_h)
    if nf not in zs and nf < acu_h: zs.append(nf)
    zs.sort()

    sig, u, sig_e = [], [], []
    curr_sig = 0
    for i in range(len(zs)):
        z = zs[i]
        if i > 0:
            dz = z - zs[i-1]
            z_mid = (z + zs[i-1])/2
            h_tmp = 0
            for e in est:
                h_tmp += e['h']
                if z_mid <= h_tmp:
                    curr_sig += dz * e['g']
                    break
        pres_u = (z - nf) * 9.81 if z > nf else 0
        sig.append(curr_sig); u.append(pres_u); sig_e.append(curr_sig - pres_u)
    
    df_e = pd.DataFrame({"Z(m)": zs, "σ Total": sig, "u": u, "σ' Efec": sig_e})
    st.dataframe(df_e)
    st.session_state.df_esf = df_e

# --- PESTAÑA 4: EXCEL (RESTAURADO) ---
with t4:
    st.subheader("Generar Reporte")
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        if "df_excel" in st.session_state: st.session_state.df_excel.to_excel(writer, sheet_name='Gravimetria', index=False)
        if "df_esf" in st.session_state: st.session_state.df_esf.to_excel(writer, sheet_name='Esfuerzos', index=False)
    
    st.download_button(label="💾 Descargar Excel", data=buffer.getvalue(), 
                       file_name="Reporte_Geotecnico.xlsx", mime="application/vnd.ms-excel")
    
