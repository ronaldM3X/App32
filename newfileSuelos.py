import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import io

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Geotecnia Suite Master v18.0", layout="wide", page_icon="🏗️")

# Estilo de acompañamiento
st.sidebar.title("👨‍🏫 Panel de Control")
st.sidebar.info("Modos actualizados: 'Metas' para datos reales y 'Académico' para teoría (Vs=1). ¡Cero valores por defecto!")

modo = st.sidebar.radio("Selecciona el Modo:", ("Metas (Laboratorio)", "Académico (Base Vs=1)"))

st.title(f"🏗️ Geotecnia Master - Modo {modo.split()[0]}")
st.markdown("---")

tabs = st.tabs(["🧩 Gravimetría & Simulación", "🗂️ Perfil de Presiones", "📈 Plasticidad & SUCS", "📥 Reporte Final"])

# --- PESTAÑA 1: GRAVIMETRÍA ---
with tabs[0]:
    diccionario_maestro = {
        "gs": "Gs (Gravedad específica)", "e": "e (Relación de vacíos)", "n": "n (Porosidad %)",
        "w": "w (Contenido de humedad %)", "s": "S (Grado de saturación %)", "wm": "Peso total muestra (Wt)",
        "ws": "Peso de los sólidos (Ws)", "ww": "Peso del agua (Ww)", "vt": "Vt (Volumen total)",
        "vs": "Vs (Volumen sólidos)", "vv": "Vv (Volumen vacíos)", "vw": "Vw (Volumen agua)",
        "va": "Va (Volumen aire)", "gh": "γ (Peso unitario húmedo)", "gd": "γd (Peso unitario seco)"
    }

    st.subheader("📥 Entrada de Datos")
    seleccionados = st.multiselect("Variables que conoces:", options=list(diccionario_maestro.keys()), format_func=lambda x: diccionario_maestro[x])
    
    inputs = {}
    cols_in = st.columns(3)
    for i, clave in enumerate(seleccionados):
        inputs[clave] = cols_in[i%3].number_input(f"{diccionario_maestro[clave]}", value=0.0, format="%.4f", key=f"in_{clave}")

    if st.button("🚀 Ejecutar Cálculo"):
        d = {k: 0.0 for k in diccionario_maestro.keys()}
        if modo == "Académico (Base Vs=1)":
            d['vs'] = 1.0
        
        for k, v in inputs.items():
            d[k] = v / 100 if k in ['w', 'n', 's'] and v > 1.0 else v
        
        # Motor de cálculo iterativo
        for _ in range(60):
            if d['gs'] > 0 and d['vs'] > 0: d['ws'] = d['gs'] * d['vs']
            if d['ws'] > 0 and d['gs'] > 0: d['vs'] = d['ws'] / d['gs']
            if d['ws'] > 0 and d['vs'] > 0: d['gs'] = d['ws'] / d['vs']
            if d['ws'] > 0 and d['w'] > 0: d['ww'] = d['ws'] * d['w']
            if d['ww'] > 0 and d['ws'] > 0: d['w'] = d['ww'] / d['ws']
            if d['wm'] > 0 and d['ws'] > 0: d['ww'] = d['wm'] - d['ws']
            if d['ws'] > 0 and d['ww'] > 0: d['wm'] = d['ws'] + d['ww']
            if d['ww'] > 0: d['vw'] = d['ww'] / 1.0
            if d['vw'] > 0: d['ww'] = d['vw'] * 1.0
            if d['vt'] > 0 and d['vs'] > 0: d['vv'] = d['vt'] - d['vs']
            if d['vs'] > 0 and d['vv'] > 0: d['vt'] = d['vs'] + d['vv']
            if d['vs'] > 0 and d['vv'] > 0: d['e'] = d['vv'] / d['vs']
            if d['e'] > 0: d['n'] = d['e'] / (1 + d['e'])
            if d['n'] > 0: d['e'] = d['n'] / (1 - d['n'])
            if d['vv'] > 0 and d['vw'] > 0: d['s'] = d['vw'] / d['vv']
            if d['vv'] > 0 and d['s'] > 0: d['vw'] = d['vv'] * d['s']
            if d['vv'] > 0 and d['vw'] > 0: d['va'] = max(0.0, d['vv'] - d['vw'])

        st.session_state.base_data = d.copy()
        st.session_state.live_data = d.copy()
        st.success("¡Cálculo Geotécnico finalizado!")

    if 'live_data' in st.session_state:
        ld = st.session_state.live_data
        st.markdown("---")
        c_sim, c_res = st.columns([1.3, 1.7])
        
        with c_sim:
            st.subheader("🕹️ Simulador Dinámico")
            # AJUSTE CRÍTICO: El slider ahora toma el valor exacto del cálculo
            # Usamos un valor mínimo de 0.001 para que el slider no explote si e es 0
            val_e = float(ld['e']) if ld['e'] > 0 else 0.001
            ld['e'] = st.slider("Ajustar e", 0.001, 5.0, val_e)
            
            val_w = float(ld['w']) if ld['w'] > 0 else 0.0
            ld['w'] = st.slider("Ajustar w (%)", 0.0, 100.0, val_w * 100) / 100
            
            val_wm = float(ld['wm']) if ld['wm'] > 0 else 0.0
            ld['wm'] = st.slider("Ajustar Wt (g)", 0.0, max(5000.0, val_wm*2), val_wm)
            
            # Recálculos en vivo
            ld['vv'] = ld['vs'] * ld['e']
            ld['vt'] = ld['vs'] + ld['vv']
            ld['ww'] = max(0.0, ld['wm'] - ld['ws'])
            ld['vw'] = ld['ww'] / 1.0
            if ld['ws'] > 0: ld['w'] = ld['ww'] / ld['ws']
            if ld['vv'] > 0: ld['s'] = ld['vw'] / ld['vv']
            ld['va'] = max(0.0, ld['vv'] - ld['vw'])
            
            st.session_state.live_data = ld
            if st.button("🔄 Resetear a Original"):
                st.session_state.live_data = st.session_state.base_data.copy()
                st.rerun()

        with c_res:
            gh = (ld['wm']/ld['vt'])*9.81 if ld['vt'] > 0 else 0
            gd = (ld['ws']/ld['vt'])*9.81 if ld['vt'] > 0 else 0
            res_df = pd.DataFrame({"Propiedad": list(diccionario_maestro.values()), 
                                  "Valor": [f"{ld['gs']:.2f}", f"{ld['e']:.4f}", f"{ld['n']*100:.2f}%", f"{ld['w']*100:.2f}%", f"{ld['s']*100:.2f}%", 
                                           f"{ld['wm']:.2f}g", f"{ld['ws']:.2f}g", f"{ld['ww']:.2f}g", f"{ld['vt']:.2f}cm³", f"{ld['vs']:.2f}cm³", 
                                           f"{ld['vv']:.2f}cm³", f"{ld['vw']:.2f}cm³", f"{ld['va']:.2f}cm³", f"{gh:.2f} kN/m³", f"{gd:.2f} kN/m³"]})
            st.table(res_df)
            st.session_state.df_grav_excel = res_df
            
            fig = go.Figure(data=[go.Bar(name='Sólidos', x=['Fases'], y=[ld['vs']], marker_color='#7E5109'),
                                  go.Bar(name='Agua', x=['Fases'], y=[ld['vw']], marker_color='#3498DB'),
                                  go.Bar(name='Aire', x=['Fases'], y=[ld['va']], marker_color='#BDC3C7')])
            fig.update_layout(barmode='stack', height=350, margin=dict(t=0,b=0)); st.plotly_chart(fig, use_container_width=True)

