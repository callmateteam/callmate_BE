"""LLM service for call analysis using OpenAI"""

from typing import Dict, Optional
import json
import openai
from app.core.config import settings
from app.core.prompt_manager import get_prompt


class LLMService:
    """Service for LLM-based call analysis"""

    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY
        self.model = "gpt-4"  # or "gpt-3.5-turbo" for cheaper option

    def summarize_call(
        self,
        transcript: str,
        sales_type: Optional[str] = None,
        conversation_goal: Optional[str] = None
    ) -> Dict:
        """
        Summarize call transcript using LLM

        Args:
            transcript: Full call transcript text
            sales_type: Type of sales (insurance, real_estate, b2b, etc)
            conversation_goal: Goal of conversation (follow_up, objection_handling, close)

        Returns:
            Dictionary with call summary:
            {
                "customer_needs": str,
                "objections": List[str],
                "decision_stage": str
            }

        Example:
            >>> service = LLMService()
            >>> result = service.summarize_call(
            ...     transcript="안녕하세요...",
            ...     sales_type="insurance"
            ... )
        """
        # Load and render prompt from markdown
        prompt = get_prompt(
            "call_analysis/summarize.md",
            {
                "transcript": transcript,
                "sales_type": sales_type or "일반",
                "conversation_goal": conversation_goal or "일반 상담"
            }
        )

        # Get system prompt
        system_prompt = get_prompt("common/system.md")

        # Call OpenAI API
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Lower temperature for more consistent output
            max_tokens=500
        )

        # Parse JSON response
        content = response.choices[0].message.content
        try:
            summary = json.loads(content)
        except json.JSONDecodeError:
            # Fallback if LLM didn't return valid JSON
            summary = {
                "customer_needs": "분석 실패",
                "objections": [],
                "decision_stage": "알 수 없음"
            }

        return summary

    def recommend_replies(
        self,
        transcript: str,
        summary: Dict,
        sales_type: Optional[str] = None,
        conversation_goal: Optional[str] = None,
        tone: Optional[str] = None
    ) -> Dict:
        """
        Generate recommended reply messages based on call analysis

        Args:
            transcript: Full call transcript
            summary: Call summary from summarize_call()
            sales_type: Type of sales
            conversation_goal: Goal of conversation
            tone: Tone of replies (friendly, professional, persuasive)

        Returns:
            Dictionary with recommendations:
            {
                "next_action": str,
                "recommended_replies": List[str]
            }

        Example:
            >>> service = LLMService()
            >>> summary = service.summarize_call(transcript)
            >>> replies = service.recommend_replies(
            ...     transcript=transcript,
            ...     summary=summary,
            ...     tone="friendly"
            ... )
        """
        # Load and render prompt
        prompt = get_prompt(
            "call_analysis/recommend_replies.md",
            {
                "transcript": transcript,
                "summary": json.dumps(summary, ensure_ascii=False),
                "sales_type": sales_type or "일반",
                "conversation_goal": conversation_goal or "일반 상담",
                "tone": tone or "friendly",
                "customer_needs": summary.get("customer_needs", ""),
                "objections": ", ".join(summary.get("objections", [])),
                "decision_stage": summary.get("decision_stage", "")
            }
        )

        # Get system prompt
        system_prompt = get_prompt("common/system.md")

        # Call OpenAI API
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,  # Higher temperature for more creative replies
            max_tokens=800
        )

        # Parse JSON response
        content = response.choices[0].message.content
        try:
            recommendations = json.loads(content)
        except json.JSONDecodeError:
            # Fallback
            recommendations = {
                "next_action": "후속 연락",
                "recommended_replies": [
                    "안녕하세요, 지난번 통화 내용 관련해서 연락드렸습니다."
                ]
            }

        return recommendations

    def analyze_call_full(
        self,
        transcript: str,
        sales_type: Optional[str] = None,
        conversation_goal: Optional[str] = None,
        tone: Optional[str] = None
    ) -> Dict:
        """
        Full call analysis: summarize + recommend replies

        Args:
            transcript: Full call transcript
            sales_type: Type of sales
            conversation_goal: Goal of conversation
            tone: Tone of replies

        Returns:
            Complete analysis result
        """
        # Step 1: Summarize
        summary = self.summarize_call(
            transcript=transcript,
            sales_type=sales_type,
            conversation_goal=conversation_goal
        )

        # Step 2: Recommend replies
        recommendations = self.recommend_replies(
            transcript=transcript,
            summary=summary,
            sales_type=sales_type,
            conversation_goal=conversation_goal,
            tone=tone
        )

        # Combine results
        return {
            "call_summary": summary,
            "next_action": recommendations["next_action"],
            "recommended_replies": recommendations["recommended_replies"]
        }


# Global instance
llm_service = LLMService()
