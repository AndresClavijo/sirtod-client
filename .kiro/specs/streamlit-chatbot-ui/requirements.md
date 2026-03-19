# Documento de Requisitos

## Introducción

Este documento define los requisitos para una interfaz web de chatbot construida con Streamlit que envuelve la lógica existente de MCP + OpenAI del archivo `main.py`. La aplicación permite al usuario realizar consultas de estadísticas del Perú (SIRTOD/MoSPI) a través de una interfaz de chat web, con una sección colapsable que muestra las llamadas a herramientas y sus respuestas en tiempo real.

## Glosario

- **Chatbot_UI**: La interfaz web de Streamlit que presenta el chat al usuario.
- **MCP_Client**: El cliente FastMCP que se conecta al servidor MoSPI MCP para ejecutar herramientas.
- **OpenAI_Client**: El cliente de OpenAI que envía mensajes al modelo gpt-4o-mini y recibe respuestas.
- **Chat_Engine**: El módulo que orquesta la comunicación entre el usuario, OpenAI_Client y MCP_Client, reutilizando la lógica de `main.py`.
- **Panel_Debug**: La sección colapsable/expandible de la interfaz que muestra las llamadas a herramientas, argumentos y resultados.
- **Historial_Mensajes**: La lista de mensajes intercambiados entre el usuario y el asistente durante la sesión.
- **Tool_Call**: Una invocación de herramienta MCP solicitada por el modelo de OpenAI durante el flujo de resolución.

## Requisitos

### Requisito 1: Inicialización de la sesión y conexión MCP

**User Story:** Como usuario, quiero que la aplicación se conecte automáticamente al servidor MCP al iniciar, para poder realizar consultas sin configuración manual.

#### Criterios de Aceptación

1. WHEN la aplicación Streamlit se inicia, THE Chat_Engine SHALL establecer conexión con el servidor MCP usando la URL configurada en la variable de entorno `MCP_SERVER_URL`.
2. WHEN la conexión MCP se establece exitosamente, THE Chat_Engine SHALL descubrir las herramientas disponibles y convertirlas al formato OpenAI.
3. IF la variable de entorno `OPENAI_API_KEY` no está configurada o es inválida, THEN THE Chatbot_UI SHALL mostrar un mensaje de error descriptivo al usuario.
4. IF la conexión al servidor MCP falla, THEN THE Chatbot_UI SHALL mostrar un mensaje de error indicando que el servidor MCP no está disponible.
5. WHEN la sesión se inicializa correctamente, THE Chat_Engine SHALL almacenar el historial de mensajes con el system prompt predefinido en el estado de sesión de Streamlit.

### Requisito 2: Interfaz de chat principal

**User Story:** Como usuario, quiero una interfaz de chat donde pueda escribir consultas y recibir respuestas del asistente, para interactuar de forma natural con el sistema de estadísticas.

#### Criterios de Aceptación

1. THE Chatbot_UI SHALL presentar un área de chat que muestre el Historial_Mensajes con distinción visual entre mensajes del usuario y del asistente.
2. THE Chatbot_UI SHALL presentar un campo de entrada de texto en la parte inferior de la pantalla para que el usuario escriba consultas.
3. WHEN el usuario envía una consulta, THE Chatbot_UI SHALL mostrar el mensaje del usuario en el área de chat de forma inmediata.
4. WHEN el Chat_Engine genera una respuesta final, THE Chatbot_UI SHALL mostrar la respuesta del asistente en el área de chat con formato Markdown.
5. WHILE el Chat_Engine procesa una consulta, THE Chatbot_UI SHALL mostrar un indicador visual de que el asistente está procesando la solicitud.
6. THE Chatbot_UI SHALL mantener el Historial_Mensajes entre interacciones dentro de la misma sesión usando `st.session_state`.

### Requisito 3: Flujo de herramientas MCP con OpenAI

**User Story:** Como usuario, quiero que el chatbot utilice las herramientas MCP en el orden correcto para obtener datos reales del sistema SIRTOD/MoSPI.

#### Criterios de Aceptación

