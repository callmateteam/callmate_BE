"""PDF parsing service for extracting sales scripts"""

from typing import Dict, List, Optional
from pathlib import Path
import pdfplumber
import re


class PDFService:
    """Service for parsing and extracting content from PDF scripts"""

    def extract_text_from_pdf(self, file_path: str) -> str:
        """
        Extract all text from PDF file

        Args:
            file_path: Path to PDF file

        Returns:
            Extracted text content
        """
        text_content = []

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_content.append(text)

        return "\n\n".join(text_content)

    def extract_key_phrases(self, text: str) -> List[str]:
        """
        Extract key phrases and recommended scripts from text

        Args:
            text: Full text content

        Returns:
            List of key phrases/scripts
        """
        key_phrases = []

        # Pattern 1: 따옴표 안의 문구 (대화 예시)
        quoted = re.findall(r'["""]([^"""]+)["""]', text)
        key_phrases.extend([q.strip() for q in quoted if len(q) > 10])

        # Pattern 2: 화살표 뒤 문구 (→, ->, ▶)
        arrow_phrases = re.findall(r'[→\->▶]\s*(.+?)(?:\n|$)', text)
        key_phrases.extend([p.strip() for p in arrow_phrases if len(p) > 10])

        # Pattern 3: 번호 + 점 패턴 (1. 멘트, 2. 멘트)
        numbered = re.findall(r'\d+[.)]\s*["""]?([^"""]+)["""]?(?:\n|$)', text)
        key_phrases.extend([n.strip() for n in numbered if len(n) > 10])

        # Pattern 4: "예시:", "멘트:", "스크립트:" 뒤 문구
        labeled = re.findall(r'(?:예시|멘트|스크립트|답변|응대)\s*[:：]\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
        key_phrases.extend([l.strip() for l in labeled if len(l) > 10])

        # 중복 제거 및 정리
        unique_phrases = list(set(key_phrases))

        # 너무 긴 문구 자르기 (200자 제한)
        cleaned = [p[:200] if len(p) > 200 else p for p in unique_phrases]

        return cleaned[:50]  # 최대 50개

    def extract_sections(self, text: str) -> Dict[str, str]:
        """
        Extract sections from script document

        Args:
            text: Full text content

        Returns:
            Dictionary of section name -> content
        """
        sections = {}

        # Common section headers in Korean scripts
        section_patterns = [
            r'(?:^|\n)(인사\s*(?:멘트|스크립트)?)\s*\n([\s\S]*?)(?=\n[가-힣]+\s*(?:멘트|스크립트)?|$)',
            r'(?:^|\n)(상품\s*소개)\s*\n([\s\S]*?)(?=\n[가-힣]+\s*(?:멘트|스크립트)?|$)',
            r'(?:^|\n)(반대\s*처리|이의\s*제기)\s*\n([\s\S]*?)(?=\n[가-힣]+|$)',
            r'(?:^|\n)(가격\s*안내)\s*\n([\s\S]*?)(?=\n[가-힣]+|$)',
            r'(?:^|\n)(마무리|클로징)\s*\n([\s\S]*?)(?=\n[가-힣]+|$)',
            r'(?:^|\n)(FAQ|자주\s*묻는\s*질문)\s*\n([\s\S]*?)(?=\n[가-힣]+|$)',
        ]

        for pattern in section_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                section_name = match[0].strip()
                section_content = match[1].strip()
                if section_content:
                    sections[section_name] = section_content

        return sections

    def parse_script_pdf(self, file_path: str) -> Dict:
        """
        Full parsing of script PDF

        Args:
            file_path: Path to PDF file

        Returns:
            Dictionary containing:
            {
                "full_text": str,
                "key_phrases": List[str],
                "sections": Dict[str, str],
                "word_count": int,
                "page_count": int
            }
        """
        # Extract text
        full_text = self.extract_text_from_pdf(file_path)

        # Extract key phrases
        key_phrases = self.extract_key_phrases(full_text)

        # Extract sections
        sections = self.extract_sections(full_text)

        # Get page count
        with pdfplumber.open(file_path) as pdf:
            page_count = len(pdf.pages)

        return {
            "full_text": full_text,
            "key_phrases": key_phrases,
            "sections": sections,
            "word_count": len(full_text),
            "page_count": page_count
        }

    def generate_prompt_context(self, parsed_pdf: Dict, company_name: str) -> str:
        """
        Generate prompt context from parsed PDF

        Args:
            parsed_pdf: Parsed PDF result
            company_name: Company name

        Returns:
            Context string for prompts
        """
        context_parts = []

        context_parts.append(f"## {company_name} 영업 스크립트 참고 정보\n")

        # Add key phrases
        if parsed_pdf.get("key_phrases"):
            context_parts.append("### 권장 멘트/스크립트")
            for i, phrase in enumerate(parsed_pdf["key_phrases"][:20], 1):
                context_parts.append(f"{i}. {phrase}")
            context_parts.append("")

        # Add sections
        if parsed_pdf.get("sections"):
            context_parts.append("### 상황별 스크립트")
            for section_name, content in parsed_pdf["sections"].items():
                context_parts.append(f"\n#### {section_name}")
                # 너무 길면 축약
                if len(content) > 500:
                    content = content[:500] + "..."
                context_parts.append(content)

        return "\n".join(context_parts)


# Global instance
pdf_service = PDFService()
