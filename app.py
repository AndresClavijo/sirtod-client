"""
📊 Asistente SIRTOD — Interfaz web Streamlit.

Aplicación de chat que conecta al servidor MCP y usa OpenAI para
responder consultas sobre estadísticas del Perú.
"""

import asyncio
import json
import os

from dotenv import load_dotenv
import streamlit as st
from openai import OpenAI

import chat_engine

# ── Cargar variables de entorno ────────────────────────────────
load_dotenv()

# ── Configuración de página ────────────────────────────────────
st.set_page_config(page_title="📊 Asistente SIRTOD", layout="wide")

# ── Validar API key ────────────────────────────────────────────
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("⚠️ La variable de entorno `OPENAI_API_KEY` no está configurada. "
             "Por favor, configúrala en tu archivo `.env` o en las variables de entorno del sistema.")
    st.stop()


# ── Event loop persistente para la sesión ──────────────────────
def _get_loop() -> asyncio.AbstractEventLoop:
    """Retorna un event loop persistente almacenado en session_state."""
    if "event_loop" not in st.session_state:
        loop = asyncio.new_event_loop()
        st.session_state.event_loop = loop
    return st.session_state.event_loop


def run_async(coro):
    """Ejecuta una coroutine en el event loop persistente de la sesión."""
    return _get_loop().run_until_complete(coro)


# ── Inicializar estado de sesión ───────────────────────────────
if not st.session_state.get("initialized", False):
    mcp_server_url = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp")

    try:
        mcp_client, _, openai_tools = run_async(
            chat_engine.connect_and_discover(mcp_server_url)
        )
    except Exception as exc:
        st.error(f"❌ No se pudo conectar al servidor MCP en `{mcp_server_url}`: {exc}")
        st.stop()

    st.session_state.mcp_client = mcp_client
    st.session_state.openai_client = OpenAI(api_key=api_key)
    st.session_state.openai_tools = openai_tools
    st.session_state.messages = [{"role": "system", "content": chat_engine.SYSTEM_PROMPT}]
    st.session_state.tool_logs = []
    st.session_state.initialized = True

# ── Título y descripción ───────────────────────────────────────
st.title("📊 Asistente SIRTOD")
st.caption("Consulta estadísticas del Perú (SIRTOD/MoSPI) de forma conversacional.")

# ── Renderizar historial de mensajes ───────────────────────────
for msg in st.session_state.messages:
    if msg.get("role") in ("system", "tool"):
        continue
    # Los mensajes del asistente con tool_calls pero sin content se omiten
    if msg.get("role") == "assistant" and not msg.get("content"):
        continue
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Entrada del usuario ───────────────────────────────────────
if user_input := st.chat_input("Escribe tu consulta..."):
    # Agregar mensaje del usuario al historial
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Procesar la consulta con el motor de chat
    with st.chat_message("assistant"):
        with st.spinner("Procesando..."):
            result = run_async(
                chat_engine.process_query(
                    messages=st.session_state.messages,
                    mcp_client=st.session_state.mcp_client,
                    openai_tools=st.session_state.openai_tools,
                    openai_client=st.session_state.openai_client,
                )
            )
        st.markdown(result.content)

    # Acumular logs de herramientas
    st.session_state.tool_logs.extend(result.tool_logs)

# ── Sidebar: Panel de depuración ───────────────────────────────
with st.sidebar:
    st.header("🔧 Llamadas a Herramientas")

    for i, log in enumerate(st.session_state.tool_logs):
        with st.expander(f"🔨 {log.name}", expanded=False):
            st.subheader("Argumentos")
            st.code(json.dumps(log.arguments, indent=2, ensure_ascii=False), language="json")

            st.subheader("Resultado")
            truncated = chat_engine.truncate_result(log.result)
            if log.is_error:
                st.warning(truncated)
            else:
                st.code(truncated, language="text")

            if len(log.result) > 2000:
                st.caption(f"⚠️ Resultado truncado (original: {len(log.result)} caracteres)")

    st.divider()

    if st.button("🗑️ Nueva conversación"):
        st.session_state.messages = [{"role": "system", "content": chat_engine.SYSTEM_PROMPT}]
        st.session_state.tool_logs = []
        st.rerun()
