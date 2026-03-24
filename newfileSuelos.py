import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import io

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Geotecnia Suite Master v23.4", layout="wide", page_icon="🏗️")

st.sidebar.title("👨‍🏫 Panel de Control")
# Modos personalizados: Metas y Académico
modo = st.sidebar.radio("Selecciona el Modo:", ("Metas (Laboratorio)", "Académico (Base Vs=1)"))
st.sidebar.markdown("---")

st.title(f"🏗️ Geotecnia Master - Modo {modo.split()[0]}")

# --- PESTAÑAS ---
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

    st.subheader("📥 1. Entrada de Datos Iniciales")
    seleccionados = st.multiselect("Variables conocidas:", options=list(diccionario_maestro.keys()), format_func=lambda x: diccionario_maestro[x])
    
    inputs = {}
    cols_in = st.columns(3)
    for i, clave in enumerate(seleccionados):
        inputs[clave] = cols_in[i%3].number_input(f"{diccionario_maestro[clave]}", value=0.0, format="%.4f", key=f"in_{clave}")

    if st.button("🚀 Calcular Base"):
        # VALIDACIÓN: No inventar si faltan datos en Metas
        tiene_peso = any(k in inputs and inputs[k] > 0 for k in ['ws', 'wm', 'ww'])
        tiene_volumen = any(k in inputs and inputs[k] > 0 for k in ['vs', 'vt', 'vv', 'vw', 'va'])
        
        if modo == "Metas (Laboratorio)" and not (tiene_peso or tiene_volumen):
            st.error("❌ Datos insuficientes para magnitudes reales. Por favor, ingresa al menos un Peso (Ws, Wt) o un Volumen.")
            st.stop()

        d = {k: 0.0 for k in diccionario_maestro.keys()}
        if modo == "Académico (Base Vs=1)": d['vs'] = 1.0
        
        for k, v in inputs.items():
            d[k] = v / 100 if k in ['w', 'n', 's'] and v > 1.0 else v
        
        # LÓGICA DEDUCTIVA POTENCIADA (Tus 50 iteraciones con conexiones totales)
        for _ in range(50):
            # Relaciones básicas Gs, Ws, Vs
            if d['gs'] > 0 and d['ws'] > 0 and d['vs'] == 0: d['vs'] = d['ws'] / d['gs']
            if d['gs'] > 0 and d['vs'] > 0 and d['ws'] == 0: d['ws'] = d['gs'] * d['vs']
            if d['gs'] == 0 and d['ws'] > 0 and d['vs'] > 0: d['gs'] = d['ws'] / d['vs']
            
            # Humedad y Pesos de Agua
            if d['ws'] > 0 and d['w'] > 0 and d['ww'] == 0: d['ww'] = d['ws'] * d['w']
            if d['ww'] > 0: d['vw'] = d['ww']
            
            # Relaciones de vacíos (e, n, S)
            if d['e'] > 0 and d['vs'] > 0 and d['vv'] == 0: d['vv'] = d['e'] * d['vs']
            if d['vv'] > 0 and d['vs'] > 0 and d['e'] == 0: d['e'] = d['vv'] / d['vs']
            if d['vv'] > 0 and d['vs'] > 0 and d['n'] == 0: d['n'] = d['vv'] / (d['vs'] + d['vv'])
            if d['s'] > 0 and d['vv'] > 0 and d['vw'] == 0: d['vw'] = d['s'] * d['vv']
            if d['vw'] > 0 and d['vv'] > 0 and d['s'] == 0: d['s'] = d['vw'] / d['vv']
            
            # CONEXIONES DE VOLÚMENES (Solución Vt - Vs)
            if d['vt'] > 0 and d['vs'] > 0 and d['vv'] == 0: d['vv'] = d['vt'] - d['vs']
            if d['vt'] > 0 and d['vv'] > 0 and d['vs'] == 0: d['vs'] = d['vt'] - d['vv']
            if d['vs'] > 0 and d['vv'] > 0 and d['vt'] == 0: d['vt'] = d['vs'] + d['vv']
            
            # CONEXIONES DE PESOS (Wt - Ws)
            if d['wm'] > 0 and d['ws'] > 0 and d['ww'] == 0: d['ww'] = d['wm'] - d['ws']
            if d['wm'] > 0 and d['ww'] > 0 and d['ws'] == 0: d['ws'] = d['wm'] - d['ww']
            if d['ws'] > 0 and d['ww'] > 0 and d['wm'] == 0: d['wm'] = d['ws'] + d['ww']
            
            # AIRE Y SATURACIÓN
            if d['vv'] > 0 and d['vw'] > 0 and d['va'] == 0: d['va'] = d['vv'] - d['vw']
            if d['vw'] == 0 and d['ww'] > 0: d['vw'] = d['ww']
            
            # PESOS UNITARIOS
            if d['wm'] > 0 and d['vt'] > 0 and d['gh'] == 0: d['gh'] = d['wm'] / d['vt']
            if d['ws'] > 0 and d['vt'] > 0 and d['gd'] == 0: d['gd'] = d['ws'] / d['vt']

        st.session_state.base_calc = d.copy()
        st.session_state.slider_key = np.random.randint(1, 999)
        st.rerun()

    if 'base_calc' in st.session_state:
        st.markdown("---")
        c_sim, c_res = st.columns([1.2, 1.8])
        bc = st.session_state.base_calc
        sk = st.session_state.slider_key

        with c_sim:
            st.subheader("🕹️ 2. Simulador (Manda sobre la tabla)")
            
            # LÓGICA DE HERENCIA ESTRICTA
            e_def = float(bc['e'])
            w_def = float(bc['w'] * 100)
            s_def = float(bc['s'] * 100)
            
            ws_def = float(bc['ws'])
            if ws_def == 0 and bc['wm'] > 0:
                ws_def = bc['wm'] / (1 + bc['w'])
            
            # Mensajes de error dinámicos
            errores = []
            if e_def == 0: errores.append("Relación de vacíos (e)")
            if ws_def == 0: errores.append("Peso de Sólidos (Ws)")
            
            if errores:
                st.error(f"⚠️ **Faltan datos para simular:** No se pudo deducir {', '.join(errores)}. Ingresa estos valores arriba o mueve los sliders.")

            # Sliders
            e_val = st.slider("Relación de vacíos (e)", 0.0, 5.0, e_def, key=f"sl_e_{sk}")
            w_val = st.slider("Humedad (w %)", 0.0, 100.0, w_def, key=f"sl_w_{sk}") / 100
            s_val = st.slider("Grado de Saturación (S %)", 0.0, 100.0, s_def, key=f"sl_s_{sk}") / 100
            ws_val = st.slider("Peso de Sólidos (Ws)", 0.0, 2000.0, ws_def, key=f"sl_ws_{sk}")
            
            # Recálculo Final
            final = {k: 0.0 for k in diccionario_maestro.keys()}
            final['e'] = e_val
            final['ws'] = ws_val
            final['gs'] = bc['gs'] if bc['gs'] > 0 else 2.65
            
            if modo == "Académico (Base Vs=1)":
                final['vs'] = 1.0
                final['ws'] = final['gs'] * final['vs']
            else:
                final['vs'] = final['ws'] / final['gs'] if final['gs'] > 0 else 0
            
            final['vv'] = final['e'] * final['vs']
            
            if s_val > 0:
                final['s'] = s_val
                final['vw'] = final['s'] * final['vv']
                final['ww'] = final['vw']
                final['w'] = final['ww'] / final['ws'] if final['ws'] > 0 else 0
            else:
                final['w'] = w_val
                final['ww'] = final['ws'] * final['w']
                final['vw'] = final['ww']
                final['s'] = final['vw'] / final['vv'] if final['vv'] > 0 else 0

            if final['vw'] > final['vv'] and final['vv'] > 0:
                final['vw'] = final['vv']
                final['s'] = 1.0
                st.warning("⚠️ Saturación máxima alcanzada.")
            
            final['vt'] = final['vs'] + final['vv']
            final['va'] = max(0.0, final['vv'] - final['vw'])
            final['wm'] = final['ws'] + final['ww']
            final['n'] = final['vv'] / final['vt'] if final['vt'] > 0 else 0

            if st.button("🔄 Reiniciar"):
                del st.session_state.base_calc
                st.rerun()

        with c_res:
            st.subheader("📊 3. Resultados Finales")
            # Unidades kN/m3 (Asumiendo g = 9.81)
            gamma_h = (final['wm']/final['vt'])*9.81 if final['vt'] > 0 else 0
            gamma_d = (final['ws']/final['vt'])*9.81 if final['vt'] > 0 else 0
            
            res_df = pd.DataFrame({
                "Propiedad": list(diccionario_maestro.values()), 
                "Valor": [
                    f"{final['gs']:.3f}", f"{final['e']:.4f}", f"{final['n']*100:.2f}%", 
                    f"{final['w']*100:.2f}%", f"{final['s']*100:.2f}%", f"{final['wm']:.3f} g", 
                    f"{final['ws']:.3f} g", f"{final['ww']:.3f} g", f"{final['vt']:.3f} cm³", 
                    f"{final['vs']:.3f} cm³", f"{final['vv']:.3f} cm³", f"{final['vw']:.3f} cm³", 
                    f"{final['va']:.3f} cm³", f"{gamma_h:.2f} kN/m³", f"{gamma_d:.2f} kN/m³"
                ]
            })
            st.table(res_df)
            st.session_state.df_excel = res_df
            
            fig = go.Figure(data=[
                go.Bar(name='Sólidos', x=['Fases'], y=[final['vs']], marker_color='#7E5109', text=[f"Vs:{final['vs']:.2f}"]),
                go.Bar(name='Agua', x=['Fases'], y=[final['vw']], marker_color='#3498DB', text=[f"Vw:{final['vw']:.2f}"]),
                go.Bar(name='Aire', x=['Fases'], y=[final['va']], marker_color='#BDC3C7', text=[f"Va:{final['va']:.2f}"])
            ])
            fig.update_layout(barmode='stack', height=350); st.plotly_chart(fig, use_container_width=True)

