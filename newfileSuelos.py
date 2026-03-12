import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io

st.set_page_config(page_title="Geotecnia Master Pro", layout="wide")

st.title("🏗️ Geotecnia Master: Suite Integral")

tabs = st.tabs(["🧩 Relaciones de Fase", "🗂️ Perfiles de Presión", "📈 Plasticidad", "📥 Exportar"])

# --- PESTAÑA 1: RELACIONES DE FASE (MOTOR TOTAL) ---
with tabs[0]:
    st.header("Relaciones Gravimétricas y Volumétricas Completas")
    
    # Diccionario con TODAS las variables posibles
    opciones_nombres = {
        "gs": "Gs (Gravedad específica)",
        "e": "e (Relación de vacíos)",
        "n": "n (Porosidad %)",
        "w": "w (Humedad %)",
        "s": "S (Saturación %)",
        "gh": "γ (Peso unitario húmedo - kN/m³)",
        "gd": "γd (Peso unitario seco - kN/m³)",
        "gsat": "γsat (Peso unitario saturado - kN/m³)",
        "ws": "Ws (Peso de sólidos - g o kN)",
        "ww": "Ww (Peso del agua - g o kN)",
        "vt": "Vt (Volumen total - cm³ o m³)",
        "vs": "Vs (Volumen de sólidos - cm³ o m³)",
        "vv": "Vv (Volumen de vacíos - cm³ o m³)"
    }
    
    seleccionados = st.multiselect("¿Qué datos conoces?", options=list(opciones_nombres.keys()), format_func=lambda x: opciones_nombres[x])
    
    inputs = {}
    if seleccionados:
        cols = st.columns(min(len(seleccionados), 3))
        for i, clave in enumerate(seleccionados):
            inputs[clave] = cols[i % 3].number_input(f"{opciones_nombres[clave]}", value=0.0, step=0.01, format="%.3f")

    if st.button("🚀 Calcular Fase"):
        # Extraer valores (con conversión a decimal para porcentajes)
        gs = inputs.get("gs", 0.0); e = inputs.get("e", 0.0)
        n = inputs.get("n", 0.0)/100; w = inputs.get("w", 0.0)/100
        s = inputs.get("s", 0.0)/100; gh = inputs.get("gh", 0.0); gd = inputs.get("gd", 0.0)
        gsat = inputs.get("gsat", 0.0); ws = inputs.get("ws", 0.0); ww = inputs.get("ww", 0.0)
        vt = inputs.get("vt", 0.0); vs = inputs.get("vs", 0.0); vv = inputs.get("vv", 0.0)
        
        gw = 9.81; pasos = [] # Peso unitario del agua estándar

        # MOTOR DE INFERENCIA DE ALTO NIVEL (Iterativo)
        for _ in range(6):
            # 1. Relaciones de Volumen básicas
            if vt > 0 and vs > 0 and vv == 0: vv = vt - vs; pasos.append(f"Vv = Vt - Vs = {vv:.3f}")
            if vs > 0 and vv > 0 and vt == 0: vt = vs + vv; pasos.append(f"Vt = Vs + Vv = {vt:.3f}")
            if vt > 0 and vv > 0 and vs == 0: vs = vt - vv; pasos.append(f"Vs = Vt - Vv = {vs:.3f}")
            
            # 2. Relaciones Gravimétricas básicas
            if ws > 0 and ww > 0 and w == 0: w = ww / ws; pasos.append(f"w = Ww / Ws = {w*100:.2f}%")
            if ws > 0 and w > 0 and ww == 0: ww = w * ws; pasos.append(f"Ww = w * Ws = {ww:.3f}")
            
            # 3. Definiciones de e, n, Gs
            if vs > 0 and vv > 0 and e == 0: e = vv / vs; pasos.append(f"e = Vv / Vs = {e:.3f}")
            if e > 0 and n == 0: n = e / (1 + e); pasos.append(f"n = e / (1 + e) = {n:.3f}")
            if n > 0 and e == 0: e = n / (1 - n); pasos.append(f"e = n / (1 - n) = {e:.3f}")
            if ws > 0 and vs > 0 and gs == 0: gs = ws / (vs * 1.0); pasos.append(f"Gs = Ws / (Vs * γw) = {gs:.2f}") # Asumiendo γw=1 para g/cm3
            
            # 4. Fórmula de oro y variantes de pesos unitarios
            if s > 0 and e > 0 and gs > 0 and w == 0: w = (s*e)/gs; pasos.append(f"w = (S*e)/Gs = {w*100:.2f}%")
            if w > 0 and gs > 0 and e > 0 and s == 0: s = (w*gs)/e; pasos.append(f"S = (w*Gs)/e = {s*100:.2f}%")
            if gs > 0 and e > 0 and gd == 0: gd = (gs*gw)/(1+e); pasos.append(f"γd = (Gs*γw)/(1+e) = {gd:.2f}")
            if gs > 0 and e > 0 and gsat == 0: gsat = ((gs + e)*gw)/(1+e); pasos.append(f"γsat = ((Gs + e)*γw)/(1+e) = {gsat:.2f}")
            if gd > 0 and w > 0 and gh == 0: gh = gd*(1+w); pasos.append(f"γ = γd*(1+w) = {gh:.2f}")
            if gh > 0 and w > 0 and gd == 0: gd = gh/(1+w); pasos.append(f"γd = γ/(1+w) = {gd:.2f}")

        # Resultados en tabla
        st.subheader("📋 Resultados Calculados")
        res_data = {
            "Parámetro": ["Gs", "e", "n (%)", "w (%)", "S (%)", "γ (kN/m³)", "γd (kN/m³)", "γsat (kN/m³)"],
            "Valor": [f"{gs:.2f}", f"{e:.3f}", f"{n*100:.1f}%", f"{w*100:.1f}%", f"{s*100:.1f}%", f"{gh:.2f}", f"{gd:.2f}", f"{gsat:.2f}"]
        }
        st.table(pd.DataFrame(res_data))
        
        with st.expander("📖 Ver procedimiento paso a paso"):
            if pasos:
                for p in pasos: st.write(f"🔹 {p}")
            else:
                st.write("No se requirieron despejes adicionales.")
        
        # Diagrama de Fases
        vs_plot = 1.0 if e > 0 else (vs if vs > 0 else 1.0)
        vv_plot = e * vs_plot
        st.bar_chart(pd.DataFrame({"Fase": ["Muestra"], "Aire": [vv_plot*(1-s)], "Agua": [vv_plot*s], "Sólidos": [vs_plot]}).set_index("Fase"), color=["#BDC3C7", "#3498DB", "#7E5109"])

