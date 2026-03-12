import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import io

# 1. CONFIGURACIÓN E INYECCIÓN DE ESTILO
st.set_page_config(page_title="Geotecnia Suite Master v8.5", layout="wide", page_icon="🏗️")
st.title("🏗️ Geotecnia Master: Suite Integral v8.5")
st.markdown("---")

tabs = st.tabs(["🧩 Gravimetría Pro", "🗂️ Perfil de Presiones", "📈 Plasticidad & USCS", "📥 Reporte Final"])

# --- PESTAÑA 1: GRAVIMETRÍA ---
with tabs[0]:
    st.header("Propiedades Físicas con Escudo de Integridad")
    diccionario_maestro = {
        "gs": "Gs (Gravedad específica)", "e": "e (Relación de vacíos)", "n": "n (Porosidad %)",
        "w": "w (Contenido de humedad %)", "s": "S (Grado de saturación %)", "wm": "Wm (Peso húmedo)",
        "ws": "Ws (Peso seco)", "ww": "Ww (Peso del agua)", "vt": "Vt (Volumen total)",
        "vs": "Vs (Volumen sólidos)", "vv": "Vv (Volumen vacíos)", "vw": "Vw (Volumen agua)",
        "va": "Va (Volumen aire)", "gh": "γ (Peso unitario húmedo)", "gd": "γd (Peso unitario seco)"
    }
    seleccionados = st.multiselect("Datos de entrada:", options=list(diccionario_maestro.keys()), format_func=lambda x: diccionario_maestro[x])
    inputs = {}
    if seleccionados:
        cols = st.columns(3)
        for i, clave in enumerate(seleccionados):
            inputs[clave] = cols[i % 3].number_input(f"Ingresa {clave}", value=0.0, format="%.3f", key=f"inp_{clave}")

    if st.button("🚀 Calcular y Validar Gravimetría"):
        d = {k: inputs.get(k, 0.0) for k in diccionario_maestro.keys()}
        for pct in ['w', 'n', 's']:
            if d[pct] > 1.0: d[pct] /= 100
        
        errores = []
        if d['s'] > 1.0: errores.append("La saturación (S) no puede exceder el 100%.")
        if d['n'] >= 1.0: errores.append("La porosidad (n) no puede ser >= 100%.")
        if errores:
            for err in errores: st.error(f"🛑 {err}")
        else:
            for _ in range(20):
                if d['ws'] > 0 and d['gs'] > 0: d['vs'] = d['ws'] / (d['gs'] * 1.0)
                if d['wm'] > 0 and d['ws'] > 0: d['ww'] = d['wm'] - d['ws']
                if d['vt'] > 0 and d['vs'] > 0: d['vv'] = d['vt'] - d['vs']
                if d['vv'] > 0 and d['vs'] > 0: d['e'] = d['vv'] / d['vs']
                if d['e'] > 0: d['n'] = d['e'] / (1 + d['e'])
                if d['gs'] > 0 and d['w'] > 0 and d['e'] > 0: d['s'] = (d['w'] * d['gs']) / d['e']
                if d['vv'] > 0 and d['vw'] > 0: d['va'] = d['vv'] - d['vw']
            st.session_state.v8_base = d
            st.success("Cálculos verificados.")

    if 'v8_base' in st.session_state:
        db = st.session_state.v8_base
        c_ctrl, c_disp = st.columns([1, 2.5])
        with c_ctrl:
            st.subheader("🕹️ Simulador")
            var_m = st.radio("Ajustar:", ["Humedad (w)", "Saturación (S)"])
            if var_m == "Humedad (w)":
                w_max = (1.0 * db['e']) / db['gs']
                w_sim = st.slider("Humedad (%)", 0.0, float(w_max*100*1.2), float(db['w']*100)) / 100
                s_sim = (w_sim * db['gs']) / db['e']
                if s_sim > 1.0: st.warning("⚠️ Suelo saturado"); s_sim = 1.0
            else:
                s_sim = st.slider("Saturación (%)", 0.0, 100.0, float(db['s']*100)) / 100
                w_sim = (s_sim * db['e']) / db['gs']
            
            vs_v = db['ws'] / (db['gs'] * 1.0); vv_v = vs_v * db['e']
            vw_v = vv_v * s_sim; va_v = max(0.0, vv_v - vw_v)

        with c_disp:
            res_v = pd.DataFrame({"Propiedad": list(diccionario_maestro.values()), 
                                 "Valor": [f"{db['gs']:.2f}", f"{db['e']:.3f}", f"{db['n']*100:.1f}%", f"{w_sim*100:.2f}%", f"{s_sim*100:.1f}%", 
                                          f"{db['ws']+vw_v:.2f}g", f"{db['ws']:.2f}g", f"{vw_v:.2f}g", f"{vs_v+vv_v:.2f}cm³", f"{vs_v:.2f}cm³", 
                                          f"{vv_v:.2f}cm³", f"{vw_v:.2f}cm³", f"{va_v:.2f}cm³", f"{(db['ws']+vw_v)/(vs_v+vv_v)*9.81:.2f}", f"{db['ws']/(vs_v+vv_v)*9.81:.2f}"]})
            st.table(res_v)
            st.session_state.df_grav_excel = res_v
            fig = go.Figure(data=[go.Bar(name='Sólidos', x=['Fases'], y=[vs_v], marker_color='#7E5109'),
                                  go.Bar(name='Agua', x=['Fases'], y=[vw_v], marker_color='#3498DB'),
                                  go.Bar(name='Aire', x=['Fases'], y=[va_v], marker_color='#BDC3C7')])
            fig.update_layout(barmode='stack', height=300); st.plotly_chart(fig, use_container_width=True)

