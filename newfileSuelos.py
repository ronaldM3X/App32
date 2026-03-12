import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import io

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Geotecnia Suite Master v9.5", layout="wide", page_icon="🏗️")
st.title("🏗️ Geotecnia Master: Suite Integral v9.5")
st.markdown("---")

tabs = st.tabs(["🧩 Gravimetría", "🗂️ Perfil de Presiones", "📈 Plasticidad & SUCS", "📥 Reporte Final"])

# --- PESTAÑA 1: GRAVIMETRÍA ---
with tabs[0]:
    st.header("Propiedades Físicas")
    # Diccionario con los nombres exactos que solicitaste
    diccionario_maestro = {
        "gs": "Gs (Gravedad específica)", 
        "e": "e (Relación de vacíos)", 
        "n": "n (Porosidad %)",
        "w": "w (Contenido de humedad %)", 
        "s": "S (Grado de saturación %)", 
        "wm": "Peso total de la muestra (Wt)",
        "ws": "Peso de los sólidos (Ws)", 
        "ww": "Peso del agua (Ww)", 
        "vt": "Vt (Volumen total)",
        "vs": "Vs (Volumen sólidos)", 
        "vv": "Vv (Volumen vacíos)", 
        "vw": "Vw (Volumen agua)",
        "va": "Va (Volumen aire)", 
        "gh": "γ (Peso unitario húmedo)", 
        "gd": "γd (Peso unitario seco)"
    }
    
    seleccionados = st.multiselect("Selecciona tus datos de entrada:", options=list(diccionario_maestro.keys()), format_func=lambda x: diccionario_maestro[x])
    inputs = {}
    if seleccionados:
        cols = st.columns(3)
        for i, clave in enumerate(seleccionados):
            inputs[clave] = cols[i % 3].number_input(f"{diccionario_maestro[clave]}", value=0.0, format="%.3f", key=f"inp_{clave}")

    if st.button("🚀 Calcular Gravimetría"):
        d = {k: inputs.get(k, 0.0) for k in diccionario_maestro.keys()}
        # Normalización de porcentajes
        for pct in ['w', 'n', 's']:
            if d[pct] > 1.0: d[pct] /= 100
        
        # Motor de cálculo de relaciones de fase (Iterativo para resolver dependencias)
        for _ in range(30):
            if d['ws'] > 0 and d['gs'] > 0: d['vs'] = d['ws'] / (d['gs'] * 1.0)
            if d['wm'] > 0 and d['ws'] > 0 and d['ww'] == 0: d['ww'] = d['wm'] - d['ws']
            if d['ws'] > 0 and d['w'] > 0 and d['ww'] == 0: d['ww'] = d['ws'] * d['w']
            if d['vt'] > 0 and d['vs'] > 0 and d['vv'] == 0: d['vv'] = d['vt'] - d['vs']
            if d['vv'] > 0 and d['vs'] > 0 and d['e'] == 0: d['e'] = d['vv'] / d['vs']
            if d['e'] > 0 and d['n'] == 0: d['n'] = d['e'] / (1 + d['e'])
            if d['gs'] > 0 and d['w'] > 0 and d['e'] > 0 and d['s'] == 0: d['s'] = (d['w'] * d['gs']) / d['e']
            if d['ww'] > 0: d['vw'] = d['ww'] / 1.0
            if d['vv'] > 0 and d['vw'] > 0: d['va'] = d['vv'] - d['vw']
            if d['ws'] > 0 and d['ww'] > 0: d['wm'] = d['ws'] + d['ww']
        
        st.session_state.v95_base = d
        st.success("Cálculos completados.")

    if 'v95_base' in st.session_state:
        db = st.session_state.v95_base
        # Simulador dinámico
        st.markdown("---")
        c_ctrl, c_disp = st.columns([1, 2.5])
        with c_ctrl:
            st.subheader("🕹️ Simulador")
            var_m = st.radio("Ajustar variable:", ["Humedad (w)", "Saturación (S)"])
            w_max = (1.0 * db['e']) / db['gs']
            if var_m == "Humedad (w)":
                w_sim = st.slider("Humedad (%)", 0.0, float(w_max*100*1.1), float(db['w']*100)) / 100
                s_sim = (w_sim * db['gs']) / db['e']
                if s_sim > 1.0: st.warning("⚠️ Suelo sobresaturado"); s_sim = 1.0
            else:
                s_sim = st.slider("Saturación (%)", 0.0, 100.0, float(db['s']*100)) / 100
                w_sim = (s_sim * db['e']) / db['gs']
            
            vs_v = db['ws'] / (db['gs'] * 1.0); vv_v = vs_v * db['e']
            vw_v = vv_v * s_sim; va_v = max(0.0, vv_v - vw_v)

        with c_disp:
            res_v = pd.DataFrame({
                "Propiedad": list(diccionario_maestro.values()), 
                "Valor": [f"{db['gs']:.2f}", f"{db['e']:.3f}", f"{db['n']*100:.1f}%", f"{w_sim*100:.2f}%", f"{s_sim*100:.1f}%", 
                          f"{db['ws']+vw_v:.2f} g", f"{db['ws']:.2f} g", f"{vw_v:.2f} g", f"{vs_v+vv_v:.2f} cm³", f"{vs_v:.2f} cm³", 
                          f"{vv_v:.2f} cm³", f"{vw_v:.2f} cm³", f"{va_v:.2f} cm³", f"{(db['ws']+vw_v)/(vs_v+vv_v)*9.81:.2f}", f"{db['ws']/(vs_v+vv_v)*9.81:.2f}"]
            })
            st.table(res_v)
            st.session_state.df_grav_excel = res_v
            
            fig = go.Figure(data=[
                go.Bar(name='Sólidos (Ws)', x=['Fases'], y=[vs_v], marker_color='#7E5109'),
                go.Bar(name='Agua (Ww)', x=['Fases'], y=[vw_v], marker_color='#3498DB'),
                go.Bar(name='Aire (Va)', x=['Fases'], y=[va_v], marker_color='#BDC3C7')
            ])
            fig.update_layout(barmode='stack', height=350, title="Diagrama de Fases (Volúmenes)"); st.plotly_chart(fig, use_container_width=True)

