"""
Motor de chat compartido — lógica de negocio extraída de main.py.

Encapsula constantes, dataclasses y funciones utilitarias para la
comunicación MCP + OpenAI. No depende de ninguna interfaz (ni Rich
ni Streamlit).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from fastmcp import Client
from openai import OpenAI

# ── Constantes ─────────────────────────────────────────────────
OPENAI_MODEL: str = "gpt-4o-mini"

MAX_ITERATIONS: int = 15

SYSTEM_PROMPT: str = (
    "Eres un asistente experto en estadísticas del Perú conectado al sistema SIRTOD/MoSPI. "
    "Responde siempre en español, de forma clara y concisa.\n\n"
    "REGLAS IMPORTANTES:\n"
    "1. Usa las herramientas disponibles para obtener datos reales. NUNCA inventes datos.\n"
    "2. Sigue el flujo ordenado de las herramientas:\n"
    "   - Primero: 1_know_about_mospi_api (conocer las categorías)\n"
    "   - Segundo: 2_get_indicators (obtener indicadores de la categoría)\n"
    "   - Tercero: 3_get_metadata (obtener valores de filtros válidos)\n"
    "   - Cuarto: 4_get_data (obtener los datos con filtros correctos)\n"
    "3. NUNCA saltes al paso 4 sin haber pasado por el paso 3.\n"
    "3.1. Si en el paso 1 o 2 te falta contexto para elegir correctamente una categoría o indicador, "
    "haz una pregunta breve al usuario antes de continuar.\n"
    "4. Si no encuentras datos, di honestamente que no se encontraron.\n"
    "5. Presenta los datos de forma clara y estructurada.\n"
    "6. Cuando uses una herramienta, explica brevemente qué estás haciendo.\n"
    "7. Cuando necesites una aclaración del usuario, responde SOLO con el formato: "
    "ACLARACION_USUARIO: <pregunta breve>. No des respuesta final en ese momento."
)

_TRUNCATE_LIMIT: int = 2000
_TRUNCATE_INDICATOR: str = "\n\n... (resultado truncado)"


# ── Dataclasses ────────────────────────────────────────────────
@dataclass
class ToolCallLog:
    """Registro de una llamada a herramienta."""

    name: str
    arguments: dict
    result: str
    is_error: bool


@dataclass
class ProcessResult:
    """Resultado del procesamiento de una consulta."""

    content: str
    tool_logs: list[ToolCallLog] = field(default_factory=list)
    is_clarification: bool = False
    iterations: int = 0
    hit_max_iterations: bool = False


# ── Funciones utilitarias ──────────────────────────────────────
def mcp_tools_to_openai(mcp_tools: list) -> list[dict]:
    """Convierte las herramientas MCP al formato esperado por OpenAI."""
    openai_tools: list[dict] = []
    for tool in mcp_tools:
        openai_tools.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema,
                },
            }
        )
    return openai_tools


def is_clarification_request(content: str | None) -> bool:
    """Indica si el modelo está solicitando una aclaración al usuario."""
    if not content:
        return False
    return content.strip().startswith("ACLARACION_USUARIO:")


def truncate_result(text: str) -> str:
    """Trunca cadenas que excedan el límite de 2000 caracteres.

    Si *text* tiene más de ``_TRUNCATE_LIMIT`` caracteres, retorna los
    primeros ``_TRUNCATE_LIMIT`` caracteres seguidos de un indicador de
    truncamiento.  En caso contrario retorna la cadena sin modificar.
    """
    if len(text) <= _TRUNCATE_LIMIT:
        return text
    return text[:_TRUNCATE_LIMIT] + _TRUNCATE_INDICATOR


# ── Funciones asíncronas de conexión ───────────────────────────
async def connect_mcp(server_url: str) -> Client:
    """Crea y retorna un cliente MCP conectado."""
    return Client(server_url)


async def discover_tools(mcp_client: Client) -> tuple[list, list[dict]]:
    """Descubre herramientas MCP y retorna (mcp_tools, openai_tools)."""
    mcp_tools = await mcp_client.list_tools()
    openai_tools = mcp_tools_to_openai(mcp_tools)
    return mcp_tools, openai_tools


async def connect_and_discover(server_url: str) -> tuple[Client, list, list[dict]]:
    """Conecta al servidor MCP, entra al contexto y descubre herramientas.

    Retorna ``(mcp_client, mcp_tools, openai_tools)``.  El cliente queda
    conectado (``__aenter__`` ya fue invocado) y debe cerrarse con
    ``await mcp_client.__aexit__(None, None, None)`` cuando ya no se necesite.
    """
    client = Client(server_url)
    await client.__aenter__()
    mcp_tools = await client.list_tools()
    openai_tools = mcp_tools_to_openai(mcp_tools)
    return client, mcp_tools, openai_tools

async def connect_and_discover(server_url: str) -> tuple[Client, list, list[dict]]:
    """Conecta al servidor MCP, entra al contexto y descubre herramientas.

    Retorna ``(mcp_client, mcp_tools, openai_tools)``.  El cliente queda
    conectado (``__aenter__`` ya fue invocado) y debe cerrarse con
    ``await mcp_client.__aexit__(None, None, None)`` cuando ya no se necesite.
    """
    client = Client(server_url)
    await client.__aenter__()
    mcp_tools = await client.list_tools()
    openai_tools = mcp_tools_to_openai(mcp_tools)
    return client, mcp_tools, openai_tools



# ── Función principal de procesamiento ─────────────────────────
async def process_query(
    messages: list[dict],
    mcp_client: Client,
    openai_tools: list[dict],
    openai_client: OpenAI,
) -> ProcessResult:
    """Ejecuta el ciclo completo de consulta con herramientas.

    1. Envía *messages* a OpenAI con las herramientas disponibles.
    2. Ejecuta tool_calls en MCP (hasta ``MAX_ITERATIONS``).
    3. Retorna un ``ProcessResult`` con la respuesta y logs.

    **Modifica** ``messages`` in-place agregando los mensajes del
    asistente, herramientas y respuesta final.
    """
    tool_logs: list[ToolCallLog] = []
    iteration = 0

    while iteration < MAX_ITERATIONS:
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            tools=openai_tools if openai_tools else None,
        )
        assistant_msg = response.choices[0].message

        if assistant_msg.tool_calls:
            iteration += 1
            messages.append(assistant_msg.model_dump())

            for tool_call in assistant_msg.tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments)

                try:
                    result = await mcp_client.call_tool(fn_name, fn_args)
                except Exception as e:
                    result_text = f"Error al ejecutar la herramienta: {e}"
                    tool_logs.append(
                        ToolCallLog(
                            name=fn_name,
                            arguments=fn_args,
                            result=result_text,
                            is_error=True,
                        )
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result_text,
                        }
                    )
                    continue

                # Extraer texto del resultado
                result_text = ""
                if hasattr(result, "content"):
                    for item in result.content:
                        if hasattr(item, "text"):
                            result_text += item.text
                elif hasattr(result, "data"):
                    result_text = str(result.data)
                else:
                    result_text = str(result)

                tool_logs.append(
                    ToolCallLog(
                        name=fn_name,
                        arguments=fn_args,
                        result=result_text,
                        is_error=False,
                    )
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result_text,
                    }
                )

            continue  # next iteration — send tool results back to OpenAI

        # No tool_calls → final or clarification response
        assistant_content = assistant_msg.content or ""
        clarification = is_clarification_request(assistant_content)

        final_content = assistant_content or "(sin respuesta)"
        messages.append({"role": "assistant", "content": final_content})

        return ProcessResult(
            content=final_content,
            tool_logs=tool_logs,
            is_clarification=clarification,
            iterations=iteration,
            hit_max_iterations=False,
        )

    # Reached MAX_ITERATIONS without a final text response
    final_content = assistant_msg.content or "(sin respuesta)"
    messages.append({"role": "assistant", "content": final_content})

    return ProcessResult(
        content=final_content,
        tool_logs=tool_logs,
        is_clarification=is_clarification_request(final_content),
        iterations=iteration,
        hit_max_iterations=True,
    )
