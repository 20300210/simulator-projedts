"""
FinSim - Simulador Financiero Universitario
=============================================
Dashboard interactivo que integra 5 módulos:
  1. Valor del dinero en el tiempo
  2. Evaluación de proyectos (VAN, TIR, Payback)
  3. Préstamos y amortización (Francés vs Alemán)
  4. Portafolio de inversión con simulación Monte Carlo + estrés macroeconómico
  5. Financiación de Posgrado en Colombia (capacidad de pago, endeudamiento,
     escenarios de disminución de ingresos, comparación de alternativas)

Para correr la app:
    pip install -r requirements.txt
    streamlit run app.py
"""

import logging
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from modulos.valor_dinero import valor_futuro, valor_presente, valor_futuro_anualidad, ajustar_por_inflacion
from modulos.evaluacion import evaluar_proyecto
from modulos.prestamos import amortizacion_francesa, amortizacion_alemana, resumen_comparativo
from modulos.portafolio import Activo, simular_portafolio_monte_carlo, resumen_percentiles, probabilidad_de_meta, ESCENARIOS_MACRO
from modulos.posgrado import (
    capacidad_pago,
    nivel_endeudamiento,
    escenario_disminucion_ingreso,
    sensibilidad_tasa,
    comparar_alternativas,
    ALTERNATIVAS_EJEMPLO_COLOMBIA,
    FUENTES_TASAS_COLOMBIA,
)

# --------------------------------------------------------------------------
# NOTA DE SEGURIDAD (fuga de información / manejo de errores):
# Por defecto, si una función lanza una excepción dentro de Streamlit, el
# usuario ve el traceback completo (rutas del servidor, nombres internos de
# funciones y variables). Eso es información útil para un atacante y además
# se ve poco profesional en una demo. La política de esta app es:
#   1. El detalle técnico del error se registra con `logging` (queda en la
#      terminal/servidor, nunca en el navegador del usuario).
#   2. El usuario solo ve un mensaje corto y accionable vía st.error().
# Este patrón se llama "fail closed with a safe message".
# --------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("finsim")


def manejar_error(contexto: str, excepcion: Exception) -> None:
    """Registra el error completo en el log y muestra un mensaje seguro al usuario."""
    logger.error("Error en %s: %s", contexto, excepcion, exc_info=True)
    st.error(
        f"⚠️ No se pudo calcular '{contexto}' con los valores ingresados. "
        "Revisa que los números tengan sentido (ej. tasas y montos positivos, "
        "periodos razonables) e inténtalo de nuevo."
    )


st.set_page_config(page_title="FinSim - Simulador Financiero", page_icon="💰", layout="wide")

st.title("💰 FinSim: Simulador Financiero")
st.caption("Proyecto universitario · Finanzas · Simulación de decisiones financieras")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Valor del Dinero",
    "🏗️ Evaluación de Proyectos",
    "🏦 Préstamos",
    "🎲 Portafolio (Monte Carlo)",
    "🎓 Posgrado (Colombia)",
])

# ----------------------------------------------------------------------
# TAB 1: Valor del dinero en el tiempo
# ----------------------------------------------------------------------
with tab1:
    st.header("Valor del Dinero en el Tiempo")
    st.write("Calcula cómo crece un capital con interés compuesto y aportes periódicos.")

    col1, col2 = st.columns(2)
    with col1:
        capital = st.number_input("Capital inicial ($)", min_value=0.0, value=1000.0, step=100.0)
        aporte = st.number_input("Aporte periódico ($)", min_value=0.0, value=100.0, step=10.0)
    with col2:
        tasa_anual = st.slider("Tasa de interés anual (%)", 0.0, 30.0, 8.0) / 100
        anios = st.slider("Número de años", 1, 50, 10)

    inflacion = st.slider("Inflación anual esperada (%) — para ver el valor real", 0.0, 20.0, 3.0) / 100

    try:
        vf_capital = valor_futuro(capital, tasa_anual, anios)
        vf_aportes = valor_futuro_anualidad(aporte, tasa_anual, anios)
        vf_total = vf_capital + vf_aportes
        vf_real = ajustar_por_inflacion(vf_total, inflacion, anios)

        m1, m2, m3 = st.columns(3)
        m1.metric("Valor Futuro (nominal)", f"${vf_total:,.2f}")
        m2.metric("Valor Futuro (real, ajustado por inflación)", f"${vf_real:,.2f}")
        m3.metric("Total aportado", f"${capital + aporte*anios:,.2f}")

        # Gráfico de evolución año a año
        valores = [valor_futuro(capital, tasa_anual, t) + valor_futuro_anualidad(aporte, tasa_anual, t) for t in range(anios + 1)]
        fig, ax = plt.subplots()
        ax.plot(range(anios + 1), valores, marker="o")
        ax.set_xlabel("Año")
        ax.set_ylabel("Valor acumulado ($)")
        ax.set_title("Crecimiento del capital en el tiempo")
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)
        plt.close(fig)  # libera memoria explícitamente (evita fuga de recursos entre recargas)
    except Exception as e:
        manejar_error("Valor del Dinero", e)

