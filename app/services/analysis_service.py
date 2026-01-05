"""Comprehensive call analysis service"""

from typing import Dict, List, Optional
import json
from datetime import datetime
import openai

from app.core.config import settings
from app.core.prompt_manager import get_prompt
from app.services.company_prompt_service import company_prompt_service
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


class AnalysisService:
    """Comprehensive call analysis service"""

    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY
        self.model = "gpt-4"

    def analyze_call_comprehensive(
        self,
        transcript_id: str,
        conversation_formatted: str,
        speaker_segments: List[Dict],
        utterances: List[Dict],
        company_id: Optional[str] = None,
        industry: Optional[str] = None
    ) -> ComprehensiveAnalysis:
        """
        Comprehensive call analysis including sentiment, flow, and customer needs

        Args:
            transcript_id: Transcript ID
            conversation_formatted: Formatted conversation (A: ... B: ...)
            speaker_segments: Speaker-separated segments
            utterances: Time-ordered utterances
            company_id: Optional company ID for company-specific analysis (SaaS)
            industry: Optional industry type for free tier users

        Returns:
            ComprehensiveAnalysis object
        """
        # Prepare speaker texts
        speaker_texts = {}
        for segment in speaker_segments:
            speaker_texts[segment["speaker"]] = segment["full_text"]

        # Get speakers (usually A and B)
        speakers = list(speaker_texts.keys())

        # Detect customer speaker (who speaks first usually)
        customer_speaker = self.detect_customer_speaker(speaker_segments, utterances)
        agent_speaker = [s for s in speakers if s != customer_speaker][0] if len(speakers) > 1 else speakers[0]

        customer_text = speaker_texts.get(customer_speaker, "")
        agent_text = speaker_texts.get(agent_speaker, "")

        # Format utterances for prompt with role labels
        utterances_text = "\n".join([
            f"[{'고객' if u['speaker'] == customer_speaker else '상담사'}] {u['text']}"
            for u in utterances
        ])

        # Format conversation with roles
        conversation_with_roles = "\n".join([
            f"{'고객' if u['speaker'] == customer_speaker else '상담사'}: {u['text']}"
            for u in utterances
        ])

        # Load and render prompt
        # Use company-specific prompt if company_id is provided (SaaS)
        variables = {
            "conversation": conversation_with_roles,
            "customer_text": customer_text,
            "agent_text": agent_text,
            "utterances": utterances_text,
            "customer_speaker": customer_speaker,
            "agent_speaker": agent_speaker
        }

        # Get prompt with appropriate context
        # - SaaS: company_id → company-specific scripts from PDF
        # - Free tier: industry → industry-specific default scripts
        prompt = company_prompt_service.get_analysis_prompt(
            company_id=company_id,
            base_prompt_path="call_analysis/comprehensive_analysis.md",
            variables=variables,
            industry=industry
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
            temperature=0.3,
            max_tokens=3000
        )

        # Parse JSON response
        content = response.choices[0].message.content
        try:
            analysis_dict = json.loads(content)
        except json.JSONDecodeError as e:
            # Fallback if parsing fails
            raise ValueError(f"Failed to parse LLM response: {e}\nContent: {content}")

        # Convert to Pydantic models
        speaker_sentiments = [
            SpeakerSentiment(**s) for s in analysis_dict["speaker_sentiments"]
        ]

        conversation_summary = ConversationSummary(
            **analysis_dict["conversation_summary"]
        )

        customer_need = CustomerNeed(**analysis_dict["customer_need"])

        conversation_turns = [
            ConversationTurn(**t) for t in analysis_dict["call_flow"]["conversation_turns"]
        ]

        call_flow = CallFlowAnalysis(
            conversation_turns=conversation_turns,
            customer_journey=analysis_dict["call_flow"]["customer_journey"],
            critical_moments=analysis_dict["call_flow"].get("critical_moments", [])
        )

        # Build final analysis
        analysis = ComprehensiveAnalysis(
            transcript_id=transcript_id,
            speaker_sentiments=speaker_sentiments,
            customer_state=CustomerState(analysis_dict["customer_state"]),
            conversation_summary=conversation_summary,
            customer_need=customer_need,
            call_flow=call_flow,
            next_action=analysis_dict["next_action"],
            recommended_replies=analysis_dict["recommended_replies"],
            analysis_timestamp=datetime.utcnow().isoformat(),
            confidence_score=analysis_dict.get("confidence_score", 0.0)
        )

        return analysis

    def get_quick_summary(
        self,
        conversation_formatted: str,
        max_length: int = 200
    ) -> str:
        """
        Get a quick one-line summary of the conversation

        Args:
            conversation_formatted: Formatted conversation
            max_length: Maximum summary length

        Returns:
            Quick summary string
        """
        prompt = f"""다음 대화를 한 문장으로 요약하세요 (최대 {max_length}자):

{conversation_formatted}

요약:"""

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Use cheaper model for quick summary
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=100
        )

        summary = response.choices[0].message.content.strip()
        return summary[:max_length]

    def detect_customer_speaker(
        self,
        speaker_segments: List[Dict],
        utterances: List[Dict]
    ) -> str:
        """
        Detect which speaker is the customer (vs sales agent)

        Uses multiple heuristics:
        1. Question patterns (customers ask more questions)
        2. Greeting patterns (sales agent often greets formally)
        3. Length of speech (agent usually speaks more)

        Args:
            speaker_segments: Speaker segments
            utterances: Utterances list

        Returns:
            Speaker label of customer (e.g., "A" or "B")
        """
        if not utterances or len(utterances) == 0:
            return "A"  # Default

        speakers = list(set(u["speaker"] for u in utterances))
        if len(speakers) < 2:
            return speakers[0]

        # Score for each speaker (higher = more likely customer)
        scores = {speaker: 0 for speaker in speakers}

        # Heuristic 1: Question patterns (고객이 질문을 더 많이 함)
        question_keywords = ["어떻게", "뭐", "무엇", "왜", "어디", "언제", "얼마", "어느", "?"]
        for utterance in utterances:
            text = utterance["text"]
            speaker = utterance["speaker"]
            for keyword in question_keywords:
                if keyword in text:
                    scores[speaker] += 2

        # Heuristic 2: Agent greeting patterns (상담사가 회사명으로 인사)
        agent_greeting_patterns = [
            "입니다", "되십니까", "도와드리겠습니다",
            "안녕하세요 ", "감사합니다", "고객님"
        ]
        for i, utterance in enumerate(utterances[:3]):  # Check first 3 utterances
            text = utterance["text"]
            speaker = utterance["speaker"]
            for pattern in agent_greeting_patterns:
                if pattern in text:
                    scores[speaker] -= 3  # Negative score = likely agent

        # Heuristic 3: Customer initiates with purpose
        customer_opening_patterns = [
            "문의", "알아보", "궁금", "상담", "신청", "가입",
            "전화했", "듣고 싶", "받고 싶"
        ]
        if len(utterances) > 0:
            first_text = utterances[0]["text"]
            first_speaker = utterances[0]["speaker"]
            for pattern in customer_opening_patterns:
                if pattern in first_text:
                    scores[first_speaker] += 5

        # Heuristic 4: Speech length (상담사가 보통 더 많이 말함)
        total_words = {speaker: 0 for speaker in speakers}
        for segment in speaker_segments:
            total_words[segment["speaker"]] = len(segment["full_text"])

        # Customer usually speaks less
        if len(total_words) == 2:
            speakers_sorted = sorted(total_words.items(), key=lambda x: x[1])
            if speakers_sorted[0][1] < speakers_sorted[1][1] * 0.7:
                # If one speaker speaks significantly less
                scores[speakers_sorted[0][0]] += 3

        # Return speaker with highest score
        customer_speaker = max(scores.items(), key=lambda x: x[1])[0]

        return customer_speaker


# Global instance
analysis_service = AnalysisService()