1. WHEN el usuario envía una consulta, THE Chat_Engine SHALL enviar el Historial_Mensajes al OpenAI_Client con las herramientas MCP disponibles.
2. WHEN el OpenAI_Client responde con Tool_Calls, THE Chat_Engine SHALL ejecutar cada herramienta en el MCP_Client y agregar los resultados al Historial_Mensajes.
3. WHILE existan Tool_Calls pendientes en la respuesta de OpenAI, THE Chat_Engine SHALL continuar el ciclo de ejecución de herramientas hasta obtener una respuesta final de texto.
4. THE Chat_Engine SHALL limitar el número de iteraciones de herramientas a un máximo de 15 por consulta para prevenir bucles infinitos.
5. IF una Tool_Call falla durante la ejecución, THEN THE Chat_Engine SHALL incluir el mensaje de error como resultado de la herramienta y continuar el flujo.
6. WHEN el modelo responde con el formato `ACLARACION_USUARIO:`, THE Chat_Engine SHALL presentar la pregunta de aclaración como un mensaje del asistente en el chat, permitiendo al usuario responder normalmente.

### Requisito 4: Panel de depuración de llamadas a herramientas

**User Story:** Como usuario, quiero ver las llamadas a herramientas y sus respuestas en una sección colapsable, para entender el proceso interno sin perder el foco en la conversación principal.

#### Criterios de Aceptación

1. THE Chatbot_UI SHALL incluir un Panel_Debug colapsable/expandible que no interfiera con el área de chat principal.
2. WHEN una Tool_Call es ejecutada, THE Panel_Debug SHALL mostrar el nombre de la herramienta y los argumentos enviados en formato JSON legible.
3. WHEN una Tool_Call retorna un resultado, THE Panel_Debug SHALL mostrar el resultado de la herramienta asociado a la llamada correspondiente.
4. THE Panel_Debug SHALL estar colapsado por defecto para mantener el foco en la conversación.
5. WHEN el Panel_Debug muestra resultados de herramientas con más de 2000 caracteres, THE Panel_Debug SHALL truncar el contenido y mostrar una indicación de truncamiento.
6. THE Panel_Debug SHALL mostrar las Tool_Calls en orden cronológico dentro de cada mensaje del asistente.

### Requisito 5: Gestión del estado de sesión

**User Story:** Como usuario, quiero que mi conversación se mantenga durante la sesión activa, para poder hacer múltiples consultas sin perder contexto.

#### Criterios de Aceptación

1. THE Chatbot_UI SHALL persistir el Historial_Mensajes en `st.session_state` durante toda la sesión del navegador.
2. THE Chatbot_UI SHALL persistir la conexión MCP_Client y las herramientas descubiertas en `st.session_state` para evitar reconexiones en cada interacción.
3. THE Chatbot_UI SHALL proporcionar un botón o acción para limpiar el Historial_Mensajes e iniciar una nueva conversación.
4. WHEN el usuario limpia la conversación, THE Chat_Engine SHALL reiniciar el Historial_Mensajes con solo el system prompt predefinido.

### Requisito 6: Diseño responsivo y buenas prácticas de UI

**User Story:** Como usuario, quiero que la interfaz se adapte a diferentes tamaños de pantalla, para poder usar el chatbot desde dispositivos móviles y de escritorio.

#### Criterios de Aceptación

1. THE Chatbot_UI SHALL utilizar los componentes nativos de Streamlit para garantizar un diseño responsivo por defecto.
2. THE Chatbot_UI SHALL presentar un diseño limpio con título descriptivo y breve descripción del asistente.
3. THE Chatbot_UI SHALL utilizar `st.chat_message` y `st.chat_input` para seguir los patrones estándar de chat de Streamlit.
4. THE Chatbot_UI SHALL organizar el Panel_Debug usando `st.expander` o `st.sidebar` para que sea accesible sin interrumpir el flujo de chat.

### Requisito 7: Separación de lógica y reutilización de código

**User Story:** Como desarrollador, quiero que la lógica de negocio esté separada de la interfaz, para mantener el código organizado y reutilizable.

#### Criterios de Aceptación

1. THE Chat_Engine SHALL extraer la lógica de conexión MCP, conversión de herramientas y ciclo de herramientas en un módulo separado reutilizable desde `main.py`.
2. THE Chat_Engine SHALL exponer funciones asíncronas que reciban el Historial_Mensajes y retornen la respuesta junto con los registros de Tool_Calls.
3. THE Chatbot_UI SHALL importar y utilizar el Chat_Engine sin duplicar lógica de conexión o procesamiento de herramientas.
4. THE Chat_Engine SHALL mantener compatibilidad con el flujo de consola existente en `main.py`.
