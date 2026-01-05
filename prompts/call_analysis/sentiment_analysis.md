# 감정 분석 프롬프트

다음 통화에서 각 화자의 감정을 분석하세요.

## 화자 정보
- **고객**: {{customer_speaker}}
- **상담사**: {{agent_speaker}}

## 고객 발화
{{customer_text}}

## 상담사 발화
{{agent_text}}

## 분석 기준

### 감정 유형
- 긍정: 만족, 기대, 감사, 흥분
- 중립: 평범한 대화, 정보 요청
- 부정: 불만, 걱정, 화남, 실망

### 말투 분석
- 차분함, 급함, 친근함, 방어적, 설득적, 공격적

### 참여도
- 높음: 적극적 질문, 긴 응답
- 보통: 일반적 대화
- 낮음: 짧은 대답, 무관심

## 출력 형식

```json
{
  "customer": {
    "overall_sentiment": "긍정|중립|부정",
    "sentiment_score": 0.7,
    "tone": "차분하고 궁금한 말투",
    "engagement_level": "높음|보통|낮음",
    "key_emotions": ["관심", "기대"]
  },
  "agent": {
    "overall_sentiment": "긍정",
    "sentiment_score": 0.8,
    "tone": "친근하고 전문적인 말투",
    "engagement_level": "높음",
    "key_emotions": ["적극적", "친절함"]
  },
  "customer_state": "관심 있음|고민 중|망설임|만족|불만족|구매 준비됨|관심 없음"
}
```

JSON만 출력하세요.
