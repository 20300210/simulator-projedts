"""
Módulo: Simulación de Portafolio (Monte Carlo)
-------------------------------------------------
Este es el módulo "estrella" del simulador: en vez de mostrar un único
resultado determinístico ("tu inversión valdrá X"), genera miles de
posibles trayectorias futuras y muestra el RANGO de resultados probables.
Esto refleja mejor la realidad: los mercados son inciertos.

Además incluye un motor de "escenarios macroeconómicos" (innovación):
permite aplicar un shock (crisis, alta inflación, alza de tasas) a los
supuestos de rendimiento y volatilidad, y comparar cómo cambia el
resultado esperado del portafolio.

Modelo usado: cada año, el rendimiento del portafolio se simula como
una variable aleatoria normal ~ N(rendimiento_esperado, volatilidad).
Es una simplificación estándar a nivel de pregrado (no pretende ser un
modelo de trading profesional, sino ilustrar el concepto de riesgo).
"""

from dataclasses import dataclass
from typing import List, Optional
import numpy as np
import pandas as pd


@dataclass
class Activo:
    """Representa un activo o clase de activo dentro del portafolio."""
    nombre: str
    peso: float                 # proporción del capital, entre 0 y 1
    rendimiento_esperado: float  # rendimiento anual esperado (decimal), ej. 0.08
    volatilidad: float           # desviación estándar anual del rendimiento (decimal)

    def __post_init__(self):
        """
        Validación defensiva del objeto. Un Activo mal formado (peso fuera de
        [0,1], volatilidad negativa) no debe fallar silenciosamente ni
        propagar un resultado numérico incorrecto varios pasos más adelante
        (donde sería mucho más difícil de diagnosticar) — falla rápido, aquí.
        """
        if not (0 <= self.peso <= 1):
            raise ValueError(f"El peso de '{self.nombre}' debe estar entre 0 y 1 (recibido: {self.peso}).")
        if self.volatilidad < 0:
            raise ValueError(f"La volatilidad de '{self.nombre}' no puede ser negativa.")
        if self.rendimiento_esperado <= -1:
            raise ValueError(f"El rendimiento esperado de '{self.nombre}' no puede ser <= -100%.")


# Escenarios macroeconómicos predefinidos: ajustan rendimiento y volatilidad
# de TODOS los activos del portafolio para simular un contexto distinto.
ESCENARIOS_MACRO = {
    "base": {"ajuste_rendimiento": 0.0, "multiplicador_volatilidad": 1.0},
    "crisis": {"ajuste_rendimiento": -0.08, "multiplicador_volatilidad": 1.8},
    "inflacion_alta": {"ajuste_rendimiento": -0.03, "multiplicador_volatilidad": 1.3},
    "auge_economico": {"ajuste_rendimiento": 0.04, "multiplicador_volatilidad": 0.9},
}


def _validar_pesos(activos: List[Activo]) -> None:
    suma_pesos = sum(a.peso for a in activos)
    if not np.isclose(suma_pesos, 1.0, atol=1e-3):
        raise ValueError(f"Los pesos de los activos deben sumar 1.0 (suma actual: {suma_pesos:.3f}).")


def simular_portafolio_monte_carlo(
    capital_inicial: float,
    activos: List[Activo],
    anios: int,
    n_simulaciones: int = 1000,
    aporte_anual: float = 0.0,
    escenario: str = "base",
    semilla: Optional[int] = 42,
) -> pd.DataFrame:
    """
    Corre una simulación de Monte Carlo del valor del portafolio a través del tiempo.

    Parámetros:
        capital_inicial: monto invertido al inicio
        activos: lista de objetos Activo que componen el portafolio (pesos deben sumar 1)
        anios: horizonte de la simulación, en años
        n_simulaciones: número de trayectorias aleatorias a generar
        aporte_anual: aporte adicional que se hace cada año (opcional)
        escenario: uno de "base", "crisis", "inflacion_alta", "auge_economico"
        semilla: semilla aleatoria para reproducibilidad (usar None para variar cada corrida)

    Retorna:
        DataFrame de forma (anios+1) x n_simulaciones, donde cada columna es una
        trayectoria simulada del valor del portafolio, y el índice son los años (0..anios).
    """
    _validar_pesos(activos)

    if escenario not in ESCENARIOS_MACRO:
        raise ValueError(f"Escenario '{escenario}' no reconocido. Opciones: {list(ESCENARIOS_MACRO)}")

    # Límites anti-DoS: sin esto, un valor mal ingresado (o un uso malicioso
    # si esto se expone alguna vez como servicio web) podría pedir una matriz
    # de, por ejemplo, 10 millones de años x 10 millones de simulaciones y
    # agotar la memoria del servidor.
    if not (1 <= anios <= 100):
        raise ValueError("anios debe estar entre 1 y 100.")
    if not (1 <= n_simulaciones <= 20000):
        raise ValueError("n_simulaciones debe estar entre 1 y 20000.")
    if capital_inicial < 0:
        raise ValueError("capital_inicial no puede ser negativo.")

    ajuste = ESCENARIOS_MACRO[escenario]

    # Rendimiento y volatilidad combinados del portafolio (promedio ponderado),
    # ajustados según el escenario macroeconómico elegido.
    rendimiento_portafolio = sum(a.peso * a.rendimiento_esperado for a in activos) + ajuste["ajuste_rendimiento"]
    volatilidad_portafolio = sum(a.peso * a.volatilidad for a in activos) * ajuste["multiplicador_volatilidad"]

    rng = np.random.default_rng(semilla)

    trayectorias = np.zeros((anios + 1, n_simulaciones))
    trayectorias[0, :] = capital_inicial

    for t in range(1, anios + 1):
        rendimientos_anio = rng.normal(
            loc=rendimiento_portafolio,
            scale=volatilidad_portafolio,
            size=n_simulaciones,
        )
        trayectorias[t, :] = trayectorias[t - 1, :] * (1 + rendimientos_anio) + aporte_anual

    df = pd.DataFrame(trayectorias, index=range(anios + 1))
    df.index.name = "anio"
    return df


def resumen_percentiles(trayectorias: pd.DataFrame, percentiles=(5, 25, 50, 75, 95)) -> pd.DataFrame:
    """
    Resume las trayectorias simuladas en percentiles por año.
    Muy útil para graficar un "cono de incertidumbre": la mediana (P50)
    junto con un rango pesimista (P5) y optimista (P95).
    """
    resumen = trayectorias.apply(lambda fila: np.percentile(fila, percentiles), axis=1, result_type="expand")
    resumen.columns = [f"p{p}" for p in percentiles]
    return resumen


def probabilidad_de_meta(trayectorias: pd.DataFrame, meta: float) -> float:
    """
    Calcula qué porcentaje de las simulaciones alcanza o supera una meta
    de capital al final del horizonte de tiempo. Responde a la pregunta:
    "¿Qué tan probable es que llegue a mi objetivo financiero?"
    """
    valores_finales = trayectorias.iloc[-1, :]
    return float((valores_finales >= meta).mean() * 100)