# --- RESTO DE PESTAÑAS ---
with tabs[1]:
    st.header("🗂️ Esfuerzos Geostáticos")
    cp1, cp2 = st.columns([1, 2])
    with cp1:
        n_est = st.number_input("Número de Estratos", 1, 5, 2)
        nf = st.number_input("NF (m)", 0.0, 50.0, 2.0)
        estratos = []
        for i in range(int(n_est)):
            h = st.number_input(f"H{i+1}", 0.1, 20.0, 3.0, key=f"pres_h_{i}")
            g = st.number_input(f"γ{i+1}", 1.0, 22.0, 18.0, key=f"pres_g_{i}")
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
        u_p = (z - nf) * 9.81 if z > nf else 0
        st_l.append(s_acu); u_l.append(u_p); se_l.append(s_acu - u_p)

    with cp2:
        df_p = pd.DataFrame({"Z (m)": z_pts, "σ Total": st_l, "u": u_l, "σ' Ef.": se_l})
        st.dataframe(df_p)
        fig_p = go.Figure()
        fig_p.add_trace(go.Scatter(x=st_l, y=z_pts, name='Total', line=dict(color='brown')))
        fig_p.add_trace(go.Scatter(x=u_l, y=z_pts, name='u', line=dict(color='blue', dash='dash')))
        fig_p.add_trace(go.Scatter(x=se_l, y=z_pts, name='Efectivo', fill='tonextx', line=dict(color='green')))
        fig_p.update_yaxes(autorange="reversed"); st.plotly_chart(fig_p)

with tabs[2]:
    st.header("📈 Plasticidad")
    cl1, cl2 = st.columns([1, 2])
    with cl1:
        ll = st.number_input("LL", 0, 120, 40); lp = st.number_input("LP", 0, 100, 20)
        ip = ll - lp
        st.metric("IP", ip)
        st.info("Clasificación SUCS automática en desarrollo...")
    with cl2:
        xv = np.linspace(0, 100, 100)
        fig_c = go.Figure()
        fig_c.add_trace(go.Scatter(x=xv, y=0.73*(xv-20), name='Línea A', line=dict(color='black')))
        fig_c.add_trace(go.Scatter(x=[ll], y=[ip], mode='markers', marker=dict(size=12, color='red')))
        fig_c.update_xaxes(title="LL"); fig_c.update_yaxes(title="IP"); st.plotly_chart(fig_c)

with tabs[3]:
    st.header("📥 Descargar Reporte")
    if st.button("📊 Generar Excel"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            if 'df_excel' in st.session_state: st.session_state.df_excel.to_excel(writer, sheet_name='Resultados')
        st.download_button("Descargar_Reporte.xlsx", output.getvalue(), "Reporte_Geotecnia.xlsx")
        
