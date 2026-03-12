import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import io

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Geotecnia Suite Master v12.5", layout="wide", page_icon="🏗️")
st.title("🏗️ Geotecnia Master: Suite Integral v12.5")
st.markdown("---")

tabs = st.tabs(["🧩 Gravimetría & Simulación", "🗂️ Perfil de Presiones", "📈 Plasticidad & SUCS", "📥 Reporte Final"])

# --- PESTAÑA 1: GRAVIMETRÍA & DIAGNÓSTICO ---
with tabs[0]:
    st.header("Propiedades Físicas con Control Estructural (e)")
    
    diccionario_maestro = {
        "gs": "Gs (Gravedad específica)", "e": "e (Relación de vacíos)", "n": "n (Porosidad %)",
        "w": "w (Contenido de humedad %)", "s": "S (Grado de saturación %)", "wm": "Peso total muestra (Wt)",
        "ws": "Peso de los sólidos (Ws)", "ww": "Peso del agua (Ww)", "vt": "Vt (Volumen total)",
        "vs": "Vs (Volumen sólidos)", "vv": "Vv (Volumen vacíos)", "vw": "Vw (Volumen agua)",
        "va": "Va (Volumen aire)", "gh": "γ (Peso unitario húmedo)", "gd": "γd (Peso unitario seco)"
    }
    
    col_sel, col_val = st.columns([1, 2])
    with col_sel:
        seleccionados = st.multiselect("Datos de entrada de laboratorio:", options=list(diccionario_maestro.keys()), format_func=lambda x: diccionario_maestro[x])
        inputs = {}
        for i, clave in enumerate(seleccionados):
            inputs[clave] = st.number_input(f"Ingresa {clave}", value=0.0, format="%.3f", key=f"inp_{clave}")

    if st.button("🚀 Calcular e Inicializar Simulador"):
        d = {k: inputs.get(k, 0.0) for k in diccionario_maestro.keys()}
        for pct in ['w', 'n', 's']:
            if d[pct] > 1.0: d[pct] /= 100
        
        # Motor de cálculo de 30 iteraciones para resolver todas las dependencias
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

    if 'live_data' in st.session_state:
        st.markdown("---")
        if st.button("🔄 Resetear a Valores Iniciales"):
            st.session_state.live_data = st.session_state.base_data.copy()
            st.rerun()

        ld = st.session_state.live_data
        c_sim, c_res, c_ref = st.columns([1.2, 1.8, 1])
        
        with c_sim:
            st.subheader("🕹️ Controles Dinámicos")
            # 1. Ajuste de Relación de Vacíos (e)
            max_e_val = max(5.0, float(ld['e'] * 2))
            new_e = st.slider("Relación de vacíos (e)", 0.1, max_e_val, float(ld['e']))
            if new_e != ld['e']:
                ld['e'] = new_e; ld['vv'] = ld['vs'] * new_e; ld['n'] = new_e / (1 + new_e)
                ld['vw'] = ld['vv'] * ld['s']; ld['ww'] = ld['vw'] * 1.0
                ld['w'] = ld['ww'] / ld['ws'] if ld['ws'] > 0 else 0
            
            # 2. Humedad y Saturación
            new_w = st.slider("Humedad w (%)", 0.0, 100.0, float(ld['w']*100)) / 100
            if new_w != ld['w']:
                ld['w'] = new_w; ld['ww'] = ld['ws'] * new_w; ld['vw'] = ld['ww'] / 1.0
                ld['s'] = ld['vw'] / ld['vv'] if ld['vv'] > 0 else 0
            
            new_s = st.slider("Saturación S (%)", 0.0, 100.0, float(ld['s']*100)) / 100
            if new_s != ld['s']:
                ld['s'] = new_s; ld['vw'] = ld['vv'] * new_s; ld['ww'] = ld['vw'] * 1.0
                ld['w'] = ld['ww'] / ld['ws'] if ld['ws'] > 0 else 0

            # 3. Masas y Volúmenes de Sólidos
            ld['ws'] = st.number_input("Peso Sólidos Ws (g)", value=float(ld['ws']))
            ld['vs'] = ld['ws'] / ld['gs']
            
            # Recalcular finales para tabla y gráfico
            ld['vt'] = ld['vs'] + ld['vv']
            ld['wm'] = ld['ws'] + ld['ww']
            ld['va'] = max(0.0, ld['vv'] - ld['vw'])
            st.session_state.live_data = ld

        with c_res:
            st.subheader("📊 Estado en Tiempo Real")
            res_df = pd.DataFrame({"Propiedad": list(diccionario_maestro.values()), 
                                  "Valor": [f"{ld['gs']:.2f}", f"{ld['e']:.3f}", f"{ld['n']*100:.1f}%", f"{ld['w']*100:.2f}%", f"{ld['s']*100:.1f}%", 
                                           f"{ld['wm']:.2f}g", f"{ld['ws']:.2f}g", f"{ld['ww']:.2f}g", f"{ld['vt']:.2f}cm³", f"{ld['vs']:.2f}cm³", 
                                           f"{ld['vv']:.2f}cm³", f"{ld['vw']:.2f}cm³", f"{ld['va']:.2f}cm³", f"{(ld['wm']/ld['vt'])*9.81:.2f}", f"{(ld['ws']/ld['vt'])*9.81:.2f}"]})
            st.table(res_df)
            st.session_state.df_grav_excel = res_df
            
            fig = go.Figure(data=[go.Bar(name='Sólidos', x=['Fases'], y=[ld['vs']], marker_color='#7E5109'),
                                  go.Bar(name='Agua', x=['Fases'], y=[ld['vw']], marker_color='#3498DB'),
                                  go.Bar(name='Aire', x=['Fases'], y=[ld['va']], marker_color='#BDC3C7')])
            fig.update_layout(barmode='stack', height=350); st.plotly_chart(fig, use_container_width=True)

        with c_ref:
            st.subheader("🔬 Diagnóstico")
            diagnostico = "Orgánico/Blando" if ld['e'] > 1.5 else "Mineral/Firme"
            st.info(f"Tipo probable: **{diagnostico}**")
            st.write("**Valores típicos de e:**")
            st.write("- Arenas: 0.4 - 1.0")
            st.write("- Arcillas: 0.6 - 1.5")
            st.write("- Turbas: > 3.0")