# ----------------------------------------------------------------------
# TAB 2: Evaluación de proyectos
# ----------------------------------------------------------------------
with tab2:
    st.header("Evaluación de Proyectos de Inversión")
    st.write("Ingresa el flujo de caja del proyecto (año 0 = inversión inicial, normalmente negativa).")

    tasa_descuento = st.slider("Tasa de descuento / costo de capital (%)", 0.0, 30.0, 10.0, key="tasa_van") / 100
    n_flujos = st.number_input("Número de años del proyecto (sin contar el año 0)", min_value=1, max_value=15, value=5)

    flujos = []
    cols = st.columns(int(n_flujos) + 1)
    for i, col in enumerate(cols):
        valor_default = -1000.0 if i == 0 else 300.0
        etiqueta = "Inversión inicial (año 0)" if i == 0 else f"Año {i}"
        flujo = col.number_input(etiqueta, value=valor_default, step=50.0, key=f"flujo_{i}")
        flujos.append(flujo)

    try:
        resultado = evaluar_proyecto(tasa_descuento, flujos)

        m1, m2, m3 = st.columns(3)
        m1.metric("VAN", f"${resultado['van']:,.2f}")
        m2.metric("TIR", f"{resultado['tir']*100:.2f}%" if resultado["tir"] is not None else "No definida")
        m3.metric("Payback", f"{resultado['payback']:.2f} años" if resultado["payback"] is not None else "No se recupera")

        if resultado["conviene"]:
            st.success("✅ El proyecto CONVIENE: el VAN es positivo, genera valor por encima del costo de capital.")
        else:
            st.error("❌ El proyecto NO conviene: el VAN es negativo o nulo.")
    except Exception as e:
        manejar_error("Evaluación de Proyectos", e)

# ----------------------------------------------------------------------
# TAB 3: Préstamos
# ----------------------------------------------------------------------
with tab3:
    st.header("Préstamos: Sistema Francés vs Sistema Alemán")

    col1, col2, col3 = st.columns(3)
    monto_prestamo = col1.number_input("Monto del préstamo ($)", min_value=0.0, value=10000.0, step=500.0)
    tasa_anual_prestamo = col2.slider("Tasa de interés anual (%)", 0.0, 40.0, 12.0) / 100
    plazo_meses = col3.number_input("Plazo (meses)", min_value=1, max_value=360, value=24)

    try:
        tasa_mensual = tasa_anual_prestamo / 12
        tabla_fr = amortizacion_francesa(monto_prestamo, tasa_mensual, int(plazo_meses))
        tabla_al = amortizacion_alemana(monto_prestamo, tasa_mensual, int(plazo_meses))
        comparativo = resumen_comparativo(monto_prestamo, tasa_mensual, int(plazo_meses))

        m1, m2 = st.columns(2)
        m1.metric("Interés total (Francés)", f"${comparativo['interes_total_frances']:,.2f}")
        m2.metric("Interés total (Alemán)", f"${comparativo['interes_total_aleman']:,.2f}")

        m3, m4 = st.columns(2)
        m3.metric("Costo total del crédito (Francés)", f"${comparativo['costo_total_frances']:,.2f}")
        m4.metric("Costo total del crédito (Alemán)", f"${comparativo['costo_total_aleman']:,.2f}")

        fig, ax = plt.subplots()
        ax.plot(tabla_fr["periodo"], tabla_fr["cuota"], label="Sistema Francés (cuota fija)")
        ax.plot(tabla_al["periodo"], tabla_al["cuota"], label="Sistema Alemán (cuota decreciente)")
        ax.set_xlabel("Mes")
        ax.set_ylabel("Cuota ($)")
        ax.set_title("Comparación de cuotas mensuales")
        ax.legend()
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)
        plt.close(fig)

        with st.expander("Ver tabla de amortización completa"):
            sub1, sub2 = st.tabs(["Sistema Francés", "Sistema Alemán"])
            sub1.dataframe(tabla_fr, use_container_width=True)
            sub2.dataframe(tabla_al, use_container_width=True)
    except Exception as e:
        manejar_error("Préstamos", e)