# --- PESTAÑAS RESTANTES (IGUALES Y COMPLETAS) ---
with tabs[1]: # Presiones
    st.header("Esfuerzos Geostáticos")
    col_p1, col_p2 = st.columns([1, 2])
    with col_p1:
        n_estratos = st.number_input("Estratos", 1, 10, 1)
        nf = st.number_input("NF (m)", 0.0, 100.0, 0.0)
        datos_estratos = []
        for i in range(int(n_estratos)):
            h = st.number_input(f"H {i+1}", 0.0, 50.0, 0.0, key=f"z_h{i}")
            g = st.number_input(f"γ {i+1}", 0.0, 25.0, 0.0, key=f"z_g{i}")
            datos_estratos.append({'h': h, 'g': g})
    puntos = sorted(list(set([0.0, nf] + [sum(e['h'] for e in datos_estratos[:i+1]) for i in range(len(datos_estratos))])))
    puntos = [p for p in puntos if p <= sum(e['h'] for e in datos_estratos)]
    z_l, st_l, u_l, se_l = [], [], [], []
    s_acu = 0
    for i in range(len(puntos)):
        z = puntos[i]
        if i > 0:
            dz = z - puntos[i-1]
            z_t = 0
            for e in datos_estratos:
                if z <= z_t + e['h'] + 0.01:
                    s_acu += dz * e['g']; break
                z_t += e['h']
        u = (z - nf) * 9.81 if z > nf else 0
        z_l.append(z); st_l.append(round(s_acu,2)); u_l.append(round(u,2)); se_l.append(round(s_acu-u,2))
    with col_p2:
        df_p = pd.DataFrame({"Z (m)": z_l, "σ Total": st_l, "u": u_l, "σ' Ef.": se_l})
        st.dataframe(df_p, use_container_width=True)
        st.session_state.df_pres_excel = df_p
        fig_p = go.Figure()
        fig_p.add_trace(go.Scatter(x=st_l, y=z_l, name='Total', line=dict(color='brown')))
        fig_p.add_trace(go.Scatter(x=u_l, y=z_l, name='Neutro', line=dict(color='blue', dash='dash')))
        fig_p.add_trace(go.Scatter(x=se_l, y=z_l, name='Efectivo', fill='tonextx', line=dict(color='green')))
        fig_p.update_yaxes(autorange="reversed", title="Z (m)"); st.plotly_chart(fig_p, use_container_width=True)

