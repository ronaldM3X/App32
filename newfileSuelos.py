import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import io

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="Geotecnia Suite Master v24.2", layout="wide", page_icon="🏗️")

# Estilos CSS para mejorar legibilidad (TDAH friendly)
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 10px; border-radius: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# Barra lateral - Selección de Modo
st.sidebar.title("👨‍🏫 Panel de Control")
modo = st.sidebar.radio("Selecciona el Modo:", ("Metas (Laboratorio)", "Académico (Base Vs=1)"))
st.sidebar.markdown("---")
st.sidebar.info(f"Estás operando en Modo: **{modo.split()[0]}**")

st.title(f"🏗️ Geotecnia Master - {modo}")
st.markdown("---")

tabs = st.tabs(["🧩 Gravimetría & Fases", "🗂️ Perfil de Presiones", "📈 Plasticidad & SUCS", "📥 Reporte Final"])

# --- PESTAÑA 1: GRAVIMETRÍA ---
with tabs[0]:
    diccionario_maestro = {
        "gs": "Gs (Gravedad específica)", "e": "e (Relación de vacíos)", "n": "n (Porosidad %)",
        "w": "w (Contenido de humedad %)", "s": "S (Grado de saturación %)", "wm": "Wt (Peso total)",
        "ws": "Ws (Peso sólidos)", "ww": "Ww (Peso agua)", "vt": "Vt (Volumen total)",
        "vs": "Vs (Volumen sólidos)", "vv": "Vv (Volumen vacíos)", "vw": "Vw (Volumen agua)",
        "va": "Va (Volumen aire)", "gh": "γ (Unitario húmedo)", "gd": "γd (Unitario seco)"
    }

    st.subheader("📥 1. Entrada de Datos")
    seleccionados = st.multiselect("Variables conocidas:", options=list(diccionario_maestro.keys()), format_func=lambda x: diccionario_maestro[x])
    
    inputs = {}
    cols_in = st.columns(3)
    for i, clave in enumerate(seleccionados):
        inputs[clave] = cols_in[i%3].number_input(f"{diccionario_maestro[clave]}", value=0.0, format="%.4f", key=f"main_in_{clave}")

    if st.button("🚀 Calcular Relaciones"):
        d = {k: 0.0 for k in diccionario_maestro.keys()}
        if modo == "Académico (Base Vs=1)": d['vs'] = 1.0
        for k, v in inputs.items():
            d[k] = v / 100 if k in ['w', 'n', 's'] and v > 1.0 else v
        
        # Motor de cálculo iterativo (50 pasadas para converger relaciones)
        for _ in range(50):
            if d['gs'] > 0 and d['ws'] > 0 and d['vs'] == 0: d['vs'] = d['ws'] / d['gs']
            if d['gs'] > 0 and d['vs'] > 0: d['ws'] = d['gs'] * d['vs']
            if d['ws'] > 0 and d['w'] > 0: d['ww'] = d['ws'] * d['w']
            if d['ww'] > 0: d['vw'] = d['ww']
            if d['e'] > 0 and d['vs'] > 0: d['vv'] = d['e'] * d['vs']
            if d['vw'] > 0 and d['vv'] > 0: d['s'] = d['vw'] / d['vv']

        st.session_state.base_calc = d.copy()
        st.session_state.slider_key = np.random.randint(1, 999)
        st.rerun()

    if 'base_calc' in st.session_state:
        st.markdown("---")
        c_sim, c_res = st.columns([1.3, 1.7])
        bc = st.session_state.base_calc
        sk = st.session_state.slider_key

        with c_sim:
            st.subheader("🕹️ Simulador Dinámico")
            # Definición de Sliders con Humedad (w) como control
            e_sl = st.slider("Relación de Vacíos (e)", 0.01, 5.0, float(bc['e']) if bc['e'] > 0 else 0.60, key=f"sl_e_{sk}")
            w_sl = st.slider("Humedad (w %)", 0.0, 100.0, float(bc['w']*100) if bc['w'] > 0 else 15.0, key=f"sl_w_{sk}") / 100
            ws_sl = st.slider("Peso de Sólidos (Ws)", 0.1, 1500.0, float(bc['ws']) if bc['ws'] > 0 else 2.70, key=f"sl_ws_{sk}")
            
            # Recálculo Final (Sincronizado)
            f = {k: 0.0 for k in diccionario_maestro.keys()}
            f['gs'] = bc['gs'] if bc['gs'] > 0 else 2.65
            f['e'], f['w'], f['ws'] = e_sl, w_sl, ws_sl
            
            # Vs dinámico
            f['vs'] = 1.0 if modo == "Académico (Base Vs=1)" else f['ws'] / f['gs']
            if modo == "Académico (Base Vs=1)": f['ws'] = f['gs'] * f['vs']
            
            f['vv'] = f['e'] * f['vs']
            f['ww'] = f['ws'] * f['w']
            f['vw'] = f['ww']
            f['s'] = f['vw'] / f['vv'] if f['vv'] > 0 else 0
            
            # Lógica de Saturación (Ajuste automático de e si se satura)
            if f['s'] > 1.0:
                f['s'] = 1.0
                f['vv'] = f['vw']
                f['e'] = f['vv'] / f['vs']
                st.warning("⚠️ Suelo Saturado: Los vacíos se expandieron por el agua.")
            
            f['vt'] = f['vs'] + f['vv']
            f['va'] = max(0.0, f['vv'] - f['vw'])
            f['wm'] = f['ws'] + f['ww']
            f['n'] = f['vv'] / f['vt']

            if st.button("🔄 Reiniciar Valores"):
                del st.session_state.base_calc
                st.rerun()

        with c_res:
            st.subheader("📊 Resultados Sincronizados")
            gh = (f['wm']/f['vt'])*9.81 if f['vt'] > 0 else 0
            gd = (f['ws']/f['vt'])*9.81 if f['vt'] > 0 else 0
            
            res_df = pd.DataFrame({"Propiedad": list(diccionario_maestro.values()), 
                                  "Valor": [f"{f['gs']:.3f}", f"{f['e']:.4f}", f"{f['n']*100:.2f}%", f"{f['w']*100:.2f}%", 
                                           f"{f['s']*100:.2f}%", f"{f['wm']:.3f} g", f"{f['ws']:.3f} g", f"{f['ww']:.3f} g", 
                                           f"{f['vt']:.3f} cm³", f"{f['vs']:.3f} cm³", f"{f['vv']:.3f} cm³", f"{f['vw']:.3f} cm³", 
                                           f"{f['va']:.3f} cm³", f"{gh:.2f} kN/m³", f"{gd:.2f} kN/m³"]})
            st.table(res_df)
            st.session_state.df_grav = res_df
            
            fig = go.Figure(data=[go.Bar(name='Sólidos', x=['Fases'], y=[f['vs']], marker_color='#7E5109'),
                                  go.Bar(name='Agua', x=['Fases'], y=[f['vw']], marker_color='#3498DB'),
                                  go.Bar(name='Aire', x=['Fases'], y=[f['va']], marker_color='#BDC3C7')])
            fig.update_layout(barmode='stack', height=300, margin=dict(t=0,b=0)); st.plotly_chart(fig, use_container_width=True)

