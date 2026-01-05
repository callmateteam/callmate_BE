"""
Multi-model analysis service.
Uses different LLM models for different analysis tasks based on plan tier.
"""

from typing import Dict, List, Optional
from datetime import datetime

from app.core.prompt_manager import get_prompt
from app.core.llm_config import PromptType
from app.services.llm_client import llm_service
from app.services.company_prompt_service import company_prompt_service
from app.services.industry_script_service import industry_script_service
from app.schemas.analysis import (
    ComprehensiveAnalysis,
    SpeakerSentiment,
    ConversationSummary,
    CustomerNeed,
    CallFlowAnalysis,
    ConversationTurn,
    CustomerState,
    SentimentType
)


class MultiModelAnalysisService:
    """
    Analysis service that uses different models for different tasks.

    Cost optimization strategy:
    - Quick summary: Cheapest model (Gemini Flash)
    - Sentiment analysis: Mid-tier model
    - Customer needs: Mid-tier model
    - Call flow: Mid-tier model
    - Recommended replies: Premium model (Claude) - Korean quality matters most
    """

    def __init__(self):
        self.models_used = []  # Track which models were used

    def analyze_call_comprehensive(
        self,
        transcript_id: str,
        conversation_formatted: str,
        speaker_segments: List[Dict],
        utterances: List[Dict],
        plan: str = "free",
        company_id: Optional[str] = None,
        industry: Optional[str] = None
    ) -> ComprehensiveAnalysis:
        """
        Comprehensive call analysis using multiple models.

        Args:
            transcript_id: Transcript ID
            conversation_formatted: Formatted conversation
            speaker_segments: Speaker-separated segments
            utterances: Time-ordered utterances
            plan: User's plan (free, basic, pro, enterprise)
            company_id: Optional company ID for SaaS
            industry: Optional industry for free tier

        Returns:
            ComprehensiveAnalysis with all results
        """
        self.models_used = []

        # Prepare speaker info
        speaker_texts = {}
        for segment in speaker_segments:
            speaker_texts[segment["speaker"]] = segment["full_text"]

        speakers = list(speaker_texts.keys())
        customer_speaker = self._detect_customer_speaker(speaker_segments, utterances)
        agent_speaker = [s for s in speakers if s != customer_speaker][0] if len(speakers) > 1 else speakers[0]

        customer_text = speaker_texts.get(customer_speaker, "")
        agent_text = speaker_texts.get(agent_speaker, "")

        # Format conversation with roles
        conversation_with_roles = "\n".join([
            f"{'고객' if u['speaker'] == customer_speaker else '상담사'}: {u['text']}"
            for u in utterances
        ])

        utterances_text = "\n".join([
            f"[{'고객' if u['speaker'] == customer_speaker else '상담사'}] {u['text']}"
            for u in utterances
        ])

        # Get script context for recommended replies
        script_context = self._get_script_context(company_id, industry)

        # Step 1: Quick Summary (cheapest model)
        summary_result = self._analyze_summary(
            conversation_with_roles, plan
        )

        # Step 2: Sentiment Analysis (mid-tier)
        sentiment_result = self._analyze_sentiment(
            customer_text, agent_text,
            customer_speaker, agent_speaker,
            plan
        )

        # Step 3: Customer Needs (mid-tier)
        needs_result = self._analyze_customer_needs(
            customer_text, conversation_with_roles, plan
        )

        # Step 4: Call Flow (mid-tier)
        flow_result = self._analyze_call_flow(
            utterances_text, customer_speaker, agent_speaker, plan
        )

        # Step 5: Recommended Replies (premium model - Korean quality)
        replies_result = self._generate_recommended_replies(
            conversation_with_roles,
            sentiment_result.get("customer_state", "고민 중"),
            needs_result.get("primary_reason", "문의"),
            needs_result.get("pain_points", []),
            needs_result.get("urgency_level", "보통"),
            script_context,
            plan
        )

        # Build response
        speaker_sentiments = self._build_speaker_sentiments(
            sentiment_result, customer_speaker, agent_speaker
        )

        conversation_summary = ConversationSummary(
            overview=summary_result.get("summary", ""),
            main_topics=summary_result.get("main_topics", []),
            key_questions=[],
            key_answers=[],
            outcome=summary_result.get("outcome", "")
        )

        customer_need = CustomerNeed(
            primary_reason=needs_result.get("primary_reason", ""),
            specific_needs=needs_result.get("specific_needs", []),
            pain_points=needs_result.get("pain_points", []),
            urgency_level=needs_result.get("urgency_level", "보통")
        )

        conversation_turns = [
            ConversationTurn(**turn)
            for turn in flow_result.get("conversation_turns", [])
        ]

        call_flow = CallFlowAnalysis(
            conversation_turns=conversation_turns,
            customer_journey=flow_result.get("customer_journey", []),
            critical_moments=flow_result.get("critical_moments", [])
        )

        return ComprehensiveAnalysis(
            transcript_id=transcript_id,
            speaker_sentiments=speaker_sentiments,
            customer_state=CustomerState(sentiment_result.get("customer_state", "고민 중")),
            conversation_summary=conversation_summary,
            customer_need=customer_need,
            call_flow=call_flow,
            next_action=replies_result.get("next_action", "후속 연락 필요"),
            recommended_replies=replies_result.get("recommended_replies", []),
            analysis_timestamp=datetime.utcnow().isoformat(),
            confidence_score=0.85,
            models_used=self.models_used  # Include which models were used
        )

    def _analyze_summary(self, conversation: str, plan: str) -> Dict:
        """Step 1: Quick summary using cheapest model"""
        prompt = get_prompt("call_analysis/quick_summary.md", {
            "conversation": conversation
        })

        result = llm_service.generate_json(
            prompt=prompt,
            prompt_type=PromptType.QUICK_SUMMARY,
            plan=plan
        )

        self.models_used.append({
            "task": "quick_summary",
            "model": result["model_display_name"]
        })

        return result.get("parsed", {})

    def _analyze_sentiment(
        self,
        customer_text: str,
        agent_text: str,
        customer_speaker: str,
        agent_speaker: str,
        plan: str
    ) -> Dict:
        """Step 2: Sentiment analysis using mid-tier model"""
        prompt = get_prompt("call_analysis/sentiment_analysis.md", {
            "customer_text": customer_text,
            "agent_text": agent_text,
            "customer_speaker": customer_speaker,
            "agent_speaker": agent_speaker
        })

        result = llm_service.generate_json(
            prompt=prompt,
            prompt_type=PromptType.SENTIMENT_ANALYSIS,
            plan=plan
        )

        self.models_used.append({
            "task": "sentiment_analysis",
            "model": result["model_display_name"]
        })

        return result.get("parsed", {})

    def _analyze_customer_needs(
        self,
        customer_text: str,
        conversation: str,
        plan: str
    ) -> Dict:
        """Step 3: Customer needs analysis"""
        prompt = get_prompt("call_analysis/customer_needs.md", {
            "customer_text": customer_text,
            "conversation": conversation
        })

        result = llm_service.generate_json(
            prompt=prompt,
            prompt_type=PromptType.CUSTOMER_NEEDS,
            plan=plan
        )

        self.models_used.append({
            "task": "customer_needs",
            "model": result["model_display_name"]
        })

        return result.get("parsed", {})

    def _analyze_call_flow(
        self,
        utterances: str,
        customer_speaker: str,
        agent_speaker: str,
        plan: str
    ) -> Dict:
        """Step 4: Call flow analysis"""
        prompt = get_prompt("call_analysis/call_flow.md", {
            "utterances": utterances,
            "customer_speaker": customer_speaker,
            "agent_speaker": agent_speaker
        })

        result = llm_service.generate_json(
            prompt=prompt,
            prompt_type=PromptType.CALL_FLOW,
            plan=plan
        )

        self.models_used.append({
            "task": "call_flow",
            "model": result["model_display_name"]
        })

        return result.get("parsed", {})

    def _generate_recommended_replies(
        self,
        conversation: str,
        customer_state: str,
        primary_need: str,
        pain_points: List[str],
        urgency_level: str,
        script_context: str,
        plan: str
    ) -> Dict:
        """Step 5: Generate recommended replies using premium model"""
        prompt = get_prompt("call_analysis/recommended_replies.md", {
            "conversation": conversation,
            "customer_state": customer_state,
            "primary_need": primary_need,
            "pain_points": ", ".join(pain_points) if pain_points else "없음",
            "urgency_level": urgency_level,
            "script_context": script_context or "업종별 기본 스크립트 사용"
        })

        result = llm_service.generate_json(
            prompt=prompt,
            prompt_type=PromptType.RECOMMENDED_REPLIES,
            plan=plan
        )

        self.models_used.append({
            "task": "recommended_replies",
            "model": result["model_display_name"]
        })

        return result.get("parsed", {})

    def _get_script_context(
        self,
        company_id: Optional[str],
        industry: Optional[str]
    ) -> str:
        """Get script context for recommended replies"""
        if company_id:
            company = company_prompt_service.get_company(company_id)
            if company:
                context = company_prompt_service.get_prompt_context(company_id)
                if context:
                    return context
                # Fall back to industry if no scripts uploaded
                return industry_script_service.get_industry_context_for_prompt(
                    company.get("industry")
                )

        # Free tier with industry
        return industry_script_service.get_industry_context_for_prompt(
            industry or "other"
        )

    def _detect_customer_speaker(
        self,
        speaker_segments: List[Dict],
        utterances: List[Dict]
    ) -> str:
        """Detect which speaker is the customer"""
        if not utterances:
            return "A"

        speakers = list(set(u["speaker"] for u in utterances))
        if len(speakers) < 2:
            return speakers[0]

        scores = {speaker: 0 for speaker in speakers}

        # Question patterns
        question_keywords = ["어떻게", "뭐", "무엇", "왜", "어디", "언제", "얼마", "?"]
        for utterance in utterances:
            for keyword in question_keywords:
                if keyword in utterance["text"]:
                    scores[utterance["speaker"]] += 2

        # Agent greeting patterns
        agent_patterns = ["입니다", "되십니까", "도와드리겠습니다", "고객님"]
        for i, utterance in enumerate(utterances[:3]):
            for pattern in agent_patterns:
                if pattern in utterance["text"]:
                    scores[utterance["speaker"]] -= 3

        return max(scores.items(), key=lambda x: x[1])[0]

    def _build_speaker_sentiments(
        self,
        sentiment_result: Dict,
        customer_speaker: str,
        agent_speaker: str
    ) -> List[SpeakerSentiment]:
        """Build SpeakerSentiment objects from sentiment analysis result"""
        sentiments = []

        customer_data = sentiment_result.get("customer", {})
        if customer_data:
            sentiments.append(SpeakerSentiment(
                speaker=customer_speaker,
                overall_sentiment=self._parse_sentiment(customer_data.get("overall_sentiment", "중립")),
                sentiment_score=customer_data.get("sentiment_score", 0.5),
                tone_analysis=customer_data.get("tone", ""),
                engagement_level=customer_data.get("engagement_level", "보통"),
                key_emotions=customer_data.get("key_emotions", [])
            ))

        agent_data = sentiment_result.get("agent", {})
        if agent_data:
            sentiments.append(SpeakerSentiment(
                speaker=agent_speaker,
                overall_sentiment=self._parse_sentiment(agent_data.get("overall_sentiment", "중립")),
                sentiment_score=agent_data.get("sentiment_score", 0.5),
                tone_analysis=agent_data.get("tone", ""),
                engagement_level=agent_data.get("engagement_level", "보통"),
                key_emotions=agent_data.get("key_emotions", [])
            ))

        return sentiments

    def _parse_sentiment(self, sentiment_str: str) -> SentimentType:
        """Parse sentiment string to enum"""
        mapping = {
            "긍정": SentimentType.POSITIVE,
            "부정": SentimentType.NEGATIVE,
            "중립": SentimentType.NEUTRAL,
        }
        return mapping.get(sentiment_str, SentimentType.NEUTRAL)


# Global instance
multi_model_analysis_service = MultiModelAnalysisService()
