"""
Script extractor service for MVP.
Supports two input methods:
1. Form input from frontend (4-step wizard)
2. PDF file upload
"""

from typing import Dict, List, Optional
import re
from app.services.pdf_service import pdf_service
from app.schemas.script import (
    ConsultationType,
    ToneStyle,
    FormScriptRequest,
    InformationDetails,
    SalesDetails,
    ComplaintDetails,
    ToneSettings
)


class ScriptExtractorService:
    """
    MVP용 스크립트 추출 서비스.
    폼 입력 또는 PDF에서 영업 스크립트 정보를 추출합니다.
    """

    def extract_from_form(self, request: FormScriptRequest) -> Dict:
        """
        폼 입력에서 스크립트 정보 추출

        Args:
            request: FormScriptRequest (4단계 폼 데이터)

        Returns:
            추출된 스크립트 정보 딕셔너리
        """
        result = {
            "company_name": request.company_name,
            "consultation_type": request.consultation_type.value,
            "product_name": "",
            "key_features": [],
            "faq": [],
            "pricing_info": [],
            "competitive_advantages": [],
            "objection_responses": [],
            "common_problems": [],
            "compensation_options": [],
            "escalation_criteria": [],
            "tone_style": None,
            "forbidden_phrases": [],
            "required_phrases": [],
            "key_phrases": []
        }

        # 3단계: 유형별 세부 정보
        if request.consultation_type == ConsultationType.INFORMATION:
            if request.information_details:
                details = request.information_details
                result["product_name"] = details.product_name
                result["key_features"] = details.key_features
                result["faq"] = [
                    {"question": qa.question, "answer": qa.answer}
                    for qa in details.faq
                ]

        elif request.consultation_type == ConsultationType.SALES:
            if request.sales_details:
                details = request.sales_details
                result["product_name"] = details.product_name
                result["key_features"] = details.key_features
                result["pricing_info"] = details.pricing_info
                result["competitive_advantages"] = details.competitive_advantages
                result["objection_responses"] = [
                    {"objection": obj.objection, "response": obj.response}
                    for obj in details.objection_responses
                ]

        elif request.consultation_type == ConsultationType.COMPLAINT:
            if request.complaint_details:
                details = request.complaint_details
                result["common_problems"] = [
                    {"problem": ps.problem, "solution": ps.solution}
                    for ps in details.common_problems
                ]
                result["compensation_options"] = details.compensation_options
                result["escalation_criteria"] = details.escalation_criteria

        # 4단계: 톤 & 추가 설정 (선택)
        if request.tone_settings:
            tone = request.tone_settings
            result["tone_style"] = tone.tone_style.value if tone.tone_style else None
            result["forbidden_phrases"] = tone.forbidden_phrases
            result["required_phrases"] = tone.required_phrases
            result["key_phrases"] = tone.key_phrases

        return result

    def extract_from_pdf(self, file_path: str) -> Dict:
        """
        PDF 파일에서 스크립트 정보 추출

        Args:
            file_path: PDF 파일 경로

        Returns:
            추출된 스크립트 정보 딕셔너리
        """
        # 기존 PDF 서비스 활용
        parsed = pdf_service.parse_script_pdf(file_path)

        result = {
            "company_name": "",
            "consultation_type": None,
            "product_name": "",
            "key_features": [],
            "faq": [],
            "pricing_info": [],
            "competitive_advantages": [],
            "objection_responses": [],
            "common_problems": [],
            "compensation_options": [],
            "escalation_criteria": [],
            "tone_style": None,
            "forbidden_phrases": [],
            "required_phrases": [],
            "key_phrases": parsed.get("key_phrases", []),
            "raw_text": parsed.get("full_text", ""),
            "sections": parsed.get("sections", {}),
            "page_count": parsed.get("page_count", 0)
        }

        # 섹션에서 정보 매핑
        sections = parsed.get("sections", {})

        for section_name, content in sections.items():
            section_lower = section_name.lower()
            items = self._extract_list_items(content)

            if any(k in section_lower for k in ["상품", "제품", "서비스", "특장점"]):
                result["key_features"] = items
            elif any(k in section_lower for k in ["faq", "질문"]):
                result["faq"] = self._extract_qa_pairs(content)
            elif any(k in section_lower for k in ["가격", "요금", "혜택"]):
                result["pricing_info"] = items
            elif any(k in section_lower for k in ["경쟁", "비교", "장점"]):
                result["competitive_advantages"] = items
            elif any(k in section_lower for k in ["반대", "이의", "거절"]):
                result["objection_responses"] = self._extract_objection_pairs(content)
            elif any(k in section_lower for k in ["문제", "불만", "클레임"]):
                result["common_problems"] = self._extract_problem_solution_pairs(content)
            elif any(k in section_lower for k in ["보상", "대안"]):
                result["compensation_options"] = items
            elif any(k in section_lower for k in ["에스컬", "상위", "담당자"]):
                result["escalation_criteria"] = items

        return result

    def generate_prompt_context(
        self,
        extracted_data: Dict,
        company_name: Optional[str] = None
    ) -> str:
        """
        추출된 데이터를 AI 프롬프트용 컨텍스트로 변환

        Args:
            extracted_data: extract_from_* 메서드의 결과
            company_name: 회사명 (없으면 추출 데이터에서 사용)

        Returns:
            프롬프트에 주입할 컨텍스트 문자열
        """
        name = company_name or extracted_data.get("company_name", "고객사")
        consultation_type = extracted_data.get("consultation_type")

        # 상담 유형별 라벨
        type_labels = {
            "information": "안내/정보 제공",
            "sales": "판매/유지/설득",
            "complaint": "불만/문제 해결"
        }
        type_label = type_labels.get(consultation_type, "일반 상담")

        context_parts = [
            f"## {name} 스크립트 가이드",
            f"**상담 유형**: {type_label}\n"
        ]

        # 제품/서비스명
        if extracted_data.get("product_name"):
            context_parts.append(f"**제품/서비스**: {extracted_data['product_name']}\n")

        # 주요 특장점
        if extracted_data.get("key_features"):
            context_parts.append("### 주요 특장점")
            for feature in extracted_data["key_features"][:5]:
                context_parts.append(f"- {feature}")
            context_parts.append("")

        # 가격/혜택 정보 (판매용)
        if extracted_data.get("pricing_info"):
            context_parts.append("### 가격/혜택 정보")
            for info in extracted_data["pricing_info"][:5]:
                context_parts.append(f"- {info}")
            context_parts.append("")

        # 경쟁사 대비 장점 (판매용)
        if extracted_data.get("competitive_advantages"):
            context_parts.append("### 경쟁사 대비 장점")
            for adv in extracted_data["competitive_advantages"][:5]:
                context_parts.append(f"- {adv}")
            context_parts.append("")

        # FAQ
        if extracted_data.get("faq"):
            context_parts.append("### FAQ 응대")
            for qa in extracted_data["faq"][:5]:
                if isinstance(qa, dict):
                    context_parts.append(f"Q: {qa.get('question', '')}")
                    context_parts.append(f"A: {qa.get('answer', '')}")
                    context_parts.append("")
            context_parts.append("")

        # 거절 대응 (판매용)
        if extracted_data.get("objection_responses"):
            context_parts.append("### 거절 시 응대")
            for obj in extracted_data["objection_responses"][:5]:
                if isinstance(obj, dict):
                    context_parts.append(f"거절: \"{obj.get('objection', '')}\"")
                    context_parts.append(f"응대: \"{obj.get('response', '')}\"")
                    context_parts.append("")
            context_parts.append("")

        # 문제 해결 (불만용)
        if extracted_data.get("common_problems"):
            context_parts.append("### 문제 해결 가이드")
            for ps in extracted_data["common_problems"][:5]:
                if isinstance(ps, dict):
                    context_parts.append(f"문제: {ps.get('problem', '')}")
                    context_parts.append(f"해결: {ps.get('solution', '')}")
                    context_parts.append("")
            context_parts.append("")

        # 보상 옵션 (불만용)
        if extracted_data.get("compensation_options"):
            context_parts.append("### 보상/대안 제시 가능 범위")
            for opt in extracted_data["compensation_options"][:5]:
                context_parts.append(f"- {opt}")
            context_parts.append("")

        # 에스컬레이션 기준 (불만용)
        if extracted_data.get("escalation_criteria"):
            context_parts.append("### 에스컬레이션 기준")
            for crit in extracted_data["escalation_criteria"][:5]:
                context_parts.append(f"- {crit}")
            context_parts.append("")

        # 톤 설정 (4단계)
        tone_style = extracted_data.get("tone_style")
        if tone_style:
            tone_labels = {
                "formal": "격식체",
                "friendly": "친근체",
                "professional": "전문가 스타일"
            }
            context_parts.append(f"### 말투 스타일: {tone_labels.get(tone_style, tone_style)}\n")

        # 금지 표현
        if extracted_data.get("forbidden_phrases"):
            context_parts.append("### 금지 표현 (사용하지 마세요)")
            for phrase in extracted_data["forbidden_phrases"][:10]:
                context_parts.append(f"- \"{phrase}\"")
            context_parts.append("")

        # 필수 포함 멘트
        if extracted_data.get("required_phrases"):
            context_parts.append("### 필수 포함 멘트")
            for phrase in extracted_data["required_phrases"][:10]:
                context_parts.append(f"- \"{phrase}\"")
            context_parts.append("")

        # 핵심 멘트
        if extracted_data.get("key_phrases"):
            context_parts.append("### 핵심 멘트 (적극 활용)")
            for phrase in extracted_data["key_phrases"][:10]:
                context_parts.append(f"- \"{phrase}\"")

        return "\n".join(context_parts)

    def _extract_list_items(self, text: str) -> List[str]:
        """텍스트에서 리스트 아이템 추출 (-, *, 숫자.)"""
        items = []

        # 마크다운 리스트 패턴
        patterns = [
            r'^[-*]\s+(.+?)$',  # - item, * item
            r'^\d+[.)]\s+(.+?)$',  # 1. item, 1) item
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.MULTILINE)
            for match in matches:
                # 따옴표 제거
                cleaned = match.strip().strip('"').strip("'").strip('"').strip('"')
                if cleaned and len(cleaned) > 2:
                    items.append(cleaned)

        # 리스트가 없으면 따옴표 안의 내용 추출
        if not items:
            items = self._extract_quoted_phrases(text)

        return items

    def _extract_quoted_phrases(self, text: str) -> List[str]:
        """따옴표 안의 문구 추출"""
        phrases = []

        # 다양한 따옴표 패턴
        patterns = [
            r'"([^"]+)"',  # "문구"
            r'"([^"]+)"',  # "문구"
            r"'([^']+)'",  # '문구'
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if len(match) > 5:  # 너무 짧은 건 제외
                    phrases.append(match.strip())

        return list(set(phrases))[:20]  # 중복 제거, 최대 20개

    def _extract_qa_pairs(self, text: str) -> List[Dict[str, str]]:
        """Q&A 형식 추출"""
        qa_pairs = []

        # Q: A: 패턴
        pattern = r'(?:Q|질문|Q\.)\s*[:：]?\s*(.+?)(?:\n|$)\s*(?:A|답변|A\.)\s*[:：]?\s*(.+?)(?:\n\n|\n(?=Q)|$)'
        matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)

        for q, a in matches:
            qa_pairs.append({
                "question": q.strip(),
                "answer": a.strip()
            })

        # ### Q: 헤더 패턴
        header_pattern = r'###\s*Q\s*[:：]?\s*(.+?)$\s*(?:A\s*[:：]?)?\s*(.+?)(?=###|$)'
        header_matches = re.findall(header_pattern, text, re.MULTILINE | re.DOTALL)

        for q, a in header_matches:
            qa_pairs.append({
                "question": q.strip(),
                "answer": a.strip()
            })

        return qa_pairs

    def _extract_objection_pairs(self, text: str) -> List[Dict[str, str]]:
        """거절-응대 쌍 추출"""
        pairs = []

        # 거절: 응대: 패턴
        pattern = r'(?:거절|반대)\s*[:：]\s*(.+?)(?:\n|$)\s*(?:응대|대응)\s*[:：]\s*(.+?)(?:\n\n|\n(?=거절)|$)'
        matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)

        for objection, response in matches:
            pairs.append({
                "objection": objection.strip(),
                "response": response.strip()
            })

        return pairs

    def _extract_problem_solution_pairs(self, text: str) -> List[Dict[str, str]]:
        """문제-해결 쌍 추출"""
        pairs = []

        # 문제: 해결: 패턴
        pattern = r'(?:문제|상황)\s*[:：]\s*(.+?)(?:\n|$)\s*(?:해결|대응|조치)\s*[:：]\s*(.+?)(?:\n\n|\n(?=문제)|$)'
        matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)

        for problem, solution in matches:
            pairs.append({
                "problem": problem.strip(),
                "solution": solution.strip()
            })

        return pairs


# Global instance
script_extractor_service = ScriptExtractorService()
