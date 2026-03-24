import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import io

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Geotecnia Suite Master v23.3", layout="wide", page_icon="🏗️")

# Barra lateral - Personalización de Modos
st.sidebar.title("👨‍🏫 Panel de Control")
modo = st.sidebar.radio("Selecciona el Modo:", ("Metas (Laboratorio)", "Académico (Base Vs=1)"))
st.sidebar.markdown("---")
st.sidebar.info(f"Modo actual: **{modo}**")

st.title(f"🏗️ Geotecnia Master - Modo {modo.split()[0]}")
st.markdown("---")

# Estructura de Pestañas
tabs = st.tabs(["🧩 Gravimetría & Fases", "🗂️ Perfil de Presiones", "📈 Plasticidad & SUCS", "📥 Reporte Final"])

# --- PESTAÑA 1: GRAVIMETRÍA ---
with tabs[0]:
    diccionario_maestro = {
        "gs": "Gs (Gravedad específica)", "e": "e (Relación de vacíos)", "n": "n (Porosidad %)",
        "w": "w (Contenido de humedad %)", "s": "S (Grado de saturación %)", "wm": "Wt (Peso total muestra)",
        "ws": "Ws (Peso de los sólidos)", "ww": "Ww (Peso del agua)", "vt": "Vt (Volumen total)",
        "vs": "Vs (Volumen sólidos)", "vv": "Vv (Volumen vacíos)", "vw": "Vw (Volumen agua)",
        "va": "Va (Volumen aire)", "gh": "γ (Peso unitario húmedo)", "gd": "γd (Peso unitario seco)"
    }

    st.subheader("📥 Entrada de Datos")
    seleccionados = st.multiselect("Variables conocidas:", options=list(diccionario_maestro.keys()), format_func=lambda x: diccionario_maestro[x])
    
    inputs = {}
    cols_in = st.columns(3)
    for i, clave in enumerate(seleccionados):
        inputs[clave] = cols_in[i%3].number_input(f"{diccionario_maestro[clave]}", value=0.0, format="%.4f", key=f"main_in_{clave}")

    if st.button("🚀 Calcular Relaciones"):
        d = {k: 0.0 for k in diccionario_maestro.keys()}
        
        # Lógica de Modos: En Metas Vs es 0 hasta calcularlo. En Académico es 1.
        if modo == "Académico (Base Vs=1)": d['vs'] = 1.0
        else: d['vs'] = 0.0
            
        for k, v in inputs.items():
            d[k] = v / 100 if k in ['w', 'n', 's'] and v > 1.0 else v
        
        # Motor de cálculo iterativo
        for _ in range(100):
            if d['ww'] > 0: d['vw'] = d['ww']
            if d['vw'] > 0: d['ww'] = d['vw']
            if d['gs'] > 0 and d['vs'] > 0: d['ws'] = d['gs'] * d['vs']
            if d['ws'] > 0 and d['vs'] > 0: d['gs'] = d['ws'] / d['vs']
            if d['ws'] > 0 and d['gs'] > 0: d['vs'] = d['ws'] / d['gs']
            if d['ws'] > 0 and d['w'] > 0: d['ww'] = d['ws'] * d['w']
            if d['e'] > 0 and d['vs'] > 0: d['vv'] = d['e'] * d['vs']
            if d['vs'] > 0 and d['vv'] > 0: d['vt'] = d['vs'] + d['vv']
            if d['vw'] > 0 and d['vv'] > 0: d['s'] = d['vw'] / d['vv']
            if d['ws'] > 0 and d['ww'] > 0: d['wm'] = d['ws'] + d['ww']
        
        st.session_state.base_data = d.copy()
        st.session_state.live_data = d.copy()
        st.session_state.slider_key = np.random.randint(1, 1000)
        st.rerun()

    if 'live_data' in st.session_state:
        ld = st.session_state.live_data
        k = st.session_state.get('slider_key', 0)
        c_sim, c_res = st.columns([1.3, 1.7])
        
        with c_sim:
            st.subheader("🕹️ Simulador Dinámico")
            # Los sliders sobreescriben la lógica para sincronizar con la tabla
            e_slide = st.slider("Relación de Vacíos (e)", 0.01, 5.0, float(ld['e']) if ld['e'] > 0 else 0.60, key=f"e_{k}")
            w_slide = st.slider("Humedad (w %)", 0.0, 100.0, float(ld['w']*100) if ld['w'] > 0 else 15.0, key=f"w_{k}") / 100
            ws_slide = st.slider("Peso de Sólidos (Ws)", 0.1, 1000.0, float(ld['ws']) if ld['ws'] > 0 else 2.70, key=f"ws_{k}")
            
            # Aplicar cambios del simulador a los datos en vivo
            ld['e'] = e_slide
            ld['w'] = w_slide
            ld['ws'] = ws_slide
            
            curr_gs = ld['gs'] if ld['gs'] > 0 else 2.65
            ld['vs'] = ld['ws'] / curr_gs
            ld['vv'] = ld['e'] * ld['vs']
            ld['ww'] = ld['ws'] * ld['w']
            ld['vw'] = ld['ww']
            
            # Control de saturación física
            if ld['vw'] > ld['vv']:
                ld['vv'] = ld['vw']
                ld['s'] = 1.0
                st.warning("⚠️ Suelo saturado por humedad.")
            else:
                ld['s'] = ld['vw'] / ld['vv'] if ld['vv'] > 0 else 0
            
            ld['vt'] = ld['vs'] + ld['vv']
            ld['va'] = max(0.0, ld['vv'] - ld['vw'])
            ld['wm'] = ld['ws'] + ld['ww']
            ld['n'] = (ld['vv'] / ld['vt']) if ld['vt'] > 0 else 0

            if st.button("🔄 Reiniciar Valores"):
                st.session_state.live_data = st.session_state.base_data.copy()
                st.session_state.slider_key = np.random.randint(1001, 2000)
                st.rerun()

        with c_res:
            st.subheader("📊 Tabla de Resultados")
            gh = (ld['wm']/ld['vt'])*9.81 if ld['vt'] > 0 else 0
            gd = (ld['ws']/ld['vt'])*9.81 if ld['vt'] > 0 else 0
            
            res_df = pd.DataFrame({"Propiedad": list(diccionario_maestro.values()), 
                                  "Valor": [f"{curr_gs:.3f}", f"{ld['e']:.4f}", f"{ld['n']*100:.2f}%", f"{ld['w']*100:.2f}%", 
                                           f"{ld['s']*100:.2f}%", f"{ld['wm']:.3f} g", f"{ld['ws']:.3f} g", f"{ld['ww']:.3f} g", 
                                           f"{ld['vt']:.3f} cm³", f"{ld['vs']:.3f} cm³", f"{ld['vv']:.3f} cm³", f"{ld['vw']:.3f} cm³", 
                                           f"{ld['va']:.3f} cm³", f"{gh:.2f} kN/m³", f"{gd:.2f} kN/m³"]})
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
            h = st.number_input(f"Espesor H{i+1} (m)", 0.1, 50.0, 3.0, key=f"hp_{i}")
            g = st.number_input(f"γ{i+1} (kN/m³)", 1.0, 25.0, 18.0, key=f"gp_{i}")
            estratos.append({'h': h, 'g': g})

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
        df_p = pd.DataFrame({"Z (m)": z_pts, "σ Total (kPa)": st_l, "u (kPa)": u_l, "σ' Ef. (kPa)": se_l})
        st.dataframe(df_p, use_container_width=True)
        st.session_state.df_pres_excel = df_p
        fig_p = go.Figure()
        fig_p.add_trace(go.Scatter(x=st_l, y=z_pts, name='Total', line=dict(color='brown')))
        fig_p.add_trace(go.Scatter(x=u_l, y=z_pts, name='Poros (u)', line=dict(color='blue', dash='dash')))
        fig_p.add_trace(go.Scatter(x=se_l, y=z_pts, name='Efectivo', fill='tonextx', line=dict(color='green')))
        fig_p.update_yaxes(autorange="reversed", title="Profundidad (m)"); st.plotly_chart(fig_p, use_container_width=True)

