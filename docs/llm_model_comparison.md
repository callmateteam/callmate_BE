# LLM 모델 비교 분석 (2025년 1월 기준)

## 1. 비용 비교 (1M 토큰당)

| 모델 | Input | Output | 총 비용 예상* |
|------|-------|--------|--------------|
| **GPT-4o** | $5.00 | $15.00 | $10.00/1K 분석 |
| **GPT-4o-mini** | $0.15 | $0.60 | $0.38/1K 분석 |
| **Claude Sonnet 4** | $3.00 | $15.00 | $9.00/1K 분석 |
| **Claude Haiku 3.5** | $1.00 | $5.00 | $3.00/1K 분석 |
| **Gemini 2.5 Pro** | $1.25 | $10.00 | $5.63/1K 분석 |
| **Gemini 2.5 Flash** | $0.15 | $0.60 | $0.38/1K 분석 |

*1회 분석 기준: Input ~1,500 토큰, Output ~1,000 토큰 가정

## 2. 통화 분석 1,000건당 예상 비용

| 모델 | 비용 | 비고 |
|------|------|------|
| GPT-4o | ~$10.00 | 최고 품질 |
| Claude Sonnet 4 | ~$9.00 | 한국어 우수 |
| Gemini 2.5 Pro | ~$5.63 | 가성비 |
| GPT-4o-mini | ~$0.38 | 경량 모델 |
| Gemini Flash | ~$0.38 | 경량 모델 |
| Claude Haiku | ~$3.00 | 중간 품질/비용 |

## 3. 성능 벤치마크 (2025년)

### 일반 추론 능력
| 모델 | LMArena Elo | MMMLU (다국어) |
|------|-------------|----------------|
| Gemini 3 Pro | 1501 | 91.8% |
| Claude Opus 4.5 | 1489 | 90.8% |
| Claude Sonnet 4.5 | 1451 | 89.1% |
| GPT-4o | 1420 | 87.5% |

### 코딩/분석 능력 (SWE-bench)
| 모델 | 점수 |
|------|------|
| Claude Sonnet 4.5 | 77.2% |
| GPT-5 | 74.9% |
| Gemini 3 Pro | 72.8% |

## 4. 한국어 성능 평가

### 한국어 특화 분석
| 항목 | GPT-4o | Claude Sonnet | Gemini Pro |
|------|--------|---------------|------------|
| **한국어 자연스러움** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **존댓말/반말 구분** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **영업 멘트 톤** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **감정 분석 정확도** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **문맥 이해** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

### 한국어 영업 통화 분석 적합성
- **Claude Sonnet**: 한국어 뉘앙스 파악에 강점. "괜찮습니다"가 긍정인지 거절인지 맥락 파악 우수
- **GPT-4o**: 전반적으로 균형 잡힌 성능. JSON 출력 안정성 높음
- **Gemini Pro**: 가성비 좋음. 다만 한국어 존댓말 체계 이해가 약간 부족

## 5. CallMate 서비스 추천 구성

### Option A: 프리미엄 품질 우선
```
추천: Claude Sonnet 4
- 한국어 영업 멘트 생성 품질 최고
- 감정/뉘앙스 분석 정확도 높음
- 비용: ~$9/1K 분석
```

### Option B: 가성비 균형
```
추천: Gemini 2.5 Pro
- 비용 대비 성능 우수
- MMMLU 다국어 점수 최상위
- 비용: ~$5.63/1K 분석 (40% 절감)
```

### Option C: 대량 처리 (무료 티어용)
```
추천: GPT-4o-mini 또는 Gemini Flash
- 저렴한 비용으로 대량 처리
- 기본적인 분석 품질 확보
- 비용: ~$0.38/1K 분석 (95% 절감)
```

### Option D: 하이브리드 전략 (추천)
```
무료 사용자: Gemini Flash ($0.38/1K)
- 기본 분석 + 업종별 기본 스크립트

SaaS Basic: Gemini Pro ($5.63/1K)
- 회사 PDF 기반 맞춤 분석

SaaS Pro/Enterprise: Claude Sonnet ($9/1K)
- 최고 품질 한국어 멘트 생성
```

## 6. 응답 속도 비교

| 모델 | 평균 응답 시간 | TTFT* |
|------|---------------|-------|
| GPT-4o | 15-25초 | ~0.5초 |
| Claude Sonnet | 12-20초 | ~0.4초 |
| Gemini Pro | 10-18초 | ~0.3초 |
| GPT-4o-mini | 3-8초 | ~0.2초 |
| Gemini Flash | 2-5초 | ~0.1초 |

*TTFT: Time To First Token (첫 토큰 응답 시간)

## 7. API 안정성 및 특이사항

### OpenAI (GPT)
- ✅ JSON 모드 지원 (안정적)
- ✅ Function calling 성숙
- ⚠️ Rate limit 주의 필요
- ✅ 한국 리전 지원

### Anthropic (Claude)
- ✅ 프롬프트 캐싱 할인
- ✅ 긴 컨텍스트 (200K 토큰)
- ✅ 한국어 뉘앙스 우수
- ⚠️ JSON 출력 가끔 불안정

### Google (Gemini)
- ✅ 가장 저렴
- ✅ 빠른 응답 속도
- ✅ GCP 연동 할인
- ⚠️ 한국어 존댓말 약점

## 8. 최종 추천

### CallMate MVP용 추천
```
1순위: Claude Sonnet 4
- 이유: 한국어 영업 멘트 품질 최우선
- 비용: 월 1,000건 분석 시 ~$9

2순위: GPT-4o
- 이유: JSON 출력 안정성, 범용성
- 비용: 월 1,000건 분석 시 ~$10

3순위: Gemini Pro (가성비)
- 이유: 비용 절감 40%, 괜찮은 품질
- 비용: 월 1,000건 분석 시 ~$5.63
```

### 스케일업 시
```
무료 티어: Gemini Flash
SaaS 티어: Claude Sonnet
```

## 9. 구현 권장사항

### 멀티 모델 전략
```python
# config.py
LLM_CONFIG = {
    "free_tier": {
        "model": "gemini-2.5-flash",
        "provider": "google"
    },
    "basic_tier": {
        "model": "gemini-2.5-pro",
        "provider": "google"
    },
    "pro_tier": {
        "model": "claude-sonnet-4",
        "provider": "anthropic"
    },
    "enterprise_tier": {
        "model": "claude-sonnet-4",
        "provider": "anthropic",
        "fallback": "gpt-4o"
    }
}
```

### Fallback 전략
- Primary 실패 시 Secondary로 자동 전환
- 예: Claude → GPT-4o → Gemini Pro

---

## 참고 자료

- [LLM API Pricing Comparison 2025](https://intuitionlabs.ai/articles/llm-api-pricing-comparison-2025)
- [AI Model Benchmarks 2025](https://lmcouncil.ai/benchmarks)
- [LLM Leaderboard](https://www.vellum.ai/llm-leaderboard)
- [Artificial Analysis](https://artificialanalysis.ai/leaderboards/models)
