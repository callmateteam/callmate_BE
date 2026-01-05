"""Example responses for API documentation"""

# Transcript examples
TRANSCRIPT_EXAMPLE = {
    "transcript_id": "abc123-def456-ghi789",
    "full_text": "안녕하세요 네 안녕하세요 보험 상담 받고 싶은데요 네 어떤 보험을 찾으세요 가족 건강 보험 알아보고 있어요",
    "utterances": [
        {
            "speaker": "A",
            "text": "안녕하세요",
            "start": 0,
            "end": 1500,
            "confidence": 0.95
        },
        {
            "speaker": "B",
            "text": "네, 안녕하세요",
            "start": 1600,
            "end": 3200,
            "confidence": 0.92
        },
        {
            "speaker": "A",
            "text": "보험 상담 받고 싶은데요",
            "start": 3300,
            "end": 5800,
            "confidence": 0.94
        }
    ],
    "speakers": ["A", "B"],
    "duration": 125000
}

SPEAKER_SEPARATED_EXAMPLE = {
    "transcript_id": "abc123-def456-ghi789",
    "speakers": ["A", "B"],
    "duration": 125000,
    "speaker_segments": [
        {
            "speaker": "A",
            "total_utterances": 5,
            "total_duration": 35000,
            "utterances": [
                {
                    "speaker": "A",
                    "text": "안녕하세요",
                    "start": 0,
                    "end": 1500,
                    "confidence": 0.95
                },
                {
                    "speaker": "A",
                    "text": "보험 상담 받고 싶은데요",
                    "start": 3300,
                    "end": 5800,
                    "confidence": 0.94
                }
            ],
            "full_text": "안녕하세요 보험 상담 받고 싶은데요 가족 건강 보험 알아보고 있어요 가격이 부담되지 않을까요 알겠습니다 감사합니다"
        },
        {
            "speaker": "B",
            "total_utterances": 4,
            "total_duration": 90000,
            "utterances": [
                {
                    "speaker": "B",
                    "text": "네, 안녕하세요",
                    "start": 1600,
                    "end": 3200,
                    "confidence": 0.92
                }
            ],
            "full_text": "네 안녕하세요 어떤 보험을 찾으세요 가족 건강 보험 상품이 여러 가지 있습니다 월 3만원부터 시작하는 상품도 있어요"
        }
    ],
    "conversation_formatted": "A: 안녕하세요\nB: 네, 안녕하세요\nA: 보험 상담 받고 싶은데요\nB: 어떤 보험을 찾으세요\nA: 가족 건강 보험 알아보고 있어요"
}

# Analysis examples
COMPREHENSIVE_ANALYSIS_EXAMPLE = {
    "transcript_id": "abc123-def456-ghi789",
    "speaker_sentiments": [
        {
            "speaker": "A",
            "overall_sentiment": "긍정",
            "sentiment_score": 0.7,
            "tone_analysis": "차분하고 궁금한 말투",
            "engagement_level": "높음",
            "key_emotions": ["관심", "기대", "호기심"]
        },
        {
            "speaker": "B",
            "overall_sentiment": "긍정",
            "sentiment_score": 0.8,
            "tone_analysis": "친근하고 전문적인 말투",
            "engagement_level": "높음",
            "key_emotions": ["자신감", "적극적", "친절함"]
        }
    ],
    "customer_state": "관심 있음",
    "conversation_summary": {
        "overview": "고객이 가족 건강보험 상담을 요청했으며, 월 보험료와 보장범위에 관심을 보였습니다. 상담사가 여러 옵션을 제시하여 긍정적으로 검토 중입니다.",
        "main_topics": ["건강보험", "가격", "보장범위", "가족 보험"],
        "key_questions": [
            "월 보험료가 얼마인가요?",
            "가족 모두 보장되나요?",
            "암 보장도 포함되어 있나요?"
        ],
        "key_answers": [
            "월 3만원부터 시작하는 상품이 있습니다",
            "가족 전체를 보장하는 플랜이 있습니다",
            "암 진단비 3천만원까지 보장됩니다"
        ],
        "outcome": "견적서 발송 예정, 3일 내 후속 전화 예정"
    },
    "customer_need": {
        "primary_reason": "가족 건강보험 가입을 희망함",
        "specific_needs": ["가족 전체 보장", "합리적인 가격", "암 보장 포함"],
        "pain_points": ["현재 건강보험이 없음", "가격이 부담될까 걱정", "보장 범위가 헷갈림"],
        "urgency_level": "보통"
    },
    "call_flow": {
        "conversation_turns": [
            {
                "turn_number": 1,
                "speaker": "A",
                "message": "안녕하세요, 건강보험 상담 받고 싶습니다",
                "customer_reaction": None,
                "key_point": "상담 목적 전달"
            },
            {
                "turn_number": 2,
                "speaker": "B",
                "message": "네, 어떤 보험을 찾으세요?",
                "customer_reaction": "구체적인 니즈 설명 시작",
                "key_point": "니즈 파악 질문"
            },
            {
                "turn_number": 3,
                "speaker": "A",
                "message": "가족 모두 보장되는 상품이요",
                "customer_reaction": None,
                "key_point": "핵심 니즈 표현"
            }
        ],
        "customer_journey": [
            "처음: 조심스럽게 문의",
            "중간: 가격 질문하며 관심 표현",
            "끝: 긍정적으로 검토 의향 표시"
        ],
        "critical_moments": [
            "가격 질문 시점 - 고객의 핵심 관심사 드러남",
            "혜택 설명 후 - 고객 태도가 긍정적으로 변화",
            "견적서 발송 제안 - 다음 단계로 진행 동의"
        ]
    },
    "next_action": "견적서 이메일로 발송 후, 3일 내 후속 전화로 추가 질문 답변",
    "recommended_replies": [
        "안녕하세요, 지난번 말씀하신 가족 건강보험 견적서 보내드렸습니다. 혹시 추가로 궁금하신 점 있으신가요?",
        "말씀하신 암 보장 관련해서, 추가로 암 진단비를 3천만원에서 5천만원으로 올릴 수 있는 옵션도 있습니다.",
        "가격 부담 관련해서 말씀하셨는데, 단계적으로 보장을 추가하는 방법도 가능합니다. 자세히 설명드릴까요?"
    ],
    "analysis_timestamp": "2026-01-03T12:34:56.789Z",
    "confidence_score": 0.85
}

QUICK_ANALYSIS_EXAMPLE = {
    "transcript_id": "abc123-def456-ghi789",
    "summary": "고객이 가족 건강보험 상담을 요청하여 긍정적으로 검토 중",
    "customer_state": "관심 있음",
    "overall_sentiment": "긍정",
    "key_needs": ["가족 전체 보장", "합리적인 가격", "암 보장 포함"],
    "next_action": "견적서 발송 후 3일 내 후속 전화"
}
