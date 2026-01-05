"""Prompt management system for LLM interactions"""

import os
from pathlib import Path
from typing import Dict, Optional
import re


class PromptManager:
    """Manages prompt templates from markdown files"""

    def __init__(self, prompts_dir: str = "prompts"):
        self.prompts_dir = Path(prompts_dir)
        self._cache: Dict[str, str] = {}

    def load_prompt(self, prompt_path: str, use_cache: bool = True) -> str:
        """
        Load prompt from markdown file

        Args:
            prompt_path: Path relative to prompts directory (e.g., "call_analysis/summarize.md")
            use_cache: Whether to use cached prompt

        Returns:
            Prompt content as string

        Example:
            >>> pm = PromptManager()
            >>> prompt = pm.load_prompt("call_analysis/summarize.md")
        """
        # Check cache
        if use_cache and prompt_path in self._cache:
            return self._cache[prompt_path]

        # Load from file
        full_path = self.prompts_dir / prompt_path

        if not full_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {full_path}")

        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Cache it
        if use_cache:
            self._cache[prompt_path] = content

        return content

    def render_prompt(self, prompt_path: str, variables: Optional[Dict[str, str]] = None) -> str:
        """
        Load and render prompt with variables

        Args:
            prompt_path: Path to prompt template
            variables: Dictionary of variables to inject (e.g., {"transcript": "..."})

        Returns:
            Rendered prompt with variables replaced

        Example:
            >>> pm = PromptManager()
            >>> prompt = pm.render_prompt(
            ...     "call_analysis/summarize.md",
            ...     {"transcript": "안녕하세요...", "sales_type": "insurance"}
            ... )
        """
        template = self.load_prompt(prompt_path)

        if not variables:
            return template

        # Replace {{variable}} with actual values
        rendered = template
        for key, value in variables.items():
            pattern = r"\{\{" + re.escape(key) + r"\}\}"
            rendered = re.sub(pattern, str(value), rendered)

        return rendered

    def clear_cache(self):
        """Clear all cached prompts"""
        self._cache.clear()

    def reload_prompt(self, prompt_path: str) -> str:
        """Reload prompt from file, bypassing cache"""
        return self.load_prompt(prompt_path, use_cache=False)


# Global instance
prompt_manager = PromptManager()


def get_prompt(prompt_path: str, variables: Optional[Dict[str, str]] = None) -> str:
    """
    Convenience function to get rendered prompt

    Args:
        prompt_path: Path to prompt template
        variables: Variables to inject

    Returns:
        Rendered prompt

    Example:
        >>> from app.core.prompt_manager import get_prompt
        >>> prompt = get_prompt(
        ...     "call_analysis/summarize.md",
        ...     {"transcript": "안녕하세요...", "sales_type": "insurance"}
        ... )
    """
    return prompt_manager.render_prompt(prompt_path, variables)