# --- PESTAÑA 2: PERFIL DE PRESIONES ---
with tabs[1]:
    st.header("Análisis de Esfuerzos Geostáticos")
    col_in, col_gr = st.columns([1, 2])
    with col_in:
        n_est = st.number_input("Estratos", 1, 10, 2); nf = st.number_input("Nivel Freático (m)", 0.0, 100.0, 2.0)
        est = []
        for i in range(int(n_est)):
            h = st.number_input(f"Espesor H{i+1} (m)", 0.1, 50.0, 3.0, key=f"hp{i}")
            g = st.number_input(f"γ{i+1} (kN/m³)", 10.0, 25.0, 18.0, key=f"gp{i}")
            est.append({'h': h, 'g': g})

    # Cálculo de puntos críticos
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
        df_p = pd.DataFrame({"Z(m)": z_f, "σ Total": s_f, "u (Poros)": u_f, "σ' Efec.": ef_f})
        st.subheader("📊 Resultados Detallados")
        st.dataframe(df_p, use_container_width=True)
        st.session_state.df_pres_excel = df_p
        
        fig_p = go.Figure()
        fig_p.add_trace(go.Scatter(x=s_f, y=z_f, name='σ Total', line=dict(color='#5D4037')))
        fig_p.add_trace(go.Scatter(x=u_f, y=z_f, name='u', line=dict(color='#0288D1', dash='dash')))
        fig_p.add_trace(go.Scatter(x=ef_f, y=z_f, name="σ' Ef.", fill='tonextx', line=dict(color='#2E7D32', width=3)))
        fig_p.update_yaxes(autorange="reversed", title="Profundidad (m)"); st.plotly_chart(fig_p, use_container_width=True)

# --- PESTAÑA 3: PLASTICIDAD & SUCS ---
with tabs[2]:
    st.header("Clasificación de Suelos Finos (SUCS)")
    c1, c2 = st.columns([1, 2])
    with c1:
        ll = st.number_input("Límite Líquido (LL)", 0, 120, 45)
        lp = st.number_input("Límite Plástico (LP)", 0, 100, 20)
        ip = ll - lp
        st.metric("Índice de Plasticidad (IP)", ip)
        
        # Clasificación SUCS
        linea_a = 0.73 * (ll - 20)
        if ll < 50:
            if ip > 7 and ip >= linea_a: s_tipo = "CL (Arcilla de baja plasticidad)"
            elif ip < 4 or ip < linea_a: s_tipo = "ML (Limo de baja plasticidad)"
            else: s_tipo = "CL-ML (Suelo Dual)"
        else:
            if ip >= linea_a: s_tipo = "CH (Arcilla de alta plasticidad)"
            else: s_tipo = "MH (Limo de alta plasticidad)"
        
        st.subheader(f"Resultado: {s_tipo}")
        st.session_state.df_lim_excel = pd.DataFrame({"LL": [ll], "LP": [lp], "IP": [ip], "Clasificación": [s_tipo]})

    with c2:
        x_c = np.linspace(0, 100, 100)
        fig_c = go.Figure()
        fig_c.add_trace(go.Scatter(x=x_c, y=0.73*(x_c-20), name='Línea A', line=dict(color='black')))
        fig_c.add_trace(go.Scatter(x=[ll], y=[ip], mode='markers+text', text=[s_tipo.split()[0]], textposition="top center", marker=dict(size=15, color='red')))
        fig_c.update_xaxes(range=[0,100], title="Límite Líquido"); fig_c.update_yaxes(range=[0,60], title="IP")
        st.plotly_chart(fig_c, use_container_width=True)

# --- PESTAÑA 4: EXPORTACIÓN ---
with tabs[3]:
    st.header("Exportar a Excel")
    if st.button("📥 Generar Reporte"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            if 'df_grav_excel' in st.session_state: st.session_state.df_grav_excel.to_excel(writer, sheet_name='Gravimetria')
            if 'df_pres_excel' in st.session_state: st.session_state.df_pres_excel.to_excel(writer, sheet_name='Esfuerzos')
            if 'df_lim_excel' in st.session_state: st.session_state.df_lim_excel.to_excel(writer, sheet_name='Plasticidad')
        st.download_button("Descargar_Proyecto.xlsx", output.getvalue(), "reporte_geotecnico.xlsx")
        
