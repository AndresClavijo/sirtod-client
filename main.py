"""
Cliente MCP + OpenAI con visualización del flujo de ejecución.

Conecta al servidor MoSPI MCP (HTTP) ya existente, descubre
herramientas y utiliza OpenAI para resolver consultas del usuario
mostrando cada paso del flujo con Rich.

La lógica de negocio se importa desde ``chat_engine``.
"""

import asyncio
import json
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from chat_engine import (
    OPENAI_MODEL,
    SYSTEM_PROMPT,
    MAX_ITERATIONS,
    ToolCallLog,
    ProcessResult,
    mcp_tools_to_openai,
    is_clarification_request,
    connect_mcp,
    discover_tools,
    process_query,
)

load_dotenv()

console = Console()

# ── Configuración local (solo consola) ─────────────────────────
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp")


# ── Visualización Rich ─────────────────────────────────────────
def show_welcome(server_name: str, instructions: str, tools: list):
    """Muestra panel de bienvenida con info del servidor."""
    console.print()
    console.rule("[bold cyan]🚀 FastMCP + OpenAI Client[/]")
    console.print()

    console.print(
        Panel(
            f"[bold]{server_name}[/]\n"
            f"[dim]URL: {MCP_SERVER_URL}[/]\n\n"
            f"{instructions}",
            title="🖥️  Servidor MCP",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    # Tabla de herramientas
    table = Table(
        title="🔧 Herramientas disponibles",
        show_header=True,
        header_style="bold magenta",
        border_style="dim",
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("Nombre", style="green bold", min_width=22)
    table.add_column("Descripción", style="white", max_width=60)

    for i, tool in enumerate(tools, 1):
        # Tomar solo la primera línea de la descripción
        desc = (tool.description or "—").split("\n")[0].strip()
        if len(desc) > 80:
            desc = desc[:77] + "..."
        table.add_row(str(i), tool.name, desc)

    console.print(table)
    console.print()
    console.print(
        "[dim]Escribe tu consulta y presiona Enter. "
        'Escribe "salir" para terminar.[/]'
    )
    console.rule(style="dim")
    console.print()


def show_user_input(query: str):
    """Muestra la consulta del usuario."""
    console.print(
        Panel(query, title="📥 Tu consulta", border_style="blue", padding=(0, 2))
    )


def show_tool_call(name: str, arguments: dict):
    """Muestra que se detectó una llamada a herramienta."""
    args_str = json.dumps(arguments, ensure_ascii=False, indent=2)
    console.print(
        Panel(
            f"[bold green]{name}[/]\n\n[yellow]Argumentos:[/]\n{args_str}",
            title="🔧 Tool Call detectada",
            border_style="yellow",
            padding=(0, 2),
        )
    )


def show_tool_result(name: str, result_text: str):
    """Muestra el resultado devuelto por la herramienta."""
    # Truncar resultados muy largos para la visualización
    display = result_text
    if len(display) > 2000:
        display = (
            display[:2000] + "\n\n[dim]... (resultado truncado para visualización)[/]"
        )
    console.print(
        Panel(
            display,
            title=f"⚙️  Resultado de [bold]{name}[/]",
            border_style="green",
            padding=(0, 2),
        )
    )


def show_final_response(content: str):
    """Muestra la respuesta final del LLM."""
    console.print(
        Panel(
            Markdown(content),
            title="💬 Respuesta del asistente",
            border_style="magenta",
            padding=(1, 2),
        )
    )


def show_clarification_request(content: str):
    """Muestra una solicitud de aclaración al usuario."""
    question = content.replace("ACLARACION_USUARIO:", "", 1).strip()
    console.print(
        Panel(
            question,
            title="❓ Aclaración requerida",
            border_style="yellow",
            padding=(0, 2),
        )
    )


def show_step(emoji: str, message: str, style: str = "dim"):
    """Muestra un paso intermedio del flujo."""
    console.print(f"  {emoji}  [{style}]{message}[/]")


# ── Lógica principal ───────────────────────────────────────────
async def run():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key.startswith("sk-tu-"):
        console.print(
            Panel(
                "[bold red]Error:[/] Configura tu OPENAI_API_KEY en el archivo .env",
                border_style="red",
            )
        )
        sys.exit(1)

    openai_client = OpenAI(api_key=api_key)

    # ── Conectar al servidor MCP existente ──────────────────
    show_step(
        "🔌", f"Conectando al servidor MCP en [bold]{MCP_SERVER_URL}[/]...", "cyan"
    )
    mcp_client = await connect_mcp(MCP_SERVER_URL)

    async with mcp_client:
        # ── Info del servidor ───────────────────────────────
        server_name = "MCP Server"
        instructions = "Servidor MCP"
        if mcp_client.initialize_result:
            info = mcp_client.initialize_result
            server_name = info.serverInfo.name or server_name
            instructions = info.instructions or instructions

        show_step("✅", f"Conectado a [bold]{server_name}[/]", "green")

        # ── Descubrir tools ─────────────────────────────────
        show_step("🔍", "Descubriendo herramientas...", "cyan")
        mcp_tools, openai_tools = await discover_tools(mcp_client)
        show_step("✅", f"{len(mcp_tools)} herramienta(s) encontrada(s)", "green")

        # ── Bienvenida ──────────────────────────────────────
        show_welcome(server_name, instructions, mcp_tools)

        # ── Loop de conversación ────────────────────────────
        messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

        while True:
            try:
                user_input = console.input("[bold blue]Tú >[/] ").strip()
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]👋 ¡Hasta luego![/]\n")
                break

            if not user_input:
                continue
            if user_input.lower() in ("salir", "exit", "quit"):
                console.print("\n[dim]👋 ¡Hasta luego![/]\n")
                break

            show_user_input(user_input)
            messages.append({"role": "user", "content": user_input})

            # ── Procesar consulta via chat_engine ───────────
            show_step("🤖", "Enviando a OpenAI...", "cyan")

            result: ProcessResult = await process_query(
                messages, mcp_client, openai_tools, openai_client
            )

            # ── Renderizar tool logs con Rich ───────────────
            for log in result.tool_logs:
                show_tool_call(log.name, log.arguments)
                if log.is_error:
                    show_tool_result(log.name, f"[red]{log.result}[/]")
                else:
                    show_tool_result(log.name, log.result)

            # ── Manejar resultado ───────────────────────────
            if result.hit_max_iterations:
                show_step("⚠️", "Se alcanzó el límite de iteraciones", "yellow")

            if result.is_clarification:
                show_clarification_request(result.content)
            else:
                show_final_response(result.content)

            console.print()
            console.rule(style="dim")
            console.print()


# ── Punto de entrada ────────────────────────────────────────────
if __name__ == "__main__":
    asyncio.run(run())
