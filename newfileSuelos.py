import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import io

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Geotecnia Suite Master v22.9", layout="wide", page_icon="🏗️")

# Barra lateral - Personalización
st.sidebar.title("👨‍🏫 Panel de Control")
modo = st.sidebar.radio("Selecciona el Modo:", ("Metas (Laboratorio)", "Académico (Base Vs=1)"))
st.sidebar.markdown("---")
st.sidebar.info(f"📍 **Modo {modo.split()[0]}**: Física de fases 1:1 para el agua ($\gamma_w=1$).")

st.title(f"🏗️ Geotecnia Master - Modo {modo.split()[0]}")
st.markdown("---")

# Estructura de Pestañas
tabs = st.tabs(["🧩 Gravimetría & Fases", "🗂️ Perfil de Presiones", "📈 Plasticidad & SUCS", "📥 Reporte Final"])

# --- PESTAÑA 1: GRAVIMETRÍA (Saturación Variable) ---
with tabs[0]:
    diccionario_maestro = {
        "gs": "Gs", "e": "e", "n": "n %", "w": "w %", "s": "S %", "wm": "Wt (g)",
        "ws": "Ws (g)", "ww": "Ww (g)", "vt": "Vt (cm³)", "vs": "Vs (cm³)",
        "vv": "Vv (cm³)", "vw": "Vw (cm³)", "va": "Va (cm³)", "gh": "γ (kN/m³)", "gd": "γd (kN/m³)"
    }

    st.subheader("📥 Entrada de Datos")
    seleccionados = st.multiselect("Variables conocidas:", options=list(diccionario_maestro.keys()), format_func=lambda x: diccionario_maestro[x])
    
    inputs = {}
    cols_in = st.columns(3)
    for i, clave in enumerate(seleccionados):
        inputs[clave] = cols_in[i%3].number_input(f"{diccionario_maestro[clave]}", value=0.0, format="%.4f", key=f"main_in_{clave}")

    if st.button("🚀 Ejecutar Cálculo"):
        d = {k: 0.0 for k in diccionario_maestro.keys()}
        if modo == "Académico (Base Vs=1)": d['vs'] = 1.0
        for k, v in inputs.items():
            d[k] = v / 100 if k in ['w', 'n', 's'] and v > 1.0 else v
        
        # MOTOR DE CÁLCULO DEDUCTIVO (100 iteraciones para convergencia)
        for _ in range(100):
            if d['ww'] > 0: d['vw'] = d['ww']
            if d['vw'] > 0: d['ww'] = d['vw']
            if d['gs'] > 0 and d['vs'] > 0: d['ws'] = d['gs'] * d['vs']
            if d['ws'] > 0 and d['vs'] > 0: d['gs'] = d['ws'] / d['vs']
            if d['ws'] > 0 and d['w'] > 0: d['ww'] = d['ws'] * d['w']; d['vw'] = d['ww']
            if d['ww'] > 0 and d['ws'] > 0: d['w'] = d['ww'] / d['ws']
            if d['e'] > 0 and d['vs'] > 0: d['vv'] = d['e'] * d['vs']
            if d['vv'] > 0 and d['vs'] > 0: d['e'] = d['vv'] / d['vs']
            if d['vw'] > 0 and d['vv'] > 0: d['s'] = d['vw'] / d['vv']
            if d['s'] > 0 and d['vv'] > 0 and d['vw'] == 0: d['vw'] = d['s'] * d['vv']; d['ww'] = d['vw']
            if d['vs'] > 0 and d['vv'] > 0: d['vt'] = d['vs'] + d['vv']
            if d['ws'] > 0 and d['ww'] > 0: d['wm'] = d['ws'] + d['ww']
            if d['vv'] > 0 and d['vw'] > 0: d['va'] = max(0.0, d['vv'] - d['vw'])

        st.session_state.base_data = d.copy()
        st.session_state.live_data = d.copy()
        st.session_state.slider_key = np.random.randint(1, 1000)
        st.rerun()

    if 'live_data' in st.session_state:
        ld = st.session_state.live_data
        k = st.session_state.get('slider_key', 0)
        c_sim, c_res = st.columns([1.3, 1.7])
        
        with c_sim:
            st.subheader("🕹️ Ajuste Manual")
            ld['e'] = st.slider("Relación de Vacíos (e)", 0.01, 5.0, float(ld['e']) if ld['e'] > 0 else 0.6, key=f"e_{k}")
            ld['s'] = st.slider("Grado de Saturación (S %)", 0.0, 100.0, float(ld['s']*100), key=f"s_{k}") / 100
            ld['ws'] = st.slider("Peso Sólidos (Ws g)", 0.1, 15.0, float(ld['ws']) if ld['ws'] > 0 else 2.65, key=f"ws_{k}")
            
            # Recálculo Dinámico
            ld['vv'] = ld['e'] * ld['vs']
            ld['vw'] = ld['s'] * ld['vv']
            ld['ww'] = ld['vw']
            ld['va'] = max(0.0, ld['vv'] - ld['vw'])
            ld['vt'] = ld['vs'] + ld['vv']
            ld['wm'] = ld['ws'] + ld['ww']
            if ld['ws'] > 0: ld['w'] = ld['ww'] / ld['ws']
            if ld['vs'] > 0: ld['gs'] = ld['ws'] / ld['vs']

        with c_res:
            safe_e = f"{ld['vv']/ld['vs']:.4f}" if ld['vs'] > 0 else "0.0000"
            safe_n = f"{(ld['vv']/ld['vt'])*100:.2f}%" if ld['vt'] > 0 else "0.00%"
            gh_val = (ld['wm']/ld['vt'])*9.81 if ld['vt'] > 0 else 0
            gd_val = (ld['ws']/ld['vt'])*9.81 if ld['vt'] > 0 else 0
            
            res_df = pd.DataFrame({"Propiedad": list(diccionario_maestro.values()), 
                                  "Valor": [f"{ld['gs']:.3f}", safe_e, safe_n, f"{ld['w']*100:.2f}%", f"{ld['s']*100:.2f}%", 
                                           f"{ld['wm']:.3f} g", f"{ld['ws']:.3f} g", f"{ld['ww']:.3f} g", f"{ld['vt']:.3f} cm³", 
                                           f"{ld['vs']:.3f} cm³", f"{ld['vv']:.3f} cm³", f"{ld['vw']:.3f} cm³", f"{ld['va']:.3f} cm³", 
                                           f"{gh_val:.2f}", f"{gd_val:.2f}"]})
            st.table(res_df)
            st.session_state.df_grav_excel = res_df
            
            fig = go.Figure(data=[go.Bar(name='Sólidos', x=['Fases'], y=[ld['vs']], marker_color='#7E5109', text=[f"{ld['vs']:.2f}"]),
                                  go.Bar(name='Agua', x=['Fases'], y=[ld['vw']], marker_color='#3498DB', text=[f"{ld['vw']:.2f}"]),
                                  go.Bar(name='Aire', x=['Fases'], y=[ld['va']], marker_color='#BDC3C7', text=[f"{ld['va']:.2f}"])])
            fig.update_layout(barmode='stack', height=300, margin=dict(t=0,b=0)); st.plotly_chart(fig, use_container_width=True)

