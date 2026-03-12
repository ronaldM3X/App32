import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io

st.set_page_config(page_title="Geotecnia Master Pro", layout="wide")
st.title("🏗️ Geotecnia Master: Suite Integral")

tabs = st.tabs(["🧩 Relaciones de Fase", "🗂️ Perfiles de Presión", "📈 Plasticidad", "📥 Exportar"])

# --- PESTAÑA 1: RELACIONES DE FASE ---
with tabs[0]:
    st.header("Relaciones Gravimétricas y Volumétricas")
    
    opciones_nombres = {
        "gs": "Gs (Gravedad específica)",
        "e": "e (Relación de vacíos)",
        "n": "n (Porosidad %)",
        "w": "w (Humedad %)",
        "s": "S (Saturación %)",
        "gh": "γ (Peso unitario húmedo - kN/m³)",
        "gd": "γd (Peso unitario seco - kN/m³)",
        "wm": "Wm (Peso total húmedo - g o kN)",
        "ws": "Ws (Peso seco/horno - g o kN)",
        "vt": "Vt (Volumen total - cm³ o m³)"
    }
    
    seleccionados = st.multiselect("¿Qué datos conoces?", options=list(opciones_nombres.keys()), format_func=lambda x: opciones_nombres[x])
    
    inputs = {}
    if seleccionados:
        cols = st.columns(3)
        for i, clave in enumerate(seleccionados):
            inputs[clave] = cols[i % 3].number_input(f"{opciones_nombres[clave]}", value=0.0, step=0.01, format="%.3f")

    if st.button("🚀 Calcular"):
        # Inicialización
        gs = inputs.get("gs", 0.0); e = inputs.get("e", 0.0); n = inputs.get("n", 0.0)/100
        w = inputs.get("w", 0.0)/100; s = inputs.get("s", 0.0)/100; gh = inputs.get("gh", 0.0)
        gd = inputs.get("gd", 0.0); wm = inputs.get("wm", 0.0); ws = inputs.get("ws", 0.0); vt = inputs.get("vt", 0.0)
        
        gw = 9.81; pasos = []; ww = 0.0

        # Motor de cálculo
        for _ in range(10):
            # Lógica de pesos (Wm, Ws, Ww)
            if wm > 0 and ws > 0 and ww == 0:
                ww = wm - ws
                pasos.append(f"Peso del agua (Ww): Wm - Ws = {wm} - {ws} = {ww:.2f}")
            if ws > 0 and ww > 0 and w == 0:
                w = ww / ws
                pasos.append(f"Humedad (w): Ww / Ws = {ww:.2f} / {ws} = {w*100:.2f}%")
            
            # Detección de sistema de unidades (Laboratorio g/cm3 vs Campo kN/m3)
            unit_w = 1.0 if (vt > 0 and vt < 5000) or (ws > 0 and ws > 50) else 9.81
            
            # Volumen de sólidos
            if ws > 0 and gs > 0:
                vs = ws / (gs * unit_w)
                if vt > 0 and e == 0:
                    e = (vt - vs) / vs
                    pasos.append(f"Relación de vacíos: (Vt - Vs)/Vs = ({vt} - {vs:.2f})/{vs:.2f} = {e:.3f}")

            # Cruce de variables maestras
            if e > 0 and n == 0: n = e/(1+e); pasos.append(f"n = e/(1+e) = {n:.3f}")
            if n > 0 and e == 0: e = n/(1-n); pasos.append(f"e = n/(1-n) = {e:.3f}")
            if s > 0 and e > 0 and gs > 0 and w == 0: w = (s*e)/gs; pasos.append(f"w = (S*e)/Gs = {w:.3f}")
            if w > 0 and gs > 0 and e > 0 and s == 0: s = (w*gs)/e; pasos.append(f"S = (w*Gs)/e = {s:.3f}")
            if gs > 0 and e > 0 and gd == 0: gd = (gs*gw)/(1+e); pasos.append(f"γd = (Gs*gw)/(1+e) = {gd:.2f}")
            if gd > 0 and w > 0 and gh == 0: gh = gd*(1+w); pasos.append(f"γ = γd*(1+w) = {gh:.2f}")

        # Mostrar Resultados
        st.success("✅ Cálculos completados")
        res_df = pd.DataFrame({
            "Parámetro": ["Gs", "e", "n (%)", "w (%)", "S (%)", "γ (kN/m³)", "γd (kN/m³)"],
            "Valor": [f"{gs:.2f}", f"{e:.3f}", f"{n*100:.1f}%", f"{w*100:.1f}%", f"{s*100:.1f}%", f"{gh:.2f}", f"{gd:.2f}"]
        })
        st.table(res_df)
        
        with st.expander("📖 Ver procedimiento detallado"):
            for p in pasos: st.write(f"🔹 {p}")
        
        # Gráfico de Fases
        vs_graph = 1.0; vv_graph = e
        st.bar_chart(pd.DataFrame({"Fase": ["Muestra"], "Aire": [vv_graph*(1-s)], "Agua": [vv_graph*s], "Sólidos": [vs_graph]}).set_index("Fase"), color=["#BDC3C7", "#3498DB", "#7E5109"])

# --- LAS DEMÁS PESTAÑAS SE MANTIENEN IGUAL ---
with tabs[1]:
    st.header("Esfuerzos en el Suelo")
    n_capas = st.number_input("N° de Capas", 1, 5, 2)
    nf = st.number_input("Nivel Freático (m)", 0.0, 50.0, 2.0)
    capas = []
    for i in range(int(n_capas)):
        cols_c = st.columns(2)
        h = cols_c[0].number_input(f"Espesor H{i+1}", 0.1, 50.0, 3.0, key=f"h_{i}")
        g = cols_c[1].number_input(f"γ{i+1} (kN/m³)", 10.0, 25.0, 18.0, key=f"g_{i}")
        capas.append({'h': h, 'g': g})
    
    z, stot, u, sef = [0], [0], [0], [0]
    za, sta = 0, 0
    for cp in capas:
        za += cp['h']; sta += cp['g']*cp['h']
        ua = (za-nf)*9.81 if za > nf else 0
        z.append(za); stot.append(sta); u.append(ua); sef.append(sta-ua)
    st.table(pd.DataFrame({"Prof (m)": z, "σ Total": stot, "u": u, "σ' Efectivo": sef}))

with tabs[2]:
    st.header("Carta de Plasticidad")
    ll = st.number_input("LL", 0, 120, 40)
    lp = st.number_input("LP", 0, 100, 20)
    ip = ll - lp
    fig = go.Figure()
    ax = list(range(20, 101)); ay = [0.73*(x-20) for x in ax]
    fig.add_trace(go.Scatter(x=ax, y=ay, mode='lines', name='Línea A', line=dict(color='black')))
    fig.add_trace(go.Scatter(x=[ll], y=[ip], marker=dict(color='red', size=15), name='Suelo'))
    st.plotly_chart(fig)

with tabs[3]:
    st.header("Reporte")
    st.button("Preparar Excel")