# --- PESTAÑA 2: PRESIONES ---
with tabs[1]:
    st.header("🗂️ Perfil de Esfuerzos")
    cp1, cp2 = st.columns([1, 2])
    with cp1:
        n_est = st.number_input("Estratos", 1, 10, 2)
        nf = st.number_input("NF (m)", 0.0, 50.0, 2.0)
        estratos = []
        for i in range(int(n_est)):
            estratos.append({'h': st.number_input(f"H{i+1}", 0.1, 20.0, 3.0, key=f"ph{i}"), 
                             'g': st.number_input(f"γ{i+1}", 1.0, 25.0, 18.0, key=f"pg{i}")})

    z_pts = sorted(list(set([0.0, nf] + [sum(e['h'] for e in estratos[:i+1]) for i in range(len(estratos))])))
    z_pts = [p for p in z_pts if p <= sum(e['h'] for e in estratos)]
    st_l, u_l, se_l, s_acu = [], [], [], 0
    for i, z in enumerate(z_pts):
        if i > 0:
            dz = z - z_pts[i-1]
            z_m = (z + z_pts[i-1])/2
            z_t = 0
            for e in estratos:
                if z_m <= z_t + e['h']: s_acu += dz * e['g']; break
                z_t += e['h']
        u = (z - nf) * 9.81 if z > nf else 0
        st_l.append(s_acu); u_l.append(u); se_l.append(s_acu - u)

    with cp2:
        df_p = pd.DataFrame({"Z (m)": z_pts, "σ Total": st_l, "u": u_l, "σ' Ef.": se_l})
        st.dataframe(df_p, use_container_width=True); st.session_state.df_pres = df_p
        fig_p = go.Figure()
        fig_p.add_trace(go.Scatter(x=st_l, y=z_pts, name='Total', line=dict(color='brown')))
        fig_p.add_trace(go.Scatter(x=u_l, y=z_pts, name='u', line=dict(color='blue', dash='dash')))
        fig_p.add_trace(go.Scatter(x=se_l, y=z_pts, name='Efectivo', fill='tonextx', line=dict(color='green')))
        fig_p.update_yaxes(autorange="reversed"); st.plotly_chart(fig_p, use_container_width=True)

# --- PESTAÑA 3: PLASTICIDAD ---
with tabs[2]:
    st.header("📈 Clasificación SUCS")
    cl1, cl2 = st.columns([1, 2])
    with cl1:
        ll = st.number_input("Límite Líquido", 0, 150, 40)
        lp = st.number_input("Límite Plástico", 0, 100, 20)
        ip = ll - lp
        st.metric("Índice de Plasticidad", ip)
        st.success(f"SUCS: {'Fino de alta' if ll >= 50 else 'Fino de baja'} plasticidad")
        st.session_state.df_lim = pd.DataFrame({"Parámetro": ["LL", "LP", "IP"], "Valor": [ll, lp, ip]})
    with cl2:
        xv = np.linspace(0, 100, 100)
        fig_c = go.Figure()
        fig_c.add_trace(go.Scatter(x=xv, y=0.73*(xv-20), name='Línea A', line=dict(color='black')))
        fig_c.add_trace(go.Scatter(x=[ll], y=[ip], mode='markers', marker=dict(size=15, color='red')))
        fig_c.update_xaxes(title="Límite Líquido", range=[0, 100]); fig_c.update_yaxes(title="Índice de Plasticidad", range=[0, 60])
        st.plotly_chart(fig_c, use_container_width=True)

# --- PESTAÑA 4: REPORTE ---
with tabs[3]:
    st.header("📥 Descargar Resultados")
    if st.button("📊 Generar Excel Completo"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            if 'df_grav' in st.session_state: st.session_state.df_grav.to_excel(writer, sheet_name='Gravimetria')
            if 'df_pres' in st.session_state: st.session_state.df_pres.to_excel(writer, sheet_name='Presiones')
            if 'df_lim' in st.session_state: st.session_state.df_lim.to_excel(writer, sheet_name='Plasticidad')
        st.download_button("Descargar_Reporte_V24.xlsx", output.getvalue(), "Reporte_Geotecnia_Master.xlsx")
