"""
Pruebas rápidas de las fórmulas financieras clave.
Se puede correr con: python -m pytest tests/  (si tienes pytest instalado)
o simplemente: python tests/test_modulos.py
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from modulos.valor_dinero import valor_futuro, valor_presente, valor_futuro_anualidad
from modulos.evaluacion import van, tir, payback, evaluar_proyecto
from modulos.prestamos import amortizacion_francesa, amortizacion_alemana
from modulos.portafolio import Activo, simular_portafolio_monte_carlo, probabilidad_de_meta
from modulos.posgrado import (
    costo_total_credito,
    capacidad_pago,
    nivel_endeudamiento,
    escenario_disminucion_ingreso,
    sensibilidad_tasa,
    comparar_alternativas,
)


def test_valor_futuro():
    # $1000 al 10% anual durante 2 años -> 1000 * 1.1^2 = 1210
    assert abs(valor_futuro(1000, 0.10, 2) - 1210.0) < 1e-6
    print("OK: valor_futuro")


def test_valor_presente():
    # Inverso del anterior
    assert abs(valor_presente(1210.0, 0.10, 2) - 1000.0) < 1e-6
    print("OK: valor_presente")


def test_anualidad():
    # $100 anuales al 5%, 3 años -> 100*[(1.05^3 -1)/0.05] = 315.25
    resultado = valor_futuro_anualidad(100, 0.05, 3)
    assert abs(resultado - 315.25) < 0.01
    print("OK: valor_futuro_anualidad")


def test_van_positivo():
    # Inversión de 1000, retorna 600 por 2 años, tasa 10% -> VAN > 0
    flujos = [-1000, 600, 600]
    resultado = van(0.10, flujos)
    assert resultado > 0
    print(f"OK: van (VAN={resultado:.2f})")


def test_tir_conocida():
    # Caso clásico: -1000, 500, 500, 500 -> TIR ~ 23.4%
    flujos = [-1000, 500, 500, 500]
    resultado = tir(flujos)
    assert 0.20 < resultado < 0.27
    print(f"OK: tir (TIR={resultado*100:.2f}%)")


def test_payback():
    flujos = [-1000, 400, 400, 400, 400]
    resultado = payback(flujos)
    assert 2 < resultado < 3
    print(f"OK: payback ({resultado:.2f} periodos)")


def test_amortizacion_francesa_saldo_final_cero():
    tabla = amortizacion_francesa(10000, 0.01, 12)  # 1% mensual, 12 cuotas
    assert abs(tabla["saldo"].iloc[-1]) < 0.5
    print("OK: amortizacion_francesa (saldo final ~0)")


def test_amortizacion_alemana_saldo_final_cero():
    tabla = amortizacion_alemana(10000, 0.01, 12)
    assert abs(tabla["saldo"].iloc[-1]) < 0.5
    print("OK: amortizacion_alemana (saldo final ~0)")


def test_amortizacion_alemana_cuotas_decrecientes():
    tabla = amortizacion_alemana(10000, 0.01, 12)
    assert tabla["cuota"].iloc[0] > tabla["cuota"].iloc[-1]
    print("OK: amortizacion_alemana (cuotas decrecientes)")


def test_monte_carlo_portafolio():
    activos = [
        Activo("Acciones", peso=0.6, rendimiento_esperado=0.10, volatilidad=0.18),
        Activo("Bonos", peso=0.4, rendimiento_esperado=0.04, volatilidad=0.05),
    ]
    trayectorias = simular_portafolio_monte_carlo(
        capital_inicial=10000, activos=activos, anios=10, n_simulaciones=500
    )
    # Debe tener 11 filas (año 0 a 10) y 500 columnas (simulaciones)
    assert trayectorias.shape == (11, 500)
    prob = probabilidad_de_meta(trayectorias, meta=15000)
    assert 0 <= prob <= 100
    print(f"OK: simular_portafolio_monte_carlo (prob. de llegar a 15000: {prob:.1f}%)")


def test_escenario_crisis_reduce_resultado_esperado():
    activos = [Activo("Acciones", peso=1.0, rendimiento_esperado=0.10, volatilidad=0.18)]
    base = simular_portafolio_monte_carlo(10000, activos, 10, 2000, escenario="base", semilla=1)
    crisis = simular_portafolio_monte_carlo(10000, activos, 10, 2000, escenario="crisis", semilla=1)
    assert crisis.iloc[-1, :].mean() < base.iloc[-1, :].mean()
    print("OK: escenario 'crisis' reduce el resultado esperado vs 'base'")


def test_seguridad_prestamo_rechaza_periodos_negativos():
    try:
        amortizacion_francesa(10000, 0.01, -5)
        assert False, "Debió lanzar ValueError con n_periodos negativo"
    except ValueError:
        print("OK (seguridad): amortizacion_francesa rechaza n_periodos negativo")


def test_seguridad_prestamo_rechaza_periodos_excesivos():
    try:
        amortizacion_francesa(10000, 0.01, 999999)
        assert False, "Debió lanzar ValueError con n_periodos absurdamente grande (anti-DoS)"
    except ValueError:
        print("OK (seguridad): amortizacion_francesa rechaza n_periodos excesivo (límite anti-DoS)")


def test_seguridad_activo_rechaza_peso_invalido():
    try:
        Activo("Cripto", peso=1.5, rendimiento_esperado=0.5, volatilidad=0.9)
        assert False, "Debió lanzar ValueError con peso > 1"
    except ValueError:
        print("OK (seguridad): Activo rechaza peso fuera de [0,1]")


def test_seguridad_monte_carlo_rechaza_simulaciones_excesivas():
    activos = [Activo("Acciones", peso=1.0, rendimiento_esperado=0.10, volatilidad=0.18)]
    try:
        simular_portafolio_monte_carlo(10000, activos, anios=10, n_simulaciones=999_999_999)
        assert False, "Debió lanzar ValueError con n_simulaciones absurdamente grande (anti-DoS)"
    except ValueError:
        print("OK (seguridad): simular_portafolio_monte_carlo rechaza n_simulaciones excesivo")


def test_seguridad_tir_rechaza_lista_vacia():
    try:
        tir([])
        assert False, "Debió lanzar ValueError con lista de flujos vacía"
    except ValueError:
        print("OK (seguridad): tir rechaza lista de flujos vacía")


# ------------------- Módulo de posgrado (Colombia) -------------------

def test_costo_total_credito():
    resultado = costo_total_credito(monto=10000, interes_total=2500)
    assert resultado == 12500
    print(f"OK: costo_total_credito ({resultado})")


def test_capacidad_pago_cumple():
    resultado = capacidad_pago(cuota_mensual=500_000, ingreso_mensual=2_000_000, umbral=0.35)
    # 500000/2000000 = 25% <= 35% -> cumple
    assert resultado["cumple"] is True
    assert abs(resultado["ratio"] - 0.25) < 1e-6
    print(f"OK: capacidad_pago cumple (ratio={resultado['ratio_pct']:.1f}%)")


def test_capacidad_pago_no_cumple():
    resultado = capacidad_pago(cuota_mensual=900_000, ingreso_mensual=2_000_000, umbral=0.35)
    # 900000/2000000 = 45% > 35% -> no cumple
    assert resultado["cumple"] is False
    print(f"OK: capacidad_pago detecta cuando NO cumple (ratio={resultado['ratio_pct']:.1f}%)")


def test_nivel_endeudamiento_incluye_otras_deudas():
    resultado = nivel_endeudamiento(cuota_mensual=400_000, ingreso_mensual=2_000_000, otras_deudas_mensuales=300_000, umbral=0.40)
    # (400000+300000)/2000000 = 35% <= 40% -> cumple
    assert resultado["carga_total"] == 700_000
    assert resultado["cumple"] is True
    print(f"OK: nivel_endeudamiento con otras deudas (ratio={resultado['ratio_pct']:.1f}%)")


def test_escenario_disminucion_ingreso_empeora_ratio():
    normal = nivel_endeudamiento(cuota_mensual=500_000, ingreso_mensual=2_000_000)
    estres = escenario_disminucion_ingreso(ingreso_mensual=2_000_000, porcentaje_disminucion=0.30, cuota_mensual=500_000)
    assert estres["ratio"] > normal["ratio"]
    assert estres["ingreso_reducido"] == 1_400_000
    print(f"OK: escenario_disminucion_ingreso empeora el ratio ({normal['ratio_pct']:.1f}% -> {estres['ratio_pct']:.1f}%)")


def test_sensibilidad_tasa_cuota_sube_con_tasa():
    tabla = sensibilidad_tasa(monto=20_000_000, tasa_anual_base=0.12, plazo_meses=48)
    fila_menos2 = tabla[tabla["delta_pp"] == -2].iloc[0]
    fila_mas2 = tabla[tabla["delta_pp"] == 2].iloc[0]
    assert fila_mas2["cuota_mensual"] > fila_menos2["cuota_mensual"]
    print("OK: sensibilidad_tasa (cuota sube cuando sube la tasa, como debe ser)")


def test_comparar_alternativas_ordena_por_costo_total():
    alternativas = [
        {"nombre": "ICETEX", "monto": 20_000_000, "tasa_anual": 0.09, "plazo_meses": 60},
        {"nombre": "Banco", "monto": 20_000_000, "tasa_anual": 0.19, "plazo_meses": 48},
    ]
    resultado = comparar_alternativas(alternativas, ingreso_mensual=3_000_000)
    # ICETEX tiene tasa mucho más baja -> debería quedar primero (menor costo total)
    assert resultado.iloc[0]["nombre"] == "ICETEX"
    assert "endeudamiento_pct" in resultado.columns
    assert "capacidad_pago_pct" in resultado.columns
    print("OK: comparar_alternativas ordena correctamente por costo total")


def test_seguridad_comparar_alternativas_rechaza_nombres_duplicados():
    alternativas = [
        {"nombre": "Banco X", "monto": 10_000_000, "tasa_anual": 0.15, "plazo_meses": 24},
        {"nombre": "Banco X", "monto": 15_000_000, "tasa_anual": 0.12, "plazo_meses": 36},
    ]
    try:
        comparar_alternativas(alternativas)
        assert False, "Debió lanzar ValueError con nombres duplicados"
    except ValueError:
        print("OK (seguridad): comparar_alternativas rechaza nombres de alternativa duplicados")


def test_seguridad_capacidad_pago_rechaza_ingreso_cero():
    try:
        capacidad_pago(cuota_mensual=100, ingreso_mensual=0)
        assert False, "Debió lanzar ValueError con ingreso_mensual=0"
    except ValueError:
        print("OK (seguridad): capacidad_pago rechaza ingreso mensual <= 0")


if __name__ == "__main__":
    test_valor_futuro()
    test_valor_presente()
    test_anualidad()
    test_van_positivo()
    test_tir_conocida()
    test_payback()
    test_amortizacion_francesa_saldo_final_cero()
    test_amortizacion_alemana_saldo_final_cero()
    test_amortizacion_alemana_cuotas_decrecientes()
    test_monte_carlo_portafolio()
    test_escenario_crisis_reduce_resultado_esperado()
    test_seguridad_prestamo_rechaza_periodos_negativos()
    test_seguridad_prestamo_rechaza_periodos_excesivos()
    test_seguridad_activo_rechaza_peso_invalido()
    test_seguridad_monte_carlo_rechaza_simulaciones_excesivas()
    test_seguridad_tir_rechaza_lista_vacia()
    test_costo_total_credito()
    test_capacidad_pago_cumple()
    test_capacidad_pago_no_cumple()
    test_nivel_endeudamiento_incluye_otras_deudas()
    test_escenario_disminucion_ingreso_empeora_ratio()
    test_sensibilidad_tasa_cuota_sube_con_tasa()
    test_comparar_alternativas_ordena_por_costo_total()
    test_seguridad_comparar_alternativas_rechaza_nombres_duplicados()
    test_seguridad_capacidad_pago_rechaza_ingreso_cero()
    print("\n✅ Todas las pruebas (funcionales + seguridad) pasaron correctamente.")
