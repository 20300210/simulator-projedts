# FinSim — Simulador Financiero Universitario

Simulador interactivo construido en Python + Streamlit para el curso de Finanzas.
Integra cinco módulos, incluyendo uno especializado en **financiación de
posgrado en Colombia** (el caso de uso principal del proyecto), más un
componente de **simulación de riesgo (Monte Carlo)** para inversiones.

## 🚀 Cómo correrlo

1. Instala las dependencias (idealmente en un entorno virtual):
   ```bash
   pip install -r requirements.txt
   ```
2. Ejecuta la app:
   ```bash
   streamlit run app.py
   ```
3. Se abrirá automáticamente en tu navegador (normalmente en `http://localhost:8501`).

## 📂 Estructura del proyecto

```
finsim/
├── app.py                     # Interfaz web (Streamlit) — punto de entrada
├── requirements.txt           # Dependencias
├── modulos/
│   ├── valor_dinero.py        # VF, VP, anualidades, ajuste por inflación
│   ├── evaluacion.py          # VAN, TIR (bisección), Payback
│   ├── prestamos.py           # Amortización Francesa y Alemana + costo total
│   ├── portafolio.py          # Monte Carlo + escenarios macroeconómicos
│   └── posgrado.py            # Financiación de posgrado en Colombia
└── tests/
    └── test_modulos.py        # Pruebas unitarias de todas las fórmulas
```

## 🎓 Módulo de Financiación de Posgrado (Colombia) — alcance "Opción A"

Cubre exactamente el alcance delimitado del proyecto: **desembolso único,
tasa constante durante la simulación, sistema de cuota fija**. Incluye:

- **Costo total del crédito** (capital + todos los intereses).
- **Capacidad de pago**: ¿la cuota nueva es manejable frente al ingreso?
- **Nivel de endeudamiento**: cuota nueva + otras deudas, frente al ingreso.
- **Escenario de disminución de ingresos**: ¿sigue siendo pagable si el
  ingreso cae (ej. 30%) durante el posgrado?
- **Sensibilidad de tasa**: comparación de escenarios de tasa constante
  distintos entre sí (no un crédito de tasa variable real — eso queda
  fuera del alcance de la Opción A).
- **Comparación de N alternativas** (ICETEX, banco, fondo/cooperativa, u
  otras) lado a lado, ordenadas por costo total, marcando cuáles cumplen
  los umbrales de capacidad de pago y endeudamiento.

Las alternativas vienen prellenadas con tasas de ejemplo — reemplázalas
por las tasas reales que te ofrezca cada entidad al momento de sustentar.

## 🧠 Otros módulos incluidos

| Módulo | Conceptos | Fórmula clave |
|---|---|---|
| Valor del Dinero | Interés compuesto, anualidades, inflación | VF = VP(1+i)ⁿ |
| Evaluación de Proyectos | VAN, TIR, Payback | VAN = Σ FCₜ/(1+i)ᵗ |
| Préstamos | Amortización Francesa vs Alemana | Cuota = P·i(1+i)ⁿ / [(1+i)ⁿ-1] |
| Portafolio | Simulación Monte Carlo, riesgo/retorno | Rₜ ~ N(μ, σ) |

## 🧪 Correr las pruebas

```bash
python tests/test_modulos.py
```

26 pruebas: funcionales (fórmulas conocidas) + de seguridad (rechazo de
valores negativos, absurdos, o mal formados) para los cinco módulos.

## 📝 Ampliaciones futuras (mencionadas explícitamente como fuera de alcance)

- **Desembolsos semestrales** (en vez de desembolso único).
- **Modelos de tasa variable real** (hoy solo hay análisis de sensibilidad
  con tasas constantes distintas, no un crédito que cambie de tasa a mitad
  de camino).
- Conectar a datos de mercado reales con `yfinance` para el módulo de
  portafolio.
- Exportar la comparación de alternativas a PDF o Excel para el informe.

