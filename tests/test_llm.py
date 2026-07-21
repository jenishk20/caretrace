from types import SimpleNamespace

from core import llm


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def test_ask_prepends_reasoning_effort_to_system_message(monkeypatch):
    client = FakeClient({"message": {"content": "done"}})
    monkeypatch.setattr(llm, "_client", client)

    assert llm.ask("hello", system="Be careful.", effort="high") == "done"

    assert client.calls[0]["messages"][0] == {
        "role": "system",
        "content": "Reasoning: high\n\nBe careful.",
    }


def test_ask_tools_returns_serializable_assistant_message_and_logs_call(monkeypatch):
    response = SimpleNamespace(
        message=SimpleNamespace(
            role="assistant",
            content="",
            thinking="private reasoning",
            tool_calls=[
                SimpleNamespace(
                    function=SimpleNamespace(name="reconcile_medication", arguments={"drug": "ketorolac"})
                )
            ],
        )
    )
    client = FakeClient(response)
    monkeypatch.setattr(llm, "_client", client)

    message = llm.ask_tools(
        [{"role": "user", "content": "check this"}],
        [{"type": "function", "function": {"name": "reconcile_medication"}}],
        effort="high",
    )

    assert message == {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {"id": "call_0", "function": {"name": "reconcile_medication", "arguments": {"drug": "ketorolac"}}}
        ],
    }
    assert "thinking" not in message
    assert client.calls[0]["model"] == "gpt-oss:20b"
    assert client.calls[0]["tools"][0]["function"]["name"] == "reconcile_medication"
    assert llm.recent_calls(1)[0]["kind"] == "tools"


def test_ask_vision_fails_closed_for_text_only_model():
    try:
        llm.ask_vision("read", "/tmp/example.png")
    except NotImplementedError as exc:
        assert "Tesseract" in str(exc)
    else:
        raise AssertionError("ask_vision should reject image inference")
