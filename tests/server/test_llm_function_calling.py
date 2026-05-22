"""测试 LLM Client 的 function calling 参数构建（不实际调用 API）。"""
import pytest
from server.llm.client import LLMClient


@pytest.fixture
def client():
    return LLMClient(api_key="test-key", base_url="http://fake", model="test-model")


def test_chat_with_tools_builds_correct_payload(client):
    """传入 tools 参数时，payload 包含 tools 字段"""
    tools = [
        {
            "type": "function",
            "function": {
                "name": "eat",
                "description": "进食",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        }
    ]
    payload = client._build_payload(
        messages=[{"role": "user", "content": "test"}],
        tools=tools,
    )
    assert "tools" in payload
    assert payload["tools"] == tools
    assert payload["tool_choice"] == "auto"


def test_chat_without_tools_no_tools_field(client):
    """不传 tools 时，payload 不含 tools 字段"""
    payload = client._build_payload(
        messages=[{"role": "user", "content": "test"}],
        tools=None,
    )
    assert "tools" not in payload
    assert "tool_choice" not in payload


def test_parse_tool_call_from_response():
    """从 LLM 响应中解析 tool_calls"""
    response = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "eat",
                        "arguments": "{}",
                    },
                }],
            },
            "finish_reason": "tool_calls",
        }],
    }
    from server.llm.client import parse_tool_calls
    calls = parse_tool_calls(response)
    assert len(calls) == 1
    assert calls[0]["name"] == "eat"
    assert calls[0]["arguments"] == {}
    assert calls[0]["call_id"] == "call_123"


def test_parse_tool_call_with_arguments():
    """解析带参数的 tool_call"""
    response = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": "call_456",
                    "type": "function",
                    "function": {
                        "name": "move",
                        "arguments": '{"destination": "tavern"}',
                    },
                }],
            },
            "finish_reason": "tool_calls",
        }],
    }
    from server.llm.client import parse_tool_calls
    calls = parse_tool_calls(response)
    assert calls[0]["name"] == "move"
    assert calls[0]["arguments"] == {"destination": "tavern"}


def test_parse_no_tool_calls_returns_empty():
    """普通文本回复（无 tool_calls）返回空列表"""
    response = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "你好，我是农夫。",
            },
            "finish_reason": "stop",
        }],
    }
    from server.llm.client import parse_tool_calls
    calls = parse_tool_calls(response)
    assert calls == []


def test_build_payload_with_tool_choice_none(client):
    """tool_choice='none' 时强制不调用工具"""
    tools = [{"type": "function", "function": {"name": "eat", "description": "x", "parameters": {"type": "object", "properties": {}, "required": []}}}]
    payload = client._build_payload(
        messages=[{"role": "user", "content": "test"}],
        tools=tools,
        tool_choice="none",
    )
    assert payload["tool_choice"] == "none"
