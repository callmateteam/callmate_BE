"""LLM configuration for different tiers and providers"""

from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


class ModelTier(str, Enum):
    """Model tiers by cost/quality"""
    ECONOMY = "economy"      # Cheapest, basic quality
    STANDARD = "standard"    # Good balance
    PREMIUM = "premium"      # Best quality


class LLMModelConfig(BaseModel):
    """Configuration for a specific LLM model"""
    provider: LLMProvider
    model_id: str
    display_name: str
    input_cost_per_1m: float   # USD per 1M input tokens
    output_cost_per_1m: float  # USD per 1M output tokens
    max_tokens: int = 4096
    temperature: float = 0.3
    supports_json_mode: bool = True


# Available models configuration
AVAILABLE_MODELS: Dict[str, LLMModelConfig] = {
    # Google Gemini - Economy tier
    "gemini-flash": LLMModelConfig(
        provider=LLMProvider.GOOGLE,
        model_id="gemini-2.0-flash",
        display_name="Gemini 2.0 Flash",
        input_cost_per_1m=0.15,
        output_cost_per_1m=0.60,
        max_tokens=8192,
    ),
    "gemini-pro": LLMModelConfig(
        provider=LLMProvider.GOOGLE,
        model_id="gemini-2.5-pro",
        display_name="Gemini 2.5 Pro",
        input_cost_per_1m=1.25,
        output_cost_per_1m=10.00,
        max_tokens=8192,
    ),

    # OpenAI GPT - Standard tier
    "gpt-4o-mini": LLMModelConfig(
        provider=LLMProvider.OPENAI,
        model_id="gpt-4o-mini",
        display_name="GPT-4o Mini",
        input_cost_per_1m=0.15,
        output_cost_per_1m=0.60,
        max_tokens=4096,
    ),
    "gpt-4o": LLMModelConfig(
        provider=LLMProvider.OPENAI,
        model_id="gpt-4o",
        display_name="GPT-4o",
        input_cost_per_1m=5.00,
        output_cost_per_1m=15.00,
        max_tokens=4096,
    ),

    # Anthropic Claude - Premium tier
    "claude-haiku": LLMModelConfig(
        provider=LLMProvider.ANTHROPIC,
        model_id="claude-3-5-haiku-latest",
        display_name="Claude 3.5 Haiku",
        input_cost_per_1m=1.00,
        output_cost_per_1m=5.00,
        max_tokens=4096,
    ),
    "claude-sonnet": LLMModelConfig(
        provider=LLMProvider.ANTHROPIC,
        model_id="claude-sonnet-4-20250514",
        display_name="Claude Sonnet 4",
        input_cost_per_1m=3.00,
        output_cost_per_1m=15.00,
        max_tokens=4096,
    ),
}


class PromptType(str, Enum):
    """Types of prompts/tasks"""
    QUICK_SUMMARY = "quick_summary"           # 간단 요약 - 저렴한 모델
    SENTIMENT_ANALYSIS = "sentiment_analysis"  # 감정 분석 - 중간 모델
    CUSTOMER_NEEDS = "customer_needs"          # 니즈 분석 - 중간 모델
    CALL_FLOW = "call_flow"                    # 대화 흐름 - 중간 모델
    RECOMMENDED_REPLIES = "recommended_replies" # 추천 멘트 - 프리미엄 모델 (한국어 품질)
    COMPREHENSIVE = "comprehensive"            # 종합 분석 - 프리미엄 모델