# --- PESTAÑA 2: PERFIL DE PRESIONES ---
with tabs[1]:
    st.header("Análisis de Esfuerzos Geostáticos")
    col_in, col_gr = st.columns([1, 2])
    with col_in:
        n_est = st.number_input("Estratos", 1, 10, 2); nf = st.number_input("Nivel Freático (m)", 0.0, 100.0, 2.0)
        est = []
        for i in range(int(n_est)):
            h = st.number_input(f"H {i+1}", 0.1, 50.0, 3.0, key=f"hp{i}")
            g = st.number_input(f"γ {i+1}", 10.0, 25.0, 18.0, key=f"gp{i}")
            est.append({'h': h, 'g': g})

    z_plot, stot, u_p, sef = [0.0], [0.0], [0.0], [0.0]
    z_acum, s_acum = 0.0, 0.0
    # Lógica de puntos críticos (Estratos + NF)
    pts = [0.0, nf] + [sum(e['h'] for e in est[:i+1]) for i in range(len(est))]
    pts = sorted(list(set([p for p in pts if p <= sum(e['h'] for e in est)])))
    
    z_final, s_final, u_final, ef_final = [], [], [], []
    s_curr = 0
    for i in range(len(pts)):
        zp = pts[i]
        if i > 0:
            dz = zp - pts[i-1]
            # Buscar gamma del estrato correspondiente
            z_temp = 0
            for e in est:
                if zp <= z_temp + e['h'] + 0.01:
                    s_curr += dz * e['g']
                    break
                z_temp += e['h']
        u_curr = (zp - nf) * 9.81 if zp > nf else 0
        z_final.append(zp); s_final.append(s_curr); u_final.append(u_curr); ef_final.append(s_curr - u_curr)

    with col_gr:
        df_p = pd.DataFrame({"Z(m)": z_final, "Total": s_final, "u": u_final, "Efectivo": ef_final})
        st.subheader("📊 Tabla de Cálculos")
        st.dataframe(df_p, use_container_width=True)
        st.session_state.df_pres_excel = df_p
        fig_p = go.Figure()
        fig_p.add_trace(go.Scatter(x=s_final, y=z_final, name='σ Total', line=dict(color='brown')))
        fig_p.add_trace(go.Scatter(x=u_final, y=z_final, name='u', line=dict(color='blue')))
        fig_p.add_trace(go.Scatter(x=ef_final, y=z_final, name="σ' Ef.", fill='tonextx', line=dict(color='green')))
        fig_p.update_yaxes(autorange="reversed"); st.plotly_chart(fig_p, use_container_width=True)

# --- PESTAÑA 3: PLASTICIDAD ---
with tabs[2]:
    st.header("Carta de Plasticidad")
    ll = st.number_input("LL", 0, 120, 45); lp = st.number_input("LP", 0, 100, 20); ip = ll - lp
    st.metric("IP", ip)
    fig_c = go.Figure(); x_c = np.linspace(0,100,100)
    fig_c.add_trace(go.Scatter(x=x_c, y=0.73*(x_c-20), name='Línea A', line=dict(color='black')))
    fig_c.add_trace(go.Scatter(x=[ll], y=[ip], mode='markers', marker=dict(size=15, color='red')))
    st.plotly_chart(fig_c, use_container_width=True)
    st.session_state.df_lim_excel = pd.DataFrame({"LL": [ll], "LP": [lp], "IP": [ip]})

# --- PESTAÑA 4: EXPORTAR ---
with tabs[3]:
    st.header("Generar Reporte Excel")
    if st.button("📥 Preparar Descarga"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            if 'df_grav_excel' in st.session_state: st.session_state.df_grav_excel.to_excel(writer, sheet_name='Gravimetria')
            if 'df_pres_excel' in st.session_state: st.session_state.df_pres_excel.to_excel(writer, sheet_name='Presiones')
            if 'df_lim_excel' in st.session_state: st.session_state.df_lim_excel.to_excel(writer, sheet_name='Plasticidad')
        st.download_button("Descargar_Reporte_Geotecnico.xlsx", output.getvalue(), "reporte_geotecnico.xlsx")
                
