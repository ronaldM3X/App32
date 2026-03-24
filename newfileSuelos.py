import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import io

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Geotecnia Suite Master v23.0", layout="wide", page_icon="🏗️")

st.sidebar.title("👨‍🏫 Panel de Control")
modo = st.sidebar.radio("Selecciona el Modo:", ("Metas (Laboratorio)", "Académico (Base Vs=1)"))
st.sidebar.markdown("---")

st.title(f"🏗️ Geotecnia Master - Modo {modo.split()[0]}")
st.markdown("---")

tabs = st.tabs(["🧩 Gravimetría & Fases", "🗂️ Perfil de Presiones", "📈 Plasticidad & SUCS", "📥 Reporte Final"])

# --- PESTAÑA 1: GRAVIMETRÍA ---
with tabs[0]:
    # Diccionario con nombres largos para que sea fácil de leer (TDAH friendly)
    diccionario_maestro = {
        "gs": "Gs (Gravedad específica)", "e": "e (Relación de vacíos)", "n": "n (Porosidad %)",
        "w": "w (Contenido de humedad %)", "s": "S (Grado de saturación %)", "wm": "Wt (Peso total muestra)",
        "ws": "Ws (Peso de los sólidos)", "ww": "Ww (Peso del agua)", "vt": "Vt (Volumen total)",
        "vs": "Vs (Volumen sólidos)", "vv": "Vv (Volumen vacíos)", "vw": "Vw (Volumen agua)",
        "va": "Va (Volumen aire)", "gh": "γ (Peso unitario húmedo)", "gd": "γd (Peso unitario seco)"
    }

    st.subheader("📥 Entrada de Datos")
    seleccionados = st.multiselect("Selecciona las variables conocidas:", options=list(diccionario_maestro.keys()), format_func=lambda x: diccionario_maestro[x])
    
    inputs = {}
    cols_in = st.columns(3)
    for i, clave in enumerate(seleccionados):
        inputs[clave] = cols_in[i%3].number_input(f"{diccionario_maestro[clave]}", value=0.0, format="%.4f", key=f"main_in_{clave}")

    if st.button("🚀 Calcular Relaciones"):
        d = {k: 0.0 for k in diccionario_maestro.keys()}
        if modo == "Académico (Base Vs=1)": d['vs'] = 1.0
        for k, v in inputs.items():
            # Manejo de porcentajes
            d[k] = v / 100 if k in ['w', 'n', 's'] and v > 1.0 else v
        
        # MOTOR DE CÁLCULO
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
            if d['vs'] > 0 and d['vv'] > 0: d['vt'] = d['vs'] + d['vv']
            if d['ws'] > 0 and d['ww'] > 0: d['wm'] = d['ws'] + d['ww']
            d['va'] = max(0.0, d['vv'] - d['vw'])

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
            # Restauramos el slider de Humedad (w) y Relación de vacíos (e)
            ld['e'] = st.slider("Ajustar Relación de Vacíos (e)", 0.01, 5.0, float(ld['e']) if ld['e'] > 0 else 0.6, key=f"e_{k}")
            ld['w'] = st.slider("Ajustar Humedad (w %)", 0.0, 100.0, float(ld['w']*100) if ld['w'] > 0 else 15.0, key=f"w_{k}") / 100
            ld['ws'] = st.slider("Ajustar Peso de Sólidos (Ws g)", 0.1, 15.0, float(ld['ws']) if ld['ws'] > 0 else 2.65, key=f"ws_{k}")
            
            # RE-CÁLCULO FÍSICO (Respetando w y e)
            ld['ww'] = ld['ws'] * ld['w']
            ld['vw'] = ld['ww'] # Identidad Ww = Vw
            vv_teorico = ld['e'] * ld['vs']
            
            # Si el agua supera los vacíos, el suelo se expande (S=100%)
            if ld['vw'] > vv_teorico:
                ld['vv'] = ld['vw']
                ld['s'] = 1.0
                st.warning("⚠️ Suelo Saturado por exceso de humedad.")
            else:
                ld['vv'] = vv_teorico
                ld['s'] = ld['vw'] / ld['vv'] if ld['vv'] > 0 else 0
            
            ld['vt'] = ld['vs'] + ld['vv'] # FISICA: Vt siempre es la suma real
            ld['va'] = max(0.0, ld['vv'] - ld['vw'])
            ld['wm'] = ld['ws'] + ld['ww']
            if ld['vs'] > 0: ld['gs'] = ld['ws'] / ld['vs']

        with c_res:
            st.subheader("📊 Tabla de Resultados")
            safe_e = f"{ld['vv']/ld['vs']:.4f}" if ld['vs'] > 0 else "0.0000"
            safe_n = f"{(ld['vv']/ld['vt'])*100:.2f}%" if ld['vt'] > 0 else "0.00%"
            
            res_df = pd.DataFrame({"Propiedad": list(diccionario_maestro.values()), 
                                  "Valor": [f"{ld['gs']:.3f}", safe_e, safe_n, f"{ld['w']*100:.2f}%", f"{ld['s']*100:.2f}%", 
                                           f"{ld['wm']:.3f} g", f"{ld['ws']:.3f} g", f"{ld['ww']:.3f} g", f"{ld['vt']:.3f} cm³", 
                                           f"{ld['vs']:.3f} cm³", f"{ld['vv']:.3f} cm³", f"{ld['vw']:.3f} cm³", f"{ld['va']:.3f} cm³", 
                                           f"{(ld['wm']/ld['vt'])*9.81:.2f} kN/m³", f"{(ld['ws']/ld['vt'])*9.81:.2f} kN/m³"]})
            st.table(res_df)
            st.session_state.df_grav_excel = res_df
            
            fig = go.Figure(data=[go.Bar(name='Sólidos', x=['Fases'], y=[ld['vs']], marker_color='#7E5109', text=[f"{ld['vs']:.2f}"]),
                                  go.Bar(name='Agua', x=['Fases'], y=[ld['vw']], marker_color='#3498DB', text=[f"{ld['vw']:.2f}"]),
                                  go.Bar(name='Aire', x=['Fases'], y=[ld['va']], marker_color='#BDC3C7', text=[f"{ld['va']:.2f}"])])
            fig.update_layout(barmode='stack', height=300); st.plotly_chart(fig, use_container_width=True)