# --- PESTAÑA 2: PERFILES DE PRESIÓN ---
with tabs[1]:
    st.header("Esfuerzos en el Suelo (σ, u, σ')")
    c1, c2 = st.columns([1, 2])
    with c1:
        n_capas = st.number_input("N° de Capas", 1, 5, 2)
        nf = st.number_input("Nivel Freático (m)", 0.0, 50.0, 2.0)
        capas = []
        for i in range(int(n_capas)):
            h = st.number_input(f"H capa {i+1}", 0.1, 50.0, 4.0, key=f"h{i}")
            g = st.number_input(f"γ capa {i+1}", 10.0, 25.0, 18.0, key=f"g{i}")
            capas.append({'h': h, 'g': g})
    with c2:
        z, stot, u, sef = [0], [0], [0], [0]
        za, sta = 0, 0
        for cp in capas:
            za += cp['h']; sta += cp['g']*cp['h']
            ua = (za-nf)*9.81 if za > nf else 0
            z.append(za); stot.append(sta); u.append(ua); sef.append(sta-ua)
        df_p = pd.DataFrame({"Z (m)": z, "Total": stot, "u": u, "Efectivo": sef})
        st.table(df_p)
        st.line_chart(df_p.set_index("Z (m)"))

# --- PESTAÑA 3: PLASTICIDAD ---
with tabs[2]:
    st.header("Carta de Plasticidad (Casagrande)")
    ll = st.number_input("Límite Líquido", 0, 120, 45)
    lp = st.number_input("Límite Plástico", 0, 100, 20)
    ip = ll - lp
    fig = go.Figure()
    ax = list(range(20, 101)); ay = [0.73*(x-20) for x in ax]
    fig.add_trace(go.Scatter(x=ax, y=ay, mode='lines', name='Línea A', line=dict(color='black')))
    fig.add_trace(go.Scatter(x=[ll], y=[ip], marker=dict(color='red', size=12), name='Tu Suelo'))
    st.plotly_chart(fig)

# --- PESTAÑA 4: EXPORTAR ---
with tabs[3]:
    st.header("Generar Reporte Profesional")
    if st.button("Preparar Excel"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            pd.DataFrame({"Dato": ["Reporte Geotécnico Completo"]}).to_excel(writer)
        st.download_button("📥 Descargar reporte.xlsx", output.getvalue(), "reporte_suelos.xlsx")
        
