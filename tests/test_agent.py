import pytest
import asyncio
import json
from agent import AIAgent, SimpleTextProvider, FileMessageStore, AgentRequest, AgentError, AgentResponse
from agent import AgentConfig, LLMProvider


@pytest.mark.asyncio
async def test_respond_happy_path(tmp_path):
    store = FileMessageStore(str(tmp_path))
    provider = SimpleTextProvider(agent_name="TestAgent")
    agent = AIAgent(AgentConfig(agent_name="TestAgent"), provider=provider, store=store)

    resp = await agent.respond("Hello world")
    assert "Received message" in resp


@pytest.mark.asyncio
async def test_validation_errors_non_string_and_empty(tmp_path):
    store = FileMessageStore(str(tmp_path))
    provider = SimpleTextProvider(agent_name="TestAgent")
    agent = AIAgent(AgentConfig(agent_name="TestAgent"), provider=provider, store=store)

    # empty message
    with pytest.raises(AgentError):
        await agent.respond("")

    # non-string handled in process_request -> returns AgentResponse.success == False
    request = AgentRequest(content=123)
    response = await agent.process_request(request)
    assert response.success is False
    assert response.error_code is not None


class BadProvider(LLMProvider):
    async def generate_response(self, message: str, context=None, timeout: float = 30.0) -> str:
        raise RuntimeError("provider failed")

    async def health_check(self) -> bool:
        return False


@pytest.mark.asyncio
async def test_storage_audit_on_success_and_error(tmp_path):
    store = FileMessageStore(str(tmp_path))
    # success
    provider = SimpleTextProvider(agent_name="AuditAgent")
    agent = AIAgent(AgentConfig(agent_name="AuditAgent"), provider=provider, store=store)
    resp = await agent.respond("ok")
    # history file should exist
    files = list(tmp_path.iterdir())
    assert any(f.name.endswith("_messages.jsonl") for f in files)

    # error path
    bad_provider = BadProvider()
    agent_err = AIAgent(AgentConfig(agent_name="ErrAgent"), provider=bad_provider, store=store)
    request = AgentRequest(content="trigger")
    response = await agent_err.process_request(request)
    assert response.success is False
    # ensure audit line for error exists
    found = False
    for f in tmp_path.iterdir():
        if f.name.endswith("_messages.jsonl"):
            with f.open("r", encoding="utf-8") as fh:
                for line in fh:
                    try:
                        entry = json.loads(line)
                        if entry.get("request", {}).get("request_id") == request.message_id or entry.get("request", {}).get("message_id") == request.message_id:
                            found = True
                    except Exception:
                        continue
    assert found is True


class FlakyProvider(LLMProvider):
    def __init__(self):
        self._calls = 0

    async def generate_response(self, message: str, context=None, timeout: float = 30.0) -> str:
        self._calls += 1
        if self._calls == 1:
            # simulate transient error
            raise RuntimeError("transient")
        return "ok"

    async def health_check(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_provider_retry_logic(tmp_path):
    store = FileMessageStore(str(tmp_path))
    flaky = FlakyProvider()
    cfg = AgentConfig(agent_name="FlakyAgent", max_retries=2)
    agent = AIAgent(cfg, provider=flaky, store=store)

    response = await agent.process_request(AgentRequest(content="hi"))
    assert response.success is True
    assert response.content == "ok"
