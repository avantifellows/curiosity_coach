import asyncio
import sys
import types
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "Brain"))

fake_openai = types.ModuleType("openai")
fake_openai.OpenAI = object
sys.modules.setdefault("openai", fake_openai)

fake_groq = types.ModuleType("groq")
fake_groq.Groq = object
sys.modules.setdefault("groq", fake_groq)

from src.core.chat_controller import control_chat_response  # noqa: E402
from src.core.turn_context import PromptExecutionContext, TurnExecutionContext  # noqa: E402
from src.pipelines.intent_legacy_v2 import execute_turn as execute_intent_legacy_v2_turn  # noqa: E402
from src.pipelines.intent_legacy_v2 import prepare_turn as prepare_intent_legacy_v2_turn  # noqa: E402
from src.process_query_entrypoint import resolve_prompt_execution_context  # noqa: E402
from src.schemas import ProcessQueryResponse  # noqa: E402
from src.utils.prompt_injection import inject_memory_placeholders  # noqa: E402


def test_process_query_response_preserves_prompt_metadata_fields():
    response = ProcessQueryResponse(
        query="Why is the sky blue?",
        config_used={"use_simplified_mode": True},
        steps=[
            {
                "name": "simplified_conversation",
                "enabled": True,
                "prompt": "formatted prompt",
                "prompt_name": "visit_2",
                "prompt_version": 7,
                "prompt_template": "template with {{QUERY}}",
                "formatted_prompt": "template with Why is the sky blue?",
                "step_id": "legacy-stack-v1:main",
                "step_kind": "response_generation",
                "result": "Because of scattering.",
            }
        ],
        final_response="Because of scattering.",
    )

    dumped = response.model_dump()
    step = dumped["steps"][0]
    assert step["prompt_name"] == "visit_2"
    assert step["prompt_version"] == 7
    assert step["prompt_template"] == "template with {{QUERY}}"
    assert step["formatted_prompt"] == "template with Why is the sky blue?"
    assert step["step_id"] == "legacy-stack-v1:main"
    assert step["step_kind"] == "response_generation"


def test_inject_memory_placeholders_supports_nested_keys_and_fallback():
    memory = {
        "curiosity_boosters": {
            "comment": "Maps and stories worked best.",
        },
        "invitation_to_come_back": {"comment": "Ended with a mini challenge."},
        "knowledge_journey": {"initial_knowledge": {"space": "basic planet facts"}},
        "kid_learning_profile": {"attention_span": {"comment": "Strong on short bursts."}},
    }

    rendered = inject_memory_placeholders(
        "Current: {{CONVERSATION_MEMORY__curiosity_boosters__comment}}",
        memory,
    )
    assert "curiosity_boosters__comment" in rendered
    assert "Maps and stories worked best." in rendered

    fallback = inject_memory_placeholders("Current: {{CONVERSATION_MEMORY}}", None)
    assert "Conversation memory not available." in fallback


def test_resolve_prompt_execution_context_uses_assigned_prompt_metadata(monkeypatch):
    async def fake_get_conversation_prompt(conversation_id):
        assert conversation_id == 42
        return {
            "prompt_text": "Hello {{QUERY}} {{CORE_THEME}} {{CONVERSATION_MEMORY}}",
            "version_number": 5,
            "prompt_purpose": "visit_3",
        }

    monkeypatch.setattr(
        "src.process_query_entrypoint.api_service.get_conversation_prompt",
        fake_get_conversation_prompt,
    )

    context = asyncio.run(
        resolve_prompt_execution_context(
            purpose="chat",
            conversation_id=42,
        )
    )

    assert context.prompt_name == "visit_3"
    assert context.prompt_version == 5
    assert context.requires_core_theme is True
    assert context.requires_conversation_memory is True
    assert context.requires_previous_memories is False


def test_control_chat_response_uses_prefetched_core_theme(monkeypatch):
    async def fail_if_called(_conversation_id):
        raise AssertionError("core theme should not be refetched when already provided")

    async def fake_get_prompt_template(prompt_name, prefer_production=False):
        assert prompt_name == "chat_controller"
        assert prefer_production is False
        return "Theme={{CORE_THEME}} Query={{USER_QUERY}} Response={{QUERY_RESPONSE}}"

    class FakeLLM:
        def generate_response(self, final_prompt, call_type, json_mode):
            assert "Theme=oceans" in final_prompt
            assert call_type == "chat_controller"
            assert json_mode is False
            return {"raw_response": "controlled answer"}

    monkeypatch.setattr("src.core.chat_controller.get_conversation_core_theme", fail_if_called)
    monkeypatch.setattr("src.core.chat_controller.api_service.get_prompt_template", fake_get_prompt_template)
    monkeypatch.setattr("src.core.chat_controller.LLMService", FakeLLM)

    result = asyncio.run(
        control_chat_response(
            conversation_id=9,
            original_response="original answer",
            user_query="tell me more",
            core_theme="oceans",
        )
    )

    assert result["chat_controller_applied"] is True
    assert result["core_theme"] == "oceans"
    assert result["controlled_response"] == "controlled answer"


