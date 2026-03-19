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
st.set_page_config(page_title="Asistente Estadístico SIRTOD", page_icon="🇵🇪", layout="wide")

try:
    st.logo("https://upload.wikimedia.org/wikipedia/commons/a/ab/Logo_INEI.png")
except AttributeError:
    pass

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stChatInput {padding-bottom: 2rem;}
</style>
""", unsafe_allow_html=True)

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

# ── Splash Intro Dinámica ──────────────────────────────────────
if "splash_colors" not in st.session_state:
    import random
    PALETTES = [
        ["#F3EEEA", "#EBE3D5", "#B0A695", "#776B5D", "#4A4138", "#C7BCAB", "#8F8477", "#E1D5C5"],
        ["#D6C7AE", "#BFB29E", "#B3A492", "#DADDB1", "#968979", "#EFE5D3", "#7A6E60", "#CDBEAE"],
        ["#D6D46D", "#F4DFB6", "#DE8F5F", "#9A4444", "#6B2D2D", "#BA7A4F", "#823838", "#E6C895"],
        ["#FFBB5C", "#FF9B50", "#E25E3E", "#C63D2F", "#A03024", "#FFD79A", "#E64E33", "#FCA66A"],
        ["#186F65", "#B5CB99", "#FCE09B", "#B2533E", "#0F4740", "#548873", "#D4B874", "#8B3A29"],
        ["#CD5C08", "#F5E8B7", "#C1D8C3", "#6A9C89", "#3E5C50", "#E86F1C", "#DE9450", "#A5B8A8"],
        ["#EAC696", "#C8AE7D", "#765827", "#65451F", "#3B2812", "#D6B080", "#543919", "#997D51"],
        ["#FFC95F", "#FFF9C9", "#862B0D", "#B5C99A", "#521A08", "#DDE8B3", "#DAAA4C", "#9EAF88"],
        ["#F7F1E5", "#E7B10A", "#898121", "#4C4B16", "#2B2B0C", "#D1A30A", "#66611B", "#E8DDBC"]
    ]
    st.session_state.splash_colors = random.sample(random.choice(PALETTES), 8)

is_intro = len(st.session_state.messages) == 1

if is_intro:
    colors = st.session_state.splash_colors
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap');
    
    .splash-container {{
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        justify-content: space-between;
        min-height: 500px;
        padding-top: 2rem;
        padding-bottom: 2rem;
        overflow: hidden;
    }}
    .splash-text {{
        flex: 1;
        min-width: 300px;
        padding-right: 2rem;
        z-index: 10;
        margin-bottom: 2rem;
    }}
    .splash-text h1 {{
        font-family: 'Playfair Display', serif;
        font-size: 5rem;
        font-weight: 500;
        line-height: 1.05;
        color: #0b1c2c;
        margin: 0;
        letter-spacing: -2px;
    }}
    .square-bullet {{
        width: 2.5rem;
        height: 2.5rem;
        background-color: #0b1c2c;
        margin-top: 2rem;
    }}
    .splash-shapes {{
        flex: 1;
        min-width: 300px;
        position: relative;
        height: 550px;
        margin-left: -20px;
    }}
    .shape {{
        position: absolute;
        box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        animation: shape-tremor 1.5s ease-in-out;
        transform-origin: center;
        transition: transform 0.2s ease;
    }}
    .shape:hover {{
        animation: shape-tremor 0.5s infinite ease-in-out;
        z-index: 10 !important;
        cursor: pointer;
    }}
    
    @keyframes shape-tremor {{
        0%   {{ transform: translate(1px, 1px)   rotate(calc(var(--rot) + 0deg)); }}
        10%  {{ transform: translate(-1px, -2px) rotate(calc(var(--rot) - 1deg)); }}
        20%  {{ transform: translate(-2px, 0px)  rotate(calc(var(--rot) + 1deg)); }}
        30%  {{ transform: translate(2px, 2px)   rotate(calc(var(--rot) + 0deg)); }}
        40%  {{ transform: translate(1px, -1px)  rotate(calc(var(--rot) + 1deg)); }}
        50%  {{ transform: translate(-1px, 2px)  rotate(calc(var(--rot) - 1deg)); }}
        60%  {{ transform: translate(-2px, 1px)  rotate(calc(var(--rot) + 0deg)); }}
        70%  {{ transform: translate(2px, 1px)   rotate(calc(var(--rot) - 1deg)); }}
        80%  {{ transform: translate(-1px, -1px) rotate(calc(var(--rot) + 1deg)); }}
        90%  {{ transform: translate(1px, 2px)   rotate(calc(var(--rot) + 0deg)); }}
        100% {{ transform: translate(0px, 0px)   rotate(var(--rot)); }}
    }}

    .shape-1 {{ --rot: 10deg; width: 140px; height: 190px; top: 25%; left: 0%; transform: rotate(var(--rot)); z-index: 2; background-color: {colors[0]}; }}
    .shape-2 {{ --rot: 15deg; width: 140px; height: 180px; bottom: 5%; left: -10%; transform: rotate(var(--rot)); z-index: 2; background-color: {colors[1]}; }}
    .shape-3 {{ --rot: -3deg; width: 155px; height: 230px; top: 0%; left: 20%; transform: rotate(var(--rot)); z-index: 3; background-color: {colors[2]}; }}
    .shape-4 {{ --rot: 5deg; width: 155px; height: 160px; top: -5%; right: 5%; transform: rotate(var(--rot)); z-index: 4; background-color: {colors[3]}; }}
    .shape-5 {{ --rot: -5deg; width: 170px; height: 230px; top: 40%; left: 15%; transform: rotate(var(--rot)); z-index: 5; background-color: {colors[4]}; }}
    .shape-6 {{ --rot: 2deg; width: 155px; height: 195px; bottom: 0%; right: 5%; transform: rotate(var(--rot)); z-index: 6; background-color: {colors[5]}; }}
    .shape-7 {{ --rot: -12deg; width: 130px; height: 150px; top: -10%; left: -5%; transform: rotate(var(--rot)); z-index: 1; background-color: {colors[6]}; }}
    .shape-8 {{ --rot: 8deg; width: 120px; height: 180px; top: 25%; right: -5%; transform: rotate(var(--rot)); z-index: 1; background-color: {colors[7]}; }}
    
    @media (max-width: 768px) {{
        .splash-text h1 {{ font-size: 3.5rem; }}
        .splash-container {{ flex-direction: column; min-height: auto; }}
        .splash-shapes {{ width: 100%; height: 350px; transform: scale(0.85); transform-origin: top left; margin-top: 1rem; }}
    }}
    </style>
    
    <div class="splash-container">
        <div class="splash-text">
            <h1>Asistente<br>estadístico<br>SIRTOD.</h1>
            <div class="square-bullet"></div>
        </div>
        <div class="splash-shapes">
            <div class="shape shape-1"></div>
            <div class="shape shape-2"></div>
            <div class="shape shape-3"></div>
            <div class="shape shape-4"></div>
            <div class="shape shape-5"></div>
            <div class="shape shape-6"></div>
            <div class="shape shape-7"></div>
            <div class="shape shape-8"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    # ── Título y descripción (Vista Chat Normal) ───────────────────
    st.title("Asistente Estadístico SIRTOD")
    st.markdown("Bienvenido al sistema de consultas conversacional del **Instituto Nacional de Estadística e Informática (INEI)**. "
                "Realice sus preguntas sobre datos estadísticos del Perú y reciba información oficial y actualizada.")

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

# ── Sidebar: Guía y Panel ──────────────────────────────────────
with st.sidebar:
    st.markdown("### Guía de Uso")
    st.info(
        "**1.** Escriba su consulta estadística en el cuadro de texto inferior.\n\n"
        "**2.** El asistente buscará la información en la base de datos oficial.\n\n"
        "**3.** Recibirá una respuesta estructurada y fácil de entender."
    )
    
    st.success(
        "💡 **No se preocupe por equivocarse**. El sistema está diseñado para guiarlo "
        "y le pedirá aclaraciones si la pregunta es muy amplia o requiere más detalles."
    )
    
    st.markdown("---")
    st.markdown("<div style='text-align: center; color: #666;'><small>Powered by:<br><b>Labstat - Laboratorio de Estadística del INEI</b></small></div>", unsafe_allow_html=True)
    st.markdown("---")
    
    with st.expander("🔧 Detalles Técnicos (Depuración)"):
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

        if st.button("🗑️ Nueva conversación", use_container_width=True):
            st.session_state.messages = [{"role": "system", "content": chat_engine.SYSTEM_PROMPT}]
            st.session_state.tool_logs = []
            st.rerun()
