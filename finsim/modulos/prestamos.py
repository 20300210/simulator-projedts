"""
Módulo: Préstamos y Tablas de Amortización
---------------------------------------------
Genera tablas de amortización usando dos sistemas clásicos:
- Sistema Francés: cuota total constante (lo más común en créditos de consumo/hipotecarios)
- Sistema Alemán: amortización de capital constante (la cuota va bajando con el tiempo)

Ambas funciones retornan un pandas.DataFrame con el detalle periodo a periodo,
listo para graficar o mostrar en una tabla.
"""

import pandas as pd


def _validar_parametros_prestamo(monto: float, tasa_periodica: float, n_periodos: int) -> None:
    """
    Validación defensiva compartida por ambos sistemas de amortización.

    Nota de seguridad: esta validación NO debe vivir solo en la interfaz
    (app.py). Si mañana este módulo se reutiliza desde otro script, una API,
    o una notebook, sin esta capa cualquier valor fuera de rango (negativo,
    cero, o absurdamente grande) puede producir división por cero, resultados
    financieros incorrectos, o un bucle que consuma memoria/CPU sin control.
    """
    if not isinstance(n_periodos, int) or n_periodos <= 0:
        raise ValueError("n_periodos debe ser un entero positivo.")
    if n_periodos > 1200:  # 100 años en meses: límite razonable anti-DoS
        raise ValueError("n_periodos excede el límite permitido (máx. 1200).")
    if monto <= 0:
        raise ValueError("El monto del préstamo debe ser positivo.")
    if tasa_periodica < 0:
        raise ValueError("La tasa periódica no puede ser negativa.")
    if tasa_periodica <= -1:
        raise ValueError("La tasa periódica no puede ser <= -100% (indefinición matemática).")


def amortizacion_francesa(monto: float, tasa_periodica: float, n_periodos: int) -> pd.DataFrame:
    """
    Sistema Francés (cuota fija).

    Cuota = P * [ i (1+i)^n ] / [ (1+i)^n - 1 ]

    Parámetros:
        monto: monto del préstamo (principal)
        tasa_periodica: tasa de interés por periodo (decimal). Si la tasa
                        anual es 12% y los periodos son meses, usar 0.12/12.
        n_periodos: número total de cuotas

    Retorna:
        DataFrame con columnas: periodo, cuota, interes, amortizacion, saldo
    """
    _validar_parametros_prestamo(monto, tasa_periodica, n_periodos)
    if tasa_periodica == 0:
        cuota = monto / n_periodos
    else:
        i = tasa_periodica
        cuota = monto * (i * (1 + i) ** n_periodos) / ((1 + i) ** n_periodos - 1)

    filas = []
    saldo = monto
    for periodo in range(1, n_periodos + 1):
        interes = saldo * tasa_periodica
        amortizacion = cuota - interes
        saldo = max(saldo - amortizacion, 0)
        filas.append({
            "periodo": periodo,
            "cuota": round(cuota, 2),
            "interes": round(interes, 2),
            "amortizacion": round(amortizacion, 2),
            "saldo": round(saldo, 2),
        })

    return pd.DataFrame(filas)


def amortizacion_alemana(monto: float, tasa_periodica: float, n_periodos: int) -> pd.DataFrame:
    """
    Sistema Alemán (amortización de capital constante).

    La amortización de capital es siempre la misma (monto / n_periodos),
    por lo que la cuota total va disminuyendo periodo a periodo porque
    el interés se calcula sobre un saldo cada vez menor.

    Retorna:
        DataFrame con columnas: periodo, cuota, interes, amortizacion, saldo
    """
    _validar_parametros_prestamo(monto, tasa_periodica, n_periodos)
    amortizacion_fija = monto / n_periodos
    filas = []
    saldo = monto
    for periodo in range(1, n_periodos + 1):
        interes = saldo * tasa_periodica
        cuota = amortizacion_fija + interes
        saldo = max(saldo - amortizacion_fija, 0)
        filas.append({
            "periodo": periodo,
            "cuota": round(cuota, 2),
            "interes": round(interes, 2),
            "amortizacion": round(amortizacion_fija, 2),
            "saldo": round(saldo, 2),
        })

    return pd.DataFrame(filas)


def resumen_comparativo(monto: float, tasa_periodica: float, n_periodos: int) -> dict:
    """
    Compara el costo total (interés total pagado) entre ambos sistemas
    para el mismo préstamo. Útil para mostrar en el dashboard cuál
    conviene más según el criterio del estudiante.
    """
    tabla_fr = amortizacion_francesa(monto, tasa_periodica, n_periodos)
    tabla_al = amortizacion_alemana(monto, tasa_periodica, n_periodos)

    interes_total_fr = round(tabla_fr["interes"].sum(), 2)
    interes_total_al = round(tabla_al["interes"].sum(), 2)

    return {
        "interes_total_frances": interes_total_fr,
        "interes_total_aleman": interes_total_al,
        # Costo total = capital + todos los intereses pagados durante el
        # plazo. Es el número que de verdad permite comparar alternativas,
        # porque una cuota baja con plazo largo puede costar más en total.
        "costo_total_frances": round(monto + interes_total_fr, 2),
        "costo_total_aleman": round(monto + interes_total_al, 2),
        "cuota_inicial_frances": tabla_fr["cuota"].iloc[0],
        "cuota_inicial_aleman": tabla_al["cuota"].iloc[0],
        "cuota_final_frances": tabla_fr["cuota"].iloc[-1],
        "cuota_final_aleman": tabla_al["cuota"].iloc[-1],
    }