# ----------------------------------------------------------------------
# TAB 4: Portafolio - Monte Carlo + Escenarios macro
# ----------------------------------------------------------------------
with tab4:
    st.header("Simulación de Portafolio con Monte Carlo")
    st.write(
        "En vez de un único resultado, esta simulación genera miles de escenarios "
        "posibles para mostrar el **rango de resultados probables** de tu inversión."
    )

    col1, col2 = st.columns(2)
    with col1:
        capital_inicial = st.number_input("Capital inicial a invertir ($)", min_value=0.0, value=10000.0, step=500.0)
        peso_acciones = st.slider("% del portafolio en Acciones (más riesgo)", 0, 100, 60)
        anios_sim = st.slider("Horizonte de inversión (años)", 1, 40, 15)
    with col2:
        aporte_anual = st.number_input("Aporte anual adicional ($)", min_value=0.0, value=500.0, step=100.0)
        n_simulaciones = st.select_slider("Número de simulaciones", options=[100, 500, 1000, 5000], value=1000)
        meta = st.number_input("Meta de capital a alcanzar ($)", min_value=0.0, value=50000.0, step=1000.0)

    escenario = st.selectbox(
        "🌎 Escenario macroeconómico (innovación: 'estrés' del portafolio)",
        options=list(ESCENARIOS_MACRO.keys()),
        format_func=lambda x: {
            "base": "Base (condiciones normales)",
            "crisis": "Crisis económica (shock negativo)",
            "inflacion_alta": "Inflación alta persistente",
            "auge_economico": "Auge económico (shock positivo)",
        }[x],
    )

    try:
        peso_bonos = 100 - peso_acciones
        activos = [
            Activo("Acciones", peso=peso_acciones / 100, rendimiento_esperado=0.10, volatilidad=0.18),
            Activo("Bonos", peso=peso_bonos / 100, rendimiento_esperado=0.04, volatilidad=0.05),
        ]

        trayectorias = simular_portafolio_monte_carlo(
            capital_inicial=capital_inicial,
            activos=activos,
            anios=anios_sim,
            n_simulaciones=n_simulaciones,
            aporte_anual=aporte_anual,
            escenario=escenario,
        )

        percentiles = resumen_percentiles(trayectorias)
        prob_meta = probabilidad_de_meta(trayectorias, meta)

        m1, m2, m3 = st.columns(3)
        m1.metric("Resultado esperado (mediana)", f"${percentiles['p50'].iloc[-1]:,.0f}")
        m2.metric("Escenario pesimista (P5)", f"${percentiles['p5'].iloc[-1]:,.0f}")
        m3.metric(f"Probabilidad de alcanzar ${meta:,.0f}", f"{prob_meta:.1f}%")

        fig, ax = plt.subplots()
        ax.fill_between(percentiles.index, percentiles["p5"], percentiles["p95"], alpha=0.2, label="Rango P5–P95")
        ax.fill_between(percentiles.index, percentiles["p25"], percentiles["p75"], alpha=0.35, label="Rango P25–P75")
        ax.plot(percentiles.index, percentiles["p50"], color="black", linewidth=2, label="Mediana (P50)")
        ax.axhline(meta, color="red", linestyle="--", label="Meta")
        ax.set_xlabel("Año")
        ax.set_ylabel("Valor del portafolio ($)")
        ax.set_title(f"Cono de incertidumbre — Escenario: {escenario}")
        ax.legend()
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)
        plt.close(fig)

        st.info(
            "💡 **Cómo interpretarlo:** la banda ancha (P5–P95) muestra que el 90% de las "
            "simulaciones cayeron dentro de ese rango. Cambia el escenario macroeconómico "
            "arriba para ver cómo una crisis o un auge afectan tanto el resultado esperado "
            "como la incertidumbre alrededor de él."
        )
    except Exception as e:
        manejar_error("Portafolio Monte Carlo", e)

