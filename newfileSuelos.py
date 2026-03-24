import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import io

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Geotecnia Master v25.0", layout="wide")

# Forzar reinicio al cambiar de modo
if "m_act" not in st.session_state:
    st.session_state.m_act = "Metas"

st.sidebar.title("⚙️ Configuración")
modo = st.sidebar.radio("Modo de Trabajo:", ("Metas", "Académico"))

if modo != st.session_state.m_act:
    st.session_state.m_act = modo
    st.session_state.clear()
    st.rerun()

# Etiquetas completas
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

with t1:
    col_in, col_sim = st.columns([1, 1.2])
    
    with col_in:
        st.subheader("Paso 1: Entrada")
        sel = st.multiselect("Variables conocidas:", options=list(LABELS.keys()), format_func=lambda x: LABELS[x])
        d_in = {}
        for k in sel:
            d_in[k] = st.number_input(LABELS[k], value=0.0, format="%.4f", key=f"p1_{k}")
        
        if st.button("🚀 Calcular Base"):
            # Lógica simple sin bucles infinitos
            b = {k: 0.0 for k in LABELS.keys()}
            for k, v in d_in.items():
                b[k] = v / 100 if k in ['w', 'n', 's'] and v > 1.0 else v
            
            # Cálculo de emergencia para inicializar sliders
            if b['gs'] == 0: b['gs'] = 2.65
            if b['ws'] == 0: b['ws'] = 2.65
            if b['e'] == 0 and b['n'] > 0: b['e'] = b['n'] / (1 - b['n'])
            elif b['e'] == 0: b['e'] = 0.65
            
            st.session_state.base = b
            st.rerun()

    if "base" in st.session_state:
        with col_sim:
            st.subheader("🕹️ Simulador Dinámico")
            b = st.session_state.base
            
            # Sliders independientes
            e_s = st.slider("Relación de vacíos (e)", 0.01, 5.0, float(b['e']))
            w_s = st.slider("Humedad (w %)", 0.0, 100.0, float(b['w']*100)) / 100
            ws_s = st.slider("Peso Sólidos (Ws)", 0.1, 5000.0, float(b['ws']), disabled=(modo=="Académico"))
            
            # --- CÁLCULO MATEMÁTICO REAL ---
            Gs = b['gs']
            
            if modo == "Académico":
                Vs = 1.0
                Ws = Gs * Vs
            else:
                Ws = ws_s
                Vs = Ws / Gs # VS DEPENDE DE WS. SI WS=2.65 Y GS=2.65, VS SERÁ 1.0. SI WS=5, VS SERÁ 1.88.
            
            Vv = e_s * Vs
            Vt = Vs + Vv
            Ww = Ws * w_s
            Vw = Ww
            Sat = (Vw / Vv) if Vv > 0 else 0
            
            if Sat > 1.0:
                st.warning("⚠️ Saturación corregida al 100%")
                Sat, Vw, Ww = 1.0, Vv, Vv
            
            res = {
                "gs": Gs, "e": e_s, "n": Vv/Vt, "w": w_s, "s": Sat,
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
            st.subheader("📊 Resultados")
            df_res = pd.DataFrame([{"Propiedad": LABELS[k], "Valor": f"{res[k]*100:.2f}%" if "%" in LABELS[k] else f"{res[k]:.4f}"} for k in LABELS])
            st.table(df_res)
            st.session_state.df_excel = df_res

        with c_gra:
            fig = go.Figure(data=[
                go.Bar(name='Sólidos', x=['Fases'], y=[res['vs']], marker_color='#7E5109', text=f"{res['vs']:.3f}"),
                go.Bar(name='Agua', x=['Fases'], y=[res['vw']], marker_color='#3498DB', text=f"{res['vw']:.3f}"),
                go.Bar(name='Aire', x=['Fases'], y=[res['va']], marker_color='#BDC3C7', text=f"{res['va']:.3f}")
            ])
            fig.update_layout(barmode='stack', title="Diagrama de Fases (Vs dinámico)")
            st.plotly_chart(fig, use_container_width=True)

# --- PESTAÑA 2: ESFUERZOS ---
with t2:
    st.subheader("Perfil de Esfuerzos")
    n_e = st.number_input("Estratos", 1, 10, 2)
    nf = st.number_input("N.F. (m)", 0.0, 50.0, 2.0)
    data = []
    for i in range(int(n_e)):
        c1, c2 = st.columns(2)
        h = c1.number_input(f"Espesor {i+1}", 0.1, 50.0, 2.0, key=f"h{i}")
        g = c2.number_input(f"γ {i+1}", 1.0, 30.0, 18.0, key=f"g{i}")
        data.append({'h': h, 'g': g})
    
    zs = sorted(list(set([0.0, nf] + [sum(d['h'] for d in data[:i+1]) for i in range(len(data))])))
    zs = [z for z in zs if z <= sum(d['h'] for d in data)]
    
    sig, u, sig_e = [], [], []
    s_acu = 0
    for i in range(len(zs)):
        z = zs[i]
        if i > 0:
            dz = z - zs[i-1]
            z_m = (z + zs[i-1])/2
            h_c = 0
            for d in data:
                h_c += d['h']
                if z_m <= h_c:
                    s_acu += dz * d['g']
                    break
        pres_u = (z - nf) * 9.81 if z > nf else 0
        sig.append(s_acu); u.append(pres_u); sig_e.append(s_acu - pres_u)
    
    df_e = pd.DataFrame({"Z(m)": zs, "Total": sig, "Poros": u, "Efectivo": sig_e})
    st.dataframe(df_e)
    st.session_state.df_esf = df_e

# --- PESTAÑA 4: EXCEL ---
with t4:
    st.subheader("Reporte")
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
        if "df_excel" in st.session_state: st.session_state.df_excel.to_excel(writer, sheet_name='Fases', index=False)
        if "df_esf" in st.session_state: st.session_state.df_esf.to_excel(writer, sheet_name='Esfuerzos', index=False)
    st.download_button("💾 Bajar Excel", buf.getvalue(), "Geotecnia_Reporte.xlsx")
    
