"""API endpoints for comprehensive call analysis"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from app.schemas.analysis import ComprehensiveAnalysis, QuickAnalysis, SentimentType
from app.services.multi_model_analysis_service import multi_model_analysis_service
from app.services.company_prompt_service import company_prompt_service
from app.api.v1.transcripts import transcripts_store
from app.api.v1.examples import COMPREHENSIVE_ANALYSIS_EXAMPLE, QUICK_ANALYSIS_EXAMPLE

router = APIRouter()

# In-memory storage for analysis results
analysis_store = {}


@router.get(
    "/{transcript_id}/comprehensive",
    response_model=ComprehensiveAnalysis,
    summary="종합 통화 분석",
    description="""
    **화자별 감정 분석 + 대화 흐름 + 고객 니즈 + 추천 멘트**를 제공하는 종합 분석 API입니다.

    ## 분석 항목

    ### 1. 화자별 감정 분석
    - 전반적 감정 (긍정/부정/중립 등)
    - 감정 점수 (-1 ~ 1)
    - 말투 분석 (차분함, 급함, 설득적 등)
    - 참여도 (높음/보통/낮음)

    ### 2. 고객 상태
    - 관심 있음, 고민 중, 망설임, 구매 준비됨 등

    ### 3. 대화 요약
    - 전체 요약 (2-3문장)
    - 주요 주제, 질문/답변
    - 대화 결과

    ### 4. 고객 니즈
    - **전화한 사유**: 왜 전화했는지
    - **요구사항**: 무엇을 원하는지
    - **고민거리**: 어떤 문제가 있는지
    - **긴급도**: 얼마나 급한지

    ### 5. 통화 흐름
    - 대화 턴별 분석
    - 고객 반응 변화 (처음→중간→끝)
    - 중요한 순간/전환점

    ### 6. 추천 액션
    - 다음 취해야 할 행동
    - 후속 연락 시 사용할 멘트 3-5개

    **처리 시간:** 5분 통화 기준 약 15-25초

    **비용:** 요청당 약 $0.03-0.05 (GPT-4)

    ## SaaS 모드 (회사별 맞춤 분석)

    `company_id` 파라미터를 제공하면 해당 회사의 영업 스크립트를 기반으로
    맞춤형 추천 멘트를 생성합니다.

    - **무료 사용자**: company_id 없이 호출 → 일반 분석
    - **SaaS 고객**: company_id 포함 → 회사 스크립트 기반 분석
    """,
    responses={
        200: {
            "description": "분석 성공",
            "content": {
                "application/json": {
                    "example": COMPREHENSIVE_ANALYSIS_EXAMPLE
                }
            }
        },
        404: {
            "description": "전사 결과를 찾을 수 없음",
            "content": {
                "application/json": {
                    "example": {"detail": "Transcript not found"}
                }
            }
        },
        500: {
            "description": "분석 실패",
            "content": {
                "application/json": {
                    "example": {"detail": "Analysis failed: [error message]"}
                }
            }
        }
    }
)
async def get_comprehensive_analysis(
    transcript_id: str,
    company_id: Optional[str] = Query(
        None,
        description="회사 ID (SaaS 모드). 제공 시 해당 회사의 스크립트 기반 맞춤 분석"
    ),
    industry: Optional[str] = Query(
        None,
        description="업종 (무료 사용자용). insurance, real_estate, b2b, telecom, finance, healthcare, retail, other"
    )
):
    """
    종합 통화 분석 조회

    화자별 감정 분석, 대화 흐름, 고객 니즈, 추천 액션 등 모든 분석 결과를 제공합니다.

    - **transcript_id**: 전사 ID
    - **company_id**: (선택) 회사 ID - SaaS 고객용 맞춤 분석
    - **industry**: (선택) 업종 - 무료 사용자도 업종별 맞춤 추천 가능

    Returns:
        - 화자별 감정 분석 (감정 유형, 점수, 말투, 참여도)
        - 고객 상태 (관심 있음, 고민 중, 망설임 등)
        - 대화 요약 (전체 요약, 주요 주제, 질문/답변)
        - 고객 니즈 (전화 사유, 요구사항, 고민거리, 긴급도)
        - 통화 흐름 (턴별 분석, 고객 반응 변화, 중요한 순간)
        - 추천 액션 및 멘트

    Example response:
        ```json
        {
          "transcript_id": "abc123",
          "speaker_sentiments": [
            {
              "speaker": "A",
              "overall_sentiment": "긍정",
              "sentiment_score": 0.7,
              "tone_analysis": "차분하고 궁금한 말투",
              "engagement_level": "높음",
              "key_emotions": ["관심", "기대"]
            }
          ],
          "customer_state": "관심 있음",
          "conversation_summary": {
            "overview": "고객이 가족 건강보험 상담을 요청...",
            "main_topics": ["건강보험", "가격", "보장범위"],
            "key_questions": ["월 보험료가 얼마인가요?"],
            "key_answers": ["월 3만원부터 시작합니다"],
            "outcome": "견적서 발송 예정"
          },
          "customer_need": {
            "primary_reason": "가족 건강보험 가입 희망",
            "specific_needs": ["가족 전체 보장", "합리적 가격"],
            "pain_points": ["현재 보험 없음", "가격 부담"],
            "urgency_level": "보통"
          },
          "call_flow": {
            "conversation_turns": [...],
            "customer_journey": ["처음: 조심스러움", "중간: 관심 표현"],
            "critical_moments": ["가격 질문 시점", "혜택 설명 후"]
          },
          "next_action": "견적서 발송 및 3일 내 후속 전화",
          "recommended_replies": [...]
        }
        ```
    """
    # Validate company_id if provided
    if company_id:
        company = company_prompt_service.get_company(company_id)
        if not company:
            raise HTTPException(
                status_code=404,
                detail=f"Company {company_id} not found"
            )

    # Check if already analyzed (with same company_id and industry)
    cache_key = f"{transcript_id}:{company_id or 'general'}:{industry or 'none'}"
    if cache_key in analysis_store:
        return analysis_store[cache_key]

    # Get transcript data
    if transcript_id not in transcripts_store:
        raise HTTPException(status_code=404, detail="Transcript not found")

    stored = transcripts_store[transcript_id]
    result = stored["result"]

    # Get speaker-separated data
    from app.services.stt_service import stt_service

    speaker_segments = []
    for speaker in result["speakers"]:
        speaker_utterances = stt_service.get_speaker_segments(
            result["utterances"],
            speaker
        )
        full_text = " ".join(u["text"] for u in speaker_utterances)

        speaker_segments.append({
            "speaker": speaker,
            "full_text": full_text,
            "utterances": speaker_utterances
        })

    # Format conversation
    conversation_formatted = stt_service.format_conversation(
        result["utterances"],
        format_type="simple"
    )

    # Determine plan from company if provided
    plan = "free"
    if company_id:
        company = company_prompt_service.get_company(company_id)
        if company:
            plan = company.get("config", {}).get("plan", "free")

    # Perform comprehensive analysis using multi-model service
    try:
        analysis = multi_model_analysis_service.analyze_call_comprehensive(
            transcript_id=transcript_id,
            conversation_formatted=conversation_formatted,
            speaker_segments=speaker_segments,
            utterances=result["utterances"],
            plan=plan,
            company_id=company_id,
            industry=industry
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )

    # Store analysis result with cache key
    analysis_store[cache_key] = analysis

    return analysis


@router.get("/{transcript_id}/quick", response_model=QuickAnalysis)
async def get_quick_analysis(
    transcript_id: str,
    company_id: Optional[str] = Query(
        None,
        description="회사 ID (SaaS 모드)"
    ),
    industry: Optional[str] = Query(
        None,
        description="업종 (무료 사용자용)"
    )
):
    """
    간단한 통화 분석 조회 (빠른 조회용)

    - **transcript_id**: 전사 ID
    - **company_id**: (선택) 회사 ID - SaaS 고객용 맞춤 분석
    - **industry**: (선택) 업종 - 무료 사용자용

    Returns:
        한 줄 요약, 고객 상태, 전반적 감정, 핵심 니즈, 다음 액션
    """
    # Get comprehensive analysis (will use cache if exists)
    comprehensive = await get_comprehensive_analysis(transcript_id, company_id, industry)

    # Extract quick info
    return QuickAnalysis(
        transcript_id=transcript_id,
        summary=comprehensive.conversation_summary.overview,
        customer_state=comprehensive.customer_state,
        overall_sentiment=comprehensive.speaker_sentiments[0].overall_sentiment if comprehensive.speaker_sentiments else SentimentType.NEUTRAL,
        key_needs=comprehensive.customer_need.specific_needs,
        next_action=comprehensive.next_action
    )


@router.delete("/{transcript_id}/analysis")
async def delete_analysis(transcript_id: str):
    """
    분석 결과 삭제 (재분석 시 사용)

    - **transcript_id**: 전사 ID
    """
    if transcript_id not in analysis_store:
        raise HTTPException(status_code=404, detail="Analysis not found")

    del analysis_store[transcript_id]

    return {"message": "Analysis deleted successfully"}


@router.post("/{transcript_id}/reanalyze", response_model=ComprehensiveAnalysis)
async def reanalyze_call(
    transcript_id: str,
    company_id: Optional[str] = Query(
        None,
        description="회사 ID (SaaS 모드)"
    ),
    industry: Optional[str] = Query(
        None,
        description="업종 (무료 사용자용)"
    )
):
    """
    통화 재분석 (캐시 무시하고 새로 분석)

    - **transcript_id**: 전사 ID
    - **company_id**: (선택) 회사 ID - SaaS 고객용 맞춤 분석
    - **industry**: (선택) 업종 - 무료 사용자용
    """
    # Delete existing analysis for this company/industry
    cache_key = f"{transcript_id}:{company_id or 'general'}:{industry or 'none'}"
    if cache_key in analysis_store:
        del analysis_store[cache_key]

    # Perform new analysis
    return await get_comprehensive_analysis(transcript_id, company_id, industry)
