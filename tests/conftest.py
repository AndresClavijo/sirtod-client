"""Fixtures compartidos y estrategias Hypothesis para tests del chat engine."""

from __future__ import annotations

import json
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest
from hypothesis import strategies as st

from chat_engine import ToolCallLog


# ── Hypothesis Strategies ──────────────────────────────────────

def mcp_tool_strategy():
    """Genera objetos MCP tool con name, description e inputSchema."""
    return st.builds(
        SimpleNamespace,
        name=st.from_regex(r"[a-z][a-z0-9_]{0,29}", fullmatch=True),
        description=st.text(min_size=0, max_size=200),
        inputSchema=st.fixed_dictionaries(
            {"type": st.just("object")},
            optional={"properties": st.dictionaries(
                keys=st.from_regex(r"[a-z_][a-z0-9_]{0,19}", fullmatch=True),
                values=st.fixed_dictionaries({"type": st.sampled_from(["string", "integer", "boolean"])}),
                min_size=0,
                max_size=5,
            )},
        ),
    )


def openai_message_strategy():
    """Genera mensajes OpenAI válidos (user o assistant)."""
    user_msg = st.fixed_dictionaries({
        "role": st.just("user"),
        "content": st.text(min_size=1, max_size=300),
    })
    assistant_msg = st.fixed_dictionaries({
        "role": st.just("assistant"),
        "content": st.text(min_size=1, max_size=300),
    })
    return st.one_of(user_msg, assistant_msg)


def tool_call_log_strategy():
    """Genera instancias de ToolCallLog con datos aleatorios."""
    return st.builds(
        ToolCallLog,
        name=st.from_regex(r"[a-z][a-z0-9_]{0,29}", fullmatch=True),
        arguments=st.dictionaries(
            keys=st.from_regex(r"[a-z_][a-z0-9_]{0,19}", fullmatch=True),
            values=st.one_of(st.text(max_size=50), st.integers(), st.booleans()),
            min_size=0,
            max_size=5,
        ),
        result=st.text(min_size=0, max_size=500),
        is_error=st.booleans(),
    )


# ── Mock OpenAI Client ─────────────────────────────────────────

@dataclass
class MockChoice:
    message: Any


@dataclass
class MockCompletion:
    choices: list[MockChoice]


@dataclass
class MockToolCall:
    """Simula un tool_call de OpenAI."""
    id: str
    type: str = "function"
    function: Any = None


@dataclass
class MockFunction:
    name: str
    arguments: str  # JSON string


class MockMessage:
    """Simula un mensaje de respuesta de OpenAI."""

    def __init__(self, content: str | None = None, tool_calls: list | None = None):
        self.content = content
        self.tool_calls = tool_calls

    def model_dump(self) -> dict:
        data: dict[str, Any] = {"role": "assistant", "content": self.content}
        if self.tool_calls:
            data["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in self.tool_calls
            ]
        return data


class MockChatCompletions:
    """Simula openai_client.chat.completions con respuestas configurables."""

    def __init__(self):
        self._responses: list[MockCompletion] = []
        self._call_index = 0

    def set_responses(self, responses: list[MockCompletion]):
        self._responses = responses
        self._call_index = 0

    def create(self, **kwargs) -> MockCompletion:
        if self._call_index < len(self._responses):
            resp = self._responses[self._call_index]
            self._call_index += 1
            return resp
        # Default: return empty text response
        return MockCompletion(choices=[MockChoice(message=MockMessage(content="default response"))])


class MockChat:
    def __init__(self):
        self.completions = MockChatCompletions()


class MockOpenAIClient:
    """Mock del cliente OpenAI con patrón factory para configurar respuestas."""

    def __init__(self):
        self.chat = MockChat()

    def set_text_response(self, text: str):
        """Configura una respuesta de texto simple."""
        completion = MockCompletion(
            choices=[MockChoice(message=MockMessage(content=text))]
        )
        self.chat.completions.set_responses([completion])

    def set_tool_calls_then_text(self, tool_calls: list[MockToolCall], final_text: str):
        """Configura una respuesta con tool_calls seguida de texto final."""
        tc_completion = MockCompletion(
            choices=[MockChoice(message=MockMessage(content=None, tool_calls=tool_calls))]
        )
        text_completion = MockCompletion(
            choices=[MockChoice(message=MockMessage(content=final_text))]
        )
        self.chat.completions.set_responses([tc_completion, text_completion])

    def set_responses(self, responses: list[MockCompletion]):
        """Configura una secuencia arbitraria de respuestas."""
        self.chat.completions.set_responses(responses)


# ── Mock MCP Client ────────────────────────────────────────────

class MockToolResult:
    """Simula el resultado de una herramienta MCP."""

    def __init__(self, text: str):
        self.content = [SimpleNamespace(text=text)]


class MockMCPClient:
    """Mock del cliente MCP con call_tool y list_tools configurables."""

    def __init__(self):
        self._tools: list = []
        self._call_results: dict[str, str] = {}
        self._default_result: str = "mock result"

    def set_tools(self, tools: list):
        self._tools = tools

    def set_call_result(self, tool_name: str, result: str):
        self._call_results[tool_name] = result

    def set_default_result(self, result: str):
        self._default_result = result

    async def call_tool(self, name: str, args: dict) -> MockToolResult:
        text = self._call_results.get(name, self._default_result)
        return MockToolResult(text=text)

    async def list_tools(self) -> list:
        return self._tools


# ── Pytest Fixtures ────────────────────────────────────────────

@pytest.fixture
def mock_openai_client() -> MockOpenAIClient:
    """Retorna un MockOpenAIClient configurable."""
    return MockOpenAIClient()


@pytest.fixture
def mock_mcp_client() -> MockMCPClient:
    """Retorna un MockMCPClient configurable."""
    return MockMCPClient()