# --- PESTAÑA 2: PRESIONES ---
with tabs[1]:
    st.header("🗂️ Perfil de Esfuerzos Geostáticos")
    cp1, cp2 = st.columns([1, 2])
    with cp1:
        n_est = st.number_input("Número de Estratos", 1, 10, 2)
        nf = st.number_input("Nivel Freático (m)", 0.0, 100.0, 2.0)
        estratos = []
        for i in range(int(n_est)):
            h_e = st.number_input(f"Espesor H{i+1} (m)", 0.1, 50.0, 3.0, key=f"hp_{i}")
            g_e = st.number_input(f"Peso Unitario γ{i+1} (kN/m³)", 1.0, 25.0, 18.0, key=f"gp_{i}")
            estratos.append({'h': h_e, 'g': g_e})

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
        u_p = (z - nf) * 9.81 if z > nf else 0
        st_l.append(round(s_acu,2)); u_l.append(round(u_p,2)); se_l.append(round(s_acu - u_p,2))

    with cp2:
        df_p = pd.DataFrame({"Z (m)": z_pts, "σ Total (kPa)": st_l, "u (kPa)": u_l, "σ' Ef. (kPa)": se_l})
        st.dataframe(df_p, use_container_width=True)
        st.session_state.df_pres_excel = df_p
        fig_p = go.Figure()
        fig_p.add_trace(go.Scatter(x=st_l, y=z_pts, name='Total', line=dict(color='brown')))
        fig_p.add_trace(go.Scatter(x=u_l, y=z_pts, name='Poros (u)', line=dict(color='blue', dash='dash')))
        fig_p.add_trace(go.Scatter(x=se_l, y=z_pts, name='Efectivo', fill='tonextx', line=dict(color='green')))
        fig_p.update_yaxes(autorange="reversed", title="Profundidad Z (m)"); st.plotly_chart(fig_p, use_container_width=True)