with tabs[2]: # Plasticidad
    st.header("SUCS")
    cl1, cl2 = st.columns([1, 2])
    with cl1:
        ll = st.number_input("LL", 0, 150, 0); lp = st.number_input("LP", 0, 100, 0); ip = ll - lp
        st.metric("IP", ip)
        lin_a = 0.73 * (ll - 20)
        if ll == 0: s_t = "Esperando..."
        elif ll < 50:
            if ip > 7 and ip >= lin_a: s_t = "CL"
            elif ip < 4 or ip < lin_a: s_t = "ML"
            else: s_t = "CL-ML"
        else:
            if ip >= lin_a: s_t = "CH"
            else: s_t = "MH"
        st.subheader(f"Tipo: {s_t}")
        st.session_state.df_lim_excel = pd.DataFrame({"LL": [ll], "LP": [lp], "IP": [ip], "SUCS": [s_t]})
    with cl2:
        fig_c = go.Figure()
        x_v = np.linspace(0,100,100)
        fig_c.add_trace(go.Scatter(x=x_v, y=0.73*(x_v-20), name='Línea A', line=dict(color='black')))
        if ll > 0: fig_c.add_trace(go.Scatter(x=[ll], y=[ip], mode='markers', marker=dict(size=15, color='red')))
        fig_c.update_xaxes(title="LL", range=[0,100]); fig_c.update_yaxes(title="IP", range=[0,60])
        st.plotly_chart(fig_c, use_container_width=True)

with tabs[3]: # Reporte
    st.header("Finalizar")
    if st.button("📥 Generar Excel Final"):
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
            if 'df_grav_excel' in st.session_state: st.session_state.df_grav_excel.to_excel(writer, sheet_name='Gravimetria')
            if 'df_pres_excel' in st.session_state: st.session_state.df_pres_excel.to_excel(writer, sheet_name='Presiones')
            if 'df_lim_excel' in st.session_state: st.session_state.df_lim_excel.to_excel(writer, sheet_name='Plasticidad')
        st.download_button("Descargar_Geotecnia.xlsx", out.getvalue(), "Reporte_Geotecnia_Suite.xlsx")
