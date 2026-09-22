"""
Módulo: Evaluación de Proyectos de Inversión
---------------------------------------------
Implementa los tres criterios clásicos para evaluar si un proyecto conviene:
- VAN (Valor Actual Neto)
- TIR (Tasa Interna de Retorno)
- Payback (Periodo de recuperación de la inversión)

No dependemos de librerías externas (como numpy_financial) para que el
proyecto sea 100% portable: la TIR se calcula con el método de bisección,
que es exactamente el algoritmo que se explica en el curso de finanzas.
"""

from typing import List


def van(tasa: float, flujos: List[float]) -> float:
    """
    Calcula el Valor Actual Neto de un proyecto.

    VAN = sum( FC_t / (1 + i)^t )  para t = 0, 1, ..., n

    Parámetros:
        tasa: tasa de descuento (costo de capital), en decimal
        flujos: lista de flujos de caja, donde flujos[0] es la inversión
                inicial (normalmente negativa) y el resto son los flujos
                de los periodos siguientes.

    Retorna:
        El VAN del proyecto. Si VAN > 0, el proyecto crea valor.
    """
    return sum(fc / (1 + tasa) ** t for t, fc in enumerate(flujos))


def tir(flujos: List[float], tol: float = 1e-6, max_iter: int = 1000) -> float:
    """
    Calcula la Tasa Interna de Retorno usando el método de bisección:
    busca la tasa 'i' tal que VAN(i) = 0.

    Parámetros:
        flujos: lista de flujos de caja (flujos[0] es la inversión inicial)
        tol: tolerancia de error aceptada
        max_iter: máximo número de iteraciones

    Retorna:
        La TIR en decimal (ej. 0.15 = 15%).

    Lanza:
        ValueError si no se encuentra una raíz en el rango de búsqueda
        (esto pasa si el proyecto no tiene una TIR real, por ejemplo,
        si todos los flujos tienen el mismo signo).
    """
    if not flujos or len(flujos) < 2:
        raise ValueError("Se necesitan al menos 2 flujos de caja (inversión inicial + 1 periodo) para calcular la TIR.")
    # max_iter viene de un valor por defecto seguro, pero si alguna vez se
    # expone a un input externo, lo acotamos para que nadie pueda forzar un
    # bucle de bisección arbitrariamente largo (consumo de CPU).
    max_iter = min(max(int(max_iter), 1), 10_000)

    tasa_baja, tasa_alta = -0.99, 10.0  # rango de búsqueda: -99% a 1000%

    van_baja = van(tasa_baja, flujos)
    van_alta = van(tasa_alta, flujos)

    if van_baja * van_alta > 0:
        raise ValueError(
            "No se encontró una TIR en el rango [-99%, 1000%]. "
            "Revisa los flujos: probablemente todos tienen el mismo signo."
        )

    for _ in range(max_iter):
        tasa_media = (tasa_baja + tasa_alta) / 2
        van_media = van(tasa_media, flujos)

        if abs(van_media) < tol:
            return tasa_media

        if van_baja * van_media < 0:
            tasa_alta = tasa_media
            van_alta = van_media
        else:
            tasa_baja = tasa_media
            van_baja = van_media

    return (tasa_baja + tasa_alta) / 2


def payback(flujos: List[float]) -> float:
    """
    Calcula el periodo de recuperación (Payback) simple, en número de periodos,
    interpolando dentro del periodo donde el flujo acumulado cambia de signo.

    Parámetros:
        flujos: lista de flujos de caja (flujos[0] es la inversión inicial, negativa)

    Retorna:
        Número de periodos (puede ser fraccionario) para recuperar la inversión.
        Retorna None si la inversión nunca se recupera con los flujos dados.
    """
    if not flujos:
        raise ValueError("La lista de flujos no puede estar vacía.")
    acumulado = 0.0
    for t, fc in enumerate(flujos):
        acumulado_anterior = acumulado
        acumulado += fc
        if acumulado >= 0 and t > 0:
            # Interpolación lineal dentro del periodo t
            fraccion = -acumulado_anterior / fc if fc != 0 else 0
            return (t - 1) + fraccion
    return None  # nunca se recupera la inversión


def evaluar_proyecto(tasa: float, flujos: List[float]) -> dict:
    """
    Función de conveniencia: corre los tres criterios de una sola vez
    y devuelve un diccionario con el veredicto.
    """
    resultado = {
        "van": van(tasa, flujos),
        "payback": payback(flujos),
    }
    try:
        resultado["tir"] = tir(flujos)
    except ValueError:
        resultado["tir"] = None

    resultado["conviene"] = resultado["van"] > 0
    return resultado
