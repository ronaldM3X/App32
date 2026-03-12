import streamlit as st
import pandas as pd

st.set_page_config(page_title="Geotecnia Smart Solver + Guía", layout="centered")

st.title("🏗️ Geotecnia Smart: Relaciones Gravimétricas")
st.markdown("Selecciona tus datos y descubre el procedimiento paso a paso.")

# --- SELECCIÓN DE DATOS ---
opciones_nombres = {
    "gs": "Gravedad Específica (Gs)",
    "e": "Relación de Vacíos (e)",
    "n": "Porosidad (n)",
    "w": "Contenido de Humedad (w %)",
    "s": "Grado de Saturación (S %)",
    "gh": "Peso Unitario Húmedo (γ)",
    "gd": "Peso Unitario Seco (γd)"
}

st.subheader("1. Configuración del problema")
seleccionados = st.multiselect(
    "¿Qué datos tienes?",
    options=list(opciones_nombres.keys()),
    format_func=lambda x: opciones_nombres[x]
)

inputs = {}
if seleccionados:
    st.subheader("2. Ingresa los valores")
    cols = st.columns(len(seleccionados))
    for i, clave in enumerate(seleccionados):
        with cols[i]:
            inputs[clave] = st.number_input(f"{opciones_nombres[clave]}", value=0.0, step=0.01, format="%.3f")

# --- MOTOR DE CÁLCULO CON MEMORIA ---
if st.button("🚀 Calcular y mostrar procedimiento"):
    gs = inputs.get("gs", 0.0)
    e = inputs.get("e", 0.0)
    n = inputs.get("n", 0.0) / 100 if "n" in inputs else 0.0
    w = inputs.get("w", 0.0) / 100 if "w" in inputs else 0.0
    s = inputs.get("s", 0.0) / 100 if "s" in inputs else 0.0
    gh = inputs.get("gh", 0.0)
    gd = inputs.get("gd", 0.0)
    gw = 9.81
    
    pasos = [] # Aquí guardaremos la explicación

    for _ in range(5):
        # Relación e - n
        if e > 0 and n == 0: 
            n = e / (1 + e)
            pasos.append(f"Cálculo de Porosidad: n = e / (1 + e) = {e} / (1 + {e}) = {n:.3f}")
        if n > 0 and e == 0: 
            e = n / (1 - n)
            pasos.append(f"Cálculo de Relación de Vacíos: e = n / (1 - n) = {n} / (1 - {n}) = {e:.3f}")
        
        # Fórmula de oro
        if s > 0 and e > 0 and gs > 0 and w == 0: 
            w = (s * e) / gs
            pasos.append(f"Cálculo de Humedad (Fórmula de Oro): w = (S * e) / Gs = ({s} * {e}) / {gs} = {w:.3f}")
        if w > 0 and gs > 0 and e > 0 and s == 0: 
            s = (w * gs) / e
            pasos.append(f"Cálculo de Saturación: S = (w * Gs) / e = ({w} * {gs}) / {e} = {s:.3f}")
        if s > 0 and e > 0 and w > 0 and gs == 0:
            gs = (s * e) / w
            pasos.append(f"Cálculo de Gs: Gs = (S * e) / w = ({s} * {e}) / {w} = {gs:.3f}")

        # Pesos unitarios
        if gs > 0 and e > 0 and gd == 0: 
            gd = (gs * gw) / (1 + e)
            pasos.append(f"Cálculo de γd: γd = (Gs * γw) / (1 + e) = ({gs} * 9.81) / (1 + {e}) = {gd:.2f}")
        if gd > 0 and w > 0 and gh == 0: 
            gh = gd * (1 + w)
            pasos.append(f"Cálculo de γ: γ = γd * (1 + w) = {gd} * (1 + {w}) = {gh:.2f}")

    # --- RESULTADOS ---
    st.success("✅ Resultados obtenidos")
    res = pd.DataFrame({
        "Parámetro": ["Gs", "e", "n (%)", "w (%)", "S (%)", "γ", "γd"],
        "Valor": [f"{gs:.2f}", f"{e:.3f}", f"{n*100:.2f}%", f"{w*100:.2f}%", f"{s*100:.2f}%", f"{gh:.2f}", f"{gd:.2f}"]
    })
    st.table(res)

    # SECCIÓN PASO A PASO
    with st.expander("📖 Ver procedimiento paso a paso"):
        if pasos:
            for p in pasos:
                st.write(f"🔹 {p}")
        else:
            st.write("No se requirieron despejes complejos con los datos aportados.")

    # Diagrama
    vs, vv = 1.0, e
    vw, va = s * vv, vv - (s * vv)
    st.bar_chart(pd.DataFrame({"Fase": ["Suelo"], "Aire": [va], "Agua": [vw], "Sólidos": [vs]}).set_index("Fase"), color=["#BDC3C7", "#3498DB", "#7E5109"])