# --- PESTAÑA 3: PLASTICIDAD ---
with tabs[2]:
    st.header("📈 Clasificación de Suelos (Carta de Plasticidad)")
    cl1, cl2 = st.columns([1, 2])
    with cl1:
        ll_in = st.number_input("Límite Líquido (LL)", 0, 150, 40)
        lp_in = st.number_input("Límite Plástico (LP)", 0, 100, 20)
        ip_in = ll_in - lp_in
        st.metric("Índice de Plasticidad (IP)", ip_in)
        lin_a = 0.73 * (ll_in - 20)
        if ll_in == 0: sucs_res = "N/A"
        elif ll_in < 50:
            sucs_res = "CL" if ip_in > 7 and ip_in >= lin_a else "ML" if ip_in < 4 or ip_in < lin_a else "CL-ML"
        else:
            sucs_res = "CH" if ip_in >= lin_a else "MH"
        st.success(f"Clasificación SUCS Sugerida: **{sucs_res}**")
        st.session_state.df_lim_excel = pd.DataFrame({"Parámetro": ["LL", "LP", "IP", "SUCS"], "Valor": [ll_in, lp_in, ip_in, sucs_res]})
    with cl2:
        fig_c = go.Figure()
        xv_c = np.linspace(0, 100, 100)
        fig_c.add_trace(go.Scatter(x=xv_c, y=0.73*(xv_c-20), name='Línea A', line=dict(color='black')))
        fig_c.add_trace(go.Scatter(x=[ll_in], y=[ip_in], mode='markers+text', text=["Muestra"], marker=dict(size=12, color='red')))
        fig_c.update_xaxes(title="Límite Líquido (LL)", range=[0, 100]); fig_c.update_yaxes(title="Índice Plasticidad (IP)", range=[0, 60])
        st.plotly_chart(fig_c, use_container_width=True)

# --- PESTAÑA 4: REPORTE ---
with tabs[3]:
    st.header("📥 Descargar Reporte Consolidado")
    st.write("Presiona el botón para generar un archivo Excel con todas las pestañas calculadas.")
    if st.button("📊 Generar y Descargar Excel"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            if 'df_grav_excel' in st.session_state: st.session_state.df_grav_excel.to_excel(writer, sheet_name='Gravimetria', index=False)
            if 'df_pres_excel' in st.session_state: st.session_state.df_pres_excel.to_excel(writer, sheet_name='Presiones', index=False)
            if 'df_lim_excel' in st.session_state: st.session_state.df_lim_excel.to_excel(writer, sheet_name='Plasticidad', index=False)
        st.download_button(label="💾 Guardar Reporte_Geotecnia.xlsx", data=output.getvalue(), file_name="Reporte_Geotecnia_Master.xlsx", mime="application/vnd.ms-excel")