def test_intent_legacy_v2_prepare_turn_injects_interest_guidance(monkeypatch):
    async def fake_router(*, turn_context, user_input):
        assert user_input == "still didnt explain"
        return {
            "prompt_name": "interest_intent_router_v2",
            "interest_signal": "confused",
            "interest_change": "weak_dip",
            "student_intent": "repair_confusion",
            "depth_breadth": "reground",
            "topic_action": "stay",
            "question_policy": "no_question",
            "response_contract": "Give the direct definition first.",
            "coach_adjustment": "Stop asking and explain plainly.",
            "reason_short": "The student says the explanation did not land.",
            "check_in_question": "",
            "confidence": 0.91,
        }

    monkeypatch.setattr(
        "src.pipelines.intent_legacy_v2.run_interest_intent_router",
        fake_router,
    )

    context = TurnExecutionContext(
        user_input="still didnt explain",
        purpose="chat",
        conversation_id=42,
        conversation_history="User: what is scalar\nAI: Imagine distance...",
        prompt_context=PromptExecutionContext(
            prompt_template="Main prompt\n{{INTEREST_INTENT_GUIDANCE}}\nStudent: {{QUERY}}",
            prompt_name="steady_state",
            prompt_version=6,
            prompt_id=174,
        ),
    )

    prepared = asyncio.run(
        prepare_intent_legacy_v2_turn(
            message=object(),
            turn_context=context,
            user_input="still didnt explain",
        )
    )

    assert "student intent: repair_confusion" in prepared.prompt_context.prompt_template
    assert "question policy: no_question" in prepared.prompt_context.prompt_template
    assert "Give the direct definition first." in prepared.prompt_context.prompt_template
    assert "{{INTEREST_INTENT_GUIDANCE}}" not in prepared.prompt_context.prompt_template
    assert prepared.pipeline_state["interest_intent_router_v2"]["confidence"] == 0.91


def test_intent_legacy_v2_execute_turn_prepends_compact_router_step():
    response = ProcessQueryResponse(
        query="boring",
        config_used={"use_simplified_mode": True},
        steps=[
            {
                "name": "simplified_conversation",
                "enabled": True,
                "prompt": "formatted prompt",
                "result": "Want to switch angles?",
            }
        ],
        final_response="Want to switch angles?",
    )
    context = TurnExecutionContext(
        user_input="boring",
        purpose="chat",
        pipeline_state={
            "interest_intent_router_v2": {
                "prompt_name": "interest_intent_router_v2",
                "prompt_template": "long router prompt",
                "formatted_prompt": "long filled router prompt",
                "raw_output": '{"interest_signal":"low"}',
                "parsed_output": {"interest_signal": "low"},
                "interest_signal": "low",
                "interest_change": "strong_dip",
                "student_intent": "meta_check_in",
                "depth_breadth": "check_in",
                "topic_action": "stay",
                "question_policy": "ask_one",
                "response_contract": "Ask what is not working.",
                "coach_adjustment": "Reduce teaching pressure.",
                "reason_short": "The student explicitly says boring.",
                "check_in_question": "Want to switch angles?",
                "confidence": 0.88,
            }
        },
    )

    updated_score = asyncio.run(
        execute_intent_legacy_v2_turn(
            message=object(),
            response_data=response,
            turn_context=context,
            user_input="boring",
            current_curiosity_score=4,
        )
    )

    assert updated_score == 4
    router_step = response.steps[0]
    assert router_step["name"] == "interest_intent_router_v2"
    assert router_step["interest_signal"] == "low"
    assert router_step["student_intent"] == "meta_check_in"
    assert "prompt" not in router_step or router_step["prompt"] is None
    assert "formatted_prompt" not in router_step or router_step["formatted_prompt"] is None
    assert response.steps[1].name == "simplified_conversation"
