"""Multi-provider LLM client with fallback support"""

import json
from typing import Dict, Optional, Any
from abc import ABC, abstractmethod

import openai
import anthropic
import google.generativeai as genai

from app.core.config import settings
from app.core.llm_config import (
    LLMProvider,
    LLMModelConfig,
    PromptType,
    AVAILABLE_MODELS,
    get_model_for_prompt,
    get_fallback_models,
)


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients"""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        json_mode: bool = False
    ) -> str:
        """Generate response from the model"""
        pass


class OpenAIClient(BaseLLMClient):
    """OpenAI GPT client"""

    def __init__(self, model_id: str):
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model_id = model_id

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        json_mode: bool = False
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model": self.model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude client"""

    def __init__(self, model_id: str):
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model_id = model_id

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        json_mode: bool = False
    ) -> str:
        kwargs = {
            "model": self.model_id,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        response = self.client.messages.create(**kwargs)
        return response.content[0].text


class GoogleClient(BaseLLMClient):
    """Google Gemini client"""

    def __init__(self, model_id: str):
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.model = genai.GenerativeModel(model_id)
        self.model_id = model_id

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        json_mode: bool = False
    ) -> str:
        # Combine system prompt with user prompt for Gemini
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        generation_config = genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        if json_mode:
            generation_config.response_mime_type = "application/json"

        response = self.model.generate_content(
            full_prompt,
            generation_config=generation_config
        )
        return response.text


def get_llm_client(model_config: LLMModelConfig) -> BaseLLMClient:
    """
    Factory function to get the appropriate LLM client

    Args:
        model_config: Model configuration

    Returns:
        LLM client instance
    """
    if model_config.provider == LLMProvider.OPENAI:
        return OpenAIClient(model_config.model_id)
    elif model_config.provider == LLMProvider.ANTHROPIC:
        return AnthropicClient(model_config.model_id)
    elif model_config.provider == LLMProvider.GOOGLE:
        return GoogleClient(model_config.model_id)
    else:
        raise ValueError(f"Unknown provider: {model_config.provider}")


class MultiModelLLMService:
    """
    Service that uses different models for different prompt types.
    Supports fallback when a model fails.
    """

    def __init__(self):
        self._clients: Dict[str, BaseLLMClient] = {}

    def _get_client(self, model_key: str) -> BaseLLMClient:
        """Get or create a client for a model"""
        if model_key not in self._clients:
            model_config = AVAILABLE_MODELS.get(model_key)
            if not model_config:
                raise ValueError(f"Unknown model: {model_key}")
            self._clients[model_key] = get_llm_client(model_config)
        return self._clients[model_key]

    def generate(
        self,
        prompt: str,
        prompt_type: PromptType,
        plan: str = "free",
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate response using the appropriate model for the prompt type

        Args:
            prompt: The prompt text
            prompt_type: Type of prompt (determines which model to use)
            plan: User's plan (free, basic, pro, enterprise)
            system_prompt: Optional system prompt
            json_mode: Whether to request JSON output
            variables: Variables to inject into prompt

        Returns:
            Dict with response and metadata
        """
        # Get the model for this prompt type and plan
        model_config = get_model_for_prompt(plan, prompt_type)
        model_key = None

        # Find model key
        for key, config in AVAILABLE_MODELS.items():
            if config.model_id == model_config.model_id:
                model_key = key
                break

        # Try primary model, then fallbacks
        models_to_try = [model_key] + get_fallback_models(model_key)
        last_error = None

        for try_model_key in models_to_try:
            try:
                client = self._get_client(try_model_key)
                config = AVAILABLE_MODELS[try_model_key]

                response = client.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                    json_mode=json_mode
                )

                return {
                    "content": response,
                    "model_used": try_model_key,
                    "model_display_name": config.display_name,
                    "provider": config.provider.value,
                    "was_fallback": try_model_key != model_key,
                }

            except Exception as e:
                last_error = e
                continue

        # All models failed
        raise RuntimeError(
            f"All models failed for {prompt_type}. Last error: {last_error}"
        )

    def generate_json(
        self,
        prompt: str,
        prompt_type: PromptType,
        plan: str = "free",
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate and parse JSON response

        Returns:
            Dict with parsed JSON and metadata
        """
        result = self.generate(
            prompt=prompt,
            prompt_type=prompt_type,
            plan=plan,
            system_prompt=system_prompt,
            json_mode=True
        )

        # Parse JSON
        try:
            parsed = json.loads(result["content"])
            result["parsed"] = parsed
        except json.JSONDecodeError as e:
            # Try to extract JSON from response
            content = result["content"]
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    parsed = json.loads(content[start:end])
                    result["parsed"] = parsed
                except json.JSONDecodeError:
                    raise ValueError(f"Failed to parse JSON: {e}")
            else:
                raise ValueError(f"Failed to parse JSON: {e}")

        return result


# Global instance
llm_service = MultiModelLLMService()