# ----------------------------------------------------------------------
# TAB 5: Financiación de Posgrado en Colombia
# ----------------------------------------------------------------------
with tab5:
    st.header("Financiación de Posgrado en Colombia")
    st.write(
        "Alcance del proyecto (**Opción A**): desembolso único, tasa constante "
        "durante la simulación, sistema de cuota fija. Compara varias alternativas "
        "reales (ICETEX, banco, fondo/cooperativa) y evalúa si te alcanza el bolsillo."
    )
    st.caption(
        "✅ Las tasas de las 3 primeras alternativas son **reales y verificadas** "
        "(ICETEX, Davivienda, Bancoomeva) — ver la fuente de cada una abajo. Si "
        "agregas más alternativas o cambias montos/plazos, edítalos según tu caso."
    )
    with st.expander("📎 Ver fuente y fecha de verificación de cada tasa"):
        for nombre, info in FUENTES_TASAS_COLOMBIA.items():
            st.markdown(
                f"**{nombre}** — {info['tasa_ea']*100:.2f}% E.A.  \n"
                f"{info['descripcion']}  \n"
                f"Fuente: [{info['fuente']}]({info['url']}) · Vigente para: {info['vigente_para']}  \n"
                f"⚠️ {info['nota']}"
            )
            st.divider()

    st.subheader("1. Tus datos financieros")
    c1, c2, c3, c4 = st.columns(4)
    ingreso_mensual = c1.number_input("Ingreso mensual disponible ($)", min_value=0.0, value=3_000_000.0, step=100_000.0)
    otras_deudas = c2.number_input("Otras deudas mensuales ($)", min_value=0.0, value=0.0, step=50_000.0)
    umbral_capacidad = c3.slider("Umbral capacidad de pago (%)", 10, 60, 35) / 100
    umbral_endeudamiento_ui = c4.slider("Umbral endeudamiento total (%)", 10, 70, 40) / 100

    st.subheader("2. Alternativas de financiación a comparar")
    n_alternativas = st.number_input("¿Cuántas alternativas quieres comparar?", min_value=1, max_value=10, value=3)

    alternativas_input = []
    for i in range(int(n_alternativas)):
        ejemplo = ALTERNATIVAS_EJEMPLO_COLOMBIA[i] if i < len(ALTERNATIVAS_EJEMPLO_COLOMBIA) else {
            "nombre": f"Alternativa {i+1}", "monto": 20_000_000, "tasa_anual": 0.15, "plazo_meses": 36,
        }
        cA, cB, cC, cD = st.columns(4)
        nombre = cA.text_input("Nombre", value=ejemplo["nombre"], key=f"pg_nombre_{i}")
        monto = cB.number_input("Monto ($)", min_value=0.0, value=float(ejemplo["monto"]), step=500_000.0, key=f"pg_monto_{i}")
        tasa_pct = cC.number_input("Tasa anual (%)", min_value=0.0, value=ejemplo["tasa_anual"] * 100, step=0.5, key=f"pg_tasa_{i}")
        plazo = cD.number_input("Plazo (meses)", min_value=1, max_value=360, value=ejemplo["plazo_meses"], key=f"pg_plazo_{i}")
        alternativas_input.append({"nombre": nombre, "monto": monto, "tasa_anual": tasa_pct / 100, "plazo_meses": int(plazo)})

    if st.button("Comparar alternativas"):
        try:
            tabla_comparativa = comparar_alternativas(
                alternativas_input,
                ingreso_mensual=ingreso_mensual if ingreso_mensual > 0 else None,
                otras_deudas_mensuales=otras_deudas,
                umbral_capacidad_pago=umbral_capacidad,
                umbral_endeudamiento=umbral_endeudamiento_ui,
            )
            # Se guarda en session_state para que las secciones 3 y 4 (que
            # dependen de un rerun posterior de Streamlit) puedan reutilizar
            # esta comparación sin que el usuario tenga que repetir datos.
            st.session_state["pg_tabla"] = tabla_comparativa
            st.session_state["pg_alternativas"] = alternativas_input
        except Exception as e:
            manejar_error("Financiación de Posgrado", e)

    if "pg_tabla" in st.session_state:
        tabla_comparativa = st.session_state["pg_tabla"]
        mejor = tabla_comparativa.iloc[0]
        st.success(
            f"💡 La alternativa con **menor costo total** es **{mejor['nombre']}** "
            f"(costo total ${mejor['costo_total']:,.0f})."
        )
        st.dataframe(tabla_comparativa, use_container_width=True)

        if "capacidad_pago_pct" in tabla_comparativa.columns:
            for _, fila in tabla_comparativa.iterrows():
                estado_cap = "✅" if fila["cumple_capacidad_pago"] else "❌"
                estado_end = "✅" if fila["cumple_endeudamiento"] else "❌"
                st.caption(
                    f"**{fila['nombre']}** — Capacidad de pago: {estado_cap} "
                    f"({fila['capacidad_pago_pct']:.1f}% del ingreso) · "
                    f"Endeudamiento total: {estado_end} ({fila['endeudamiento_pct']:.1f}%)"
                )

        st.divider()
        st.subheader("3. Escenario: disminución de ingresos")
        st.write("Simula qué pasaría con tu nivel de endeudamiento si tu ingreso cae temporalmente.")

        c1, c2 = st.columns(2)
        nombre_seleccionado = c1.selectbox("Alternativa a evaluar", tabla_comparativa["nombre"])
        pct_disminucion = c2.slider("Disminución del ingreso (%)", 0, 90, 30) / 100

        try:
            cuota_seleccionada = tabla_comparativa.loc[tabla_comparativa["nombre"] == nombre_seleccionado, "cuota_mensual"].iloc[0]
            resultado_estres = escenario_disminucion_ingreso(
                ingreso_mensual=ingreso_mensual,
                porcentaje_disminucion=pct_disminucion,
                cuota_mensual=cuota_seleccionada,
                otras_deudas_mensuales=otras_deudas,
                umbral=umbral_endeudamiento_ui,
            )
            m1, m2, m3 = st.columns(3)
            m1.metric("Ingreso original", f"${resultado_estres['ingreso_original']:,.0f}")
            m2.metric("Ingreso reducido", f"${resultado_estres['ingreso_reducido']:,.0f}")
            m3.metric("Endeudamiento bajo estrés", f"{resultado_estres['ratio_pct']:.1f}%")
            if resultado_estres["cumple"]:
                st.success("✅ Incluso con esa caída de ingresos, la deuda seguiría siendo manejable.")
            else:
                st.error("❌ Con esa caída de ingresos, la deuda superaría el umbral recomendado — riesgo de sobreendeudamiento.")
        except Exception as e:
            manejar_error("Escenario de disminución de ingresos", e)

        st.divider()
        st.subheader("4. Sensibilidad a la tasa de interés")
        st.write(
            "Compara, para UNA alternativa, cómo cambiaría la cuota si la hubieras "
            "tomado con una tasa distinta (todas las tasas siguen siendo constantes "
            "durante el crédito — esto no es un crédito de tasa variable)."
        )
        alt_seleccionada = next(a for a in st.session_state["pg_alternativas"] if a["nombre"] == nombre_seleccionado)

        try:
            tabla_sensibilidad = sensibilidad_tasa(
                monto=alt_seleccionada["monto"],
                tasa_anual_base=alt_seleccionada["tasa_anual"],
                plazo_meses=alt_seleccionada["plazo_meses"],
            )
            fig, ax = plt.subplots()
            ax.bar(tabla_sensibilidad["tasa_anual_pct"].astype(str) + "%", tabla_sensibilidad["cuota_mensual"], color="#A87D3F")
            ax.set_xlabel("Tasa anual")
            ax.set_ylabel("Cuota mensual ($)")
            ax.set_title(f"Sensibilidad de la cuota — {nombre_seleccionado}")
            ax.grid(True, alpha=0.3, axis="y")
            st.pyplot(fig)
            plt.close(fig)
        except Exception as e:
            manejar_error("Sensibilidad de tasa", e)

