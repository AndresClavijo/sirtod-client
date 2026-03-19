# Plan de Implementación: Streamlit Chatbot UI

## Descripción General

Extraer la lógica de negocio de `main.py` en un módulo reutilizable `chat_engine.py`, crear la aplicación Streamlit `app.py` que consuma ese módulo, refactorizar `main.py` para importar desde `chat_engine`, y validar las propiedades de correctitud con tests basados en Hypothesis.

## Tareas

- [x] 1. Crear el módulo `chat_engine.py` con la lógica de negocio extraída
  - [x] 1.1 Crear `chat_engine.py` con las constantes, dataclasses y funciones utilitarias
    - Definir `OPENAI_MODEL`, `SYSTEM_PROMPT`, `MAX_ITERATIONS`
    - Crear dataclasses `ToolCallLog` y `ProcessResult`
    - Implementar `mcp_tools_to_openai()` (extraída de `main.py`)
    - Implementar `is_clarification_request()` (extraída de `main.py`)
    - Implementar función de truncamiento de resultados (límite 2000 caracteres)
    - _Requisitos: 7.1, 1.2, 3.6, 4.5_

  - [x] 1.2 Implementar las funciones asíncronas `connect_mcp` y `discover_tools`
    - `connect_mcp(server_url)` crea y retorna un cliente MCP conectado
    - `discover_tools(mcp_client)` descubre herramientas y retorna `(mcp_tools, openai_tools)`
    - _Requisitos: 1.1, 1.2, 7.1, 7.2_

  - [x] 1.3 Implementar `process_query` con el ciclo completo de herramientas
    - Enviar mensajes a OpenAI con herramientas disponibles
    - Ejecutar tool_calls en MCP y registrar en `ToolCallLog`
    - Ciclo hasta respuesta final o `MAX_ITERATIONS` (15)
    - Capturar errores de tool_calls y registrar con `is_error=True`
    - Detectar solicitudes de aclaración con `is_clarification_request`
    - Modificar `messages` in-place y retornar `ProcessResult`
    - _Requisitos: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 7.2_

  - [ ]* 1.4 Escribir test de propiedad para conversión MCP-a-OpenAI
    - **Propiedad 1: Conversión MCP-a-OpenAI preserva estructura**
    - Generar herramientas MCP con nombre, descripción y schema aleatorios
    - Verificar que `function.name`, `function.description` y `function.parameters` se preservan
    - **Valida: Requisito 1.2**

  - [ ]* 1.5 Escribir test de propiedad para detección de aclaración
    - **Propiedad 5: Detección de solicitudes de aclaración**
    - Generar cadenas con/sin prefijo `ACLARACION_USUARIO:` y verificar detección correcta
    - Verificar que `None` y cadenas vacías retornan `False`
    - **Valida: Requisito 3.6**

  - [ ]* 1.6 Escribir test de propiedad para truncamiento de resultados
    - **Propiedad 7: Truncamiento de resultados largos**
    - Generar cadenas de longitud variable (0 a 5000 caracteres)
    - Verificar que cadenas >2000 se truncan con indicador, y las demás no se modifican
    - **Valida: Requisito 4.5**

  - [ ]* 1.7 Escribir test de propiedad para integridad de ToolCallLog
    - **Propiedad 6: Integridad de datos en ToolCallLog**
    - Generar ejecuciones de herramientas con resultados/errores aleatorios
    - Verificar que `name` no está vacío, `arguments` es serializable a JSON, `result` es string
    - Verificar que si la herramienta falló, `is_error` es `True`
    - **Valida: Requisitos 4.2, 3.5**

- [x] 2. Checkpoint - Verificar que `chat_engine.py` y sus tests funcionan
  - Asegurar que todos los tests pasan, preguntar al usuario si surgen dudas.