# --- PESTAÑA 2: PERFIL DE PRESIONES ---
with tabs[1]:
    st.header("Análisis de Esfuerzos Geostáticos")
    col_in, col_gr = st.columns([1, 2])
    with col_in:
        n_est = st.number_input("Número de Estratos", 1, 10, 2); nf = st.number_input("Nivel Freático (m)", 0.0, 100.0, 2.0)
        est = []
        for i in range(int(n_est)):
            h = st.number_input(f"H {i+1} (m)", 0.1, 50.0, 3.0, key=f"z_h{i}")
            g = st.number_input(f"γ {i+1} (kN/m³)", 10.0, 25.0, 18.0, key=f"z_g{i}")
            est.append({'h': h, 'g': g})

    # Cálculo en puntos críticos (bordes y NF)
    pts = sorted(list(set([0.0, nf] + [sum(e['h'] for e in est[:i+1]) for i in range(len(est))])))
    pts = [p for p in pts if p <= sum(e['h'] for e in est)]
    
    z_f, s_f, u_f, ef_f = [], [], [], []
    s_acu = 0
    for i in range(len(pts)):
        zp = pts[i]
        if i > 0:
            dz = zp - pts[i-1]
            z_temp = 0
            for e in est:
                if zp <= z_temp + e['h'] + 0.01:
                    s_acu += dz * e['g']; break
                z_temp += e['h']
        u_curr = (zp - nf) * 9.81 if zp > nf else 0
        z_f.append(zp); s_f.append(round(s_acu,2)); u_f.append(round(u_curr,2)); ef_f.append(round(s_acu-u_curr,2))

    with col_gr:
        df_p = pd.DataFrame({"Z (m)": z_f, "σ Total": s_f, "u (Poros)": u_f, "σ' Efectivo": ef_f})
        st.subheader("📊 Tabla de Cálculos")
        st.dataframe(df_p, use_container_width=True)
        st.session_state.df_pres_excel = df_p
        
        fig_p = go.Figure()
        fig_p.add_trace(go.Scatter(x=s_f, y=z_f, name='σ Total', line=dict(color='brown')))
        fig_p.add_trace(go.Scatter(x=u_f, y=z_f, name='u (Agua)', line=dict(color='blue', dash='dash')))
        fig_p.add_trace(go.Scatter(x=ef_f, y=z_f, name="σ' Efectivo", fill='tonextx', line=dict(color='green', width=3)))
        fig_p.update_yaxes(autorange="reversed", title="Profundidad (m)"); st.plotly_chart(fig_p, use_container_width=True)

# --- PESTAÑA 3: PLASTICIDAD & SUCS ---
with tabs[2]:
    st.header("Clasificación SUCS (Finos)")
    c1, c2 = st.columns([1, 2])
    with c1:
        ll = st.number_input("Límite Líquido (LL)", 0, 150, 45)
        lp = st.number_input("Límite Plástico (LP)", 0, 100, 20)
        ip = ll - lp
        st.metric("Índice de Plasticidad (IP)", ip)
        
        linea_a = 0.73 * (ll - 20)
        if ll < 50:
            if ip > 7 and ip >= linea_a: s_tipo = "CL (Arcilla de baja plasticidad)"
            elif ip < 4 or ip < linea_a: s_tipo = "ML (Limo de baja plasticidad)"
            else: s_tipo = "CL-ML (Suelo Dual)"
        else:
            if ip >= linea_a: s_tipo = "CH (Arcilla de alta plasticidad)"
            else: s_tipo = "MH (Limo de alta plasticidad)"
        
        st.subheader(f"Clasificación: {s_tipo}")
        st.session_state.df_lim_excel = pd.DataFrame({"LL": [ll], "LP": [lp], "IP": [ip], "Clasificación": [s_tipo]})

    with c2:
        x_c = np.linspace(0, 100, 100)
        fig_c = go.Figure()
        fig_c.add_trace(go.Scatter(x=x_c, y=0.73*(x_c-20), name='Línea A', line=dict(color='black')))
        fig_c.add_trace(go.Scatter(x=[ll], y=[ip], mode='markers+text', text=["Suelo"], textposition="top right", marker=dict(size=15, color='red')))
        fig_c.update_xaxes(title="Límite Líquido", range=[0,100]); fig_c.update_yaxes(title="IP", range=[0,60])
        st.plotly_chart(fig_c, use_container_width=True)

# --- PESTAÑA 4: EXPORTACIÓN ---
with tabs[3]:
    st.header("Generar Reporte Final")
    if st.button("📥 Preparar Excel"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            if 'df_grav_excel' in st.session_state: st.session_state.df_grav_excel.to_excel(writer, sheet_name='Gravimetria')
            if 'df_pres_excel' in st.session_state: st.session_state.df_pres_excel.to_excel(writer, sheet_name='Esfuerzos')
            if 'df_lim_excel' in st.session_state: st.session_state.df_lim_excel.to_excel(writer, sheet_name='Plasticidad')
        st.download_button("Descargar_Reporte.xlsx", output.getvalue(), "reporte_geotecnico.xlsx")
        
