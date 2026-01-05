"""Tests for prompt manager"""

import pytest
from app.core.prompt_manager import PromptManager, get_prompt


def test_load_prompt():
    """Test loading prompt from file"""
    pm = PromptManager()
    prompt = pm.load_prompt("common/system.md")

    assert prompt is not None
    assert "CallMate" in prompt
    assert len(prompt) > 0


def test_render_prompt_with_variables():
    """Test rendering prompt with variables"""
    pm = PromptManager()

    variables = {
        "transcript": "안녕하세요, 보험 상담 받고 싶습니다.",
        "sales_type": "insurance",
        "conversation_goal": "follow_up"
    }

    rendered = pm.render_prompt("call_analysis/summarize.md", variables)

    # Check variables are replaced
    assert "{{transcript}}" not in rendered
    assert "안녕하세요, 보험 상담 받고 싶습니다." in rendered
    assert "insurance" in rendered
    assert "follow_up" in rendered


def test_render_prompt_without_variables():
    """Test rendering prompt without variables"""
    pm = PromptManager()
    rendered = pm.render_prompt("common/system.md")

    assert rendered is not None
    assert len(rendered) > 0


def test_cache():
    """Test prompt caching"""
    pm = PromptManager()

    # First load
    prompt1 = pm.load_prompt("common/system.md", use_cache=True)

    # Second load (from cache)
    prompt2 = pm.load_prompt("common/system.md", use_cache=True)

    assert prompt1 == prompt2
    assert "common/system.md" in pm._cache


def test_clear_cache():
    """Test clearing cache"""
    pm = PromptManager()

    # Load and cache
    pm.load_prompt("common/system.md", use_cache=True)
    assert len(pm._cache) > 0

    # Clear cache
    pm.clear_cache()
    assert len(pm._cache) == 0


def test_reload_prompt():
    """Test reloading prompt"""
    pm = PromptManager()

    # Load with cache
    prompt1 = pm.load_prompt("common/system.md", use_cache=True)

    # Reload (bypass cache)
    prompt2 = pm.reload_prompt("common/system.md")

    assert prompt1 == prompt2  # Content should be same


def test_get_prompt_convenience_function():
    """Test convenience function"""
    prompt = get_prompt(
        "call_analysis/summarize.md",
        {
            "transcript": "테스트 전사 내용",
            "sales_type": "b2b",
            "conversation_goal": "close"
        }
    )

    assert "테스트 전사 내용" in prompt
    assert "b2b" in prompt
    assert "close" in prompt


def test_missing_prompt_file():
    """Test handling of missing prompt file"""
    pm = PromptManager()

    with pytest.raises(FileNotFoundError):
        pm.load_prompt("nonexistent/prompt.md")


def test_multiple_variables():
    """Test rendering with multiple variables"""
    pm = PromptManager()

    variables = {
        "transcript": "전사 내용",
        "sales_type": "insurance",
        "conversation_goal": "follow_up",
        "tone": "friendly",
        "customer_needs": "가족 건강 보장",
        "objections": "가격 부담",
        "decision_stage": "검토 단계"
    }

    rendered = pm.render_prompt("call_analysis/recommend_replies.md", variables)

    # All variables should be replaced
    for key, value in variables.items():
        assert value in rendered
        # No unreplaced variables
        assert f"{{{{{key}}}}}" not in rendered