# 프롬프트 종류별 모델 매핑
# 핵심: 추천 멘트 생성은 한국어 품질이 중요하므로 Claude 사용
PROMPT_MODEL_MAPPING: Dict[str, Dict[str, str]] = {
    # 무료 티어 - 전체 저렴한 모델
    "free": {
        PromptType.QUICK_SUMMARY: "gemini-flash",
        PromptType.SENTIMENT_ANALYSIS: "gemini-flash",
        PromptType.CUSTOMER_NEEDS: "gemini-flash",
        PromptType.CALL_FLOW: "gemini-flash",
        PromptType.RECOMMENDED_REPLIES: "gemini-flash",
        PromptType.COMPREHENSIVE: "gemini-flash",
    },

    # Basic 티어 - 분석은 저렴하게, 추천 멘트만 좋은 모델
    "basic": {
        PromptType.QUICK_SUMMARY: "gemini-flash",
        PromptType.SENTIMENT_ANALYSIS: "gemini-flash",
        PromptType.CUSTOMER_NEEDS: "gpt-4o-mini",
        PromptType.CALL_FLOW: "gemini-flash",
        PromptType.RECOMMENDED_REPLIES: "claude-haiku",  # 한국어 멘트는 Claude
        PromptType.COMPREHENSIVE: "gpt-4o-mini",
    },

    # Pro 티어 - 분석은 중간, 추천 멘트는 프리미엄
    "pro": {
        PromptType.QUICK_SUMMARY: "gemini-flash",
        PromptType.SENTIMENT_ANALYSIS: "gpt-4o-mini",
        PromptType.CUSTOMER_NEEDS: "gpt-4o-mini",
        PromptType.CALL_FLOW: "gpt-4o-mini",
        PromptType.RECOMMENDED_REPLIES: "claude-sonnet",  # 최고 품질 한국어
        PromptType.COMPREHENSIVE: "claude-haiku",
    },

    # Enterprise 티어 - 전체 프리미엄
    "enterprise": {
        PromptType.QUICK_SUMMARY: "gpt-4o-mini",
        PromptType.SENTIMENT_ANALYSIS: "claude-haiku",
        PromptType.CUSTOMER_NEEDS: "claude-haiku",
        PromptType.CALL_FLOW: "claude-haiku",
        PromptType.RECOMMENDED_REPLIES: "claude-sonnet",
        PromptType.COMPREHENSIVE: "claude-sonnet",
    },
}


# Fallback chain when primary model fails
MODEL_FALLBACK_CHAIN: Dict[str, list] = {
    "claude-sonnet": ["gpt-4o", "gemini-pro"],
    "claude-haiku": ["gpt-4o-mini", "gemini-pro"],
    "gpt-4o": ["claude-sonnet", "gemini-pro"],
    "gpt-4o-mini": ["claude-haiku", "gemini-flash"],
    "gemini-pro": ["gpt-4o-mini", "claude-haiku"],
    "gemini-flash": ["gpt-4o-mini"],
}


def get_model_for_prompt(
    plan: str,
    prompt_type: PromptType
) -> LLMModelConfig:
    """
    Get the appropriate model for a specific prompt type and plan

    Args:
        plan: Plan type (free, basic, pro, enterprise)
        prompt_type: Type of prompt/task

    Returns:
        LLMModelConfig for the prompt type
    """
    plan_mapping = PROMPT_MODEL_MAPPING.get(plan, PROMPT_MODEL_MAPPING["free"])
    model_key = plan_mapping.get(prompt_type, "gemini-flash")
    return AVAILABLE_MODELS[model_key]


def get_model_by_key(model_key: str) -> Optional[LLMModelConfig]:
    """Get model config by key"""
    return AVAILABLE_MODELS.get(model_key)


def get_fallback_models(model_key: str) -> list:
    """Get fallback models for a given model"""
    return MODEL_FALLBACK_CHAIN.get(model_key, [])


def estimate_cost(
    model_key: str,
    input_tokens: int,
    output_tokens: int
) -> float:
    """
    Estimate cost for a request

    Args:
        model_key: Model key
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Estimated cost in USD
    """
    model = AVAILABLE_MODELS.get(model_key)
    if not model:
        return 0.0

    input_cost = (input_tokens / 1_000_000) * model.input_cost_per_1m
    output_cost = (output_tokens / 1_000_000) * model.output_cost_per_1m

    return input_cost + output_cost
