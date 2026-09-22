# Auditoría de Seguridad — FinSim

Este documento resume la revisión de seguridad aplicada al código del proyecto,
para efectos de documentación académica.

## Alcance y contexto

FinSim es una aplicación de escritorio/local (Streamlit) sin base de datos,
sin autenticación de usuarios y sin conexión a APIs externas. Por lo tanto,
categorías clásicas como inyección SQL, XSS almacenado, o fuga de credenciales
en tránsito **no aplican en este momento**. La auditoría se enfocó en las
categorías que sí son relevantes para este tipo de aplicación:

- Validación de entradas y manejo de errores
- Denegación de servicio (DoS) por parámetros absurdos
- Seguridad de la cadena de suministro (dependencias)
- Buenas prácticas de hardening ante un futuro despliegue público

## Hallazgos y correcciones aplicadas

### 1. Fuga de información vía tracebacks (Severidad: Media)
**Problema:** las excepciones no controladas en `app.py` se propagaban hasta
la interfaz, exponiendo rutas de archivos y estructura interna del código al
usuario final.
**Corrección:** se agregó la función `manejar_error()` que registra el error
completo con `logging` (lado servidor) y muestra un mensaje genérico y
accionable al usuario (patrón *fail closed with a safe message*).

### 2. Validación de entradas ausente a nivel de módulo (Severidad: Media)
**Problema:** los módulos (`prestamos.py`, `portafolio.py`, `evaluacion.py`)
confiaban en que la interfaz (`app.py`) ya había validado los datos. Si se
reutilizan desde otro script, notebook o una futura API, no había ninguna
barrera contra valores negativos, cero, o vacíos.
**Corrección:** se agregó validación defensiva (*fail fast*) directamente en
cada función/clase: `_validar_parametros_prestamo()`, `Activo.__post_init__()`,
chequeos en `tir()` y `payback()`.

### 3. Denegación de servicio por parámetros absurdos (Severidad: Media)
**Problema:** nada impedía pedir, por ejemplo, una simulación de Monte Carlo
con millones de escenarios o un préstamo a un millón de cuotas, lo cual podría
agotar la memoria/CPU del servidor si la app se expusiera públicamente.
**Corrección:** se agregaron límites explícitos (`n_periodos <= 1200`,
`n_simulaciones <= 20000`, `anios <= 100`) con mensajes de error claros.

### 4. Dependencias sin versión fijada (Severidad: Media — cadena de suministro)
**Problema:** `requirements.txt` usaba `>=`, lo que permite instalar
automáticamente versiones futuras no auditadas, incluyendo posibles versiones
con vulnerabilidades conocidas (CVEs).
**Corrección:** se fijaron versiones exactas (`==`). Recomendación adicional:
correr periódicamente `pip-audit` o `safety check` sobre el entorno para
detectar CVEs conocidos en las dependencias.

### 5. Falta de hardening para despliegue público (Severidad: Baja, condicional)
**Problema:** no existía configuración explícita de Streamlit para CSRF/CORS.
**Corrección:** se agregó `.streamlit/config.toml` con `enableXsrfProtection`,
`enableCORS` y un límite de tamaño de subida de archivos, listo para el día
en que se decida publicar la app.

### 6. Higiene de repositorio (Severidad: Baja)
**Corrección:** se agregó `.gitignore` para evitar subir accidentalmente
entornos virtuales, cachés de Python, o futuros archivos de secretos
(`.env`, `secrets.toml`) a un repositorio de la universidad.

## Recomendaciones para trabajo futuro

Si este proyecto se extiende (por ejemplo, conectando datos de mercado reales
vía una API con clave, o agregando login de usuarios), considerar:

- **Gestión de secretos**: nunca hardcodear API keys en el código; usar
  `st.secrets` o variables de entorno.
- **Rate limiting**: si se publica, limitar cuántas simulaciones puede pedir
  un mismo usuario por minuto.
- **Análisis estático automatizado**: correr `bandit` (linter de seguridad
  para Python) como parte del flujo de trabajo.
- **Autenticación**, si se agregan datos por usuario, en vez de una app
  totalmente abierta.

## Resultado de las pruebas

Se agregaron 5 pruebas de seguridad específicas a `tests/test_modulos.py`
(rechazo de periodos negativos, límites anti-DoS, validación de pesos de
activos, validación de listas vacías). Las 16 pruebas (11 funcionales + 5 de
seguridad) pasan correctamente.
