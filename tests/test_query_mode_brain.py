"""Brain unit tests for query_mode rendering and tutor_mode pipeline."""
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

from src.process_query_entrypoint import _resolve_render_query  # noqa: E402
from src.pipelines import tutor_mode  # noqa: E402


def test_resolve_render_query():
    assert _resolve_render_query("hello", "include") == "hello"
    assert _resolve_render_query("hello", "opening_only") == "hello"
    assert _resolve_render_query("hello", "omit") == ""


def test_tutor_mode_pipeline_prompt_policy():
    assert tutor_mode.TURN_PROMPT_POLICY.prompt_name == "tutor_mode_base"
    assert tutor_mode.OPENING_PROMPT_POLICY.prompt_name == "tutor_mode_base"
