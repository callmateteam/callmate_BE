"""
Script extractor service for MVP.
Supports two input methods:
1. Markdown text from frontend
2. PDF file upload
"""

from typing import Dict, List, Optional
from enum import Enum
import re
from app.services.pdf_service import pdf_service


class ScriptInputType(str, Enum):
    """스크립트 입력 방식"""
    MARKDOWN = "markdown"
    PDF = "pdf"


class ScriptExtractorService:
    """
    MVP용 스크립트 추출 서비스.
    마크다운 텍스트 또는 PDF에서 영업 스크립트 정보를 추출합니다.
    """

    def extract_from_markdown(self, markdown_text: str) -> Dict:
        """
        마크다운 텍스트에서 스크립트 정보 추출

        프론트엔드에서 다음 형식으로 전달:
        ```
        # 회사명

        ## 인사말
        - "안녕하세요, OO입니다"

        ## 상품 소개
        - 특장점 1
        - 특장점 2

        ## 자주 묻는 질문
        ### Q: 가격이 얼마인가요?
        A: 월 9,900원입니다.

        ## 클로징 멘트
        - "감사합니다. 좋은 하루 되세요"
        ```

        Args:
            markdown_text: 마크다운 형식의 스크립트 텍스트

        Returns:
            추출된 스크립트 정보 딕셔너리
        """
        result = {
            "company_name": "",
            "greeting": [],
            "product_info": [],
            "faq": [],
            "closing": [],
            "key_phrases": [],
            "objection_handling": [],
            "raw_text": markdown_text
        }

        # 회사명 추출 (# 제목)
        company_match = re.search(r'^#\s+(.+?)$', markdown_text, re.MULTILINE)
        if company_match:
            result["company_name"] = company_match.group(1).strip()

        # 섹션별 추출
        sections = self._parse_markdown_sections(markdown_text)

        # 인사말 섹션
        greeting_keys = ["인사말", "인사", "오프닝", "opening"]
        for key in greeting_keys:
            if key in sections:
                result["greeting"] = self._extract_list_items(sections[key])
                break

        # 상품 소개 섹션
        product_keys = ["상품 소개", "상품소개", "제품 소개", "서비스 소개", "특장점"]
        for key in product_keys:
            if key in sections:
                result["product_info"] = self._extract_list_items(sections[key])
                break

        # FAQ 섹션
        faq_keys = ["자주 묻는 질문", "faq", "q&a", "질문과 답변"]
        for key in faq_keys:
            if key in sections:
                result["faq"] = self._extract_qa_pairs(sections[key])
                break

        # 클로징 섹션
        closing_keys = ["클로징", "마무리", "closing", "엔딩"]
        for key in closing_keys:
            if key in sections:
                result["closing"] = self._extract_list_items(sections[key])
                break

        # 반대 처리 섹션
        objection_keys = ["반대 처리", "이의 제기", "거절 응대", "objection"]
        for key in objection_keys:
            if key in sections:
                result["objection_handling"] = self._extract_list_items(sections[key])
                break

        # 전체에서 핵심 멘트 추출 (따옴표 안의 내용)
        result["key_phrases"] = self._extract_quoted_phrases(markdown_text)

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
            "greeting": [],
            "product_info": [],
            "faq": [],
            "closing": [],
            "key_phrases": parsed.get("key_phrases", []),
            "objection_handling": [],
            "raw_text": parsed.get("full_text", ""),
            "sections": parsed.get("sections", {}),
            "page_count": parsed.get("page_count", 0)
        }

        # 섹션에서 정보 매핑
        sections = parsed.get("sections", {})

        for section_name, content in sections.items():
            section_lower = section_name.lower()
            items = self._extract_list_items(content)

            if any(k in section_lower for k in ["인사", "오프닝"]):
                result["greeting"] = items
            elif any(k in section_lower for k in ["상품", "제품", "서비스"]):
                result["product_info"] = items
            elif any(k in section_lower for k in ["faq", "질문"]):
                result["faq"] = self._extract_qa_pairs(content)
            elif any(k in section_lower for k in ["마무리", "클로징"]):
                result["closing"] = items
            elif any(k in section_lower for k in ["반대", "이의", "거절"]):
                result["objection_handling"] = items

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

        context_parts = [f"## {name} 영업 스크립트 가이드\n"]

        # 인사말
        if extracted_data.get("greeting"):
            context_parts.append("### 인사말 예시")
            for phrase in extracted_data["greeting"][:5]:
                context_parts.append(f"- {phrase}")
            context_parts.append("")

        # 상품 정보
        if extracted_data.get("product_info"):
            context_parts.append("### 상품/서비스 특장점")
            for info in extracted_data["product_info"][:10]:
                context_parts.append(f"- {info}")
            context_parts.append("")

        # FAQ
        if extracted_data.get("faq"):
            context_parts.append("### 자주 묻는 질문 응대")
            for qa in extracted_data["faq"][:5]:
                if isinstance(qa, dict):
                    context_parts.append(f"Q: {qa.get('question', '')}")
                    context_parts.append(f"A: {qa.get('answer', '')}")
                else:
                    context_parts.append(f"- {qa}")
            context_parts.append("")

        # 반대 처리
        if extracted_data.get("objection_handling"):
            context_parts.append("### 거절/반대 시 응대")
            for obj in extracted_data["objection_handling"][:5]:
                context_parts.append(f"- {obj}")
            context_parts.append("")

        # 클로징
        if extracted_data.get("closing"):
            context_parts.append("### 마무리 멘트")
            for phrase in extracted_data["closing"][:3]:
                context_parts.append(f"- {phrase}")
            context_parts.append("")

        # 핵심 멘트
        if extracted_data.get("key_phrases"):
            context_parts.append("### 권장 핵심 멘트")
            for phrase in extracted_data["key_phrases"][:10]:
                context_parts.append(f"- \"{phrase}\"")

        return "\n".join(context_parts)

    def _parse_markdown_sections(self, markdown_text: str) -> Dict[str, str]:
        """마크다운에서 ## 섹션 파싱"""
        sections = {}

        # ## 헤더로 분할
        pattern = r'^##\s+(.+?)$'
        matches = list(re.finditer(pattern, markdown_text, re.MULTILINE))

        for i, match in enumerate(matches):
            section_name = match.group(1).strip().lower()
            start = match.end()

            # 다음 섹션까지 또는 끝까지
            if i + 1 < len(matches):
                end = matches[i + 1].start()
            else:
                end = len(markdown_text)

            content = markdown_text[start:end].strip()
            sections[section_name] = content

        return sections

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


# Global instance
script_extractor_service = ScriptExtractorService()