- [x] 3. Crear la aplicación Streamlit `app.py`
  - [x] 3.1 Crear `app.py` con inicialización de sesión y conexión MCP
    - Configurar `st.set_page_config` con título y layout
    - Verificar `OPENAI_API_KEY` → `st.error()` + `st.stop()` si falta
    - Inicializar `st.session_state` con `mcp_client`, `openai_client`, `openai_tools`, `messages`, `tool_logs`, `initialized`
    - Conectar MCP y descubrir herramientas usando `chat_engine.connect_mcp()` y `chat_engine.discover_tools()`
    - Manejar errores de conexión con `st.error()` + `st.stop()`
    - _Requisitos: 1.1, 1.2, 1.3, 1.4, 5.1, 5.2_

  - [x] 3.2 Implementar el área de chat principal con `st.chat_message` y `st.chat_input`
    - Renderizar título y descripción del asistente
    - Iterar `st.session_state.messages` y mostrar con `st.chat_message` (omitir system y tool)
    - Implementar `st.chat_input` para capturar consultas del usuario
    - Agregar mensaje del usuario a `st.session_state.messages`
    - Llamar `chat_engine.process_query()` con `asyncio.run()` dentro de `st.spinner`
    - Acumular `tool_logs` en `st.session_state.tool_logs`
    - _Requisitos: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 6.1, 6.2, 6.3_

  - [x] 3.3 Implementar el Panel_Debug en `st.sidebar`
    - Mostrar título "🔧 Llamadas a Herramientas" en sidebar
    - Crear `st.expander` por cada `ToolCallLog` con nombre de herramienta
    - Mostrar argumentos en `st.code` (JSON) y resultado truncado a 2000 caracteres
    - Mostrar indicación de truncamiento si el resultado excede 2000 caracteres
    - Agregar botón "🗑️ Nueva conversación" que reinicia `messages` con solo `SYSTEM_PROMPT`
    - _Requisitos: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 5.3, 5.4, 6.4_

- [x] 4. Refactorizar `main.py` para importar desde `chat_engine`
  - [x] 4.1 Refactorizar `main.py` para usar `chat_engine`
    - Importar constantes (`OPENAI_MODEL`, `SYSTEM_PROMPT`, `MAX_ITERATIONS`) desde `chat_engine`
    - Importar funciones (`mcp_tools_to_openai`, `is_clarification_request`, `connect_mcp`, `discover_tools`, `process_query`) desde `chat_engine`
    - Importar dataclasses (`ToolCallLog`, `ProcessResult`) desde `chat_engine`
    - Eliminar las funciones duplicadas de `main.py`
    - Reescribir `run()` para usar `process_query()` y renderizar `ToolCallLog` con Rich
    - Mantener toda la visualización Rich existente
    - _Requisitos: 7.1, 7.3, 7.4_

  - [ ]* 4.2 Escribir test de propiedad para crecimiento del historial de mensajes
    - **Propiedad 2: El historial de mensajes crece tras cada consulta**
    - Mock de OpenAI que retorna texto → verificar que `len(messages)` crece estrictamente
    - **Valida: Requisitos 2.6, 3.2**

  - [ ]* 4.3 Escribir test de propiedad para correspondencia tool_calls → tool messages
    - **Propiedad 3: Cada tool_call genera un mensaje tool correspondiente**
    - Mock de OpenAI con N tool_calls aleatorios → verificar N mensajes `role: "tool"` con `tool_call_id` correcto
    - **Valida: Requisito 3.2**

  - [ ]* 4.4 Escribir test de propiedad para terminación dentro del límite
    - **Propiedad 4: process_query termina dentro del límite de iteraciones**
    - Mock de OpenAI que siempre retorna tool_calls → verificar `iterations <= MAX_ITERATIONS` y `hit_max_iterations == True`
    - **Valida: Requisitos 3.3, 3.4**

- [x] 5. Actualizar dependencias y configuración final
  - [x] 5.1 Actualizar `requirements.txt` con nuevas dependencias
    - Agregar `streamlit>=1.28` para la interfaz web
    - Agregar `hypothesis>=6.0` para tests basados en propiedades
    - Agregar `pytest>=7.0` como framework de testing
    - _Requisitos: 6.1_

  - [x] 5.2 Crear `tests/conftest.py` con fixtures compartidos
    - Crear directorio `tests/` si no existe
    - Definir fixtures para mocks de OpenAI y MCP client
    - Configurar generadores de Hypothesis reutilizables
    - _Requisitos: 7.2_

- [x] 6. Checkpoint final - Verificar integración completa
  - Asegurar que todos los tests pasan, preguntar al usuario si surgen dudas.

## Notas

- Las tareas marcadas con `*` son opcionales y pueden omitirse para un MVP más rápido
- Cada tarea referencia requisitos específicos para trazabilidad
- Los checkpoints aseguran validación incremental
- Los tests de propiedades validan propiedades universales de correctitud
- Los tests unitarios validan ejemplos específicos y casos borde
