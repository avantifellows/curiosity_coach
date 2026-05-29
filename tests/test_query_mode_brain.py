"""Brain unit tests for query_mode rendering and tutor_mode pipeline."""
import asyncio
import sys
import types
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "Brain"))
for module_name in list(sys.modules):
    if module_name == "src" or module_name.startswith("src."):
        sys.modules.pop(module_name)

fake_openai = types.ModuleType("openai")
fake_openai.OpenAI = object
sys.modules.setdefault("openai", fake_openai)

fake_groq = types.ModuleType("groq")
fake_groq.Groq = object
sys.modules.setdefault("groq", fake_groq)

fake_pypdf = types.ModuleType("pypdf")
fake_pypdf.PdfReader = object
sys.modules.setdefault("pypdf", fake_pypdf)

from src.process_query_entrypoint import _resolve_render_query  # noqa: E402
from src.pipelines import intent_legacy_v6, tutor_mode  # noqa: E402
from src.core.turn_context import TurnExecutionContext  # noqa: E402
from src.schemas import ProcessQueryResponse  # noqa: E402


def test_resolve_render_query():
    assert _resolve_render_query("hello", "include") == "hello"
    assert _resolve_render_query("hello", "opening_only") == "hello"
    assert _resolve_render_query("hello", "omit") == ""


def test_tutor_mode_pipeline_prompt_policy():
    assert tutor_mode.TURN_PROMPT_POLICY.prompt_name == "tutor_mode_base"
    assert tutor_mode.OPENING_PROMPT_POLICY.prompt_name == "tutor_mode_base"


def test_intent_legacy_v6_keeps_interest_router_async():
    assert not hasattr(intent_legacy_v6, "prepare_turn")
    assert intent_legacy_v6.TURN_PROMPT_POLICY == intent_legacy_v6.ASSIGNED_PROMPT


def test_async_prior_history_excludes_latest_user_and_saved_ai():
    history = intent_legacy_v6.format_async_prior_history(
        [
            {"id": 1, "is_user": True, "content": "old question"},
            {"id": 2, "is_user": False, "content": "old answer"},
            {"id": 3, "is_user": True, "content": "latest question"},
            {"id": 4, "is_user": False, "content": "new saved answer"},
        ],
        original_message_id=3,
        saved_message_id=4,
    )

    assert "old question" in history
    assert "old answer" in history
    assert "latest question" not in history
    assert "new saved answer" not in history


async def _fake_v4_execute_turn(**kwargs):
    response_data = kwargs["response_data"]
    response_data.pipeline_data = {"foreground_policy": "v4_policy"}
    return 42


def test_intent_legacy_v6_marks_async_interest_after_v4(monkeypatch):
    monkeypatch.setattr(intent_legacy_v6, "execute_v4_turn", _fake_v4_execute_turn)

    response_data = ProcessQueryResponse(
        query="why",
        config_used={},
        steps=[],
        final_response="because",
    )
    updated_score = asyncio.run(
        intent_legacy_v6.execute_turn(
            message=types.SimpleNamespace(),
            response_data=response_data,
            turn_context=TurnExecutionContext(user_input="why", purpose="chat"),
            user_input="why",
            current_curiosity_score=10,
        )
    )

    assert updated_score == 42
    assert response_data.pipeline_data["async_observers_enabled"] is True
    assert response_data.pipeline_data["async_interest_router_enabled"] is True
    assert response_data.pipeline_data["foreground_policy"] == (
        "legacy_response_then_chat_controller_then_13yo; "
        "interest_core_theme_exploration_score_async"
    )
