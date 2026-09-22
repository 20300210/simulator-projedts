"""
Módulo: Valor del Dinero en el Tiempo
--------------------------------------
Contiene las fórmulas base de matemática financiera:
- Valor Futuro (VF) de un capital único
- Valor Presente (VP) de un monto futuro
- Valor Futuro de una anualidad (aportes periódicos constantes)
- Ajuste de un monto por inflación (poder adquisitivo real)

Convención usada en todo el módulo:
    tasa   -> tasa de interés periódica, en decimal (ej. 0.08 = 8%)
    n      -> número de periodos (años, meses, etc., debe ser consistente con 'tasa')
"""


def valor_futuro(capital: float, tasa: float, n: int) -> float:
    """
    Calcula el Valor Futuro de un capital inicial con interés compuesto.

    VF = VP * (1 + i)^n

    Parámetros:
        capital: monto inicial invertido (VP)
        tasa: tasa de interés por periodo (decimal)
        n: número de periodos

    Retorna:
        Valor futuro del capital.
    """
    if capital < 0 or n < 0:
        raise ValueError("El capital y el número de periodos deben ser no negativos.")
    return capital * (1 + tasa) ** n


def valor_presente(monto_futuro: float, tasa: float, n: int) -> float:
    """
    Calcula el Valor Presente de un monto que se recibirá en el futuro.

    VP = VF / (1 + i)^n

    Parámetros:
        monto_futuro: monto que se espera recibir en 'n' periodos
        tasa: tasa de descuento por periodo (decimal)
        n: número de periodos

    Retorna:
        Valor presente del monto futuro.
    """
    if n < 0:
        raise ValueError("El número de periodos debe ser no negativo.")
    return monto_futuro / (1 + tasa) ** n


def valor_futuro_anualidad(aporte: float, tasa: float, n: int, anticipada: bool = False) -> float:
    """
    Calcula el Valor Futuro de una serie de aportes periódicos iguales (anualidad).

    Anualidad vencida (aporte al final de cada periodo):
        VF = A * [ ((1 + i)^n - 1) / i ]

    Anualidad anticipada (aporte al inicio de cada periodo):
        VF = A * [ ((1 + i)^n - 1) / i ] * (1 + i)

    Parámetros:
        aporte: monto constante aportado cada periodo (A)
        tasa: tasa de interés por periodo (decimal)
        n: número de aportes
        anticipada: True si el aporte se hace al inicio del periodo

    Retorna:
        Valor futuro acumulado de la anualidad.
    """
    if tasa == 0:
        vf = aporte * n
    else:
        vf = aporte * (((1 + tasa) ** n - 1) / tasa)
        if anticipada:
            vf *= (1 + tasa)
    return vf


def valor_presente_anualidad(aporte: float, tasa: float, n: int, anticipada: bool = False) -> float:
    """
    Calcula el Valor Presente de una serie de aportes/retiros periódicos iguales.
    Útil para pensar cuánto capital se necesita HOY para financiar 'n' retiros futuros
    (por ejemplo, en un plan de retiro).

    VP = A * [ (1 - (1 + i)^-n) / i ]
    """
    if tasa == 0:
        vp = aporte * n
    else:
        vp = aporte * ((1 - (1 + tasa) ** (-n)) / tasa)
        if anticipada:
            vp *= (1 + tasa)
    return vp


def ajustar_por_inflacion(monto_nominal: float, inflacion_anual: float, anios: int) -> float:
    """
    Convierte un monto nominal futuro a su valor real (poder adquisitivo de hoy),
    descontando la inflación acumulada.

    Monto real = Monto nominal / (1 + inflación)^años
    """
    return monto_nominal / (1 + inflacion_anual) ** anios
