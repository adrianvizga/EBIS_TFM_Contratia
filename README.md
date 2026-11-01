# ContratIA

ContratIA es una aplicación web para revisar, generar y consultar contratos con
ayuda de inteligencia artificial. Está orientada al derecho español y reúne en
un mismo entorno el análisis contractual, la creación de borradores y un chat
jurídico apoyado en fuentes legales.

El proyecto se ejecuta íntegramente con Docker Compose. La interfaz está hecha
con React, la API con FastAPI y las tareas de análisis se procesan en segundo
plano con Celery. PostgreSQL almacena los datos de la aplicación, Redis coordina
las tareas y Qdrant contiene el corpus jurídico utilizado por el sistema RAG.

## Análisis de contratos

Se puede subir un contrato en PDF, DOCX o TXT. El análisis se ejecuta en segundo
plano y separa el documento por cláusulas para ofrecer:

- Un nivel de riesgo general y un resumen del resultado.
- Riesgos, aspectos favorables y elementos que podrían faltar.
- Una explicación en lenguaje claro de cada cláusula y, cuando procede,
  recomendaciones.
- Relaciones entre cláusulas, como contradicciones, duplicidades, dependencias
  o referencias a cláusulas inexistentes.
- Las fuentes jurídicas recuperadas durante el análisis.

Los resultados permanecen asociados a la cuenta del usuario. Desde la
aplicación se pueden consultar de nuevo, filtrar por estado o nivel de riesgo y
descargar como informe PDF. Un análisis que haya terminado con error se puede
reintentar sin subir otra vez el archivo ni consumir una nueva unidad de cuota.

### Alcance y límites

- Se admiten archivos de hasta 10 MB y 200 páginas.
- Los PDF deben tener una capa de texto. Los documentos escaneados requieren
  OCR previo y la aplicación los rechaza con un mensaje específico.
- La cobertura incluye arrendamiento de vivienda, arrendamiento de local y
  cobertura general B2B/B2C para prestación de servicios.
- El corpus v2 cubre 13 normas: Código Civil, arrendamientos urbanos,
  consumo, condiciones generales de contratación, morosidad comercial,
  comercio electrónico, RGPD, LOPDGDD, propiedad intelectual, Código de
  Comercio, autónomos y firma electrónica (Ley 6/2020 y Reglamento eIDAS).
- La cobertura general excluye contratación pública, conflictos internacionales
  y normativa sectorial específica, como banca, seguros, sanidad,
  telecomunicaciones, transporte, turismo o energía.
- La revisión jurídica humana final del corpus v2 está pendiente; no queda
  sustituida por las evaluaciones automáticas superadas.
- `RAG_SCORE_THRESHOLD` fija la relevancia mínima de los fragmentos recuperados
  y tiene un valor predeterminado de `0.35`.

El resultado sirve como apoyo para revisar un documento, pero no sustituye el
criterio de un profesional del derecho.

## Chatbot jurídico

El chatbot mantiene conversaciones persistentes y puede vincular un contrato analizado o generado. El vínculo se conserva en las preguntas de seguimiento hasta que el usuario lo retire o seleccione otro contrato. El backend comprueba tanto la propiedad del contrato como el acceso del plan.

Las instrucciones del asistente están versionadas como `legal-chat-v2`. Los contratos y fragmentos recuperados se envían como datos no confiables, nunca como instrucciones. Las respuestas usan el idioma configurado por el usuario, validan las citas contra el resultado RAG y se abstienen cuando el corpus no aporta respaldo suficiente. El corpus incluido se limita a las fuentes descritas en “Límites del análisis contractual”; el chatbot ofrece información orientativa y no sustituye asesoramiento profesional.

Cada turno es idempotente, se persiste de forma atómica y registra modelo, versión de prompt, tokens y evidencia empleada. Las llamadas transitorias se reintentan y pueden utilizar `OPENAI_FALLBACK_MODEL`. Los límites se configuran mediante `CHAT_MAX_INPUT_CHARS`, `CHAT_MAX_HISTORY_TOKENS`, `CHAT_MAX_CONTRACT_TOKENS`, `CHAT_MAX_OUTPUT_TOKENS` y `CHAT_OPENAI_TIMEOUT_SECONDS`.

## Generación de contratos

La aplicación genera borradores para España en español y tono legal formal. Los tipos cubiertos son arrendamiento de vivienda, arrendamiento de local y prestación de servicios con cobertura general no sectorial. Todo borrador requiere revisión profesional antes de firmarse.

El flujo usa los estados `pending`, `processing`, `completed` y `error`, permite reintentar errores y conserva un historial transaccional de versiones. Los prompts y el modelo utilizado quedan identificados en el contrato generado.


## Requisito

Docker Desktop o Docker Engine con Docker Compose v2. No es necesario instalar
Python, Node.js, PostgreSQL, Redis ni Qdrant.

## Arranque

1. Crea el archivo de configuración:

   ~~~bash
   cp .env.example .env
   ~~~

   En PowerShell:

   ~~~powershell
   Copy-Item .env.example .env
   ~~~

2. Edita .env, establece una OPENAI_API_KEY válida y cambia los secretos de
   demostración. `OPENAI_MODEL` selecciona el modelo compartido por la
   generación, el análisis de contratos y el chatbot;
   `OPENAI_FALLBACK_MODEL` define la alternativa para generación y
   modificación cuando falla el modelo principal. `OPENAI_EMBEDDING_MODEL`
   selecciona el modelo de embeddings y debe coincidir con el empleado para
   generar la caché y la colección de Qdrant.
3. Construye y levanta el sistema:

   ~~~bash
   docker compose up --build
   ~~~

4. Abre http://localhost:3000.

En el primer arranque se crea el esquema PostgreSQL y se cargan en Qdrant los
2.786 fragmentos del corpus v2. Con la configuración de ejemplo también se crea la cuenta local
`demo@ebistfm.com` con contraseña `demo` y rol administrador.

El directorio `dataset/` contiene contratos de ejemplo con datos ficticios listos
para subir y probar el análisis sin necesidad de preparar documentos propios.

## Operación

~~~bash
# Segundo plano
docker compose up --build -d

# Estado y logs
docker compose ps
docker compose logs -f

# Parar conservando datos
docker compose down

# Reinicio completo y destructivo de datos
docker compose down -v
~~~

Los volúmenes conservan PostgreSQL, Redis, Qdrant y los contratos subidos.


## Servicios

- frontend: Nginx y React, único puerto público.
- backend: API FastAPI.
- worker: procesamiento asíncrono Celery.
- postgres, redis y qdrant: almacenamiento persistente.
- db-init y qdrant-init: inicializadores de una sola ejecución.
