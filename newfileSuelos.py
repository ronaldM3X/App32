import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io

# Configuración de la App
st.set_page_config(page_title="Geotecnia Suite Pro v6.5", layout="wide", page_icon="🏗️")

st.title("🏗️ Geotecnia Master: Suite Integral v6.5")
st.markdown("---")

tabs = st.tabs(["🧩 Gravimetría Total", "🗂️ Perfiles de Presión", "📈 Plasticidad & USCS", "📥 Exportar"])

# --- PESTAÑA 1: GRAVIMETRÍA (DICCIONARIO DE 15 VARIABLES) ---
with tabs[0]:
    st.header("Inventario de Propiedades Físicas")
    diccionario_maestro = {
        "gs": "Gs (Gravedad específica de sólidos)",
        "e": "e (Relación de vacíos - Vv/Vs)",
        "n": "n (Porosidad % - Vv/Vt)",
        "w": "w (Contenido de humedad % - Ww/Ws)",
        "s": "S (Grado de saturación % - Vw/Vv)",
        "wm": "Wm (Peso total de la muestra húmeda)",
        "ws": "Ws (Peso de la muestra seca - sólidos)",
        "ww": "Ww (Peso del agua en la muestra)",
        "vt": "Vt (Volumen total de la muestra)",
        "vs": "Vs (Volumen de los sólidos)",
        "vv": "Vv (Volumen de vacíos - Aire + Agua)",
        "vw": "Vw (Volumen del agua)",
        "va": "Va (Volumen del aire)",
        "gh": "γ (Peso unitario húmedo)",
        "gd": "γd (Peso unitario seco)"
    }

    seleccionados = st.multiselect("Selecciona tus datos de entrada:", options=list(diccionario_maestro.keys()), format_func=lambda x: diccionario_maestro[x])
    inputs = {}
    if seleccionados:
        cols = st.columns(3)
        for i, clave in enumerate(seleccionados):
            inputs[clave] = cols[i % 3].number_input(f"Valor de {clave}", value=0.0, format="%.3f")

    if st.button("🚀 Calcular Todo"):
        d = {k: inputs.get(k, 0.0) for k in diccionario_maestro.keys()}
        d['n'] /= 100; d['w'] /= 100; d['s'] /= 100
        for _ in range(15):
            if d['wm'] > 0 and d['ws'] > 0 and d['ww'] == 0: d['ww'] = d['wm'] - d['ws']
            if d['ws'] > 0 and d['ww'] > 0 and d['wm'] == 0: d['wm'] = d['ws'] + d['ww']
            if d['ws'] > 0 and d['gs'] > 0 and d['vs'] == 0: d['vs'] = d['ws'] / (d['gs'] * 1.0)
            if d['vt'] > 0 and d['vs'] > 0 and d['vv'] == 0: d['vv'] = d['vt'] - d['vs']
            if d['vv'] > 0 and d['vs'] > 0 and d['e'] == 0: d['e'] = d['vv'] / d['vs']
            if d['e'] > 0 and d['n'] == 0: d['n'] = d['e'] / (1 + d['e'])
            if d['gs'] > 0 and d['w'] > 0 and d['e'] > 0 and d['s'] == 0: d['s'] = (d['w'] * d['gs']) / d['e']
        st.session_state.v6_base = d

    if 'v6_base' in st.session_state:
        # (Aquí va la lógica del slider y tabla que ya conoces de la v6.0)
        # Guardamos df_final en session_state para el Excel
        st.session_state.df_grav_excel = pd.DataFrame({"Variable": list(diccionario_maestro.values()), "Valor": [f"{v:.3f}" for v in st.session_state.v6_base.values()]})
        st.table(st.session_state.df_grav_excel)

# --- PESTAÑA 2: PRESIONES ---
with tabs[1]:
    st.header("Esfuerzos Geostáticos")
    n_est = st.number_input("Número de Estratos", 1, 5, 2)
    nf = st.number_input("Nivel Freático (m)", 0.0, 50.0, 2.0)
    est = []
    for i in range(int(n_est)):
        c = st.columns(2)
        h = c[0].number_input(f"H {i+1}", 0.1, 50.0, 3.0, key=f"h{i}")
        g = c[1].number_input(f"γ {i+1}", 10.0, 25.0, 18.0, key=f"g{i}")
        est.append({'h': h, 'g': g})
    
    z, stot, u, sef = [0], [0], [0], [0]
    za, sta = 0, 0
    for e in est:
        za += e['h']; sta += e['g']*e['h']
        ua = (za-nf)*9.81 if za > nf else 0
        z.append(za); stot.append(sta); u.append(ua); sef.append(sta-ua)
    
    st.session_state.df_pres_excel = pd.DataFrame({"Z (m)": z, "σ Total": stot, "u": u, "σ Efectivo": sef})
    st.dataframe(st.session_state.df_pres_excel)

# --- PESTAÑA 3: PLASTICIDAD ---
with tabs[2]:
    st.header("Límites y Clasificación")
    ll = st.number_input("LL", 0, 120, 40); lp = st.number_input("LP", 0, 80, 20); ip = ll - lp
    clas = "CL/CH/ML/MH" # Lógica de clasificación aquí
    st.session_state.df_lim_excel = pd.DataFrame({"Propiedad": ["LL", "LP", "IP", "Clasificación"], "Valor": [ll, lp, ip, clas]})
    st.write(st.session_state.df_lim_excel)

# --- PESTAÑA 4: EXPORTAR (EL CORAZÓN DEL REPORTE) ---
with tabs[3]:
    st.header("Generar Reporte Integral")
    st.info("Este archivo contendrá todas las pestañas procesadas: Gravimetría, Presiones y Límites.")
    
    if st.button("📥 Descargar Reporte Completo en Excel"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            if 'df_grav_excel' in st.session_state:
                st.session_state.df_grav_excel.to_excel(writer, sheet_name='1. Gravimetria', index=False)
            if 'df_pres_excel' in st.session_state:
                st.session_state.df_pres_excel.to_excel(writer, sheet_name='2. Presiones', index=False)
            if 'df_lim_excel' in st.session_state:
                st.session_state.df_lim_
