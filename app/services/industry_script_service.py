"""Industry-specific script loading service"""

from typing import Optional
from pathlib import Path


class IndustryScriptService:
    """Loads industry-specific default scripts for free tier users"""

    # Industry code to filename mapping
    INDUSTRY_FILES = {
        "insurance": "insurance.md",
        "real_estate": "real_estate.md",
        "b2b": "b2b.md",
        "telecom": "telecom.md",
        "finance": "finance.md",
        "healthcare": "general.md",  # Falls back to general
        "retail": "general.md",
        "other": "general.md",
    }

    def __init__(self, base_path: str = "prompts/industry_scripts"):
        self.base_path = Path(base_path)

    def get_industry_script(self, industry: Optional[str] = None) -> str:
        """
        Get industry-specific script content

        Args:
            industry: Industry type (insurance, real_estate, b2b, etc.)
                     If None, returns general script

        Returns:
            Script content as string
        """
        # Determine which file to load
        filename = self.INDUSTRY_FILES.get(industry, "general.md")
        file_path = self.base_path / filename

        # Fallback to general if file doesn't exist
        if not file_path.exists():
            file_path = self.base_path / "general.md"

        if not file_path.exists():
            return ""

        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def get_industry_context_for_prompt(
        self,
        industry: Optional[str] = None,
        customer_state: Optional[str] = None
    ) -> str:
        """
        Generate prompt context from industry script

        Args:
            industry: Industry type
            customer_state: Current customer state (관심 있음, 고민 중, 망설임 등)

        Returns:
            Formatted context string for injection into prompt
        """
        script = self.get_industry_script(industry)
        if not script:
            return ""

        # Extract relevant sections based on customer state
        context_parts = [
            "## 업종별 영업 스크립트 참고 정보\n",
            f"업종: {industry or '일반'}\n",
        ]

        # Add full script content (will be parsed by sections)
        context_parts.append(script)

        # Add state-specific guidance if available
        if customer_state:
            state_guidance = self._get_state_guidance(customer_state)
            if state_guidance:
                context_parts.append(f"\n## 현재 고객 상태 기반 추천\n")
                context_parts.append(f"고객 상태: **{customer_state}**\n")
                context_parts.append(state_guidance)

        return "\n".join(context_parts)

    def _get_state_guidance(self, customer_state: str) -> str:
        """Get additional guidance based on customer state"""
        state_guidance = {
            "관심 있음": """
이 고객은 관심이 높습니다:
- 구체적인 정보 제공에 집중하세요
- 다음 단계로 자연스럽게 유도하세요
- 클로징 멘트를 준비하세요
""",
            "고민 중": """
이 고객은 결정을 고민하고 있습니다:
- 추가 정보나 비교 자료를 제공하세요
- 고민 포인트를 파악하고 해소해주세요
- 시간을 주되, 후속 연락 일정을 잡으세요
""",
            "망설임": """
이 고객은 우려사항이 있습니다:
- 우려 사항을 직접 물어보세요
- 반대 처리 멘트를 활용하세요
- 신뢰를 쌓는 것이 우선입니다
""",
            "구매 준비됨": """
이 고객은 구매 의향이 높습니다:
- 빠르게 클로징하세요
- 다음 단계 안내를 명확히 하세요
- 추가 혜택이 있다면 언급하세요
""",
            "관심 없음": """
이 고객은 관심이 낮습니다:
- 강압적으로 진행하지 마세요
- 간단한 정보만 제공하고 마무리하세요
- 나중에 연락할 수 있도록 여지를 남기세요
""",
            "불만족": """
이 고객은 불만이 있습니다:
- 먼저 공감을 표현하세요
- 문제 해결에 집중하세요
- 사과가 필요하면 사과하세요
""",
        }
        return state_guidance.get(customer_state, "")


# Global instance
industry_script_service = IndustryScriptService()
