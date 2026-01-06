"""Call analysis service for MVP"""

from typing import Dict, List, Optional
import json
from datetime import datetime
from openai import OpenAI

from app.core.config import settings
from app.core.prompt_manager import get_prompt
from app.schemas.analysis import (
    ComprehensiveAnalysis,
    SpeakerSentiment,
    ConversationSummary,
    CustomerNeed,
    CallFlowAnalysis,
    ConversationTurn,
    CustomerState,
    SentimentType,
    AISummaryResponse,
    FeedbackItem,
    FeedbackType,
    ResponseFeedbackResponse
)


class AnalysisService:
    """MVP Call analysis service using OpenAI"""

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY.get_secret_value())
        self.model = "gpt-4o-mini"  # MVP: 비용 효율적인 모델 사용

    def analyze_call(
        self,
        transcript_id: str,
        conversation_formatted: str,
        speaker_segments: List[Dict],
        utterances: List[Dict],
        script_context: Optional[str] = None
    ) -> ComprehensiveAnalysis:
        """
        통화 종합 분석

        Args:
            transcript_id: 전사 ID
            conversation_formatted: 포맷된 대화 (A: ... B: ...)
            speaker_segments: 화자별 발화 세그먼트
            utterances: 시간순 발화 목록
            script_context: 스크립트 컨텍스트 (폼/PDF에서 추출)

        Returns:
            ComprehensiveAnalysis 객체
        """
        # 화자별 텍스트 준비
        speaker_texts = {}
        for segment in speaker_segments:
            speaker_texts[segment["speaker"]] = segment["full_text"]

        speakers = list(speaker_texts.keys())

        # 고객/상담사 화자 구분
        customer_speaker = self._detect_customer_speaker(speaker_segments, utterances)
        agent_speaker = [s for s in speakers if s != customer_speaker][0] if len(speakers) > 1 else speakers[0]

        customer_text = speaker_texts.get(customer_speaker, "")
        agent_text = speaker_texts.get(agent_speaker, "")

        # 역할 라벨이 붙은 대화 포맷
        conversation_with_roles = "\n".join([
            f"{'고객' if u['speaker'] == customer_speaker else '상담사'}: {u['text']}"
            for u in utterances
        ])

        utterances_text = "\n".join([
            f"[{'고객' if u['speaker'] == customer_speaker else '상담사'}] {u['text']}"
            for u in utterances
        ])

        # 프롬프트 변수 준비
        variables = {
            "conversation": conversation_with_roles,
            "customer_text": customer_text,
            "agent_text": agent_text,
            "utterances": utterances_text,
            "customer_speaker": customer_speaker,
            "agent_speaker": agent_speaker
        }

        # 프롬프트 로드 및 렌더링
        prompt = get_prompt("call_analysis/comprehensive_analysis.md", variables)

        # 스크립트 컨텍스트가 있으면 프롬프트에 추가
        if script_context:
            prompt += f"\n\n---\n\n## 참고: 회사 스크립트\n\n{script_context}\n\n위 스크립트를 참고하여 추천 멘트를 생성하세요."

        # 시스템 프롬프트
        system_prompt = get_prompt("common/system.md")

        # OpenAI API 호출
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=3000
        )

        # JSON 응답 파싱
        content = response.choices[0].message.content

        # JSON 블록 추출 (```json ... ``` 형식 처리)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        try:
            analysis_dict = json.loads(content.strip())
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM 응답 파싱 실패: {e}\nContent: {content}")

        # Pydantic 모델로 변환
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

        # 최종 분석 결과
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

    def _detect_customer_speaker(
        self,
        speaker_segments: List[Dict],
        utterances: List[Dict]
    ) -> str:
        """
        고객 화자 감지 (상담사 vs 고객)

        휴리스틱:
        1. 질문 패턴 (고객이 질문을 더 많이 함)
        2. 인사 패턴 (상담사가 회사명으로 인사)
        3. 발화량 (상담사가 보통 더 많이 말함)
        """
        if not utterances or len(utterances) == 0:
            return "A"

        speakers = list(set(u["speaker"] for u in utterances))
        if len(speakers) < 2:
            return speakers[0]

        scores = {speaker: 0 for speaker in speakers}

        # 질문 패턴 (고객이 질문을 더 많이 함)
        question_keywords = ["어떻게", "뭐", "무엇", "왜", "어디", "언제", "얼마", "어느", "?"]
        for utterance in utterances:
            text = utterance["text"]
            speaker = utterance["speaker"]
            for keyword in question_keywords:
                if keyword in text:
                    scores[speaker] += 2

        # 상담사 인사 패턴
        agent_greeting_patterns = [
            "입니다", "되십니까", "도와드리겠습니다",
            "안녕하세요 ", "감사합니다", "고객님"
        ]
        for i, utterance in enumerate(utterances[:3]):
            text = utterance["text"]
            speaker = utterance["speaker"]
            for pattern in agent_greeting_patterns:
                if pattern in text:
                    scores[speaker] -= 3

        # 고객 오프닝 패턴
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

        # 발화량 (상담사가 보통 더 많이 말함)
        total_words = {speaker: 0 for speaker in speakers}
        for segment in speaker_segments:
            total_words[segment["speaker"]] = len(segment["full_text"])

        if len(total_words) == 2:
            speakers_sorted = sorted(total_words.items(), key=lambda x: x[1])
            if speakers_sorted[0][1] < speakers_sorted[1][1] * 0.7:
                scores[speakers_sorted[0][0]] += 3

        customer_speaker = max(scores.items(), key=lambda x: x[1])[0]
        return customer_speaker

    def generate_summary(
        self,
        transcript_id: str,
        conversation_formatted: str,
        customer_text: str
    ) -> AISummaryResponse:
        """
        AI 요약 생성 (500px × 3줄, 16px = 최대 90자)

        Args:
            transcript_id: 전사 ID
            conversation_formatted: 포맷된 대화
            customer_text: 고객 발화 전체

        Returns:
            AISummaryResponse 객체
        """
        # 프롬프트 준비
        variables = {
            "conversation": conversation_formatted,
            "customer_text": customer_text
        }

        prompt = get_prompt("call_analysis/summary.md", variables)
        system_prompt = get_prompt("common/system.md")

        # OpenAI API 호출
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )

        # JSON 파싱
        content = response.choices[0].message.content
        content = self._extract_json(content)

        try:
            result = json.loads(content.strip())
        except json.JSONDecodeError as e:
            raise ValueError(f"요약 응답 파싱 실패: {e}")

        # 90자 초과 시 자르기
        summary = result.get("summary", "")
        if len(summary) > 90:
            summary = summary[:87] + "..."

        return AISummaryResponse(
            transcript_id=transcript_id,
            summary=summary,
            customer_state=CustomerState(result.get("customer_state", "관심 있음"))
        )

    def generate_feedback(
        self,
        transcript_id: str,
        conversation_formatted: str,
        customer_text: str,
        consultation_type: str,
        script_context: Optional[str] = None
    ) -> ResponseFeedbackResponse:
        """
        응대 피드백 생성 (상담 유형별 3가지 추천)

        Args:
            transcript_id: 전사 ID
            conversation_formatted: 포맷된 대화
            customer_text: 고객 발화 전체
            consultation_type: 상담 유형 (sales/information/complaint)
            script_context: 스크립트 컨텍스트 (선택)

        Returns:
            ResponseFeedbackResponse 객체
        """
        # 프롬프트 준비
        variables = {
            "conversation": conversation_formatted,
            "customer_text": customer_text,
            "consultation_type": consultation_type,
            "script_context": script_context or "없음"
        }

        prompt = get_prompt("call_analysis/feedback.md", variables)

        # 스크립트 컨텍스트가 있으면 추가
        if script_context:
            prompt += f"\n\n---\n\n## 회사 스크립트 참고\n\n{script_context}"

        system_prompt = get_prompt("common/system.md")

        # OpenAI API 호출
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,  # 피드백은 약간 더 창의적으로
            max_tokens=1500
        )

        # JSON 파싱
        content = response.choices[0].message.content
        content = self._extract_json(content)

        try:
            result = json.loads(content.strip())
        except json.JSONDecodeError as e:
            raise ValueError(f"피드백 응답 파싱 실패: {e}")

        # FeedbackItem 리스트 생성
        feedbacks = []
        for fb in result.get("feedbacks", []):
            feedbacks.append(FeedbackItem(
                type=FeedbackType(fb["type"]),
                title=fb["title"],
                content=fb["content"]
            ))

        return ResponseFeedbackResponse(
            transcript_id=transcript_id,
            consultation_type=result.get("consultation_type", consultation_type),
            feedbacks=feedbacks
        )

    def _extract_json(self, content: str) -> str:
        """JSON 블록 추출"""
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        return content


# Global instance
analysis_service = AnalysisService()