# --- PESTAÑA 3: PLASTICIDAD ---
with tabs[2]:
    st.header("📈 Carta de Plasticidad y SUCS")
    cl1, cl2 = st.columns([1, 2])
    with cl1:
        ll = st.number_input("Límite Líquido (LL)", 0, 150, 40)
        lp = st.number_input("Límite Plástico (LP)", 0, 100, 20)
        ip = ll - lp
        st.metric("Índice de Plasticidad (IP)", ip)
        s_sucs = "CH/MH" if ll >= 50 else "CL/ML"
        st.success(f"Clasificación Sugerida: **{s_sucs}**")
        st.session_state.df_lim_excel = pd.DataFrame({"Dato": ["LL", "LP", "IP"], "Valor": [ll, lp, ip]})
    with cl2:
        fig_c = go.Figure()
        xv = np.linspace(0, 100, 100)
        fig_c.add_trace(go.Scatter(x=xv, y=0.73*(xv-20), name='Línea A', line=dict(color='black')))
        fig_c.add_trace(go.Scatter(x=[ll], y=[ip], mode='markers+text', text=["Suelo"], marker=dict(size=12, color='red')))
        fig_c.update_xaxes(title="LL", range=[0, 100]); fig_c.update_yaxes(title="IP", range=[0, 60])
        st.plotly_chart(fig_c, use_container_width=True)

# --- PESTAÑA 4: REPORTE ---
with tabs[3]:
    st.header("📥 Descargar Reporte Final")
    if st.button("📊 Generar Archivo Excel"):
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
            if 'df_grav_excel' in st.session_state: st.session_state.df_grav_excel.to_excel(writer, sheet_name='Gravimetria', index=False)
            if 'df_pres_excel' in st.session_state: st.session_state.df_pres_excel.to_excel(writer, sheet_name='Presiones', index=False)
            if 'df_lim_excel' in st.session_state: st.session_state.df_lim_excel.to_excel(writer, sheet_name='Plasticidad', index=False)
        st.download_button("💾 Guardar Excel", out.getvalue(), "Reporte_Geotecnia_V23.xlsx")