# --- PESTAÑA 2: PRESIONES ---
with tabs[1]:
    st.header("🗂️ Perfil de Esfuerzos")
    cp1, cp2 = st.columns([1, 2])
    with cp1:
        n_est = st.number_input("Estratos", 1, 10, 2)
        nf = st.number_input("NF (m)", 0.0, 100.0, 2.0)
        estratos = []
        for i in range(int(n_est)):
            h = st.number_input(f"H{i+1}", 0.1, 50.0, 3.0, key=f"hp_{i}")
            g = st.number_input(f"γ{i+1}", 1.0, 25.0, 18.0, key=f"gp_{i}")
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
        df_p = pd.DataFrame({"Z (m)": z_pts, "σ Total": st_l, "u": u_l, "σ' Ef.": se_l})
        st.dataframe(df_p, use_container_width=True)
        st.session_state.df_pres_excel = df_p
        fig_p = go.Figure()
        fig_p.add_trace(go.Scatter(x=st_l, y=z_pts, name='Total', line=dict(color='brown')))
        fig_p.add_trace(go.Scatter(x=u_l, y=z_pts, name='u', line=dict(color='blue')))
        fig_p.add_trace(go.Scatter(x=se_l, y=z_pts, name='Efectivo', fill='tonextx', line=dict(color='green')))
        fig_p.update_yaxes(autorange="reversed"); st.plotly_chart(fig_p, use_container_width=True)

# --- PESTAÑA 3: PLASTICIDAD ---
with tabs[2]:
    st.header("📈 SUCS")
    cl1, cl2 = st.columns([1, 2])
    with cl1:
        ll = st.number_input("LL", 0, 150, 40); lp = st.number_input("LP", 0, 100, 20); ip = ll - lp
        st.metric("IP", ip)
        lin_a = 0.73 * (ll - 20)
        sucs = "CH/MH" if ll >= 50 else "CL/ML"
        st.success(f"SUCS: {sucs}")
        st.session_state.df_lim_excel = pd.DataFrame({"Dato": ["LL", "LP", "IP"], "Valor": [ll, lp, ip]})
    with cl2:
        fig_c = go.Figure()
        xv = np.linspace(0, 100, 100)
        fig_c.add_trace(go.Scatter(x=xv, y=0.73*(xv-20), name='Línea A', line=dict(color='black')))
        fig_c.add_trace(go.Scatter(x=[ll], y=[ip], mode='markers', marker=dict(size=12, color='red')))
        st.plotly_chart(fig_c, use_container_width=True)

# --- PESTAÑA 4: REPORTE ---
with tabs[3]:
    st.header("📥 Descargar")
    if st.button("📊 Generar Excel"):
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
            if 'df_grav_excel' in st.session_state: st.session_state.df_grav_excel.to_excel(writer, sheet_name='Gravimetria')
            if 'df_pres_excel' in st.session_state: st.session_state.df_pres_excel.to_excel(writer, sheet_name='Presiones')
            if 'df_lim_excel' in st.session_state: st.session_state.df_lim_excel.to_excel(writer, sheet_name='Plasticidad')
        st.download_button("Descargar_Reporte.xlsx", out.getvalue(), "Reporte_Geotecnia.xlsx")
